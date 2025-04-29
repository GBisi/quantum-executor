"""A simple merge policy that sums all measurement counts."""

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:  # pragma: no cover
    from quantum_executor.job_runner import ResultData


def merge(
    results: dict[str, dict[str, list["ResultData"]]],
    policy_data: Any,  # noqa: ANN401
) -> tuple[dict[str, int], Any]:
    """Merge job results by summing bitstring counts.

    Parameters
    ----------
    results : Dict[str, Dict[str, List[ResultData]]]
        Nested mapping (provider -> backend -> list of ResultData objects).
    policy_data : Any
        Additional data carried along; not used in this policy.

    Returns
    -------
    Tuple[Dict, Any]
        A tuple containing the merged counts dictionary and the unchanged blob.

    """
    merged_results: dict[str, int] = {}
    for _, provider_results in results.items():  # pylint: disable=too-many-nested-blocks
        for _, job_results in provider_results.items():
            for result_data in job_results:
                if result_data is not None and isinstance(result_data, dict):
                    for bitstring, count in result_data.items():
                        if isinstance(count, int):
                            merged_results[bitstring] = merged_results.get(bitstring, 0) + count
    return merged_results, policy_data
