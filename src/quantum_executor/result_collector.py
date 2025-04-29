"""Implement thread-safe collectors for aggregating job results."""

import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Any
from typing import Optional

if TYPE_CHECKING:  # pragma: no cover
    from quantum_executor.dispatch import Job
    from quantum_executor.job_runner import ResultData


class ReadWriteLock:
    """Simple reentrant read-write lock implementation.

    This lock allows multiple readers to acquire the lock concurrently,
    while a writer gains exclusive access. It is built atop a reentrant
    mutex so that the same thread may re-acquire read or write locks.

    Locking semantics:
        - Multiple threads can hold the read lock concurrently.
        - Only one thread can hold the write lock, and only when no readers hold the lock.
        - A thread that holds the write lock can re-acquire read or write.
    Usage:
        with lock.read():
            # read-critical section
        with lock.write():
            # write-critical section
    """

    def __init__(self) -> None:
        """Initialize the ReadWriteLock."""
        self._read_ready = threading.Condition(threading.RLock())
        self._readers: int = 0
        self._writers_waiting: int = 0
        self._writer_active: bool = False

    def acquire_read(self) -> None:
        """Acquire the lock for reading.

        Multiple threads can hold the read lock concurrently.
        """
        with self._read_ready:
            while self._writers_waiting > 0 or self._writer_active:
                self._read_ready.wait()
            self._readers += 1

    def release_read(self) -> None:
        """Release the read lock.

        Decrement the reader count and notify waiting writers if no readers remain.
        """
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self) -> None:
        """Acquire the lock for writing.

        Blocks until all readers have released the lock.
        """
        with self._read_ready:
            self._writers_waiting += 1
            while self._readers > 0 or self._writer_active:
                self._read_ready.wait()
            self._writers_waiting -= 1
            self._writer_active = True

    def release_write(self) -> None:
        """Release the write lock."""
        with self._read_ready:
            self._writer_active = False
            self._read_ready.notify_all()

    @contextmanager
    def read(self) -> Generator[None, None, None]:
        """Acquire the lock for reading."""
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write(self) -> Generator[None, None, None]:
        """Acquire the lock for writing."""
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()


class JobResult:
    """Container for holding the outcome of a job execution.

    Parameters
    ----------
    job : Job
        The job instance that was executed.
    data : ResultData, optional
        The result data produced by the job execution, by default None.

    """

    def __init__(self, job: "Job", data: Optional["ResultData"] = None) -> None:
        """Initialize a JobResult instance.

        Parameters
        ----------
        job : Job
            The job instance.
        data : ResultData, optional
            The result data, by default None.

        """
        self.job: Job = job
        self.data: Any = data
        self.complete: bool = data is not None

    def __repr__(self) -> str:
        """Represent the JobResult as a string.

        Returns
        -------
        str
            A string representation indicating the job, its completion status, and result data.

        """
        status = "Complete" if self.complete else "Pending"
        return f"JobResult(job={self.job}, status={status}, data={self.data})"

    def get_data(self) -> Optional["ResultData"]:
        """Retrieve the result data if the job execution is complete.

        Returns
        -------
        ResultData or None
            The result data if complete, otherwise None.

        """
        return self.data if self.complete else None


