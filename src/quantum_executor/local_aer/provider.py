"""Local Qiskit Aer Provider Class compatible with qBraid."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from qbraid._caching import cached_method  # type: ignore
from qbraid.programs import ProgramSpec  # type: ignore
from qbraid.runtime.profile import TargetProfile  # type: ignore
from qbraid.runtime.provider import QuantumProvider  # type: ignore
from qiskit import QuantumCircuit  # type: ignore
from qiskit_aer import AerSimulator  # type: ignore
from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2  # type: ignore

from quantum_executor.local_aer.device import LocalAERBackend

if TYPE_CHECKING:  # pragma: no cover
    from qiskit.providers import BackendV2  # type: ignore


class LocalAERProvider(QuantumProvider):  # type: ignore
    """Provider class for local AerSimulator backends.

    This class provides methods for retrieving simulated quantum devices,
    including both noiseless and noisy simulators.
    """

    def _build_runtime_profile(self, backend: BackendV2, program_spec: ProgramSpec | None = None) -> TargetProfile:
        """Build a runtime profile from a backend.

        Parameters
        ----------
        backend : AerSimulator
            The Qiskit AerSimulator backend instance.
        program_spec : ProgramSpec, optional
            A specification for the quantum program, defaulting to a circuit.

        Returns
        -------
        TargetProfile
            A target profile with device details for runtime execution.

        """
        program_spec = program_spec or ProgramSpec(QuantumCircuit)

        return TargetProfile(
            device_id=backend.name,
            simulator=True,
            num_qubits=backend.num_qubits,
            program_spec=program_spec,
            provider_name="Local_AER",
        )

    @cached_method  # type: ignore
    def get_devices(self) -> list[LocalAERBackend]:
        """Retrieve a list of available quantum backends.

        This method combines a noiseless AerSimulator with additional backends
        provided by a fake IBM provider, returning a list of LocalAERBackend objects.

        Returns
        -------
        list[qbraid.runtime.ibm.QiskitBackend]
            A list of quantum backend instances.

        """
        # Create a list of backends: the primary noiseless AerSimulator, plus others.
        backends: Sequence[BackendV2] = [AerSimulator(), *FakeProviderForBackendV2().backends()]
        program_spec = ProgramSpec(QuantumCircuit)

        return [
            LocalAERBackend(
                profile=self._build_runtime_profile(backend, program_spec=program_spec),
                backend=backend,
            )
            for backend in backends
        ]

    @cached_method  # type: ignore
    def get_device(self, device_id: str) -> LocalAERBackend:
        """Retrieve a specific quantum backend by its device identifier.

        This method returns a LocalAERBackend instance corresponding to the specified device_id.
        It supports both the default noiseless simulator and a noisy simulator generated based on
        a noise strength encoded in the device_id.

        Parameters
        ----------
        device_id : str
            The identifier of the desired quantum backend.

        Returns
        -------
        qbraid.runtime.ibm.QiskitBackend
            The corresponding quantum backend.

        Raises
        ------
        ValueError
            If the device is not found among local AerSimulator backends.

        """
        if device_id == "aer_simulator":
            backend = AerSimulator()
        else:
            try:
                backend = FakeProviderForBackendV2().backend(device_id)
            except Exception as e:
                raise ValueError(f"Device '{device_id}' not found in local AerSimulator backends.") from e

        program_spec = ProgramSpec(QuantumCircuit)
        return LocalAERBackend(
            profile=self._build_runtime_profile(backend, program_spec=program_spec),
            backend=backend,
        )

    def __hash__(self) -> int:
        """Return a hash value for the LocalAERProvider instance.

        This hash is used for caching and comparison purposes.

        Returns
        -------
        int
            The hash value of the LocalAERProvider instance.

        """
        if not hasattr(self, "_hash"):
            object.__setattr__(self, "_hash", hash("Local_AER"))
        return int(self._hash)  # pylint: disable=no-member #type: ignore[unused-ignore]
