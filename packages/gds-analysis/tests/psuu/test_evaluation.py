"""Tests for the evaluation bridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_analysis.psuu import KPI, Evaluator, final_state_mean

if TYPE_CHECKING:
    from gds_sim import Model


class TestEvaluator:
    def test_evaluate_returns_result(
        self, simple_model: Model, simple_kpi: KPI
    ) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[simple_kpi],
            timesteps=5,
            runs=1,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert result.params == {"growth_rate": 0.05}
        assert "final_pop" in result.scores
        assert result.run_count == 1
        assert len(result.results) > 0

    def test_evaluate_different_params(
        self, simple_model: Model, simple_kpi: KPI
    ) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[simple_kpi],
            timesteps=10,
            runs=1,
        )
        low = evaluator.evaluate({"growth_rate": 0.01})
        high = evaluator.evaluate({"growth_rate": 0.1})
        # Higher growth rate → higher final population
        assert high.scores["final_pop"] > low.scores["final_pop"]

    def test_evaluate_multiple_runs(self, simple_model: Model, simple_kpi: KPI) -> None:
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[simple_kpi],
            timesteps=5,
            runs=3,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert result.run_count == 3

    def test_evaluate_multiple_kpis(self, simple_model: Model) -> None:
        kpis = [
            KPI(name="final_pop", fn=lambda r: final_state_mean(r, "population")),
            KPI(name="avg_pop", fn=lambda r: final_state_mean(r, "population")),
        ]
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=kpis,
            timesteps=5,
            runs=1,
        )
        result = evaluator.evaluate({"growth_rate": 0.05})
        assert "final_pop" in result.scores
        assert "avg_pop" in result.scores
