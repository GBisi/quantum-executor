##############################################################################
# test_quantum_executor.py
##############################################################################
"""Test suite for the QuantumExecutor, Dispatch, Job, MergedResultCollector, and ResultCollector classes."""

import logging
import multiprocessing
from collections.abc import Callable
from typing import Any

import pytest  # type: ignore
from qiskit import QuantumCircuit  # type: ignore

from quantum_executor.dispatch import Dispatch  # type: ignore[import-not-found,unused-ignore]
from quantum_executor.dispatch import Job  # type: ignore[import,unused-ignore]
from quantum_executor.executor import QuantumExecutor  # type: ignore[import-not-found,unused-ignore]
from quantum_executor.result_collector import JobResult  # type: ignore[import-not-found,unused-ignore]
from quantum_executor.result_collector import MergedResultCollector  # type: ignore[import,unused-ignore]
from quantum_executor.result_collector import ResultCollector  # type: ignore[import,unused-ignore]

# Force the use of the 'spawn' start method for multiprocessing to ensure compatibility
# with operating systems like Windows and macOS, where 'spawn' is the default.
# This helps make test behavior consistent across platforms and avoids issues related
# to process serialization in CI environments like GitHub Actions.
multiprocessing.set_start_method("spawn", force=True)


def test_job_creation_and_repr() -> None:
    """Test creation of a Job object and its string representation."""
    circuit = QuantumCircuit(2, 2)
    shots = 100
    config = {"noise": "basic"}

    job = Job(circuit, shots, config)
    assert job.circuit == circuit, "Job circuit should match the input circuit."
    assert job.shots == shots, "Job shots should match the specified value."
    assert job.configuration == config, "Job configuration should match."
    assert "Job(id=" in repr(job), "Job __repr__ should contain the job ID."
    assert "shots=100" in repr(job), "Job __repr__ should contain the shot count."


def test_dispatch_add_single_job() -> None:
    """Test adding a single job to a Dispatch instance."""
    dispatch = Dispatch()
    circuit = QuantumCircuit(1, 1)
    dispatch.add_job("local_aer", "aer_simulator", circuit, 10)

    all_jobs = list(dispatch.all_jobs())
    assert len(all_jobs) == 1, "Expected exactly one job in the dispatch."
    (provider_name, backend_name, job) = all_jobs[0]
    assert provider_name == "local_aer"
    assert backend_name == "aer_simulator"
    assert job.shots == 10, "Shots should be 10."


def test_dispatch_add_multiple_jobs_list() -> None:
    """Test adding multiple circuits and multiple shot values in a single call."""
    dispatch = Dispatch()
    circuits = [QuantumCircuit(1, 1), QuantumCircuit(2, 2)]
    shots = [10, 20]
    dispatch.add_job("local_aer", "aer_simulator", circuits, shots)

    all_jobs = list(dispatch.all_jobs())
    assert len(all_jobs) == 2, "Expected two jobs in the dispatch."
    job1 = all_jobs[0][2]
    job2 = all_jobs[1][2]
    assert job1.shots == 10, "First job shots should be 10."
    assert job2.shots == 20, "Second job shots should be 20."


def test_dispatch_add_jobs_list_shots_int() -> None:
    """Test adding multiple circuits when shots is provided as a single integer."""
    dispatch = Dispatch()
    circuits = [QuantumCircuit(1, 1), QuantumCircuit(2, 2)]
    shots = 50  # single int for all circuits
    dispatch.add_job("prov", "backend", circuits, shots, config={"key": "value"})
    items = dispatch.items()
    jobs = items["prov"]["backend"]
    assert len(jobs) == 2, "Expected two jobs from the list of circuits with constant shot count."
    for job in jobs:
        assert job.shots == 50, "Each job should have 50 shots."
        assert job.configuration == {"key": "value"}, "Configuration should be preserved."


def test_dispatch_add_job_single_circuit_shots_list() -> None:
    """Test adding a single circuit when shots is provided as a list of length 1."""
    dispatch = Dispatch()
    circuit = QuantumCircuit(1, 1)
    shots = [30]
    dispatch.add_job("prov", "backend", circuit, shots, config={"flag": True})
    items = dispatch.items()
    jobs = items["prov"]["backend"]
    assert len(jobs) == 1, "Expected one job from a single circuit with shots as list."
    assert jobs[0].shots == 30, "Shot value should be 30."
    assert jobs[0].configuration == {"flag": True}, "Configuration should be preserved."


