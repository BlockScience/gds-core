"""Random search optimizer — uniform random sampling."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from gds_analysis.psuu.errors import PsuuSearchError
from gds_analysis.psuu.optimizers.base import Optimizer
from gds_analysis.psuu.space import Continuous, Discrete, Integer, ParameterSpace

if TYPE_CHECKING:
    from gds_analysis.psuu.types import KPIScores, ParamPoint

_MAX_REJECTION_RETRIES = 1000


class RandomSearchOptimizer(Optimizer):
    """Samples parameter points uniformly at random.

    Uses stdlib ``random.Random`` for reproducibility — no numpy required.
    When the parameter space has constraints, uses rejection sampling
    with a configurable retry limit.
    """

    def __init__(self, n_samples: int = 20, seed: int | None = None) -> None:
        self._n_samples = n_samples
        self._rng = random.Random(seed)
        self._space: ParameterSpace | None = None
        self._count: int = 0

    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        self._space = space
        self._count = 0

    def _sample_point(self) -> ParamPoint:
        assert self._space is not None
        point: ParamPoint = {}
        for name, dim in self._space.params.items():
            if isinstance(dim, Continuous):
                point[name] = self._rng.uniform(dim.min_val, dim.max_val)
            elif isinstance(dim, Integer):
                point[name] = self._rng.randint(dim.min_val, dim.max_val)
            elif isinstance(dim, Discrete):
                point[name] = self._rng.choice(dim.values)
        return point

    def suggest(self) -> ParamPoint:
        assert self._space is not None, "Call setup() before suggest()"
        if not self._space.constraints:
            point = self._sample_point()
            self._count += 1
            return point

        for _ in range(_MAX_REJECTION_RETRIES):
            point = self._sample_point()
            if self._space.is_feasible(point):
                self._count += 1
                return point

        raise PsuuSearchError(
            f"Could not find a feasible point after {_MAX_REJECTION_RETRIES} "
            "random samples. The feasible region may be too small."
        )

    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        pass  # Random search doesn't adapt

    def is_exhausted(self) -> bool:
        return self._count >= self._n_samples
