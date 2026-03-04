"""Tests for sweep results."""

from __future__ import annotations

import pytest
from gds_sim import Results
from pydantic import ValidationError

from gds_psuu.evaluation import EvaluationResult
from gds_psuu.results import EvaluationSummary, SweepResults


def _make_eval(params: dict, scores: dict) -> EvaluationResult:
    return EvaluationResult(
        params=params,
        scores=scores,
        results=Results(state_keys=[]),
        run_count=1,
    )


class TestSweepResults:
    def test_summaries(self) -> None:
        evals = [
            _make_eval({"x": 1}, {"kpi": 10.0}),
            _make_eval({"x": 2}, {"kpi": 20.0}),
        ]
        sr = SweepResults(evaluations=evals, kpi_names=["kpi"], optimizer_name="test")
        summaries = sr.summaries
        assert len(summaries) == 2
        assert summaries[0].params == {"x": 1}
        assert summaries[1].scores == {"kpi": 20.0}

    def test_best_maximize(self) -> None:
        evals = [
            _make_eval({"x": 1}, {"kpi": 10.0}),
            _make_eval({"x": 2}, {"kpi": 30.0}),
            _make_eval({"x": 3}, {"kpi": 20.0}),
        ]
        sr = SweepResults(evaluations=evals, kpi_names=["kpi"], optimizer_name="test")
        best = sr.best("kpi", maximize=True)
        assert best.params == {"x": 2}
        assert best.scores["kpi"] == 30.0

    def test_best_minimize(self) -> None:
        evals = [
            _make_eval({"x": 1}, {"kpi": 10.0}),
            _make_eval({"x": 2}, {"kpi": 30.0}),
        ]
        sr = SweepResults(evaluations=evals, kpi_names=["kpi"], optimizer_name="test")
        best = sr.best("kpi", maximize=False)
        assert best.params == {"x": 1}

    def test_best_empty(self) -> None:
        sr = SweepResults(evaluations=[], kpi_names=["kpi"], optimizer_name="test")
        with pytest.raises(ValueError, match="No evaluations"):
            sr.best("kpi")

    def test_best_unknown_kpi(self) -> None:
        evals = [_make_eval({"x": 1}, {"kpi": 10.0})]
        sr = SweepResults(evaluations=evals, kpi_names=["kpi"], optimizer_name="test")
        with pytest.raises(ValueError, match="not found"):
            sr.best("nonexistent")

    def test_to_dataframe(self) -> None:
        pytest.importorskip("pandas")
        evals = [
            _make_eval({"x": 1, "y": "a"}, {"kpi": 10.0}),
            _make_eval({"x": 2, "y": "b"}, {"kpi": 20.0}),
        ]
        sr = SweepResults(evaluations=evals, kpi_names=["kpi"], optimizer_name="test")
        df = sr.to_dataframe()
        assert len(df) == 2
        assert list(df.columns) == ["x", "y", "kpi"]


class TestEvaluationSummary:
    def test_frozen(self) -> None:
        s = EvaluationSummary(params={"x": 1}, scores={"kpi": 10.0})
        with pytest.raises(ValidationError):
            s.params = {}  # type: ignore[misc]
