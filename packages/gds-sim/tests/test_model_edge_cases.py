"""Tests for Model/Simulation/Experiment error paths and edge cases."""

from __future__ import annotations

from typing import Any

import pytest

import gds_sim


def _noop_suf(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> tuple[str, Any]:
    return "x", state["x"]


def _increment_suf(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> tuple[str, Any]:
    return "x", state["x"] + 1


class TestModelErrorPaths:
    def test_suf_references_nonexistent_key(self) -> None:
        """SUF referencing a key not in initial_state should raise ValueError."""
        with pytest.raises(ValueError, match="not found in initial_state"):
            gds_sim.Model(
                initial_state={"x": 1},
                state_update_blocks=[
                    {"policies": {}, "variables": {"nonexistent": _noop_suf}}
                ],
            )

    def test_suf_references_nonexistent_key_in_second_block(self) -> None:
        """Error message should identify block index."""
        with pytest.raises(ValueError, match="State update block 1"):
            gds_sim.Model(
                initial_state={"x": 1},
                state_update_blocks=[
                    {"policies": {}, "variables": {"x": _noop_suf}},
                    {"policies": {}, "variables": {"missing": _noop_suf}},
                ],
            )

    def test_error_message_includes_available_keys(self) -> None:
        """Error message should list available keys."""
        with pytest.raises(ValueError, match=r"Available keys.*x"):
            gds_sim.Model(
                initial_state={"x": 1},
                state_update_blocks=[{"policies": {}, "variables": {"y": _noop_suf}}],
            )


class TestModelEdgeCases:
    def test_single_block_model(self) -> None:
        """Model with a single block and single variable."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )
        sim = gds_sim.Simulation(model=model, timesteps=3)
        rows = sim.run().to_list()
        # 1 block = 1 substep per timestep, plus initial row = 1 + 3 = 4
        assert len(rows) == 4
        assert rows[-1]["x"] == 3

    def test_empty_params_gives_single_empty_subset(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
            params={},
        )
        assert model._param_subsets == [{}]

    def test_single_param_value_gives_single_subset(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
            params={"alpha": [0.5]},
        )
        assert len(model._param_subsets) == 1
        assert model._param_subsets[0] == {"alpha": 0.5}

    def test_three_way_param_sweep(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
            params={"a": [1, 2], "b": [10, 20], "c": [100]},
        )
        # 2 x 2 x 1 = 4 subsets
        assert len(model._param_subsets) == 4

    def test_dict_blocks_coerced_to_state_update_block(self) -> None:
        """Plain dicts should be coerced to StateUpdateBlock instances."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
        )
        assert isinstance(model.state_update_blocks[0], gds_sim.StateUpdateBlock)

    def test_state_update_block_already_typed(self) -> None:
        """Pre-constructed StateUpdateBlock instances should pass through."""
        block = gds_sim.StateUpdateBlock(variables={"x": _noop_suf})
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[block],
        )
        assert len(model.state_update_blocks) == 1

    def test_multiple_state_variables_single_block(self) -> None:
        """Block updating multiple state variables."""

        def suf_y(
            state: dict[str, Any], params: dict[str, Any], **kw: Any
        ) -> tuple[str, Any]:
            return "y", state["y"] * 2

        model = gds_sim.Model(
            initial_state={"x": 0, "y": 1.0},
            state_update_blocks=[
                {"policies": {}, "variables": {"x": _increment_suf, "y": suf_y}}
            ],
        )
        sim = gds_sim.Simulation(model=model, timesteps=3)
        rows = sim.run().to_list()
        final = rows[-1]
        assert final["x"] == 3
        assert final["y"] == 8.0  # 1 * 2^3


class TestSimulationEdgeCases:
    def test_zero_timesteps(self) -> None:
        """Zero timesteps should produce only the initial state row."""
        model = gds_sim.Model(
            initial_state={"x": 42},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
        )
        sim = gds_sim.Simulation(model=model, timesteps=0)
        rows = sim.run().to_list()
        assert len(rows) == 1
        assert rows[0]["x"] == 42
        assert rows[0]["timestep"] == 0

    def test_one_timestep(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )
        sim = gds_sim.Simulation(model=model, timesteps=1)
        rows = sim.run().to_list()
        # initial + 1 timestep * 1 block = 2
        assert len(rows) == 2
        assert rows[-1]["x"] == 1


