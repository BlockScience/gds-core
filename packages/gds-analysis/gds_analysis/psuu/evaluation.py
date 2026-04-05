"""Evaluation bridge between parameter points and gds-sim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gds_sim import Model, Results, Simulation
from pydantic import BaseModel, ConfigDict

from gds_analysis.psuu.kpi import KPI  # noqa: TC001
from gds_analysis.psuu.types import KPIScores, ParamPoint  # noqa: TC001


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating a single parameter point."""

    params: ParamPoint
    scores: KPIScores
    results: Results
    run_count: int
    distributions: dict[str, list[float]] = field(default_factory=dict)
    """Per-run metric values for metric-based KPIs."""


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
        and computes KPI scores. For metric-based KPIs, also records per-run
        distributions.
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

        scores: KPIScores = {}
        distributions: dict[str, list[float]] = {}

        for kpi in self.kpis:
            scores[kpi.name] = kpi.compute(results)
            if kpi.metric is not None:
                distributions[kpi.name] = kpi.per_run(results)

        return EvaluationResult(
            params=params,
            scores=scores,
            results=results,
            run_count=self.runs,
            distributions=distributions,
        )
