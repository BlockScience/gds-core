"""Morris method (elementary effects) sensitivity analyzer."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from gds_analysis.psuu.sensitivity.base import Analyzer, SensitivityResult
from gds_analysis.psuu.space import Continuous, Discrete, Integer

if TYPE_CHECKING:
    from gds_analysis.psuu.evaluation import Evaluator
    from gds_analysis.psuu.space import ParameterSpace
    from gds_analysis.psuu.types import ParamPoint


class MorrisAnalyzer(Analyzer):
    """Morris screening method for sensitivity analysis.

    Generates ``r`` random trajectories through the parameter space,
    each with ``k+1`` points (k = number of parameters). Computes
    elementary effects per parameter:

    - ``mu_star``: mean of absolute elementary effects (influence)
    - ``sigma``: std of elementary effects (nonlinearity / interactions)
    """

    def __init__(self, r: int = 10, n_levels: int = 4, seed: int | None = None) -> None:
        self._r = r
        self._n_levels = n_levels
        self._rng = random.Random(seed)

    def analyze(self, evaluator: Evaluator, space: ParameterSpace) -> SensitivityResult:
        param_names = space.dimension_names
        k = len(param_names)

        # Precompute level values for each parameter
        level_values: dict[str, list[object]] = {}
        for name, dim in space.params.items():
            level_values[name] = _get_levels(dim, self._n_levels)

        # Collect elementary effects per parameter per KPI
        kpi_names: list[str] | None = None
        effects: dict[str, dict[str, list[float]]] = {}

        for _ in range(self._r):
            # Generate random starting point from levels
            base_point: ParamPoint = {
                name: self._rng.choice(level_values[name]) for name in param_names
            }
            base_result = evaluator.evaluate(base_point)

            if kpi_names is None:
                kpi_names = list(base_result.scores.keys())
                effects = {kpi: {p: [] for p in param_names} for kpi in kpi_names}

            # Permute parameter order for this trajectory
            order = list(range(k))
            self._rng.shuffle(order)

            current_point: ParamPoint = dict(base_point)
            current_scores = dict(base_result.scores)

            for idx in order:
                name = param_names[idx]
                levels = level_values[name]
                old_val = current_point[name]

                # Pick a different level
                candidates = [v for v in levels if v != old_val]
                if not candidates:
                    continue
                new_val = self._rng.choice(candidates)

                next_point: ParamPoint = dict(current_point)
                next_point[name] = new_val
                next_result = evaluator.evaluate(next_point)

                for kpi in kpi_names:
                    ee = next_result.scores[kpi] - current_scores[kpi]
                    effects[kpi][name].append(ee)

                current_point = next_point
                current_scores = dict(next_result.scores)

        assert kpi_names is not None
        indices: dict[str, dict[str, dict[str, float]]] = {}
        for kpi in kpi_names:
            indices[kpi] = {}
            for param in param_names:
                effs = effects[kpi][param]
                n = len(effs)
                if n == 0:
                    indices[kpi][param] = {"mu_star": 0.0, "sigma": 0.0}
                    continue
                mu_star = sum(abs(e) for e in effs) / n
                mean = sum(effs) / n
                variance = (
                    sum((e - mean) ** 2 for e in effs) / (n - 1) if n > 1 else 0.0
                )
                sigma = variance**0.5
                indices[kpi][param] = {
                    "mu_star": mu_star,
                    "sigma": sigma,
                }

        return SensitivityResult(indices=indices, method="Morris")


def _get_levels(dim: Continuous | Integer | Discrete, n_levels: int) -> list[object]:
    """Generate evenly-spaced levels for a dimension."""
    if isinstance(dim, Continuous):
        if n_levels < 2:
            return [dim.min_val]
        step = (dim.max_val - dim.min_val) / (n_levels - 1)
        return [dim.min_val + i * step for i in range(n_levels)]
    elif isinstance(dim, Integer):
        return list(range(dim.min_val, dim.max_val + 1))
    elif isinstance(dim, Discrete):
        return list(dim.values)
    return []  # pragma: no cover
