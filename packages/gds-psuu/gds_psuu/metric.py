"""Metric and Aggregation primitives for composable KPI construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from gds_psuu.types import AggregationFn, MetricFn  # noqa: TC001

if TYPE_CHECKING:
    from gds_sim import Results


class Metric(BaseModel):
    """Per-run scalar extracted from simulation output."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    fn: MetricFn


class Aggregation(BaseModel):
    """Combines per-run metric values across Monte Carlo runs."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    fn: AggregationFn


# ---------------------------------------------------------------------------
# Built-in metric factories
# ---------------------------------------------------------------------------


def _extract_run_ids(results: Results) -> list[int]:
    """Get unique run IDs from results."""
    cols = results._trimmed_columns()
    runs = cols["run"]
    seen: set[int] = set()
    ordered: list[int] = []
    for r in runs:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def _final_value_fn(results: Results, run: int, key: str) -> float:
    """Extract the final-timestep value for a specific run."""
    cols = results._trimmed_columns()
    timesteps = cols["timestep"]
    substeps = cols["substep"]
    runs_col = cols["run"]
    values = cols[key]
    n = results._size

    max_t = 0
    for i in range(n):
        if runs_col[i] == run:
            t = timesteps[i]
            if t > max_t:
                max_t = t

    max_s = 0
    for i in range(n):
        if runs_col[i] == run and timesteps[i] == max_t:
            s = substeps[i]
            if s > max_s:
                max_s = s

    for i in range(n):
        if runs_col[i] == run and timesteps[i] == max_t and substeps[i] == max_s:
            return float(values[i])

    return 0.0


def final_value(key: str) -> Metric:
    """Metric: value of a state variable at the final timestep of a run."""
    return Metric(
        name=f"final_{key}",
        fn=lambda results, run, _key=key: _final_value_fn(results, run, _key),
    )


def _trajectory_mean_fn(results: Results, run: int, key: str) -> float:
    """Mean of a state variable across all timesteps for a specific run."""
    cols = results._trimmed_columns()
    runs_col = cols["run"]
    values = cols[key]
    n = results._size

    total = 0.0
    count = 0
    for i in range(n):
        if runs_col[i] == run:
            total += float(values[i])
            count += 1

    return total / count if count else 0.0


def trajectory_mean(key: str) -> Metric:
    """Metric: mean of a state variable over time for a single run."""
    return Metric(
        name=f"mean_{key}",
        fn=lambda results, run, _key=key: _trajectory_mean_fn(results, run, _key),
    )


def _max_value_fn(results: Results, run: int, key: str) -> float:
    """Max of a state variable across all timesteps for a specific run."""
    cols = results._trimmed_columns()
    runs_col = cols["run"]
    values = cols[key]
    n = results._size

    max_val = float("-inf")
    for i in range(n):
        if runs_col[i] == run:
            v = float(values[i])
            if v > max_val:
                max_val = v
    return max_val if max_val != float("-inf") else 0.0


def max_value(key: str) -> Metric:
    """Metric: maximum value of a state variable within a single run."""
    return Metric(
        name=f"max_{key}",
        fn=lambda results, run, _key=key: _max_value_fn(results, run, _key),
    )


def _min_value_fn(results: Results, run: int, key: str) -> float:
    """Min of a state variable across all timesteps for a specific run."""
    cols = results._trimmed_columns()
    runs_col = cols["run"]
    values = cols[key]
    n = results._size

    min_val = float("inf")
    for i in range(n):
        if runs_col[i] == run:
            v = float(values[i])
            if v < min_val:
                min_val = v
    return min_val if min_val != float("inf") else 0.0


def min_value(key: str) -> Metric:
    """Metric: minimum value of a state variable within a single run."""
    return Metric(
        name=f"min_{key}",
        fn=lambda results, run, _key=key: _min_value_fn(results, run, _key),
    )


# ---------------------------------------------------------------------------
# Built-in aggregations
# ---------------------------------------------------------------------------

mean_agg = Aggregation(
    name="mean",
    fn=lambda vals: sum(vals) / len(vals) if vals else 0.0,
)

std_agg = Aggregation(
    name="std",
    fn=lambda vals: (
        (sum((x - sum(vals) / len(vals)) ** 2 for x in vals) / (len(vals) - 1)) ** 0.5
        if len(vals) > 1
        else 0.0
    ),
)


def percentile_agg(p: float) -> Aggregation:
    """Aggregation: p-th percentile across runs."""

    def _fn(vals: list[float]) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        k = (p / 100.0) * (len(s) - 1)
        lo = int(k)
        hi = min(lo + 1, len(s) - 1)
        frac = k - lo
        return s[lo] + frac * (s[hi] - s[lo])

    return Aggregation(name=f"p{p}", fn=_fn)


def probability_above(threshold: float) -> Aggregation:
    """Aggregation: fraction of runs where metric exceeds threshold."""
    return Aggregation(
        name=f"P(>{threshold})",
        fn=lambda vals: (
            sum(1 for v in vals if v > threshold) / len(vals) if vals else 0.0
        ),
    )


def probability_below(threshold: float) -> Aggregation:
    """Aggregation: fraction of runs where metric is below threshold."""
    return Aggregation(
        name=f"P(<{threshold})",
        fn=lambda vals: (
            sum(1 for v in vals if v < threshold) / len(vals) if vals else 0.0
        ),
    )
