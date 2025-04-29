"""Module containing classes representing quantum jobs and their dispatch."""

import uuid
from collections.abc import Generator
from copy import deepcopy
from typing import Any

DispatchDict = dict[str, dict[str, list[dict[str, Any]]]]  # provider -> backend -> list of job-info dicts


class Job:  # pylint: disable=too-few-public-methods
    """Represent a single quantum execution request.

    Parameters
    ----------
    circuit : Any
        The quantum circuit to be executed.
    shots : int
        The number of measurement shots.
    configuration : Optional[Dict[str, Any]]
        Additional configuration options (e.g., noise models). Defaults to None.

    """

    __slots__ = ("circuit", "configuration", "id", "shots")

    def __init__(self, circuit: Any, shots: int, configuration: dict[str, Any] | None = None) -> None:  # noqa: ANN401
        """Initialize a Job.

        Parameters
        ----------
        circuit : Any
            The quantum circuit to be executed.
        shots : int
            The number of measurement shots.
        configuration : Optional[Dict[str, Any]]
            Additional configuration options (e.g., noise models). Defaults to None.

        """
        self.id: str = str(uuid.uuid4())
        self.circuit: Any = circuit
        self.shots: int = shots
        self.configuration: dict[str, Any] = configuration or {}

    def __repr__(self) -> str:
        """Return a string representation of the Job.

        Returns
        -------
        str
            Includes job ID, circuit type, shots, and configuration.

        """
        return (
            f"Job(id={self.id}, circuit_type={type(self.circuit).__name__}, "
            f"shots={self.shots}, config={self.configuration})"
        )


class Dispatch:
    """Hold a collection of jobs grouped by provider and backend.

    Parameters
    ----------
    initial_jobs : Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]]
        Nested dictionary mapping provider names to backend names to lists of job-info dicts.
        Each job-info dict must have keys:
        - 'circuit': Any
        - 'shots': int
        - optionally 'configuration': Dict[str, Any]
        - optionally 'id': str

    Methods
    -------
    add_job(provider_name, backend_name, circuits, shots, config=None)
        Add one or multiple jobs for the specified provider/backend.
    all_jobs()
        Iterator over all (provider, backend, job) tuples.
    items()
        Returns the nested dictionary representation of the dispatch.

    """

    def __init__(
        self,
        initial_jobs: DispatchDict | None = None,
    ) -> None:
        """Initialize a Dispatch, optionally from a nested jobs dictionary.

        Parameters
        ----------
        initial_jobs : Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]]
            Nested dict mapping provider -> backend -> list of job-info dicts.
            Each job-info dict must contain 'circuit', 'shots', and optionally
            'configuration' and 'id'. Defaults to None.

        """
        # Internal nested dictionary: provider -> backend -> list of Job instances.
        self._jobs: dict[str, dict[str, list[Job]]] = {}

        if initial_jobs:
            for provider, backends in initial_jobs.items():
                for backend, jobs in backends.items():
                    for job_info in jobs:
                        circuit = job_info["circuit"]
                        shots = job_info["shots"]
                        config = deepcopy(job_info.get("configuration", {}))
                        job = Job(circuit, shots, config)
                        if "id" in job_info:
                            job.id = job_info["id"]
                        self._jobs.setdefault(provider, {}).setdefault(backend, []).append(job)

    def __repr__(self) -> str:
        """Return a string representation of the Dispatch.

        Returns
        -------
        str
            Shows the structure of jobs per provider/backend.

        """
        return f"Dispatch({self._jobs})"

    def add_job(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        self,
        provider_name: str,
        backend_name: str,
        circuits: Any | list[Any],  # noqa: ANN401
        shots: int | list[int],
        config: dict[str, Any] | None = None,
    ) -> None:
        """Add one or more jobs to the dispatch.

        If `circuits` is a list, each element is paired with either a single integer `shots` (repeated)
        or with an element from a list of shot counts.

        Parameters
        ----------
        provider_name : str
            Name of the quantum provider.
        backend_name : str
            Name of the backend.
        circuits : Union[Any, List[Any]]
            A single circuit or a list of circuits.
        shots : Union[int, List[int]]
            A single shot count or a list of shot counts corresponding to `circuits`.
        config : Optional[Dict[str, Any]], optional
            Additional configuration for the job(s), by default None.

        Raises
        ------
        ValueError
            If the lengths of circuits and shots lists do not match as required.

        """
        if provider_name not in self._jobs:
            self._jobs[provider_name] = {}
        if backend_name not in self._jobs[provider_name]:
            self._jobs[provider_name][backend_name] = []

        if isinstance(circuits, list):
            if isinstance(shots, list):
                if len(circuits) != len(shots):
                    raise ValueError(
                        f"Length of circuits list must match length of shots list: {len(circuits)} != {len(shots)}"
                    )
                for ckt, s in zip(circuits, shots, strict=False):
                    self._jobs[provider_name][backend_name].append(Job(ckt, s, deepcopy(config)))
            else:
                for ckt in circuits:
                    self._jobs[provider_name][backend_name].append(Job(ckt, shots, deepcopy(config)))
        else:
            if isinstance(shots, list):
                if len(shots) != 1:
                    raise ValueError(
                        "If circuits is a single circuit, shots must be a single integer or a list of length 1."
                    )
                self._jobs[provider_name][backend_name].append(Job(circuits, shots[0], deepcopy(config)))
            else:
                self._jobs[provider_name][backend_name].append(Job(circuits, shots, deepcopy(config)))

    def all_jobs(self) -> Generator[tuple[str, str, Job], None, None]:
        """Return terator over all jobs in the dispatch.

        Yields
        ------
        Tuple[str, str, Job]
            A tuple with (provider_name, backend_name, job).

        """
        for provider_name, backends in self._jobs.items():
            for backend_name, job_list in backends.items():
                for job in job_list:
                    yield provider_name, backend_name, job

    def items(self) -> dict[str, dict[str, list[Job]]]:
        """Return a shallow copy of the internal jobs dictionary.

        Returns
        -------
        Dict[str, Dict[str, List[Job]]]
            The nested dictionary mapping provider to backend to list of jobs.

        """
        return self._jobs.copy()
