"""A basic uniform policy that equally distribute the shot count of a quantum circuit on every backend."""

from typing import Any

from quantum_executor.dispatch import Dispatch
from quantum_executor.virtual_provider import VirtualProvider


def split(
    circuit: Any,  # noqa: ANN401
    shots: int,
    backends: dict[str, list[str]],
    _virtual_provider: VirtualProvider,  # pylint: disable=unused-argument
    policy_data: Any | None = None,  # noqa: ANN401
) -> tuple[Dispatch, Any]:
    """Uniformly distribute the same circuit and shot count to every backend.

    Parameters
    ----------
    circuit : Any
        The quantum circuit to run.
    shots : int
        Number of shots for the circuit.
    backends : Dict[str, List[str]]
        A dictionary mapping provider names to lists of backend names.
    _virtual_provider : VirtualProvider
        An instance of VirtualProvider; not used in this policy.
    policy_data : Any, optional
        Additional data carried along; not used in this policy.

    Returns
    -------
    Tuple[Dispatch, Any]
        A tuple containing the Dispatch object with registered jobs and the unchanged blob.

    """
    bakends_num = sum(len(backends_ls) for backends_ls in backends.values())
    backends_shots = [shots // bakends_num] * bakends_num
    # If shots is not divisible by the number of backends, distribute the remainder
    remainder = shots % bakends_num
    for i in range(remainder):
        backends_shots[i] += 1

    dispatch = Dispatch()
    for provider_name, backends_ls in backends.items():
        for backend_name, backend_shots in zip(backends_ls, backends_shots, strict=False):
            dispatch.add_job(
                provider_name=provider_name,
                backend_name=backend_name,
                circuits=circuit.copy(),
                shots=backend_shots,
            )
    return dispatch, policy_data
