"""Tests for the sweep orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gds.parameters import ParameterDef, ParameterSchema
from gds.types.typedef import TypeDef

from gds_analysis.psuu import (
    KPI,
    Continuous,
    Discrete,
    GridSearchOptimizer,
    ParameterSpace,
    RandomSearchOptimizer,
    Sweep,
    final_state_mean,
)

if TYPE_CHECKING:
    from gds_sim import Model


class TestSweep:
    def test_grid_sweep(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=3),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 3
        assert results.kpi_names == ["final_pop"]
        assert results.optimizer_name == "GridSearchOptimizer"

    def test_random_sweep(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=RandomSearchOptimizer(n_samples=5, seed=42),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 5

    def test_best_params(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=3),
            timesteps=10,
            runs=1,
        )
        results = sweep.run()
        best = results.best("final_pop", maximize=True)
        # Highest growth rate → highest population
        assert best.params["growth_rate"] == 0.1

    def test_sweep_with_discrete_params(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={
                    "growth_rate": Continuous(min_val=0.01, max_val=0.05),
                    "label": Discrete(values=("x", "y")),
                }
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        # 2 continuous * 2 discrete = 4
        assert len(results.evaluations) == 4

    def test_sweep_multiple_runs(self, simple_model: Model) -> None:
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=3,
        )
        results = sweep.run()
        assert len(results.evaluations) == 2
        for ev in results.evaluations:
            assert ev.run_count == 3


class TestSweepSchemaValidation:
    """Tests for optional parameter_schema validation in Sweep.run()."""

    def test_valid_schema_runs_successfully(self, simple_model: Model) -> None:
        rate_td = TypeDef(name="Rate", python_type=float)
        schema = ParameterSchema().add(
            ParameterDef(name="growth_rate", typedef=rate_td, bounds=(0.0, 1.0))
        )
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
            parameter_schema=schema,
        )
        results = sweep.run()
        assert len(results.evaluations) == 2

    def test_violated_schema_raises(self, simple_model: Model) -> None:
        rate_td = TypeDef(name="Rate", python_type=float)
        schema = ParameterSchema().add(
            ParameterDef(name="growth_rate", typedef=rate_td, bounds=(0.0, 0.05))
        )
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
            parameter_schema=schema,
        )
        with pytest.raises(ValueError, match="violates declared schema"):
            sweep.run()

    def test_no_schema_skips_validation(self, simple_model: Model) -> None:
        """Sweep without parameter_schema should run without validation."""
        sweep = Sweep(
            model=simple_model,
            space=ParameterSpace(
                params={"growth_rate": Continuous(min_val=0.01, max_val=0.1)}
            ),
            kpis=[
                KPI(
                    name="final_pop",
                    fn=lambda r: final_state_mean(r, "population"),
                )
            ],
            optimizer=GridSearchOptimizer(n_steps=2),
            timesteps=5,
            runs=1,
        )
        results = sweep.run()
        assert len(results.evaluations) == 2
