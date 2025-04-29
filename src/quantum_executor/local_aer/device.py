"""Local Qiskit Aer Backend Class compatible with qBraid.

This module provides a wrapper for the Qiskit AerSimulator backend, allowing
for the execution of quantum circuits on a local simulator.
It includes methods for transforming circuits, submitting jobs, and checking device status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from qbraid.programs import load_program  # type: ignore
from qbraid.runtime.device import QuantumDevice  # type: ignore
from qbraid.runtime.enums import DeviceStatus  # type: ignore
from qbraid.runtime.ibm import QiskitJob  # type: ignore
from qbraid.runtime.options import RuntimeOptions  # type: ignore
from qiskit import QuantumCircuit  # type: ignore
from qiskit.transpiler import PassManager  # type: ignore
from qiskit_aer import AerSimulator  # type: ignore
from qiskit_ibm_runtime import SamplerV2 as Sampler  # type: ignore
from qiskit_ibm_runtime.options import SamplerOptions  # type: ignore
from qiskit_ibm_runtime.options import SimulatorOptions

if TYPE_CHECKING:  # pragma: no cover
    from qbraid.runtime import TargetProfile  # type: ignore
    from qiskit.providers import BackendV2  # type: ignore


class LocalAERBackend(QuantumDevice):  # type: ignore
    """Wrapper class for local AerSimulator backend objects.

    This class adapts a Qiskit AerSimulator to the QuantumDevice interface, enabling
    circuit transformation and submission on a local simulation backend.

    Parameters
    ----------
    profile : TargetProfile
        The target profile configuration.
    backend : AerSimulator, optional
        An optional instance of an AerSimulator. If not provided, a new instance is created.

    """

    def __init__(
        self,
        profile: TargetProfile,
        backend: BackendV2 | None = None,
    ) -> None:
        """Initialize a LocalAERBackend instance.

        Parameters
        ----------
        profile : TargetProfile
            The target profile configuration.
        backend : AerSimulator, optional
            An optional instance of an AerSimulator. If not provided, a new instance is created.

        """
        options = RuntimeOptions(pass_manager=None)
        options.set_validator("pass_manager", lambda x: x is None or isinstance(x, PassManager))
        super().__init__(profile=profile, options=options)

        self._backend: BackendV2 = backend or AerSimulator()

    def __str__(self) -> str:
        """Return the string representation of the backend.

        Returns
        -------
        str
            A string containing the class name and backend name.

        """
        return f"{self.__class__.__name__}('{self._backend.name}')"

    def status(self) -> DeviceStatus:
        """Get the current status of the device.

        Returns
        -------
        DeviceStatus
            A status object representing the current state of the device.
            Local simulators are always considered online.

        """
        return DeviceStatus.ONLINE

    def transform(self, run_input: QuantumCircuit) -> QuantumCircuit:
        """Transpile a quantum circuit for execution on this device.

        Parameters
        ----------
        run_input : QuantumCircuit
            The quantum circuit to transpile.

        Returns
        -------
        QuantumCircuit
            The transpiled quantum circuit.

        """
        program = load_program(run_input)
        program.transform(self)
        return program.program

    def submit(
        self,
        run_input: QuantumCircuit | list[QuantumCircuit],
        *_args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> QiskitJob:
        """Submit one or more quantum circuits for execution on the backend.

        This method runs the circuit(s) on the Qiskit backend via the SamplerV2.run method.
        It handles simulator options, including an optional seed to ensure reproducibility.

        It also accepts additional keyword arguments for the number of shots and seed.

        Parameters
        ----------
        run_input : QuantumCircuit or list[QuantumCircuit]
            A single quantum circuit or a list of quantum circuits to run on the device.
        *_args : tuple
            Additional positional arguments, ignored in this implementation.
        **kwargs : dict
            Additional keyword arguments to pass to the Sampler.run method.
            - shots (int): The number of shots for the simulation.
            - seed (int): The seed for the random number generator.

        Returns
        -------
        QiskitJob
            A job-like object representing the submitted task.

        Raises
        ------
        ValueError
            If the run_input is neither a Qiskit QuantumCircuit nor a list of QuantumCircuits.

        """
        # Extract additional keyword arguments.
        shots: int | None = kwargs.pop("shots", None)
        seed: int | None = kwargs.pop("seed", None)
        if shots is None:
            raise ValueError("shots must be specified in the keyword arguments.")
        if shots <= 0:
            raise ValueError("shots must be a positive integer.")
        if seed is not None and seed < 0:
            raise ValueError("seed must be a non-negative integer.")

        # Configure simulator options based on the provided seed.
        options = SamplerOptions()
        if seed is not None:
            options.simulator = SimulatorOptions(seed_simulator=seed)  # type: ignore[unused-ignore]

        # Ensure run_input is in list format for uniform processing.
        if isinstance(run_input, list) and all(isinstance(circuit, QuantumCircuit) for circuit in run_input):
            circuits = run_input
        elif isinstance(run_input, QuantumCircuit):
            circuits = [run_input]
        else:
            raise ValueError("Invalid run_input: expected a QuantumCircuit or a list of QuantumCircuits.")

        sampler = Sampler(mode=self._backend, options=options)
        job = sampler.run(circuits, shots=shots)

        return QiskitJob(job.job_id(), job=job, device=self)
