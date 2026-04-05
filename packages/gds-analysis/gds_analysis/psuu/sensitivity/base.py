"""Analyzer ABC and SensitivityResult."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from gds_analysis.psuu.evaluation import Evaluator
    from gds_analysis.psuu.space import ParameterSpace


class SensitivityResult(BaseModel):
    """Per-KPI, per-parameter sensitivity indices."""

    model_config = ConfigDict(frozen=True)

    indices: dict[str, dict[str, dict[str, float]]]
    """kpi_name -> param_name -> {metric_name: value}."""
    method: str

    def ranking(self, kpi: str, *, metric: str = "mean_effect") -> list[str]:
        """Rank parameters by a metric for a given KPI, descending."""
        kpi_indices = self.indices[kpi]
        return sorted(
            kpi_indices,
            key=lambda p: abs(kpi_indices[p][metric]),
            reverse=True,
        )

    def to_dataframe(self) -> Any:
        """Convert to pandas DataFrame. Requires ``pandas`` installed."""
        try:
            import pandas as pd  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: uv add gds-psuu[pandas]"
            ) from exc

        rows: list[dict[str, Any]] = []
        for kpi, params in self.indices.items():
            for param, metrics in params.items():
                row: dict[str, Any] = {"kpi": kpi, "param": param}
                row.update(metrics)
                rows.append(row)
        return pd.DataFrame(rows)


class Analyzer(ABC):
    """Base class for sensitivity analyzers."""

    @abstractmethod
    def analyze(self, evaluator: Evaluator, space: ParameterSpace) -> SensitivityResult:
        """Run sensitivity analysis and return results."""