class ResultCollector:
    """Thread-safe collector for job results stored in a nested dictionary.

    The structure mirrors the dispatch structure and allows storing and retrieving
    job results across multiple providers and backends.

    Locking:
        A single ReadWriteLock (_lock) protects nested_results, _job_mapping,
        and _complete/_completion_event.
        Always acquire ResultCollector._lock before acquiring any external locks.

    Attributes
    ----------
    nested_results : Dict[str, Dict[str, List[JobResult]]]
        A nested dictionary mapping provider names to backends and their job results.

    """

    def __init__(self) -> None:
        """Initialize the ResultCollector.

        Sets up the nested results dictionary, job mapping, locks, and a completion event.
        """
        self.nested_results: dict[str, dict[str, list[JobResult]]] = {}
        # Map each Job → its placeholder JobResult, so we can update it directly.
        self._job_mapping: dict[Job, JobResult] = {}
        self._lock = ReadWriteLock()
        self._complete: bool = False
        self._completion_event = threading.Event()

    def __repr__(self) -> str:
        """Represent the ResultCollector as a string.

        Returns
        -------
        str
            A summary including the number of complete and total job results and the collector state.

        """
        with self._lock.read():
            if self.complete:
                return f"ResultCollector({self.nested_results})"
            total_jobs = sum(
                len(job_list) for backends in self.nested_results.values() for job_list in backends.values()
            )
            complete_jobs = sum(
                int(job.complete)
                for backends in self.nested_results.values()
                for job_list in backends.values()
                for job in job_list
            )
            return f"ResultCollector(complete_jobs={complete_jobs}, total_jobs={total_jobs}, complete={self.complete})"

    def register_job_mapping(self, job: "Job", provider_name: str, backend_name: str) -> None:
        """Register a job and create a placeholder JobResult in the collector.

        Parameters
        ----------
        job : Job
            The job instance.
        provider_name : str
            The provider name.
        backend_name : str
            The backend name.

        """
        with self._lock.write():
            if provider_name not in self.nested_results:
                self.nested_results[provider_name] = {}
            if backend_name not in self.nested_results[provider_name]:
                self.nested_results[provider_name][backend_name] = []
            placeholder = JobResult(job, data=None)
            self.nested_results[provider_name][backend_name].append(placeholder)
            self._job_mapping[job] = placeholder

    def store_result(self, job: "Job", result_data: "ResultData") -> None:
        """Update a job's placeholder with the actual result data.

        After storing the result, the method checks if all registered jobs are complete
        and, if so, signals completion to waiting threads.

        Parameters
        ----------
        job : Job
            The job whose result is to be stored.
        result_data : ResultData
            The result data produced by the job execution.

        Raises
        ------
        ValueError
            If the job has not been registered.

        """
        with self._lock.write():
            if job not in self._job_mapping:
                raise ValueError("Job mapping not found. Call register_job_mapping first.")
            job_result = self._job_mapping[job]
            job_result.data = result_data
            job_result.complete = True

            # Automatically mark the collector complete if all jobs are done.
            if self._all_jobs_complete():
                self._complete = True
                self._completion_event.set()

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Block until all registered job results are complete or until the timeout expires.

        This method waits on an internal event that is set when the collector is complete.

        Parameters
        ----------
        timeout : float or None, optional
            Maximum number of seconds to wait. If None, waits indefinitely.

        Returns
        -------
        bool
            True if the collector completed within the timeout, False otherwise.

        """
        return self._completion_event.wait(timeout)

    def get_results(self) -> dict[str, dict[str, list[Optional["ResultData"]]]]:
        """Retrieve a shallow copy of the nested job results.

        Returns
        -------
        Dict[str, Dict[str, List[Optional[ResultData]]]]
            A copy of the job results nested dictionary with each job's data.

        """
        with self._lock.read():
            return {
                provider: {backend: [job.get_data() for job in job_list] for backend, job_list in backends.items()}
                for provider, backends in self.nested_results.items()
            }

    def get_jobs(self) -> dict[str, dict[str, list[JobResult]]]:
        """Retrieve a shallow copy of the registered job results.

        Returns
        -------
        Dict[str, Dict[str, List[JobResult]]]
            A copy of the nested dictionary of JobResult objects.

        """
        with self._lock.read():
            return {
                provider: {backend: job_list[:] for backend, job_list in backends.items()}
                for provider, backends in self.nested_results.items()
            }

    @property
    def complete(self) -> bool:
        """Check whether all registered job results are complete.

        Returns
        -------
        bool
            True if the collector is marked complete or if all job results are complete; False otherwise.

        """
        with self._lock.read():
            return self._complete or self._all_jobs_complete()

    @complete.setter
    def complete(self, value: bool) -> None:
        """Manually set the overall completion status of the collector.

        Setting this to True signals waiting threads.

        Parameters
        ----------
        value : bool
            The new completion status.

        """
        with self._lock.write():
            self._complete = value
            if value:
                self._completion_event.set()
            else:
                self._completion_event.clear()

    def _all_jobs_complete(self) -> bool:
        """Check if all registered jobs have been completed.

        Returns
        -------
        bool
            True if every registered JobResult is complete; otherwise False.

        """
        # No lock here; callers must hold at least a read lock.
        for backends in self.nested_results.values():
            for job_list in backends.values():
                for job_result in job_list:
                    if not job_result.complete:
                        return False
        return True


class MergedResultCollector:
    """A specialized ResultCollector that handles merging of results.

    This class is used to collect and merge results from multiple jobs.

    Locking:
        When both the inner ResultCollector._lock and this
        MergedResultCollector._lock must be held, always acquire
        ResultCollector._lock first, then MergedResultCollector._lock.

    Parameters
    ----------
    results : ResultCollector
        A ResultCollector instance containing job results.

    """

    def __init__(self, results: ResultCollector) -> None:
        """Initialize the MergedResultCollector.

        Parameters
        ----------
        results : ResultCollector
            A ResultCollector instance containing job results.

        """
        self.results: ResultCollector = results
        self.merged_results: Any | None = None
        self._merged_results_ready_event = threading.Event()
        self.initial_policy_data: dict[str, Any] | None = None
        self.final_policy_data: dict[str, Any] | None = None
        self._lock = ReadWriteLock()

    @property
    def complete(self) -> bool:
        """Check if the collector has completed processing.

        Returns
        -------
        bool
            True if all jobs are complete, False otherwise.

        """
        return self.results.complete

    def wait_for_completion(self, timeout: float | None = None) -> bool:
        """Block until all registered job results are complete or until the timeout expires.

        Parameters
        ----------
        timeout : float or None, optional
            Maximum number of seconds to wait. If None, waits indefinitely.

        Returns
        -------
        bool
            True if the collector completed within the timeout, False otherwise.

        """
        start_time = time.time()
        if self.results.wait_for_completion(timeout=timeout):
            remaining_time = timeout - (time.time() - start_time) if timeout else None
            return self._merged_results_ready_event.wait(timeout=remaining_time)
        return False

    def get_jobs(self) -> dict[str, dict[str, list[JobResult]]]:
        """Return the jobs stored in the collector.

        Returns
        -------
        Dict[str, Dict[str, List[JobResult]]]
            A dictionary mapping provider names to backend names and their respective job results.

        """
        return self.results.get_jobs()

    def get_results(self) -> dict[str, dict[str, list[Optional["ResultData"]]]]:
        """Return the results stored in the collector.

        Returns
        -------
        Dict[str, Dict[str, List[Optional[ResultData]]]]
            A dictionary mapping provider names to backend names and their respective result data.

        """
        return self.results.get_results()

    def set_merged_results(
        self,
        merged_results: Any,  # noqa: ANN401
        initial_policy_data: dict[str, Any],
        final_policy_data: dict[str, Any],
    ) -> None:
        """Update the merged results, initial policy data, and final policy data.

        Parameters
        ----------
        merged_results : Any
            The merged results to store.
        initial_policy_data : Dict[str, Any]
            The initial policy data to store.
        final_policy_data : Dict[str, Any]
            The final policy data to store.

        """
        with self._lock.write():
            self.merged_results = merged_results
            self.initial_policy_data = initial_policy_data
            self.final_policy_data = final_policy_data
            self._merged_results_ready_event.set()

    def get_merged_results(self) -> Any:  # noqa: ANN401
        """Return the merged results.

        Returns
        -------
        Any
            The merged results.

        """
        with self._lock.read():
            return self.merged_results

    def get_initial_policy_data(self) -> dict[str, Any] | None:
        """Return the initial policy data.

        Returns
        -------
        Optional[Dict[str, Any]]
            The initial policy data.

        """
        with self._lock.read():
            return self.initial_policy_data

    def get_final_policy_data(self) -> dict[str, Any] | None:
        """Return the final policy data.

        Returns
        -------
        Optional[Dict[str, Any]]
            The final policy data.

        """
        with self._lock.read():
            return self.final_policy_data

    def __repr__(self) -> str:
        """Return a string representation of the MergedResultCollector.

        Returns
        -------
        str
            A summary including the merged results and initial/final policy data.

        """
        with self._lock.read():
            if self.merged_results is not None:
                return (
                    f"MergedResultCollector(merged_results={self.merged_results}, "
                    f"initial_policy_data={self.initial_policy_data}, "
                    f"final_policy_data={self.final_policy_data})"
                )
            # Snapshot jobs under proper locking via the inner collector
            jobs = self.results.get_jobs()
            total_jobs = sum(len(job_list) for backends in jobs.values() for job_list in backends.values())
            complete_jobs = sum(
                int(job.complete) for backends in jobs.values() for job_list in backends.values() for job in job_list
            )
            return (
                f"MergedResultCollector(complete_jobs={complete_jobs}, "
                f"total_jobs={total_jobs}, complete={self.complete})"
            )