def test_dispatch_add_job_single_circuit_shots_int() -> None:
    """Test adding a single circuit when shots is provided as a single integer."""
    dispatch = Dispatch()
    circuit = QuantumCircuit(1, 1)
    shots = 42
    dispatch.add_job("prov", "backend", circuit, shots, config={"single": False})
    items = dispatch.items()
    jobs = items["prov"]["backend"]
    assert len(jobs) == 1, "Expected one job from a single circuit with shots as integer."
    assert jobs[0].shots == 42, "Shot value should be 42."
    assert jobs[0].configuration == {"single": False}, "Configuration should be preserved."


def test_dispatch_add_job_single_circuit_shots_list_error() -> None:
    """Test that adding a single circuit with a shots list of length not equal to 1 raises ValueError."""
    dispatch = Dispatch()
    circuit = QuantumCircuit(1, 1)
    shots = [5, 10]
    with pytest.raises(
        ValueError,
        match="If circuits is a single circuit, shots must be a single integer or a list of length 1.",
    ):
        dispatch.add_job("prov", "backend", circuit, shots, config={"err": True})


def test_dispatch_add_multiple_calls() -> None:
    """Test adding multiple jobs by calling add_job multiple times."""
    dispatch = Dispatch()
    qc1 = QuantumCircuit(1, 1)
    qc2 = QuantumCircuit(2, 2)
    qc3 = QuantumCircuit(3, 3)

    # First call
    dispatch.add_job("local_aer", "fake_torino", qc1, 100)
    # Second call, same provider/backend
    dispatch.add_job("local_aer", "fake_torino", qc2, 200)
    # Another call, different backend
    dispatch.add_job("local_aer", "fake_oslo", qc3, 300)

    all_jobs = list(dispatch.all_jobs())
    assert len(all_jobs) == 3, "Expected three total jobs across two backends."

    # Check that fake_torino has 2 jobs, fake_oslo has 1.
    torino_jobs = [j for (p, b, j) in all_jobs if b == "fake_torino"]
    oslo_jobs = [j for (p, b, j) in all_jobs if b == "fake_oslo"]
    assert len(torino_jobs) == 2, "Expected 2 jobs for fake_torino."
    assert len(oslo_jobs) == 1, "Expected 1 job for fake_oslo."


def test_dispatch_add_job_mismatched_lists() -> None:
    """Test that adding multiple circuits and a mismatched list of shots raises ValueError."""
    dispatch = Dispatch()
    circuits = [QuantumCircuit(1, 1), QuantumCircuit(2, 2)]
    shots = [10]  # Mismatched length
    with pytest.raises(ValueError, match="Length of circuits list must match"):
        dispatch.add_job("local_aer", "aer_simulator", circuits, shots)


def test_dispatch_repr() -> None:
    """Test the Dispatch __repr__ method."""
    dispatch = Dispatch()
    dispatch.add_job("local_aer", "aer_simulator", QuantumCircuit(1), 5)
    text = repr(dispatch)
    assert "Dispatch({" in text, "Expected Dispatch representation to begin with 'Dispatch('."


def test_dispatch_iteration() -> None:
    """Test the all_jobs() method to ensure iteration returns (provider, backend, job) tuples."""
    dispatch = Dispatch()
    dispatch.add_job("p1", "b1", QuantumCircuit(1, 1), 10)
    dispatch.add_job("p1", "b1", QuantumCircuit(2, 2), 20)
    dispatch.add_job("p2", "b2", QuantumCircuit(3, 3), 30)

    all_jobs = list(dispatch.all_jobs())
    assert len(all_jobs) == 3, "Expected 3 jobs total."
    assert all_jobs[0][0] == "p1" and all_jobs[0][1] == "b1", "Provider and backend mismatch in first job."
    assert all_jobs[1][0] == "p1" and all_jobs[1][1] == "b1", "Provider and backend mismatch in second job."
    assert all_jobs[2][0] == "p2" and all_jobs[2][1] == "b2", "Provider and backend mismatch in third job."


