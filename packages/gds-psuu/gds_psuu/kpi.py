"""KPI wrapper and helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_psuu.errors import PsuuValidationError
from gds_psuu.metric import (
    Aggregation,
    Metric,
    _extract_run_ids,
    mean_agg,
)
from gds_psuu.types import KPIFn  # noqa: TC001

if TYPE_CHECKING:
    from gds_sim import Results


class KPI(BaseModel):
    """Named KPI backed by either a legacy fn or a Metric + Aggregation pair.

    Legacy usage (backwards compatible)::

        KPI(name="avg_pop", fn=lambda r: final_state_mean(r, "population"))

    Composable usage::

        KPI(name="avg_pop", metric=final_value("population"), aggregation=mean_agg)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    fn: KPIFn | None = None
    metric: Metric | None = None
    aggregation: Aggregation | None = None

    @model_validator(mode="after")
    def _validate_specification(self) -> Self:
        has_fn = self.fn is not None
        has_metric = self.metric is not None
        if not has_fn and not has_metric:
            raise PsuuValidationError("KPI must have either 'fn' or 'metric' specified")
        if has_fn and has_metric:
            raise PsuuValidationError(
                "KPI cannot have both 'fn' and 'metric' specified"
            )
        return self

    def compute(self, results: Results) -> float:
        """Compute the aggregated KPI score from results."""
        if self.fn is not None:
            return self.fn(results)
        assert self.metric is not None
        agg = self.aggregation or mean_agg
        per_run = self.per_run(results)
        return agg.fn(per_run)

    def per_run(self, results: Results) -> list[float]:
        """Compute per-run metric values. Only available for metric-based KPIs."""
        if self.metric is None:
            raise PsuuValidationError(
                "per_run() requires a metric-based KPI, not a legacy fn-based KPI"
            )
        run_ids = _extract_run_ids(results)
        return [self.metric.fn(results, r) for r in run_ids]


# ---------------------------------------------------------------------------
# Legacy helper functions (backwards compatible)
# ---------------------------------------------------------------------------


def final_state_mean(results: Results, key: str) -> float:
    """Mean of a state variable's final-timestep values across all runs.

    Filters to the last timestep (max substep) for each run and averages.
    """
    cols = results._trimmed_columns()
    timesteps = cols["timestep"]
    substeps = cols["substep"]
    runs = cols["run"]
    values = cols[key]
    n = results._size

    # Find max timestep
    max_t = 0
    for i in range(n):
        t = timesteps[i]
        if t > max_t:
            max_t = t

    # Find max substep at max timestep
    max_s = 0
    for i in range(n):
        if timesteps[i] == max_t:
            s = substeps[i]
            if s > max_s:
                max_s = s

    # Collect final values per run
    total = 0.0
    count = 0
    seen_runs: set[int] = set()
    for i in range(n):
        if timesteps[i] == max_t and substeps[i] == max_s:
            r = runs[i]
            if r not in seen_runs:
                seen_runs.add(r)
                total += float(values[i])
                count += 1

    if count == 0:
        return 0.0
    return total / count


def final_state_std(results: Results, key: str) -> float:
    """Std dev of a state variable's final-timestep values across all runs."""
    cols = results._trimmed_columns()
    timesteps = cols["timestep"]
    substeps = cols["substep"]
    runs = cols["run"]
    values = cols[key]
    n = results._size

    max_t = 0
    for i in range(n):
        t = timesteps[i]
        if t > max_t:
            max_t = t

    max_s = 0
    for i in range(n):
        if timesteps[i] == max_t:
            s = substeps[i]
            if s > max_s:
                max_s = s

    finals: list[float] = []
    seen_runs: set[int] = set()
    for i in range(n):
        if timesteps[i] == max_t and substeps[i] == max_s:
            r = runs[i]
            if r not in seen_runs:
                seen_runs.add(r)
                finals.append(float(values[i]))

    if len(finals) < 2:
        return 0.0

    mean = sum(finals) / len(finals)
    variance = sum((x - mean) ** 2 for x in finals) / (len(finals) - 1)
    return variance**0.5


def time_average(results: Results, key: str) -> float:
    """Mean of a state variable across all timesteps, substeps, and runs."""
    cols = results._trimmed_columns()
    values = cols[key]
    n = results._size

    if n == 0:
        return 0.0

    total = sum(float(v) for v in values)
    return total / n
