##############################################################################
# test_local_aer.py
##############################################################################
"""Test suite for LocalAERProvider and LocalAERBackend classes.

This test file covers:
- Retrieving devices (both noiseless and fake).
- Submitting circuits with valid and invalid parameters.
- Checking device statuses.
- Transforming circuits.
- Ensuring provider hashing behavior.
- String representations.
"""

from __future__ import annotations

import pytest  # type: ignore
from qiskit import QuantumCircuit  # type: ignore

from quantum_executor.local_aer.device import LocalAERBackend  # type: ignore[import-not-found,unused-ignore]
from quantum_executor.local_aer.provider import LocalAERProvider  # type: ignore[import-not-found,unused-ignore]

# ------------------------------------------------------------------------
# TESTS FOR LocalAERProvider
# ------------------------------------------------------------------------


def test_provider_hash() -> None:
    """Test that the LocalAERProvider's hash is consistent."""
    provider1 = LocalAERProvider()
    provider2 = LocalAERProvider()
    assert hash(provider1) == hash(provider2), "LocalAERProvider instances should have the same hash."


def test_provider_get_devices() -> None:
    """Test that get_devices returns multiple LocalAERBackend instances."""
    provider = LocalAERProvider()
    devices = provider.get_devices()
    assert len(devices) > 1, "Expected at least one real AerSimulator and some fake backends."
    # Check the presence of AerSimulator
    aer_sim_devices = [
        dev
        for dev in devices
        if dev._backend.name == "aer_simulator"  # pylint: disable=protected-access
    ]
    assert len(aer_sim_devices) == 1, "There should be exactly one default AerSimulator device."


def test_provider_get_device_aer_simulator() -> None:
    """Test that get_device('aer_simulator') returns a LocalAERBackend wrapping AerSimulator."""
    provider = LocalAERProvider()
    device = provider.get_device("aer_simulator")
    assert isinstance(device, LocalAERBackend), "Expected a LocalAERBackend instance."
    assert (
        device._backend.name == "aer_simulator"  # pylint: disable=protected-access
    ), "Expected the AerSimulator backend."


@pytest.mark.parametrize("fake_backend_name", ["fake_torino", "fake_oslo"])  # type: ignore
def test_provider_get_device_fake_backends(fake_backend_name: str) -> None:
    """Test that we can retrieve known fake backends (fake_torino, fake_oslo).

    Parameters
    ----------
    fake_backend_name : str
        The name of the fake backend to test.

    """
    provider = LocalAERProvider()
    device = provider.get_device(fake_backend_name)
    assert isinstance(device, LocalAERBackend), "Expected a LocalAERBackend instance."
    assert (
        device._backend.name == fake_backend_name  # pylint: disable=protected-access
    ), f"Expected the '{fake_backend_name}' backend."


def test_provider_get_device_invalid() -> None:
    """Test that requesting a non-existent device raises ValueError."""
    provider = LocalAERProvider()
    with pytest.raises(ValueError) as excinfo:
        provider.get_device("non_existent_device")
    assert "not found in local AerSimulator backends" in str(excinfo.value), (
        "Expected ValueError when requesting unknown device."
    )


# ------------------------------------------------------------------------
# TESTS FOR LocalAERBackend
# ------------------------------------------------------------------------


def test_backend_status_online() -> None:
    """Test that the LocalAERBackend always returns DeviceStatus.ONLINE."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")
    status = backend.status()
    assert status.name == "ONLINE", "Local simulators should always be ONLINE."


def test_backend_string_representation() -> None:
    """Test the string representation of the LocalAERBackend."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")
    string_repr = str(backend)
    assert "LocalAERBackend('aer_simulator')" in string_repr, (
        "String representation should contain the class name and backend name."
    )


def test_backend_transform_aer_simulator() -> None:
    """Test that we can transform a circuit using the AerSimulator backend."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(2)
    qc.h(0)

    transformed_circuit = backend.transform(qc)
    assert isinstance(transformed_circuit, QuantumCircuit), "Expected a QuantumCircuit result."
    assert transformed_circuit == qc, "Expected the circuit to remain identical with aer_simulator transform."


def test_backend_transform_fake_backend() -> None:
    """Test that we can transform a circuit using a fake backend.

    The transformation should be different from the original circuit.
    """
    provider = LocalAERProvider()
    backend = provider.get_device("fake_torino")

    qc = QuantumCircuit(2)
    qc.h(0)

    transformed_circuit = backend.transform(qc)
    assert isinstance(transformed_circuit, QuantumCircuit), "Expected a QuantumCircuit result."
    assert transformed_circuit != qc, "Expected the circuit to be transformed with a fake backend."


def test_backend_submit_single_circuit_valid() -> None:
    """Test submitting a single circuit with valid shots and seed."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(2)
    qc.h(0)
    qc.measure_all()

    job = backend.submit(qc, shots=100, seed=42)
    assert job is not None, "Expected a QiskitJob instance."
    assert job.device is backend, "Job should reference the current backend."
    assert job._job_id is not None, "Job ID should not be None."  # pylint: disable=protected-access


def test_backend_submit_multiple_circuits_valid() -> None:
    """Test submitting multiple circuits with valid shots and seed."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc1 = QuantumCircuit(2)
    qc1.h(0)
    qc1.measure_all()

    qc2 = QuantumCircuit(3)
    qc2.x(1)
    qc2.measure_all()

    job = backend.submit([qc1, qc2], shots=200, seed=0)
    assert job is not None, "Expected a QiskitJob instance for multiple circuits."
    assert job.device is backend, "Job should reference the current backend."
    assert job._job_id is not None, "Job ID should not be None."  # pylint: disable=protected-access


def test_backend_submit_missing_shots() -> None:
    """Test that submitting circuits without specifying shots raises ValueError."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(1)
    qc.x(0)
    qc.measure_all()

    with pytest.raises(ValueError) as excinfo:
        backend.submit(qc)
    assert "shots must be specified" in str(excinfo.value), "Expected ValueError when no shots are specified."


def test_backend_submit_zero_shots() -> None:
    """Test that submitting circuits with zero shots raises ValueError."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(1)
    qc.x(0)
    qc.measure_all()

    with pytest.raises(ValueError) as excinfo:
        backend.submit(qc, shots=0)
    assert "shots must be a positive integer" in str(excinfo.value), "Expected ValueError when shots == 0."


def test_backend_submit_negative_shots() -> None:
    """Test that submitting circuits with negative shots raises ValueError."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(1)
    qc.x(0)
    qc.measure_all()

    with pytest.raises(ValueError) as excinfo:
        backend.submit(qc, shots=-5)
    assert "shots must be a positive integer" in str(excinfo.value), "Expected ValueError when shots < 0."


def test_backend_submit_negative_seed() -> None:
    """Test that providing a negative seed raises ValueError."""
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    qc = QuantumCircuit(1)
    qc.x(0)
    qc.measure_all()

    with pytest.raises(ValueError) as excinfo:
        backend.submit(qc, shots=100, seed=-1)
    assert "seed must be a non-negative integer" in str(excinfo.value), "Expected ValueError when seed < 0."


def test_backend_submit_invalid_run_input() -> None:
    """Test that providing invalid run input raises ValueError.

    (E.g., a list containing a non-circuit object).
    """
    provider = LocalAERProvider()
    backend = provider.get_device("aer_simulator")

    # Invalid input: list with a str
    invalid_input = [QuantumCircuit(1), "NotACircuit"]

    with pytest.raises(ValueError) as excinfo:
        backend.submit(invalid_input, shots=10)
    assert "Invalid run_input" in str(excinfo.value), "Expected ValueError for invalid run_input."
