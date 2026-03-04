"""Bayesian optimizer — wraps scikit-optimize (optional dependency)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_psuu.errors import PsuuSearchError
from gds_psuu.optimizers.base import Optimizer
from gds_psuu.space import Continuous, Discrete, Integer, ParameterSpace

if TYPE_CHECKING:
    from gds_psuu.types import KPIScores, ParamPoint

try:
    from skopt import Optimizer as SkoptOptimizer  # type: ignore[import-untyped]
    from skopt.space import Categorical, Real  # type: ignore[import-untyped]
    from skopt.space import Integer as SkoptInteger

    _HAS_SKOPT = True
except ImportError:  # pragma: no cover
    _HAS_SKOPT = False


class BayesianOptimizer(Optimizer):
    """Bayesian optimization using Gaussian process surrogate.

    Requires ``scikit-optimize``. Install with::

        pip install gds-psuu[bayesian]

    Optimizes a single target KPI (by default the first one registered).
    """

    def __init__(
        self,
        n_calls: int = 20,
        target_kpi: str | None = None,
        maximize: bool = True,
        seed: int | None = None,
    ) -> None:
        if not _HAS_SKOPT:  # pragma: no cover
            raise ImportError(
                "scikit-optimize is required for BayesianOptimizer. "
                "Install with: pip install gds-psuu[bayesian]"
            )
        self._n_calls = n_calls
        self._target_kpi = target_kpi
        self._maximize = maximize
        self._seed = seed
        self._optimizer: Any = None
        self._param_names: list[str] = []
        self._count: int = 0

    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        if self._target_kpi is None:
            self._target_kpi = kpi_names[0]
        elif self._target_kpi not in kpi_names:
            raise PsuuSearchError(
                f"Target KPI '{self._target_kpi}' not found in {kpi_names}"
            )

        self._param_names = space.dimension_names
        dimensions: list[Any] = []
        for dim in space.params.values():
            if isinstance(dim, Continuous):
                dimensions.append(Real(dim.min_val, dim.max_val))
            elif isinstance(dim, Integer):
                dimensions.append(SkoptInteger(dim.min_val, dim.max_val))
            elif isinstance(dim, Discrete):
                dimensions.append(Categorical(list(dim.values)))

        self._optimizer = SkoptOptimizer(
            dimensions=dimensions,
            random_state=self._seed,
            n_initial_points=min(5, self._n_calls),
        )
        self._count = 0

    def suggest(self) -> ParamPoint:
        assert self._optimizer is not None, "Call setup() before suggest()"
        point = self._optimizer.ask()
        return dict(zip(self._param_names, point, strict=True))

    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        assert self._optimizer is not None
        assert self._target_kpi is not None
        point = [params[name] for name in self._param_names]
        value = scores[self._target_kpi]
        # skopt minimizes, so negate if we want to maximize
        if self._maximize:
            value = -value
        self._optimizer.tell(point, value)
        self._count += 1

    def is_exhausted(self) -> bool:
        return self._count >= self._n_calls
