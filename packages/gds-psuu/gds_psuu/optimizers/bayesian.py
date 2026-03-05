"""Bayesian optimizer — wraps optuna (optional dependency)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_psuu.errors import PsuuSearchError
from gds_psuu.optimizers.base import Optimizer
from gds_psuu.space import Continuous, Discrete, Integer, ParameterSpace

if TYPE_CHECKING:
    from gds_psuu.types import KPIScores, ParamPoint

try:
    import optuna

    _HAS_OPTUNA = True
except ImportError:  # pragma: no cover
    _HAS_OPTUNA = False


class BayesianOptimizer(Optimizer):
    """Bayesian optimization using optuna's TPE sampler.

    Requires ``optuna``. Install with::

        uv add gds-psuu[bayesian]

    Optimizes a single target KPI (by default the first one registered).
    """

    def __init__(
        self,
        n_trials: int = 20,
        target_kpi: str | None = None,
        maximize: bool = True,
        seed: int | None = None,
    ) -> None:
        if not _HAS_OPTUNA:  # pragma: no cover
            raise ImportError(
                "optuna is required for BayesianOptimizer. "
                "Install with: uv add gds-psuu[bayesian]"
            )
        self._n_trials = n_trials
        self._target_kpi = target_kpi
        self._maximize = maximize
        self._seed = seed
        self._study: Any = None
        self._space: ParameterSpace | None = None
        self._param_names: list[str] = []
        self._count: int = 0
        self._current_trial: Any = None

    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        if self._target_kpi is None:
            self._target_kpi = kpi_names[0]
        elif self._target_kpi not in kpi_names:
            raise PsuuSearchError(
                f"Target KPI '{self._target_kpi}' not found in {kpi_names}"
            )

        self._space = space
        self._param_names = space.dimension_names

        sampler = optuna.samplers.TPESampler(seed=self._seed)
        direction = "maximize" if self._maximize else "minimize"
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        self._study = optuna.create_study(
            direction=direction,
            sampler=sampler,
        )
        self._count = 0

    def suggest(self) -> ParamPoint:
        assert self._study is not None, "Call setup() before suggest()"
        assert self._space is not None

        self._current_trial = self._study.ask()
        point: ParamPoint = {}
        for name, dim in self._space.params.items():
            if isinstance(dim, Continuous):
                point[name] = self._current_trial.suggest_float(
                    name, dim.min_val, dim.max_val
                )
            elif isinstance(dim, Integer):
                point[name] = self._current_trial.suggest_int(
                    name, dim.min_val, dim.max_val
                )
            elif isinstance(dim, Discrete):
                point[name] = self._current_trial.suggest_categorical(
                    name, list(dim.values)
                )
        return point

    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        assert self._study is not None
        assert self._target_kpi is not None
        assert self._current_trial is not None
        value = scores[self._target_kpi]
        self._study.tell(self._current_trial, value)
        self._current_trial = None
        self._count += 1

    def is_exhausted(self) -> bool:
        return self._count >= self._n_trials
