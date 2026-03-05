"""Sweep orchestrator — the main entry point for parameter search."""

from __future__ import annotations

from gds_sim import Model  # noqa: TC002
from pydantic import BaseModel, ConfigDict

from gds_psuu.evaluation import EvaluationResult, Evaluator
from gds_psuu.kpi import KPI  # noqa: TC001
from gds_psuu.objective import Objective  # noqa: TC001
from gds_psuu.optimizers.base import Optimizer  # noqa: TC001
from gds_psuu.results import SweepResults
from gds_psuu.space import ParameterSpace  # noqa: TC001


class Sweep(BaseModel):
    """Orchestrates parameter space search.

    Drives the optimizer suggest/observe loop, delegating evaluation
    to the Evaluator which bridges to gds-sim.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    model: Model
    space: ParameterSpace
    kpis: list[KPI]
    optimizer: Optimizer
    objective: Objective | None = None
    timesteps: int = 100
    runs: int = 1

    def run(self) -> SweepResults:
        """Execute the sweep and return results."""
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
