"""Composable objective functions for multi-KPI optimization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_analysis.psuu.errors import PsuuValidationError
from gds_analysis.psuu.types import KPIScores  # noqa: TC001


class Objective(BaseModel, ABC):
    """Reduces KPIScores to a single scalar for optimizer consumption."""

    model_config = ConfigDict(frozen=True)

    @abstractmethod
    def score(self, kpi_scores: KPIScores) -> float:
        """Compute a scalar objective value from KPI scores."""


class SingleKPI(Objective):
    """Optimize a single KPI."""

    name: str
    maximize: bool = True

    def score(self, kpi_scores: KPIScores) -> float:
        val = kpi_scores[self.name]
        return val if self.maximize else -val


class WeightedSum(Objective):
    """Weighted linear combination of KPIs.

    Use negative weights to minimize a KPI.
    """

    weights: dict[str, float]

    @model_validator(mode="after")
    def _validate_nonempty(self) -> Self:
        if not self.weights:
            raise PsuuValidationError("WeightedSum must have at least 1 weight")
        return self

    def score(self, kpi_scores: KPIScores) -> float:
        return sum(w * kpi_scores[k] for k, w in self.weights.items())
