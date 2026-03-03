"""Tests for the core execution engine."""

from __future__ import annotations

from typing import Any

import gds_sim


class TestSingleRun:
    def test_basic_execution(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=10)
        results = sim.run()
        # 2 blocks → 2 substeps per timestep, plus initial row
        # rows = 1 + 10 * 2 = 21
        assert len(results) == 21

    def test_initial_state_preserved(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=5)
        results = sim.run()
        rows = results.to_list()
        assert rows[0]["timestep"] == 0
        assert rows[0]["substep"] == 0
        assert rows[0]["population"] == 100.0
        assert rows[0]["food"] == 50.0

    def test_population_grows(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=10)
        rows = sim.run().to_list()
        # Population should increase (birth_rate > death_rate by default)
        initial_pop = rows[0]["population"]
        # Get the last substep of the last timestep (block 1 updates population)
        final_pop = next(r for r in rows if r["timestep"] == 10 and r["substep"] == 1)[
            "population"
        ]
        assert final_pop > initial_pop

    def test_food_decreases(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=10)
        rows = sim.run().to_list()
        initial_food = rows[0]["food"]
        final_food = next(r for r in rows if r["timestep"] == 10 and r["substep"] == 2)[
            "food"
        ]
        assert final_food < initial_food

    def test_metadata_columns(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=3)
        rows = sim.run().to_list()
        for row in rows:
            assert "timestep" in row
            assert "substep" in row
            assert "run" in row
            assert "subset" in row


class TestMultiSubset:
    def test_param_sweep_runs_all_subsets(self, sweep_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=sweep_model, timesteps=5)
        rows = sim.run().to_list()
        subsets = {r["subset"] for r in rows}
        assert subsets == {0, 1}

    def test_param_sweep_different_results(self, sweep_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=sweep_model, timesteps=10)
        rows = sim.run().to_list()
        # Get final population for each subset (different birth rates)
        final_subset_0 = next(
            r
            for r in rows
            if r["timestep"] == 10 and r["substep"] == 1 and r["subset"] == 0
        )["population"]
        final_subset_1 = next(
            r
            for r in rows
            if r["timestep"] == 10 and r["substep"] == 1 and r["subset"] == 1
        )["population"]
        # birth_rate=0.05 should grow faster than birth_rate=0.03
        assert final_subset_1 > final_subset_0


class TestMultiRun:
    def test_multiple_runs(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=5, runs=3)
        rows = sim.run().to_list()
        runs = {r["run"] for r in rows}
        assert runs == {0, 1, 2}

    def test_runs_are_independent(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=5, runs=2)
        rows = sim.run().to_list()
        # Each run starts from the same initial state
        run0_initial = next(r for r in rows if r["run"] == 0 and r["timestep"] == 0)
        run1_initial = next(r for r in rows if r["run"] == 1 and r["timestep"] == 0)
        assert run0_initial["population"] == run1_initial["population"]


class TestHooks:
    def test_before_run_hook(self, simple_model: gds_sim.Model) -> None:
        called: list[bool] = []

        def before_run(state: dict[str, Any], params: dict[str, Any]) -> None:
            called.append(True)

        hooks = gds_sim.Hooks(before_run=before_run)
        sim = gds_sim.Simulation(model=simple_model, timesteps=5, hooks=hooks)
        sim.run()
        assert len(called) == 1

    def test_after_run_hook(self, simple_model: gds_sim.Model) -> None:
        final_states: list[dict[str, Any]] = []

        def after_run(state: dict[str, Any], params: dict[str, Any]) -> None:
            final_states.append(dict(state))

        hooks = gds_sim.Hooks(after_run=after_run)
        sim = gds_sim.Simulation(model=simple_model, timesteps=5, hooks=hooks)
        sim.run()
        assert len(final_states) == 1
        assert final_states[0]["population"] > 100.0

    def test_after_step_hook(self, simple_model: gds_sim.Model) -> None:
        step_count: list[int] = []

        def after_step(state: dict[str, Any], t: int) -> None:
            step_count.append(t)

        hooks = gds_sim.Hooks(after_step=after_step)
        sim = gds_sim.Simulation(model=simple_model, timesteps=10, hooks=hooks)
        sim.run()
        assert step_count == list(range(1, 11))

    def test_early_exit(self) -> None:
        def suf_x(
            state: dict[str, Any], params: dict[str, Any], **kw: Any
        ) -> tuple[str, Any]:
            return "x", state["x"] + 1

        def stop_at_5(state: dict[str, Any], t: int) -> bool | None:
            if state["x"] >= 5:
                return False
            return None

        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": suf_x}}],
        )
        hooks = gds_sim.Hooks(after_step=stop_at_5)
        sim = gds_sim.Simulation(model=model, timesteps=100, hooks=hooks)
        rows = sim.run().to_list()
        max_x = max(r["x"] for r in rows)
        assert max_x == 5  # stopped at 5, not 100


class TestNoPolicy:
    def test_block_without_policies(self) -> None:
        def suf_x(
            state: dict[str, Any], params: dict[str, Any], **kw: Any
        ) -> tuple[str, Any]:
            return "x", state["x"] + 1

        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": suf_x}}],
        )
        sim = gds_sim.Simulation(model=model, timesteps=5)
        rows = sim.run().to_list()
        final = rows[-1]
        assert final["x"] == 5