class TestHooksEdgeCases:
    def test_hooks_called_per_run_in_multi_run(self) -> None:
        """before_run and after_run should be called once per run."""
        before_count: list[int] = []
        after_count: list[int] = []

        def before_run(state: dict[str, Any], params: dict[str, Any]) -> None:
            before_count.append(1)

        def after_run(state: dict[str, Any], params: dict[str, Any]) -> None:
            after_count.append(1)

        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
        )
        hooks = gds_sim.Hooks(before_run=before_run, after_run=after_run)
        sim = gds_sim.Simulation(model=model, timesteps=3, runs=3, hooks=hooks)
        sim.run()
        assert len(before_count) == 3
        assert len(after_count) == 3

    def test_hooks_called_per_subset(self) -> None:
        """Hooks fire once per (subset, run) pair."""
        call_count: list[int] = []

        def before_run(state: dict[str, Any], params: dict[str, Any]) -> None:
            call_count.append(1)

        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
            params={"a": [1, 2, 3]},
        )
        hooks = gds_sim.Hooks(before_run=before_run)
        sim = gds_sim.Simulation(model=model, timesteps=2, runs=2, hooks=hooks)
        sim.run()
        # 3 subsets * 2 runs = 6
        assert len(call_count) == 6

    def test_early_exit_respects_break(self) -> None:
        """after_step returning False at timestep 1 should stop immediately."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )

        def stop_immediately(state: dict[str, Any], t: int) -> bool:
            return False

        hooks = gds_sim.Hooks(after_step=stop_immediately)
        sim = gds_sim.Simulation(model=model, timesteps=100, hooks=hooks)
        rows = sim.run().to_list()
        # initial + 1 timestep (then stopped)
        assert len(rows) == 2
        assert rows[-1]["x"] == 1

    def test_after_step_returning_none_continues(self) -> None:
        """after_step returning None should NOT stop."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )

        def do_nothing(state: dict[str, Any], t: int) -> None:
            pass

        hooks = gds_sim.Hooks(after_step=do_nothing)
        sim = gds_sim.Simulation(model=model, timesteps=5, hooks=hooks)
        rows = sim.run().to_list()
        assert rows[-1]["x"] == 5

    def test_after_step_returning_true_continues(self) -> None:
        """after_step returning True should NOT stop (only False stops)."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )

        def keep_going(state: dict[str, Any], t: int) -> bool:
            return True

        hooks = gds_sim.Hooks(after_step=keep_going)
        sim = gds_sim.Simulation(model=model, timesteps=5, hooks=hooks)
        rows = sim.run().to_list()
        assert rows[-1]["x"] == 5


class TestExperimentEdgeCases:
    def test_single_sim_single_job_sequential(self) -> None:
        """Single sim with 1 subset and 1 run should use sequential path."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )
        sim = gds_sim.Simulation(model=model, timesteps=5, runs=1)
        exp = gds_sim.Experiment(simulations=[sim])
        rows = exp.run().to_list()
        assert rows[-1]["x"] == 5

    def test_experiment_merges_multiple_sims(self) -> None:
        """Experiment with two sims should merge results."""
        model1 = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )
        model2 = gds_sim.Model(
            initial_state={"x": 100},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
        )
        sim1 = gds_sim.Simulation(model=model1, timesteps=3)
        sim2 = gds_sim.Simulation(model=model2, timesteps=3)
        exp = gds_sim.Experiment(simulations=[sim1, sim2], processes=1)
        results = exp.run()
        # Each sim: 1 + 3 = 4 rows, total 8
        assert len(results) == 8

    def test_experiment_processes_none_auto(self) -> None:
        """processes=None should still work (auto-detect)."""
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _increment_suf}}],
            params={"a": [1, 2]},
        )
        sim = gds_sim.Simulation(model=model, timesteps=3, runs=2)
        exp = gds_sim.Experiment(simulations=[sim])
        results = exp.run()
        # 2 subsets * 2 runs * (1 + 3) = 16
        assert len(results) == 16