def test_dispatch_items_structure() -> None:
    """Test that Dispatch.items() returns the correct nested dictionary structure.

    The expected structure is:
    {
        "provider1": {
            "backendA": [Job(...), Job(...)],
            "backendB": [Job(...)],
        },
        "provider2": {
            ...
        }
    }
    """
    dispatch = Dispatch()
    qc_a = QuantumCircuit(1, 1)
    qc_b = QuantumCircuit(2, 2)
    qc_c = QuantumCircuit(3, 3)

    dispatch.add_job("local_aer", "fake_torino", [qc_a, qc_b], [10, 20])
    dispatch.add_job("local_aer", "fake_oslo", qc_c, 30)

    items = dispatch.items()
    assert isinstance(items, dict), "Dispatch.items() should return a dictionary."
    assert "local_aer" in items, "Expected the provider 'local' in the top-level dictionary."
    assert "fake_torino" in items["local_aer"], "Expected 'fake_torino' in the nested dictionary."
    assert "fake_oslo" in items["local_aer"], "Expected 'fake_oslo' in the nested dictionary."

    torino_jobs = items["local_aer"]["fake_torino"]
    oslo_jobs = items["local_aer"]["fake_oslo"]
    assert len(torino_jobs) == 2, "Expected two jobs for 'fake_torino'."
    assert len(oslo_jobs) == 1, "Expected one job for 'fake_oslo'."


# ---------------------------------------------------------------------------
# Tests for ResultCollector getters
# ---------------------------------------------------------------------------


def test_result_collector_get_jobs_and_results() -> None:
    """Test that ResultCollector.get_jobs() and get_results() return the expected nested structures."""
    rc = ResultCollector()
    job1 = Job(QuantumCircuit(1, 1), 10, {"key": "value"})
    job2 = Job(QuantumCircuit(2, 2), 20, {"key": "value"})
    job1_result = JobResult(job1, {"result": "data1"})
    job2_result = JobResult(job2, {"result": "data2"})

    simulated = {"prov": {"backend": [job1_result, job2_result]}}
    rc.nested_results = simulated

    job1_result.complete = False
    assert "status=Pending" in str(job1_result), "JobResult should indicate pending status."
    assert "complete=False" in str(rc), "ResultCollector should indicate incomplete status."

    job1_result.complete = True
    assert "status=Complete" in str(job1_result), "JobResult should indicate completed status."
    assert "complete=" not in str(rc), "ResultCollector should indicate complete status."

    jobs = rc.get_jobs()
    results = rc.get_results()
    assert jobs == simulated, "get_jobs() should return the simulated nested results."
    assert results == {"prov": {"backend": [job1_result.data, job2_result.data]}}, (
        "get_results() should return the simulated results."
    )

    mc = MergedResultCollector(rc)
    assert mc.get_jobs() == simulated, "MergedResultCollector should return the same jobs."


@pytest.fixture  # type: ignore
def dummy_split_policy() -> Callable[..., Any]:
    """Provide a dummy split policy that creates a Dispatch with a single job.

    Returns
    -------
    Callable
        The split function.

    """

    def split_fn(
        circuit: Any,  # noqa: ANN401
        shots: int,
        backends: dict[str, list[str]],
        _: Any,  # noqa: ANN401
        policy_data: Any | None,  # noqa: ANN401
    ) -> tuple[Dispatch, Any]:
        """Split function that creates a Dispatch with a single job.

        Parameters
        ----------
        circuit : Any
            The quantum circuit to run.
        shots : int
            Number of shots for the circuit.
        backends : Dict[str, List[str]]
            A dictionary mapping provider names to lists of backend names.
        _ : VirtualProvider
            An instance of VirtualProvider; not used in this policy.
        policy_data : Any, optional
            Additional data carried along; not used in this policy.

        Returns
        -------
        Tuple[Dispatch, Any]
            A tuple containing the Dispatch object with registered jobs and the unchanged blob.

        """
        dispatch = Dispatch()
        # For simplicity, just add one job to the first provider and first backend.
        # In a real scenario, we'd actually parse `backends`.
        provider_names = list(backends.keys())
        if not provider_names:
            return dispatch, policy_data

        first_provider = provider_names[0]
        first_backend = backends[first_provider][0]
        dispatch.add_job(first_provider, first_backend, circuit, shots)
        return dispatch, policy_data

    return split_fn


