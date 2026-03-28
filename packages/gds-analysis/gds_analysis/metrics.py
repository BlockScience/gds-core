"""Post-trajectory metric computation using StateMetric annotations.

Computes distances between successive states along a trajectory,
using the distance functions declared in GDSSpec.state_metrics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds import GDSSpec
    from gds.constraints import StateMetric


def trajectory_distances(
    spec: GDSSpec,
    trajectory: list[dict[str, Any]],
    *,
    metric_name: str | None = None,
) -> dict[str, list[float]]:
    """Compute state distances along a trajectory for each StateMetric.

    Parameters
    ----------
    spec
        GDSSpec with registered StateMetric annotations.
    trajectory
        List of state dicts (one per timestep). State keys should be
        ``"EntityName.VariableName"`` format.
    metric_name
        If provided, compute distances for only this metric. Otherwise
        compute for all metrics that have a distance callable.

    Returns
    -------
    Dict mapping metric name to list of distances. The list has
    length ``len(trajectory) - 1`` (one distance per consecutive pair).
    """
    metrics = _select_metrics(spec, metric_name)
    result: dict[str, list[float]] = {}

    for sm in metrics:
        distances: list[float] = []
        for i in range(len(trajectory) - 1):
            x_t = _extract_metric_state(sm, trajectory[i])
            x_next = _extract_metric_state(sm, trajectory[i + 1])
            if sm.distance is None:
                raise ValueError(f"State metric '{sm.name}' has no distance callable")
            distances.append(sm.distance(x_t, x_next))
        result[sm.name] = distances

    return result


def _select_metrics(
    spec: GDSSpec,
    metric_name: str | None,
) -> list[StateMetric]:
    """Select metrics to compute, filtering out those without distance."""
    if metric_name is not None:
        if metric_name not in spec.state_metrics:
            raise KeyError(f"State metric '{metric_name}' not registered")
        sm = spec.state_metrics[metric_name]
        if sm.distance is None:
            raise ValueError(f"State metric '{metric_name}' has no distance callable")
        return [sm]

    return [sm for sm in spec.state_metrics.values() if sm.distance is not None]


def _extract_metric_state(
    sm: StateMetric,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Extract the subset of state relevant to a metric.

    Looks for keys in ``"EntityName.VariableName"`` format matching
    the metric's declared variables.
    """
    result: dict[str, Any] = {}
    for entity_name, var_name in sm.variables:
        key = f"{entity_name}.{var_name}"
        if key in state:
            result[key] = state[key]
    return result
