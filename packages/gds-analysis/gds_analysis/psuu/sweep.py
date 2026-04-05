"""Sweep orchestrator — the main entry point for parameter search."""

from __future__ import annotations

from typing import Any

from gds_sim import Model  # noqa: TC002
from pydantic import BaseModel, ConfigDict

from gds_analysis.psuu.evaluation import EvaluationResult, Evaluator
from gds_analysis.psuu.kpi import KPI  # noqa: TC001
from gds_analysis.psuu.objective import Objective  # noqa: TC001
from gds_analysis.psuu.optimizers.base import Optimizer  # noqa: TC001
from gds_analysis.psuu.results import SweepResults
from gds_analysis.psuu.space import ParameterSpace  # noqa: TC001


class Sweep(BaseModel):
    """Orchestrates parameter space search.

    Drives the optimizer suggest/observe loop, delegating evaluation
    to the Evaluator which bridges to gds-sim.

    If ``parameter_schema`` is provided, the sweep validates the
    parameter space against the declared schema before starting.
    Validation errors raise ``ValueError``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    model: Model
    space: ParameterSpace
    kpis: list[KPI]
    optimizer: Optimizer
    objective: Objective | None = None
    timesteps: int = 100
    runs: int = 1
    parameter_schema: Any = None

    def run(self) -> SweepResults:
        """Execute the sweep and return results."""
        if self.parameter_schema is not None:
            self._validate_schema()

        kpi_names = [k.name for k in self.kpis]
        self.optimizer.setup(self.space, kpi_names)

        evaluator = Evaluator(
            base_model=self.model,
            kpis=list(self.kpis),
            timesteps=self.timesteps,
            runs=self.runs,
        )

        evaluations: list[EvaluationResult] = []
        while not self.optimizer.is_exhausted():
            params = self.optimizer.suggest()
            result = evaluator.evaluate(params)
            self.optimizer.observe(params, result.scores)
            evaluations.append(result)

        return SweepResults(
            evaluations=evaluations,
            kpi_names=kpi_names,
            optimizer_name=type(self.optimizer).__name__,
        )

    def _validate_schema(self) -> None:
        """Validate the parameter space against the declared schema."""
        from gds.verification.findings import Severity

        from gds_analysis.psuu.checks import check_parameter_space_compatibility

        findings = check_parameter_space_compatibility(
            self.space, self.parameter_schema
        )
        errors = [f for f in findings if f.severity == Severity.ERROR]
        if errors:
            messages = "; ".join(f.message for f in errors)
            raise ValueError(f"Parameter space violates declared schema: {messages}")