@pytest.fixture  # type: ignore
def dummy_merge_policy() -> Callable[..., Any]:
    """Provide a dummy merge policy that returns the collected results as-is.

    Returns
    -------
    Callable
        The merge function.

    """

    def merge_fn(
        nested_results: dict[str, dict[str, list[Any]]],
        policy_data: Any | None,  # noqa: ANN401
    ) -> tuple[dict[str, Any], Any]:
        """Merge function that returns the collected results as-is.

        Parameters
        ----------
        nested_results : Dict[str, Dict[str, List[Any]]]
            Nested mapping (provider -> backend -> list of results).
        policy_data : Any
            Additional data carried along; not used in this policy.

        Returns
        -------
        Tuple[Dict[str, Any], Any]
            A tuple containing the merged results and the updated policy data.

        """
        # In a real scenario, we'd actually merge the results.
        updated = policy_data if policy_data else {}
        updated["merged"] = True
        return nested_results, updated

    return merge_fn


@pytest.fixture  # type: ignore
def quantum_executor(
    dummy_split_policy: Callable[..., Any],  # pylint: disable=redefined-outer-name
    dummy_merge_policy: Callable[..., Any],  # pylint: disable=redefined-outer-name
) -> QuantumExecutor:
    """Provide a QuantumExecutor with a custom 'test_policy' that uses dummy split/merge.

    Parameters
    ----------
    dummy_split_policy : Callable
        The dummy split policy function.
    dummy_merge_policy : Callable
        The dummy merge policy function.

    Returns
    -------
    QuantumExecutor
        The QuantumExecutor instance with the test policy added.

    """
    executor = QuantumExecutor(providers=["local_aer"])
    executor.add_policy("test_policy", dummy_split_policy, dummy_merge_policy)
    return executor


