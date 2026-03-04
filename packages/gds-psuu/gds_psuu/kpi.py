"""KPI wrapper and helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from gds_psuu.types import KPIFn  # noqa: TC001

if TYPE_CHECKING:
    from gds_sim import Results


class KPI(BaseModel):
    """Named KPI backed by a scoring function."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str
    fn: KPIFn


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
