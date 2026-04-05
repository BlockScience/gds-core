"""Tests for composable objective functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gds_sim import Results

from gds_analysis.psuu import (
    KPI,
    Continuous,
    GridSearchOptimizer,
    Objective,
    ParameterSpace,
    PsuuValidationError,
    SingleKPI,
    Sweep,
    WeightedSum,
    final_state_mean,
)
from gds_analysis.psuu.evaluation import EvaluationResult
from gds_analysis.psuu.results import SweepResults

if TYPE_CHECKING:
    from gds_sim import Model


def _make_eval(params: dict, scores: dict) -> EvaluationResult:
    return EvaluationResult(
        params=params,
        scores=scores,
        results=Results(state_keys=[]),
        run_count=1,
    )


class TestSingleKPI:
    def test_maximize(self) -> None:
        obj = SingleKPI(name="profit")
        assert obj.score({"profit": 100.0, "risk": 5.0}) == 100.0

    def test_minimize(self) -> None:
        obj = SingleKPI(name="risk", maximize=False)
        assert obj.score({"profit": 100.0, "risk": 5.0}) == -5.0


class TestWeightedSum:
    def test_basic(self) -> None:
        obj = WeightedSum(weights={"profit": 0.7, "risk": -0.3})
        score = obj.score({"profit": 100.0, "risk": 10.0})
        assert score == pytest.approx(0.7 * 100 + (-0.3) * 10)

    def test_single_weight(self) -> None:
        obj = WeightedSum(weights={"kpi": 2.0})
        assert obj.score({"kpi": 50.0}) == 100.0

    def test_empty_weights_rejected(self) -> None:
        with pytest.raises(
            (PsuuValidationError, ValueError),
            match="at least 1 weight",
        ):
            WeightedSum(weights={})


class TestObjectiveProtocol:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Objective()  # type: ignore[abstract]


class TestBestByObjective:
    def test_best_weighted_sum(self) -> None:
        evals = [
            _make_eval({"x": 1}, {"profit": 100.0, "risk": 50.0}),
            _make_eval({"x": 2}, {"profit": 80.0, "risk": 10.0}),
            _make_eval({"x": 3}, {"profit": 90.0, "risk": 30.0}),
        ]
        sr = SweepResults(
            evaluations=evals,
            kpi_names=["profit", "risk"],
            optimizer_name="test",
        )
        obj = WeightedSum(weights={"profit": 1.0, "risk": -1.0})
        # Scores: 50, 70, 60 → best is x=2
        best = sr.best_by_objective(obj)
        assert best.params == {"x": 2}

    def test_best_single_kpi(self) -> None:
        evals = [
            _make_eval({"x": 1}, {"kpi": 10.0}),
            _make_eval({"x": 2}, {"kpi": 30.0}),
        ]
        sr = SweepResults(
            evaluations=evals,
            kpi_names=["kpi"],
            optimizer_name="test",
        )
        best = sr.best_by_objective(SingleKPI(name="kpi"))
        assert best.params == {"x": 2}

    def test_best_by_objective_empty(self) -> None:
        sr = SweepResults(
            evaluations=[],
            kpi_names=["kpi"],
            optimizer_name="test",
        )
        with pytest.raises(ValueError, match="No evaluations"):
            sr.best_by_objective(SingleKPI(name="kpi"))


class TestSweepWithObjective:
    def test_sweep_with_objective(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            objective=SingleKPI(name="final_pop"),
            optimizer=GridSearchOptimizer(n_steps=3),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 3

    def test_sweep_without_objective_backwards_compat(
        self, simple_model: Model
    ) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 2
        # Old best() still works
        best = results.best("final_pop")
        assert "growth_rate" in best.params


try:
    import optuna  # noqa: F401

    _has_optuna = True
except ImportError:
    _has_optuna = False


@pytest.mark.skipif(not _has_optuna, reason="optuna not installed")
class TestBayesianOptimizer:
    def test_bayesian_sweep(self, simple_model: Model) -> None:
        from gds_analysis.psuu import BayesianOptimizer

        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=BayesianOptimizer(n_trials=5, target_kpi="final_pop", seed=42),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 5

    def test_bayesian_minimize(self, simple_model: Model) -> None:
        from gds_analysis.psuu import BayesianOptimizer

        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=BayesianOptimizer(n_trials=5, maximize=False, seed=42),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 5

    def test_bayesian_bad_target_kpi(self) -> None:
        from gds_analysis.psuu import BayesianOptimizer
        from gds_analysis.psuu.errors import PsuuSearchError

        opt = BayesianOptimizer(n_trials=5, target_kpi="nonexistent")
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=1)})
        with pytest.raises(PsuuSearchError, match="not found"):
            opt.setup(space, ["kpi_a"])

    def test_bayesian_defaults_to_first_kpi(self) -> None:
        from gds_analysis.psuu import BayesianOptimizer

        opt = BayesianOptimizer(n_trials=5, seed=0)
        space = ParameterSpace(params={"x": Continuous(min_val=0, max_val=1)})
        opt.setup(space, ["alpha", "beta"])
        assert opt._target_kpi == "alpha"
