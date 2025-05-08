"""The QuantumExecutor orchestrates quantum job splitting, dispatching, execution, and (optionally) result merging."""

import importlib.util
import logging
import threading
from collections.abc import Callable
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import as_completed
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Union

from quantum_executor.dispatch import Dispatch
from quantum_executor.job_runner import run_single_job_static
from quantum_executor.result_collector import MergedResultCollector
from quantum_executor.result_collector import ResultCollector
from quantum_executor.virtual_provider import VirtualProvider

if TYPE_CHECKING:  # pragma: no cover
    from quantum_executor.dispatch import DispatchDict

logger = logging.getLogger(__name__)


def load_policies_from_folder(  # pylint: disable=too-many-branches
    folder_path: str, raise_exc: bool = False
) -> dict[str, dict[str, Callable[..., Any]]]:
    """Dynamically load split and/or merge policies from Python files in a folder.

    Parameters
    ----------
    folder_path : str
        Path to the folder containing policy files.
    raise_exc : bool, optional
        If True, raise on missing folder or load errors. Otherwise, log a warning.
        Defaults to False.

    Returns
    -------
    Dict[str, Dict[str, Callable[..., Any]]]
        Mapping policy names → dict with keys "split" and/or "merge".

    """
    logger.debug("Loading policies from folder '%s'...", folder_path)
    if not Path.exists(Path(folder_path)):
        if raise_exc:
            raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")
        logger.warning("Folder '%s' does not exist; creating it.", folder_path)
        Path.mkdir(Path(folder_path), parents=True, exist_ok=True)
        return {}

    policies: dict[str, dict[str, Callable[..., Any]]] = {}
    for fname in Path(folder_path).iterdir():
        if not fname.is_file() or not fname.name.endswith(".py"):
            continue
        name = fname.name[:-3]
        path = folder_path / fname
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            msg = f"Cannot load module '{name}' from '{path}'."
            if raise_exc:
                raise ImportError(msg)
            logger.warning(msg)
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:  # pylint: disable=broad-except
            msg = f"Error loading '{fname}': {e}"
            if raise_exc:
                raise ImportError(msg) from e
            logger.warning(msg)
            continue

        funcs: dict[str, Callable[..., Any]] = {}
        if hasattr(module, "split") and callable(module.split):
            funcs["split"] = module.split
        if hasattr(module, "merge") and callable(module.merge):
            funcs["merge"] = module.merge

        if funcs:
            policies[name] = funcs
        else:
            msg = f"Policy file '{fname}' defines neither split nor merge."
            if raise_exc:
                raise ImportError(msg)
            logger.warning(msg)

    return policies


