"""Sweep results and summary types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from gds_psuu.evaluation import EvaluationResult  # noqa: TC001
from gds_psuu.types import KPIScores, ParamPoint  # noqa: TC001

if TYPE_CHECKING:
    from gds_psuu.objective import Objective


class EvaluationSummary(BaseModel):
    """Summary of a single evaluation (without raw simulation data)."""

    model_config = ConfigDict(frozen=True)

    params: ParamPoint
    scores: KPIScores


class SweepResults(BaseModel):
    """Container for all evaluation results from a sweep."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    evaluations: list[EvaluationResult]
    kpi_names: list[str]
    optimizer_name: str

    @property
    def summaries(self) -> list[EvaluationSummary]:
        """Summaries without raw simulation data."""
        return [
            EvaluationSummary(params=e.params, scores=e.scores)
            for e in self.evaluations
        ]

    def best(self, kpi: str, *, maximize: bool = True) -> EvaluationSummary:
        """Return the evaluation with the best score for the given KPI.

        Args:
            kpi: Name of the KPI to optimize.
            maximize: If True, return the evaluation with the highest score.
        """
        if not self.evaluations:
            raise ValueError("No evaluations to search")
        if kpi not in self.kpi_names:
            raise ValueError(f"KPI '{kpi}' not found in {self.kpi_names}")

        best_eval = max(
            self.evaluations,
            key=lambda e: e.scores[kpi] if maximize else -e.scores[kpi],
        )
        return EvaluationSummary(params=best_eval.params, scores=best_eval.scores)

    def best_by_objective(self, objective: Objective) -> EvaluationSummary:
        """Return the evaluation with the best objective score.

        The objective reduces multiple KPI scores to a single scalar.
        Higher is better.
        """
        if not self.evaluations:
            raise ValueError("No evaluations to search")

        best_eval = max(
            self.evaluations,
            key=lambda e: objective.score(e.scores),
        )
        return EvaluationSummary(params=best_eval.params, scores=best_eval.scores)

    def to_dataframe(self) -> Any:
        """Convert to pandas DataFrame. Requires ``pandas`` installed."""
        try:
            import pandas as pd  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install gds-psuu[pandas]"
            ) from exc

        rows: list[dict[str, Any]] = []
        for ev in self.evaluations:
            row: dict[str, Any] = dict(ev.params)
            row.update(ev.scores)
            rows.append(row)
        return pd.DataFrame(rows)
