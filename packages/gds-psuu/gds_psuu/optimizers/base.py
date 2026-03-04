"""Abstract base class for optimizers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gds_psuu.space import ParameterSpace
    from gds_psuu.types import KPIScores, ParamPoint


class Optimizer(ABC):
    """Base class for parameter search optimizers.

    Subclasses implement the suggest/observe loop. The optimizer is stateful
    and mutable — it tracks which points have been evaluated and uses that
    information to decide what to try next.
    """

    @abstractmethod
    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        """Initialize the optimizer with the search space and KPI names."""

    @abstractmethod
    def suggest(self) -> ParamPoint:
        """Suggest the next parameter point to evaluate."""

    @abstractmethod
    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        """Record the result of evaluating a parameter point."""

    @abstractmethod
    def is_exhausted(self) -> bool:
        """Return True if no more suggestions are available."""
