"""One-at-a-time (OAT) sensitivity analyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_analysis.psuu.sensitivity.base import Analyzer, SensitivityResult
from gds_analysis.psuu.space import Continuous, Discrete, Integer

if TYPE_CHECKING:
    from gds_analysis.psuu.evaluation import Evaluator
    from gds_analysis.psuu.space import ParameterSpace
    from gds_analysis.psuu.types import ParamPoint


class OATAnalyzer(Analyzer):
    """One-at-a-time sensitivity analysis.

    Varies each parameter independently while holding others at baseline
    (midpoint for Continuous/Integer, first value for Discrete).
    """

    def __init__(self, n_levels: int = 4) -> None:
        self._n_levels = n_levels

    def analyze(self, evaluator: Evaluator, space: ParameterSpace) -> SensitivityResult:
        baseline = _compute_baseline(space)
        baseline_result = evaluator.evaluate(baseline)
        baseline_scores = baseline_result.scores

        kpi_names = list(baseline_scores.keys())
        indices: dict[str, dict[str, dict[str, float]]] = {kpi: {} for kpi in kpi_names}

        for param_name, dim in space.params.items():
            test_values = _get_test_values(dim, self._n_levels)
            effects: dict[str, list[float]] = {kpi: [] for kpi in kpi_names}

            for val in test_values:
                point: ParamPoint = dict(baseline)
                point[param_name] = val
                result = evaluator.evaluate(point)
                for kpi in kpi_names:
                    effects[kpi].append(result.scores[kpi] - baseline_scores[kpi])

            for kpi in kpi_names:
                effs = effects[kpi]
                n = len(effs)
                mean_effect = sum(abs(e) for e in effs) / n if n else 0.0
                base_val = baseline_scores[kpi]
                relative = mean_effect / abs(base_val) if base_val != 0 else 0.0
                indices[kpi][param_name] = {
                    "mean_effect": mean_effect,
                    "relative_effect": relative,
                }

        return SensitivityResult(indices=indices, method="OAT")


def _compute_baseline(space: ParameterSpace) -> ParamPoint:
    """Compute baseline point: midpoints for numeric, first for discrete."""
    baseline: ParamPoint = {}
    for name, dim in space.params.items():
        if isinstance(dim, Continuous):
            baseline[name] = (dim.min_val + dim.max_val) / 2.0
        elif isinstance(dim, Integer):
            baseline[name] = (dim.min_val + dim.max_val) // 2
        elif isinstance(dim, Discrete):
            baseline[name] = dim.values[0]
    return baseline


def _get_test_values(
    dim: Continuous | Integer | Discrete, n_levels: int
) -> list[object]:
    """Generate test values for a dimension."""
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
