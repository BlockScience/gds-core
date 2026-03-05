"""Tests for Metric/Aggregation primitives and composable KPIs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gds_sim import Results

from gds_psuu import (
    KPI,
    Continuous,
    Evaluator,
    GridSearchOptimizer,
    ParameterSpace,
    PsuuValidationError,
    Sweep,
    final_state_mean,
    final_value,
    max_value,
    mean_agg,
    min_value,
    percentile_agg,
    probability_above,
    probability_below,
    std_agg,
    trajectory_mean,
)

if TYPE_CHECKING:
    from gds_sim import Model


def _make_results(values: list[list[float]], key: str = "x") -> Results:
    """Create Results with multiple runs. Each inner list is one run's trajectory."""
    r = Results(state_keys=[key])
    for run_id, trajectory in enumerate(values, start=1):
        for t, val in enumerate(trajectory):
            r.append(
                {key: val},
                timestep=t,
                substep=1,
                run=run_id,
                subset=0,
            )
    return r


class TestMetricFactories:
    def test_final_value(self) -> None:
        results = _make_results([[10.0, 20.0, 30.0]], key="pop")
        m = final_value("pop")
        assert m.fn(results, 1) == 30.0

    def test_final_value_multi_run(self) -> None:
        results = _make_results([[10.0, 20.0], [100.0, 200.0]], key="pop")
        m = final_value("pop")
        assert m.fn(results, 1) == 20.0
        assert m.fn(results, 2) == 200.0

    def test_trajectory_mean(self) -> None:
        results = _make_results([[10.0, 20.0, 30.0]], key="x")
        m = trajectory_mean("x")
        assert m.fn(results, 1) == 20.0

    def test_max_value(self) -> None:
        results = _make_results([[5.0, 100.0, 3.0]], key="x")
        m = max_value("x")
        assert m.fn(results, 1) == 100.0

    def test_min_value(self) -> None:
        results = _make_results([[5.0, 1.0, 3.0]], key="x")
        m = min_value("x")
        assert m.fn(results, 1) == 1.0

    def test_metric_name(self) -> None:
        assert final_value("pop").name == "final_pop"
        assert trajectory_mean("x").name == "mean_x"
        assert max_value("y").name == "max_y"
        assert min_value("z").name == "min_z"


class TestAggregations:
    def test_mean_agg(self) -> None:
        assert mean_agg.fn([10.0, 20.0, 30.0]) == 20.0

    def test_mean_agg_empty(self) -> None:
        assert mean_agg.fn([]) == 0.0

    def test_std_agg(self) -> None:
        vals = [10.0, 20.0, 30.0]
        result = std_agg.fn(vals)
        assert result == pytest.approx(10.0)

    def test_std_agg_single(self) -> None:
        assert std_agg.fn([5.0]) == 0.0

    def test_percentile_agg(self) -> None:
        agg = percentile_agg(50)
        assert agg.fn([1.0, 2.0, 3.0, 4.0, 5.0]) == 3.0

    def test_percentile_agg_boundary(self) -> None:
        assert percentile_agg(0).fn([10.0, 20.0, 30.0]) == 10.0
        assert percentile_agg(100).fn([10.0, 20.0, 30.0]) == 30.0

    def test_percentile_agg_empty(self) -> None:
        assert percentile_agg(50).fn([]) == 0.0

    def test_probability_above(self) -> None:
        agg = probability_above(15.0)
        assert agg.fn([10.0, 20.0, 30.0]) == pytest.approx(2 / 3)

    def test_probability_above_empty(self) -> None:
        assert probability_above(0).fn([]) == 0.0

    def test_probability_below(self) -> None:
        agg = probability_below(25.0)
        assert agg.fn([10.0, 20.0, 30.0]) == pytest.approx(2 / 3)

    def test_probability_below_empty(self) -> None:
        assert probability_below(0).fn([]) == 0.0


