"""Module with helper function to execute a single quantum job."""

import logging
from typing import Any

from qbraid import transpile  # type: ignore

from quantum_executor.virtual_provider import VirtualProvider

ResultData = dict[str, Any]


def run_single_job_static(  # pylint: disable=too-many-positional-arguments too-many-arguments  too-many-locals
    provider_name: str,
    backend_name: str,
    circuit: Any,  # noqa: ANN401
    shots: int,
    config: dict[str, Any] | None = None,
    providers_info: dict[str, dict[str, Any]] | None = None,
    providers: list[str] | None = None,
    raise_exc: bool = True,
    virtual_provider: VirtualProvider | None = None,
) -> "ResultData":
    """Worker function to execute a single quantum job.

    Parameters
    ----------
    provider_name : str
        Name of the quantum provider (e.g., "local_aer", "ionq", etc.).
    backend_name : str
        The specific backend name for the provider.
    circuit : Any
        The quantum circuit to be executed.
    shots : int
        Number of execution shots.
    config : Dict[str, Any], optional
        Additional job configuration parameters.
    providers_info : Dict[str, Dict[str, Any]], optional
        A dictionary mapping provider names to their respective API keys or configuration.
        The keys should be the provider names (e.g., "ionq", "azure") and the values
        should be dictionaries containing the necessary parameters for initialization.
        For example:
        {
            "ionq": {"api_key": "your-api-key-here"},
            "azure": {"subscription_id": "your-subscription-id", "resource_group": "your-resource-group"},
            "braket": {"aws_access_key_id": "your-access-key-id",
                        "aws_secret_access_key": "your-secret-access-key"},
            "local_aer": {},
            "qbraid": {"api_key": "your-api-key-here"},
        }
    providers : Dict[str, str], optional
        A list of provider names to include in the initialization.
        Only the providers with names in this list will be initialized.
        Defaults to None, meaning all providers are included.
    raise_exc : bool, optional
        If True, exceptions are re-raised; otherwise, they are logged and returned as error data.
    virtual_provider : Optional[VirtualProvider], optional
        An optional instance of VirtualProvider. If None, a new one is created.

    Returns
    -------
    ResultData
        The result counts from the job execution or an error dictionary.

    """
    logger = logging.getLogger(__name__)
    logger.debug(
        "[ChildProcess] Running job on %s/%s with %s shots.",
        provider_name,
        backend_name,
        shots,
    )

    if virtual_provider is None:
        local_virtual_provider = VirtualProvider(providers_info=providers_info, include=providers, raise_exc=raise_exc)
    else:
        local_virtual_provider = virtual_provider

    provider_backend = local_virtual_provider.get_backend(provider_name, backend_name, online=True)

    qc = circuit
    # Transpile step if needed (e.g., for IonQ)
    if provider_name.lower() == "ionq":
        qc = transpile(qc, "qiskit").remove_final_measurements(inplace=False)

    if config is None:
        config = {}

    logger.debug("[ChildProcess] Configuration: %s", config)
    try:
        job = provider_backend.run(qc, shots=shots, **config)

        if isinstance(job, list):
            job = job[0]

        result = job.result()
        return result.data.get_counts()  # type: ignore
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "[ChildProcess] Error while executing job on %s/%s: %s",
            provider_name,
            backend_name,
            exc,
        )
        if raise_exc:
            raise
        return {"error": str(exc)}