def add_policy_from_file(file_path: str, policy_folder: str, raise_exc: bool = False) -> None:
    """Load a policy module from file and copy it into the policies folder.

    Parameters
    ----------
    file_path : str
        Path to the Python file containing the policy.
    policy_folder : str
        Folder where policies live.
    raise_exc : bool, optional
        If True, raise on errors. Otherwise, log warnings.
        Defaults to False.

    """
    spec = importlib.util.spec_from_file_location("policy_mod", file_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load module from '{file_path}'."
        if raise_exc:
            raise ImportError(msg)
        logger.warning(msg)
        return

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:  # pylint: disable=broad-except
        msg = f"Error importing policy from '{file_path}': {e}"
        if raise_exc:
            raise ImportError(msg) from e
        logger.warning(msg)
        return

    has_split = hasattr(module, "split") and callable(module.split)
    has_merge = hasattr(module, "merge") and callable(module.merge)
    if not (has_split or has_merge):
        msg = f"Policy file '{file_path}' defines neither split nor merge."
        if raise_exc:
            raise ImportError(msg)
        logger.warning(msg)
        return

    Path(policy_folder).mkdir(parents=True, exist_ok=True)
    dest = Path(policy_folder) / Path(file_path).name
    with (
        Path(file_path).open(encoding="utf-8") as src,
        dest.open("w", encoding="utf-8") as dst,
    ):
        if module.__doc__:
            dst.write(module.__doc__ + "\n\n")
        dst.write(src.read())
    logger.info("Policy '%s' copied to '%s'.", Path(file_path).name, policy_folder)


class QuantumExecutor:
    """Manage splitting, dispatching, execution, and optional merging of quantum jobs.

    Parameters
    ----------
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
    providers : List[str], optional
        Which providers to initialize.
    policies_folder : str, optional
        Where to load/save policy files.
    max_workers : int, optional
        Max processes for async execution.
    raise_exc : bool, optional
        If True, propagate initialization or policy-load errors.
    virtual_provider : VirtualProvider, optional
        If provided, use this instead of creating a new one.

    """

    _default_split = "uniform"

    def __init__(  # pylint: disable=too-many-arguments too-many-positional-arguments
        self,
        providers_info: dict[str, dict[str, Any]] | None = None,
        providers: list[str] | None = None,
        policies_folder: str = __file__.replace("executor.py", "policies"),
        max_workers: int | None = None,
        raise_exc: bool = False,
        virtual_provider: VirtualProvider | None = None,
    ) -> None:
        """Manage splitting, dispatching, execution, and optional merging of quantum jobs.

        Parameters
        ----------
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
        providers : List[str], optional
            Which providers to initialize.
        policies_folder : str, optional
            Where to load/save policy files.
        max_workers : int, optional
            Max processes for async execution.
        raise_exc : bool, optional
            If True, propagate initialization or policy-load errors.
        virtual_provider : VirtualProvider, optional
            If provided, use this instead of creating a new one.

        """
        self._policies_folder = policies_folder
        self._max_workers = max_workers
        self._raise_exc = raise_exc

        if virtual_provider is None:
            self._providers_info = providers_info or {}
            self._providers = providers
            self._virtual_provider = VirtualProvider(
                providers_info=self._providers_info,
                include=self._providers,
                raise_exc=self._raise_exc,
            )
        else:
            self._providers_info = virtual_provider._providers_info
            self._providers = list(virtual_provider.get_providers().keys())
            self._virtual_provider = virtual_provider

        self._policies = load_policies_from_folder(self._policies_folder, raise_exc=self._raise_exc)
        logger.info("QuantumExecutor initialized.")

    def generate_dispatch(  # pylint: disable=too-many-positional-arguments too-many-arguments too-many-locals
        self,
        circuits: Any | Sequence[Any],  # noqa: ANN401
        shots: int | Sequence[int],
        backends: dict[str, list[str]],
        split_policy: str = _default_split,
        split_data: dict[str, Any] | None = None,
    ) -> tuple[Dispatch, dict[str, Any]]:
        """Split a circuit into jobs based on the specified split policy.

        Parameters
        ----------
        circuits : Any or Sequence[Any]
            Quantum circuit or list of quantum circuits.
        shots : int or Sequence[int]
            Number of shots or list of numbers of shots.
            If a list, it must match the length of `circuits`.
            If a single int, all circuits will use the same number of shots.
        backends : dict[str, list[str]]
            Provider → list of backends.
        split_policy : str, optional
            Which split policy to use.
        split_data : dict, optional
            Initial data for split policy.

        Returns
        -------
        tuple[Dispatch, dict[str, Any]]
            A Dispatch object containing the jobs and any updated split data.
        """
        if isinstance(circuits, Sequence):
            circuits = list(circuits)
            shots_list = [shots] * len(circuits) if isinstance(shots, int) else list(shots)

            if len(shots_list) != len(circuits):
                raise ValueError(
                    "When passing multiple circuits, shots must be a single int or a list of the same length."
                )

            split_fn = self.get_split_policy(split_policy)
            aggregated: dict[str, dict[str, list[Any]]] = {}

            split_data = split_data or {}
            for circ, sh in zip(circuits, shots_list, strict=False):
                disp_i, updated_split_data = split_fn(circ, sh, backends, self._virtual_provider, split_data)
                split_data = updated_split_data
                for prov, back_map in disp_i.to_dict().items():
                    agg_back_map = aggregated.setdefault(prov, {})
                    for back, jobs in back_map.items():
                        agg_back_map.setdefault(back, []).extend(jobs)

            return Dispatch(aggregated), split_data or {}

        if isinstance(shots, Sequence) and len(shots) > 1:
            raise ValueError("When passing a single circuit, shots must be a single int, not a list.")
        if isinstance(shots, Sequence):
            shots = shots[0]

        # Single-circuit path
        split_fn = self.get_split_policy(split_policy)
        split_data = split_data or {}
        return split_fn(  # type: ignore[no-any-return]
            circuits,
            shots,
            backends,
            self._virtual_provider,
            split_data,
        )

    def run_experiment(  # pylint: disable=too-many-positional-arguments too-many-arguments
        self,
        circuits: Any | Sequence[Any],  # noqa: ANN401
        shots: int | Sequence[int],
        backends: dict[str, list[str]],
        split_policy: str = _default_split,
        merge_policy: str | None = None,
        multiprocess: bool = False,
        wait: bool = True,
        split_data: dict[str, Any] | None = None,
        merge_data: dict[str, Any] | None = None,
        max_workers: int | None = None,
    ) -> ResultCollector | MergedResultCollector:
        """Split a circuit into jobs, dispatch them, and optionally merge results.

        Parameters
        ----------
        circuits : Any or Sequence[Any]
            Quantum circuit or list of quantum circuits.
        shots : int or Sequence[int]
            Number of shots or list of numbers of shots.
            If a list, it must match the length of `circuits`.
            If a single int, all circuits will use the same number of shots.
        backends : dict[str, list[str]]
            Provider → list of backends.
        split_policy : str, optional
            Which split policy to use.
        merge_policy : str or None, optional
            Which merge policy to use; if None, skip merging.
        multiprocess : bool, optional
            If True, run jobs in parallel processes.
        wait : bool, optional
            If True, block until execution (and merge) finishes.
        split_data : dict, optional
            Initial data for split policy.
        merge_data : dict, optional
            Initial data for merge policy, if None, use updated split data.
        max_workers : int, optional
            Override for max parallel processes.

        Returns
        -------
        ResultCollector or MergedResultCollector
            Unmerged collector if `merge_policy` is None, otherwise merged.

        """
        logger.info(
            "Experiment start: split_policy='%s', merge_policy='%s'",
            split_policy,
            merge_policy,
        )
        dispatch_obj, updated_split = self.generate_dispatch(
            circuits=circuits,
            shots=shots,
            backends=backends,
            split_policy=split_policy,
            split_data=split_data,
        )

        return self.run_dispatch(
            dispatch=dispatch_obj,
            multiprocess=multiprocess,
            wait=wait,
            max_workers=max_workers,
            merge_policy=merge_policy,
            merge_data=merge_data or updated_split,
        )

    # pylint: disable=too-many-positional-arguments too-many-arguments too-many-locals too-many-branches
    def run_dispatch(  # pylint: disable=too-many-statements
        self,
        dispatch: Union[Dispatch, "DispatchDict"],
        multiprocess: bool = False,
        wait: bool = True,
        max_workers: int | None = None,
        merge_policy: str | None = None,
        merge_data: dict[str, Any] | None = None,
    ) -> ResultCollector | MergedResultCollector:
        """Execute all jobs in a Dispatch and optionally merge their results.

        Parameters
        ----------
        dispatch : Dispatch or DispatchDict
            Jobs to execute.
        multiprocess : bool, optional
            If True, run in parallel processes.
        wait : bool, optional
            If True, block until execution (and merge) finishes.
            If False, jobs run in a background thread (sequentially if multiprocess=False,
            or gathering + merging in threads if multiprocess=True).
        max_workers : int, optional
            Override for max parallel processes.
        merge_policy : str or None, optional
            Which merge policy to apply after dispatch.
        merge_data : dict, optional
            Initial data for merge policy.

        Returns
        -------
        ResultCollector or MergedResultCollector
            Raw results if `merge_policy` is None, otherwise merged.

        """
        logger.info(
            "Dispatch start: multiprocess=%s, wait=%s, merge_policy=%s",
            multiprocess,
            wait,
            merge_policy,
        )
        if not isinstance(dispatch, Dispatch):
            dispatch = Dispatch(dispatch)

        collector = ResultCollector()
        jobs = list(dispatch.all_jobs())
        if not jobs:
            logger.warning("No jobs to dispatch.")
            collector.complete = True
            return collector if merge_policy is None else MergedResultCollector(collector)

        for prov, back, job in jobs:
            collector.register_job_mapping(job, prov, back)

        def _run_sequential() -> None:
            """Run all jobs sequentially."""
            for prov, back, job in jobs:
                try:
                    res = run_single_job_static(
                        prov,
                        back,
                        job.circuit,
                        job.shots,
                        job.configuration or {},
                        self._providers_info,
                        self._providers,
                        self._raise_exc,
                        virtual_provider=self._virtual_provider,
                    )
                except Exception as e:  # pylint: disable=broad-except
                    logger.error("Error fetching result for Job %s: %s", job.id, e)
                    res = {"error": str(e)}
                collector.store_result(job, res)
            collector.complete = True

        if not multiprocess:
            if wait:
                _run_sequential()
            else:
                threading.Thread(target=_run_sequential, daemon=True).start()
        else:
            executor = ProcessPoolExecutor(max_workers or self._max_workers)
            futures: dict[Any, Any] = {}
            for prov, back, job in jobs:
                futures[
                    executor.submit(
                        run_single_job_static,
                        prov,
                        back,
                        job.circuit,
                        job.shots,
                        job.configuration or {},
                        self._providers_info,
                        self._providers,
                        self._raise_exc,
                        None,
                    )
                ] = job

            def _gather() -> None:
                for fut in as_completed(futures):
                    job_obj = futures[fut]
                    try:
                        res = fut.result()
                    except Exception as e:  # pylint: disable=broad-except
                        logger.error("Error fetching result for Job %s: %s", job_obj.id, e)
                        res = {"error": str(e)}
                    collector.store_result(job_obj, res)
                collector.complete = True
                executor.shutdown(wait=False)

            if wait:
                _gather()
            else:
                threading.Thread(target=_gather, daemon=True).start()

        if merge_policy is None:
            return collector

        merged = MergedResultCollector(collector)

        def _merge_dispatch() -> None:
            """Merge results using the specified merge policy."""
            collector.wait_for_completion()
            try:
                merge_fn = self.get_merge_policy(merge_policy)
                md = merge_data or {}
                results, final = merge_fn(collector.get_results(), md)
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Dispatch merge error: %s", e)
                results, final = {"error": str(e)}, {}
                md = {}
            merged.set_merged_results(results, md, final)
            logger.info("Dispatch merge '%s' done.", merge_policy)

        if wait:
            _merge_dispatch()
        else:
            threading.Thread(target=_merge_dispatch, daemon=True).start()

        return merged

    def get_split_policy(self, name: str) -> Callable[..., Any]:
        """Get a split policy by name.

        Parameters
        ----------
        name : str
            Policy name.

        Returns
        -------
        Callable[..., Any]
            The split policy function.

        Raises
        ------
        KeyError
            If not found or policy lacks a split.

        """
        try:
            p = self._policies[name]["split"]
            if not callable(p):
                raise KeyError(f"Split policy '{name}' not found.")
            return p
        except KeyError:
            raise KeyError(f"Split policy '{name}' not found.") from None

    def get_merge_policy(self, name: str) -> Callable[..., Any]:
        """Get a merge policy by name.

        Parameters
        ----------
        name : str
            Policy name.

        Returns
        -------
        Callable[..., Any]
            The merge policy function.

        Raises
        ------
        KeyError
            If not found or policy lacks a merge.

        """
        try:
            p = self._policies[name]["merge"]
            if not callable(p):
                raise KeyError(f"Merge policy '{name}' not found.")
            return p
        except KeyError:
            raise KeyError(f"Merge policy '{name}' not found.") from None

    def add_policy(
        self,
        name: str,
        split_policy: Callable[..., Any] | None = None,
        merge_policy: Callable[..., Any] | None = None,
    ) -> None:
        """Dynamically add or update a policy (split and/or merge).

        Parameters
        ----------
        name : str
            Policy name.
        split_policy : Callable[..., Any], optional
            Split function.
        merge_policy : Callable[..., Any], optional
            Merge function.

        """
        entry: dict[str, Callable[..., Any]] = {}
        if split_policy:
            entry["split"] = split_policy
        if merge_policy:
            entry["merge"] = merge_policy
        if not entry:
            raise ValueError("At least one of split_policy or merge_policy must be provided.")
        self._policies[name] = entry
        logger.info("Policy '%s' added/updated.", name)

    def add_policy_from_file(self, file_path: str, raise_exc: bool | None = None) -> None:
        """Load a policy from file and (re)load all policies.

        Parameters
        ----------
        file_path : str
            Path to policy file.
        raise_exc : bool, optional
            If True, raise on errors. Defaults to constructor setting.

        """
        eff = raise_exc if raise_exc is not None else self._raise_exc
        add_policy_from_file(file_path, self._policies_folder, raise_exc=eff)
        self._policies = load_policies_from_folder(self._policies_folder, raise_exc=eff)

    @property
    def policies(self) -> list[str]:
        """List all loaded policy names.

        Returns
        -------
        List[str]
            List of loaded policy names.

        """
        return list(self._policies.keys())

    @property
    def virtual_provider(self) -> VirtualProvider:
        """Get the virtual provider.

        Returns
        -------
        VirtualProvider
            The virtual provider instance.

        """
        return self._virtual_provider

    @staticmethod
    def default_providers() -> list[str]:
        """Get a list of default providers.

        Returns
        -------
        List[str]
            A list of provider names that are available for use.

        """
        return list(VirtualProvider.default_providers())