def test_quantum_executor_run_experiment_sync(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test running a single-circuit experiment synchronously with the test_policy.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    backends = {"local_aer": ["aer_simulator"]}

    collector = quantum_executor.run_experiment(
        circuits=qc,
        shots=100,
        backends=backends,
        split_policy="test_policy",
        merge_policy="test_policy",
        multiprocess=False,
    )
    assert isinstance(collector, MergedResultCollector), "Expected a MergedResultCollector object."
    assert collector.complete, "Collector should be complete in synchronous mode."
    merged_data = collector.get_merged_results()
    assert "local_aer" in merged_data, "Merged results should contain the 'local' provider key."
    assert "aer_simulator" in merged_data["local_aer"], "Merged results should contain 'aer_simulator' key."
    data = collector.get_final_policy_data()
    assert data is not None, "Final policy data should not be None."
    assert data.get("merged") is True, "Policy data should indicate a completed merge."


def test_quantum_executor_run_experiment_missing_policy(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test that running with a non-existent policy raises KeyError.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    backends = {"local_aer": ["aer_simulator"]}

    with pytest.raises(KeyError, match="Split policy 'no_such_policy' not found"):
        quantum_executor.run_experiment(
            circuits=qc,
            shots=100,
            backends=backends,
            split_policy="no_such_policy",
            multiprocess=False,
        )


@pytest.mark.timeout(60)  # type: ignore
def test_quantum_executor_run_experiment_async_wait(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test running an experiment with multiprocess=True and wait=True.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    logging.basicConfig(level=logging.DEBUG)
    qc = QuantumCircuit(1, 1)
    backends = {"local_aer": ["aer_simulator"]}

    logging.warning("Starting quantum experiment with async execution.")
    collector = quantum_executor.run_experiment(
        circuits=qc,
        shots=50,
        backends=backends,
        split_policy="test_policy",
        merge_policy="test_policy",
        multiprocess=True,
        wait=True,
    )
    logging.warning("Quantum experiment completed.")
    assert collector.complete, "Collector should be complete after wait=True in async mode."
    assert isinstance(collector, MergedResultCollector), "Expected a MergedResultCollector object."
    data = collector.get_merged_results()
    logging.warning("Merged results: %s", data)
    assert data is not None, "Merged results should be available."
    assert isinstance(data, dict), "Merged results should be a dictionary."


@pytest.mark.timeout(60)  # type: ignore
def test_quantum_executor_run_experiment_async_no_wait(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test running an experiment with multiprocess=True and wait=False.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    qc = QuantumCircuit(1, 1)
    backends = {"local_aer": ["aer_simulator"]}

    collector = quantum_executor.run_experiment(
        circuits=qc,
        shots=25,
        backends=backends,
        split_policy="test_policy",
        merge_policy="test_policy",
        multiprocess=True,
        wait=False,
    )
    assert isinstance(collector, MergedResultCollector), "Expected a MergedResultCollector even if wait=False."
    # Because we return immediately, the collector may not be complete yet.
    completed = collector.wait_for_completion(timeout=60)
    assert completed, "Collector should eventually complete in background, within a few seconds."
    assert collector.get_merged_results() is not None, "Merged results should eventually be available."


def test_merged_result_collector_initial_properties() -> None:
    """Test initializing MergedResultCollector with an empty ResultCollector and verifying initial properties."""
    rc = ResultCollector()
    merged = MergedResultCollector(rc)
    assert merged.get_merged_results() is None, "Merged results should be None initially."
    assert merged.get_initial_policy_data() is None, "Initial policy data should be None by default."
    assert merged.get_final_policy_data() is None, "Final policy data should be None by default."


def test_merged_result_collector_repr() -> None:
    """Test the string representation of MergedResultCollector before and after merging."""
    rc = ResultCollector()
    merged = MergedResultCollector(rc)
    before_text = repr(merged)
    assert "complete_jobs=" in before_text and "total_jobs=" in before_text, (
        "Representation should indicate progress before merging."
    )
    # Mark the collector complete, simulate merges
    rc.complete = True
    merged.merged_results = {"some": "data"}
    merged_text = repr(merged)
    assert "merged_results={'some': 'data'}" in merged_text, (
        "Representation should show merged results after merging is done."
    )


def test_quantum_executor_run_dispatch_sync(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test the run_dispatch method in synchronous mode.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    dispatch = Dispatch()
    circuit = QuantumCircuit(2, 2)
    dispatch.add_job("local_aer", "aer_simulator", circuit, 10)

    collector = quantum_executor.run_dispatch(dispatch=dispatch, multiprocess=False, wait=True)
    assert collector.complete, "Collector should be complete in synchronous mode."
    results = collector.get_results()
    assert len(results["local_aer"]["aer_simulator"]) == 1, "Expected one result for the single job."
    assert results["local_aer"]["aer_simulator"][0] is not None, "Expected a non-None job result."


@pytest.mark.timeout(60)  # type: ignore
def test_quantum_executor_run_dispatch_async(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test the run_dispatch method in asynchronous mode with wait=True.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    dispatch = Dispatch()
    circuit = QuantumCircuit(2, 2)
    dispatch.add_job("local_aer", "aer_simulator", circuit, 10)

    collector = quantum_executor.run_dispatch(dispatch=dispatch, multiprocess=True, wait=True)
    assert collector.complete, "Collector should be complete after waiting in async mode."
    results = collector.get_results()
    assert "local_aer" in results, "Expected local provider key in results."
    assert "aer_simulator" in results["local_aer"], "Expected aer_simulator backend key in results."
    assert len(results["local_aer"]["aer_simulator"]) == 1, "Should have exactly one job result for the dispatch."
    assert results["local_aer"]["aer_simulator"][0] is not None, "Expected a successful result from job."


def test_quantum_executor_run_dispatch_no_jobs(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test that run_dispatch on an empty Dispatch immediately marks the result collector as complete.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    dispatch = Dispatch()
    collector = quantum_executor.run_dispatch(dispatch=dispatch, multiprocess=False, wait=True)
    assert collector.complete, "Collector should be complete immediately if no jobs are present."


def test_quantum_executor_run_experiment_no_backends(
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test that if the policy receives an empty backends dict.

    Parameters
    ----------
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    qc = QuantumCircuit(1, 1)
    backends: dict[str, list[str]] = {}  # Empty backends dictionary

    collector = quantum_executor.run_experiment(
        circuits=qc,
        shots=10,
        backends=backends,
        split_policy="test_policy",
        merge_policy="test_policy",
        multiprocess=False,
    )
    assert collector.complete, "Collector should be marked complete if no jobs were added."
    results = collector.get_results()
    assert len(results) == 0, "Expected no results in an empty dispatch scenario."
    assert isinstance(collector, MergedResultCollector), "Expected a MergedResultCollector object."
    merged_results = collector.get_merged_results()
    # Our dummy policy just returns {} if no jobs.
    assert merged_results is None, "Merged results should be None if no jobs were added."


@pytest.mark.parametrize("policy_name", ["uniform", "multiplier"])  # type: ignore
def test_quantum_executor_run_experiment_with_fake_backends(policy_name: str) -> None:
    """Test running an experiment with the 'uniform' or 'multiplier' policy using fake backends.

    We run synchronously for simplicity.

    Parameters
    ----------
    policy_name : str
        The name of the policy to use for splitting and merging.

    """
    # Create an executor that includes 'local' so it has the FakeProvider.
    executor = QuantumExecutor(providers=["local_aer"], raise_exc=True)

    # Check that we have the policy loaded (uniform or multiplier). If not found, KeyError is raised.
    # The built-in policies are typically loaded from the 'policies' folder if present.
    _ = executor.get_split_policy(policy_name)
    _ = executor.get_merge_policy("simple_aggregate")

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure_all()

    # We'll target two fake backends: fake_torino, fake_oslo
    backends = {"local_aer": ["fake_torino", "fake_oslo"]}

    collector = executor.run_experiment(
        circuits=qc,
        shots=51,
        backends=backends,
        split_policy=policy_name,
        merge_policy="simple_aggregate",
        multiprocess=False,
    )
    assert collector.complete, "Synchronous run_experiment should return a fully-complete MergedResultCollector."
    assert isinstance(collector, MergedResultCollector), "Expected a MergedResultCollector object."
    results = collector.get_merged_results()
    # Because each policy might have different splitting logic, we just verify it returned something.
    assert isinstance(results, dict), "Merged results should be a dictionary."


# ---------------------------------------------------------------------------
# Tests for QuantumExecutor.add_policy_from_file
# ---------------------------------------------------------------------------


def test_quantum_executor_add_policy_from_file_success(
    tmp_path: Any,  # noqa: ANN401
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test adding a valid policy from a file.

    A valid policy file defines both a 'split' and a 'merge' function.
    After adding, the new policy should be retrievable using get_split_policy and get_merge_policy.

    Parameters
    ----------
    tmp_path : Any
        Temporary directory for creating the policy file and QE folder.
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    # Create two separate temporary directories:
    # one for saving the policy file and one for serving as the QE policies folder.
    files_dir = tmp_path / "policy_files"
    files_dir.mkdir()
    qe_policies_dir = tmp_path / "qe_policies"
    qe_policies_dir.mkdir()

    policy_file = files_dir / "valid_policy.py"
    policy_code = """
# Test policy module for valid_policy.
def split(circuit, shots, backends, policy_data, vp):
    # Return an empty dispatch and the unmodified policy_data for testing.
    from quantum_executor.dispatch import Dispatch
    dispatch = Dispatch()
    return dispatch, policy_data

def merge(results, policy_data):
    # Return empty results and update the policy data.
    updated = dict(policy_data)
    updated["merged"] = True
    return {}, updated
"""
    policy_file.write_text(policy_code)

    # Set the policies folder to the separate qe_policies directory.
    quantum_executor._policies_folder = str(qe_policies_dir)  # pylint: disable=protected-access
    # Call add_policy_from_file with raise_exc=True.
    quantum_executor.add_policy_from_file(str(policy_file), raise_exc=True)
    # Check that the new policy is available.
    split_fn = quantum_executor.get_split_policy("valid_policy")
    merge_fn = quantum_executor.get_merge_policy("valid_policy")
    assert callable(split_fn), "The split function from the loaded policy should be callable."
    assert callable(merge_fn), "The merge function from the loaded policy should be callable."
    # Optionally, invoke the functions to verify that they return the expected types.
    dispatch, _ = split_fn(  # type: ignore[unused-ignore]
        QuantumCircuit(1), 100, {"local_aer": ["aer_simulator"]}, {}, None
    )
    assert hasattr(dispatch, "all_jobs"), "The split function should return a Dispatch instance."
    _, final_pdata = merge_fn({}, {"info": "test"})  # type: ignore[unused-ignore]
    assert isinstance(final_pdata, dict) and final_pdata.get("merged") is True, (
        "The merge function should update the policy data with 'merged': True."
    )

    new_policy_file = qe_policies_dir / "valid_policy.py"
    assert new_policy_file.exists(), "The policy file should be copied to the QE policies folder."


def test_quantum_executor_add_policy_from_file_failure(
    tmp_path: Any,  # noqa: ANN401
    quantum_executor: QuantumExecutor,  # pylint: disable=redefined-outer-name
) -> None:
    """Test that adding an invalid policy file with raise_exc=True raises ImportError.

    Parameters
    ----------
    tmp_path : Any
        Temporary directory for creating the policy file and QE folder.
    quantum_executor : QuantumExecutor
        The QuantumExecutor instance to use for the test.

    """
    # Create two temporary directories:
    files_dir = tmp_path / "policy_files"
    files_dir.mkdir()
    qe_policies_dir = tmp_path / "qe_policies"
    qe_policies_dir.mkdir()

    # Create a temporary invalid policy file (missing the 'merge' function).
    policy_file = files_dir / "invalid_policy.py"
    policy_code = '''
"""Invalid policy module: missing merge function."""
def split(circuit, shots, backends, policy_data, vp):
    return None, policy_data
'''
    policy_file.write_text(policy_code)

    # Set the policies folder to the separate qe_policies directory.
    quantum_executor._policies_folder = str(qe_policies_dir)  # pylint: disable=protected-access

    with pytest.raises(ImportError):
        quantum_executor.add_policy_from_file(str(policy_file), raise_exc=True)


# --------------------------------------------------
# Test Dispatch initialization via constructor
# --------------------------------------------------


def test_dispatch_init_from_dict_single_job() -> None:
    """Test initializing Dispatch from constructor with a single job dict."""
    circuit = QuantumCircuit(1, 1)
    initial_id = "test-id-123"
    config = {"param": 42}
    initial_jobs = {
        "provX": {
            "backendY": [
                {
                    "id": initial_id,
                    "circuit": circuit,
                    "shots": 7,
                    "configuration": config,
                }
            ]
        }
    }
    dispatch = Dispatch(initial_jobs)
    items = dispatch.items()
    assert "provX" in items, "Provider 'provX' should be initialized."
    assert "backendY" in items["provX"], "Backend 'backendY' should be initialized."
    jobs = items["provX"]["backendY"]
    assert len(jobs) == 1, "Expected one job in the initialized dispatch."
    job = jobs[0]
    assert job.id == initial_id, "Job ID should match the provided ID."
    assert job.circuit is circuit, "Job circuit should be the same object."
    assert job.shots == 7, "Job shots should match the provided shots."
    assert job.configuration == config, "Working configuration should match the provided dict."
    # Ensure deep copy of configuration
    config["param"] = 99
    assert job.configuration["param"] == 42, "Configuration should be deep-copied and not reflect external changes."


def test_dispatch_init_from_dict_multiple_jobs() -> None:
    """Test initializing Dispatch from constructor with multiple jobs without explicit IDs."""
    c1 = QuantumCircuit(1, 1)
    c2 = QuantumCircuit(2, 2)
    initial_jobs = {
        "provA": {
            "be1": [
                {"circuit": c1, "shots": 5},
                {"circuit": c2, "shots": 10, "configuration": {"a": 1}},
            ]
        }
    }
    dispatch = Dispatch(initial_jobs)
    items = dispatch.items()
    jobs = items["provA"]["be1"]
    assert len(jobs) == 2, "Expected two jobs in the initialized dispatch."
    # First job: no explicit ID and no config
    assert isinstance(jobs[0].id, str) and jobs[0].id, "First job should have an autogenerated non-empty ID."
    assert jobs[0].configuration == {}, "First job configuration should default to empty dict."
    # Second job: provided configuration and autogenerated ID
    assert jobs[1].shots == 10, "Second job shots should match the provided value."
    assert jobs[1].configuration == {"a": 1}, "Second job configuration should match provided dict."


def test_generate_dispatch_single_circuit_shots_int(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Single circuit + integer shots should produce exactly one job."""
    qc = QuantumCircuit(1, 1)
    backends = {"prov": ["backend"]}
    dispatch, split_data = quantum_executor.generate_dispatch(
        circuits=qc, shots=10, backends=backends, split_policy="test_policy"
    )
    assert isinstance(dispatch, Dispatch)
    jobs = list(dispatch.all_jobs())
    assert len(jobs) == 1
    prov, back, job = jobs[0]
    assert prov == "prov"
    assert back == "backend"
    assert job.shots == 10
    assert split_data == {}


def test_generate_dispatch_single_circuit_shots_list_length1(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Single circuit + shots=[n] should be treated as shots=n."""
    qc = QuantumCircuit(1, 1)
    backends = {"prov": ["backend"]}
    initial_data = {"foo": "bar"}
    dispatch, split_data = quantum_executor.generate_dispatch(
        circuits=qc, shots=[15], backends=backends, split_policy="test_policy", split_data=initial_data
    )
    jobs = list(dispatch.all_jobs())
    assert len(jobs) == 1
    assert jobs[0][2].shots == 15
    # initial split_data should be preserved
    assert split_data is initial_data


def test_generate_dispatch_single_circuit_shots_list_error(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Single circuit + shots list of length>1 must raise ValueError."""
    qc = QuantumCircuit(1, 1)
    backends = {"prov": ["backend"]}
    with pytest.raises(ValueError, match="single circuit, shots must be a single int"):
        quantum_executor.generate_dispatch(circuits=qc, shots=[1, 2], backends=backends, split_policy="test_policy")


def test_generate_dispatch_multiple_circuits_shots_int(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Multiple circuits + int shots should produce one job per circuit."""
    qcs = [QuantumCircuit(1, 1), QuantumCircuit(1, 1)]
    backends = {"prov": ["backend"]}
    dispatch, split_data = quantum_executor.generate_dispatch(
        circuits=qcs, shots=20, backends=backends, split_policy="test_policy"
    )
    jobs = list(dispatch.all_jobs())
    assert len(jobs) == 2
    for _, _, job in jobs:
        assert job.shots == 20
    assert split_data == {}


def test_generate_dispatch_multiple_circuits_shots_list_matching(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Multiple circuits + shots list of matching length should use per-circuit shots."""
    qcs = [QuantumCircuit(1, 1), QuantumCircuit(1, 1)]
    backends = {"prov": ["backend"]}
    initial_data = {"x": 1}
    dispatch, split_data = quantum_executor.generate_dispatch(
        circuits=qcs, shots=[5, 6], backends=backends, split_policy="test_policy", split_data=initial_data
    )
    jobs = list(dispatch.all_jobs())
    assert len(jobs) == 2
    assert jobs[0][2].shots == 5
    assert jobs[1][2].shots == 6
    assert split_data is initial_data


def test_generate_dispatch_multiple_circuits_shots_list_mismatch(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Multiple circuits + shots list of wrong length must raise ValueError."""
    qcs = [QuantumCircuit(1, 1), QuantumCircuit(1, 1)]
    backends = {"prov": ["backend"]}
    with pytest.raises(ValueError, match="single int or a list of the same length"):
        quantum_executor.generate_dispatch(circuits=qcs, shots=[10], backends=backends, split_policy="test_policy")


def test_generate_dispatch_no_backends(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Empty backends dict should yield zero jobs and empty split_data."""
    qc = QuantumCircuit(1, 1)
    dispatch, split_data = quantum_executor.generate_dispatch(
        circuits=qc, shots=10, backends={}, split_policy="test_policy"
    )
    assert isinstance(dispatch, Dispatch)
    assert not list(dispatch.all_jobs())
    assert split_data == {}


def test_generate_dispatch_preserves_initial_split_data(quantum_executor: QuantumExecutor) -> None:  # pylint: disable=redefined-outer-name
    """Whatever split_data you pass in should be returned unmodified."""
    qc = QuantumCircuit(1, 1)
    backends = {"prov": ["backend"]}
    initial_data = {"keep": True}
    _, split_data = quantum_executor.generate_dispatch(
        circuits=qc, shots=10, backends=backends, split_policy="test_policy", split_data=initial_data
    )
    assert split_data is initial_data
