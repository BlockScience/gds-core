"""Grid search optimizer — exhaustive cartesian product search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_psuu.optimizers.base import Optimizer

if TYPE_CHECKING:
    from gds_psuu.space import ParameterSpace
    from gds_psuu.types import KPIScores, ParamPoint


class GridSearchOptimizer(Optimizer):
    """Evaluates every point in a regular grid over the parameter space.

    For Continuous dimensions, ``n_steps`` evenly spaced values are used.
    For Integer dimensions, all integers in [min, max] are used.
    For Discrete dimensions, all values are used.
    """

    def __init__(self, n_steps: int = 5) -> None:
        self._n_steps = n_steps
        self._grid: list[ParamPoint] = []
        self._cursor: int = 0

    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        self._grid = space.grid_points(self._n_steps)
        self._cursor = 0

    def suggest(self) -> ParamPoint:
        point = self._grid[self._cursor]
        self._cursor += 1
        return point

    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        pass  # Grid search doesn't adapt

    def is_exhausted(self) -> bool:
        return self._cursor >= len(self._grid)
