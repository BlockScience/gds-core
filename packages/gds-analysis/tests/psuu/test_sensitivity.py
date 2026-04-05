"""Tests for sensitivity analysis framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gds_analysis.psuu import (
    KPI,
    Analyzer,
    Continuous,
    Discrete,
    Evaluator,
    Integer,
    MorrisAnalyzer,
    OATAnalyzer,
    ParameterSpace,
    SensitivityResult,
    final_state_mean,
)

if TYPE_CHECKING:
    from gds_sim import Model


class TestAnalyzerABC:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            Analyzer()  # type: ignore[abstract]


class TestSensitivityResult:
    def test_ranking(self) -> None:
        result = SensitivityResult(
            indices={
                "kpi_a": {
                    "x": {"mean_effect": 10.0},
                    "y": {"mean_effect": 50.0},
                    "z": {"mean_effect": 30.0},
                }
            },
            method="test",
        )
        ranking = result.ranking("kpi_a")
        assert ranking == ["y", "z", "x"]

    def test_ranking_custom_metric(self) -> None:
        result = SensitivityResult(
            indices={
                "kpi": {
                    "a": {"mu_star": 5.0, "sigma": 20.0},
                    "b": {"mu_star": 15.0, "sigma": 2.0},
                }
            },
            method="test",
        )
        ranking = result.ranking("kpi", metric="sigma")
        assert ranking == ["a", "b"]

    def test_to_dataframe(self) -> None:
        pytest.importorskip("pandas")
        result = SensitivityResult(
            indices={
                "kpi": {
                    "x": {"mean_effect": 10.0, "relative_effect": 0.5},
                    "y": {"mean_effect": 20.0, "relative_effect": 1.0},
                }
            },
            method="OAT",
        )
        df = result.to_dataframe()
        assert len(df) == 2
        assert "kpi" in df.columns
        assert "param" in df.columns
        assert "mean_effect" in df.columns


class TestOATAnalyzer:
    def test_oat_basic(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=10,
            runs=1,
        )
        analyzer = OATAnalyzer(n_levels=4)
        result = analyzer.analyze(evaluator, space)

        assert result.method == "OAT"
        assert "final_pop" in result.indices
        assert "growth_rate" in result.indices["final_pop"]
        metrics = result.indices["final_pop"]["growth_rate"]
        assert "mean_effect" in metrics
        assert "relative_effect" in metrics
        assert metrics["mean_effect"] > 0  # growth rate matters

    def test_oat_multi_param(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={
                "growth_rate": Continuous(min_val=0.01, max_val=0.1),
                "label": Discrete(values=("A", "B")),
            }
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=10,
            runs=1,
        )
        analyzer = OATAnalyzer(n_levels=3)
        result = analyzer.analyze(evaluator, space)

        assert "growth_rate" in result.indices["final_pop"]
        assert "label" in result.indices["final_pop"]
        # growth_rate should be more influential than label
        ranking = result.ranking("final_pop")
        assert ranking[0] == "growth_rate"

    def test_oat_integer_dim(self, simple_model: Model) -> None:
        space = ParameterSpace(params={"growth_rate": Integer(min_val=1, max_val=3)})
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=5,
            runs=1,
        )
        analyzer = OATAnalyzer(n_levels=3)
        result = analyzer.analyze(evaluator, space)
        assert "growth_rate" in result.indices["final_pop"]

    def test_oat_single_level(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=5,
            runs=1,
        )
        analyzer = OATAnalyzer(n_levels=1)
        result = analyzer.analyze(evaluator, space)
        assert "growth_rate" in result.indices["final_pop"]


class TestMorrisAnalyzer:
    def test_morris_basic(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=10,
            runs=1,
        )
        analyzer = MorrisAnalyzer(r=5, n_levels=4, seed=42)
        result = analyzer.analyze(evaluator, space)

        assert result.method == "Morris"
        assert "final_pop" in result.indices
        metrics = result.indices["final_pop"]["growth_rate"]
        assert "mu_star" in metrics
        assert "sigma" in metrics
        assert metrics["mu_star"] > 0

    def test_morris_multi_param(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={
                "growth_rate": Continuous(min_val=0.01, max_val=0.1),
                "label": Discrete(values=("A", "B")),
            }
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=10,
            runs=1,
        )
        analyzer = MorrisAnalyzer(r=8, n_levels=4, seed=42)
        result = analyzer.analyze(evaluator, space)

        ranking = result.ranking("final_pop", metric="mu_star")
        assert ranking[0] == "growth_rate"

    def test_morris_reproducible(self, simple_model: Model) -> None:
        space = ParameterSpace(
            params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
        )
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=5,
            runs=1,
        )
        r1 = MorrisAnalyzer(r=5, seed=99).analyze(evaluator, space)
        r2 = MorrisAnalyzer(r=5, seed=99).analyze(evaluator, space)
        assert (
            r1.indices["final_pop"]["growth_rate"]["mu_star"]
            == r2.indices["final_pop"]["growth_rate"]["mu_star"]
        )

    def test_morris_discrete_only(self, simple_model: Model) -> None:
        space = ParameterSpace(params={"strategy": Discrete(values=("A", "B", "C"))})
        evaluator = Evaluator(
            base_model=simple_model,
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            timesteps=5,
            runs=1,
        )
        analyzer = MorrisAnalyzer(r=5, n_levels=3, seed=42)
        result = analyzer.analyze(evaluator, space)
        assert "strategy" in result.indices["final_pop"]
