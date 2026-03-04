"""Evaluation bridge between parameter points and gds-sim."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gds_sim import Model, Results, Simulation
from pydantic import BaseModel, ConfigDict

from gds_psuu.kpi import KPI  # noqa: TC001
from gds_psuu.types import KPIScores, ParamPoint  # noqa: TC001


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating a single parameter point."""

    params: ParamPoint
    scores: KPIScores
    results: Results
    run_count: int


class Evaluator(BaseModel):
    """Runs a gds-sim simulation for a given parameter point and scores KPIs."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    base_model: Model
    kpis: list[KPI]
    timesteps: int
    runs: int

    def evaluate(self, params: ParamPoint) -> EvaluationResult:
        """Evaluate a single parameter point.

        Injects params as singleton lists into the model, runs the simulation,
        and computes KPI scores.
        """
        # Build params dict: each value as a singleton list for gds-sim
        sim_params: dict[str, list[Any]] = {k: [v] for k, v in params.items()}

        # Construct a new Model with the injected params
        model = Model(
            initial_state=dict(self.base_model.initial_state),
            state_update_blocks=list(self.base_model.state_update_blocks),
            params=sim_params,
        )

        sim = Simulation(model=model, timesteps=self.timesteps, runs=self.runs)
        results = sim.run()

        scores: KPIScores = {kpi.name: kpi.fn(results) for kpi in self.kpis}

        return EvaluationResult(
            params=params,
            scores=scores,
            results=results,
            run_count=self.runs,
        )