class TestComposableKPI:
    def test_metric_based_kpi(self) -> None:
        results = _make_results([[10.0, 20.0], [10.0, 40.0], [10.0, 60.0]], key="pop")
        kpi = KPI(name="avg_final", metric=final_value("pop"), aggregation=mean_agg)
        assert kpi.compute(results) == 40.0

    def test_metric_defaults_to_mean(self) -> None:
        results = _make_results([[10.0, 20.0], [10.0, 40.0]], key="pop")
        kpi = KPI(name="avg_final", metric=final_value("pop"))
        assert kpi.compute(results) == 30.0  # mean of [20, 40]

    def test_metric_with_percentile(self) -> None:
        results = _make_results(
            [[0.0, v] for v in [10.0, 20.0, 30.0, 40.0, 50.0]], key="x"
        )
        kpi = KPI(
            name="p50_x",
            metric=final_value("x"),
            aggregation=percentile_agg(50),
        )
        assert kpi.compute(results) == 30.0

    def test_metric_with_probability(self) -> None:
        results = _make_results([[0.0, v] for v in [10.0, 20.0, 30.0]], key="x")
        kpi = KPI(
            name="risk",
            metric=final_value("x"),
            aggregation=probability_below(25.0),
        )
        assert kpi.compute(results) == pytest.approx(2 / 3)

    def test_per_run(self) -> None:
        results = _make_results([[10.0, 20.0], [10.0, 40.0], [10.0, 60.0]], key="pop")
        kpi = KPI(name="final_pop", metric=final_value("pop"))
        per_run = kpi.per_run(results)
        assert per_run == [20.0, 40.0, 60.0]

    def test_per_run_on_fn_kpi_raises(self) -> None:
        kpi = KPI(name="legacy", fn=lambda r: 0.0)
        results = Results(state_keys=[])
        with pytest.raises(PsuuValidationError, match="metric-based"):
            kpi.per_run(results)


class TestLegacyKPI:
    def test_fn_based_still_works(self) -> None:
        results = _make_results([[10.0, 20.0, 30.0]], key="pop")
        kpi = KPI(
            name="legacy",
            fn=lambda r: final_state_mean(r, "pop"),
        )
        assert kpi.compute(results) == 30.0

    def test_validation_neither(self) -> None:
        with pytest.raises(
            (PsuuValidationError, ValueError),
            match="either 'fn' or 'metric'",
        ):
            KPI(name="bad")

    def test_validation_both(self) -> None:
        with pytest.raises(
            (PsuuValidationError, ValueError),
            match="cannot have both",
        ):
            KPI(
                name="bad",
                fn=lambda r: 0.0,
                metric=final_value("x"),
            )


class TestEvaluatorDistributions:
    def test_distributions_populated(self, simple_model: Model) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(name="final_pop", metric=final_value("population")),
            ],
            timesteps=5,
            runs=3,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert "final_pop" in result.distributions
        assert len(result.distributions["final_pop"]) == 3

    def test_distributions_empty_for_legacy_kpi(self, simple_model: Model) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="legacy_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                ),
            ],
            timesteps=5,
            runs=1,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert "legacy_pop" not in result.distributions

    def test_mixed_kpis(self, simple_model: Model) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="legacy",
                    fn=lambda r: final_state_mean(r, "population"),
                ),
                KPI(name="composable", metric=final_value("population")),
            ],
            timesteps=5,
            runs=2,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert "legacy" not in result.distributions
        assert "composable" in result.distributions
        assert len(result.distributions["composable"]) == 2


class TestSweepWithComposableKPI:
    def test_sweep_composable(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(name="avg_pop", metric=final_value("population")),
            ],
            optimizer=GridSearchOptimizer(n_steps=3),
            timesteps=5,
            runs=2,
        )
        results = sweep.run()
        assert len(results.evaluations) == 3
        # Each evaluation should have distributions
        for ev in results.evaluations:
            assert "avg_pop" in ev.distributions
            assert len(ev.distributions["avg_pop"]) == 2

    def test_sweep_legacy_still_works(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                ),
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 2
        best = results.best("final_pop")
        assert best.params["growth_rate"] == 0.1
