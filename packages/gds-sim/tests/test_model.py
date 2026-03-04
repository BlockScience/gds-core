"""Tests for Model validation, param sweep expansion, and error handling."""

from __future__ import annotations

from typing import Any

import pytest

import gds_sim


def _noop_suf(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> tuple[str, Any]:
    return "x", state["x"]


class TestModelValidation:
    def test_basic_construction(self, simple_model: gds_sim.Model) -> None:
        assert simple_model._state_keys == ["population", "food"]
        assert len(simple_model.state_update_blocks) == 2
        assert len(simple_model._param_subsets) == 1  # no params → single empty subset

    def test_invalid_suf_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="not found in initial_state"):
            gds_sim.Model(
                initial_state={"x": 1},
                state_update_blocks=[
                    {"policies": {}, "variables": {"missing": _noop_suf}}
                ],
            )

    def test_param_sweep_expansion(self, sweep_model: gds_sim.Model) -> None:
        # birth_rate=[0.03, 0.05] x death_rate=[0.01] -> 2 subsets
        assert len(sweep_model._param_subsets) == 2
        assert sweep_model._param_subsets[0] == {"birth_rate": 0.03, "death_rate": 0.01}
        assert sweep_model._param_subsets[1] == {"birth_rate": 0.05, "death_rate": 0.01}

    def test_param_sweep_cartesian(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
            params={"a": [1, 2], "b": [10, 20]},
        )
        assert len(model._param_subsets) == 4  # 2 x 2

    def test_empty_params_single_subset(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
        )
        assert model._param_subsets == [{}]

    def test_dict_blocks_coerced(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _noop_suf}}],
        )
        assert isinstance(model.state_update_blocks[0], gds_sim.StateUpdateBlock)


class TestSimulation:
    def test_defaults(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model)
        assert sim.timesteps == 100
        assert sim.runs == 1
        assert sim.history is None

    def test_custom_timesteps(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=500, runs=3)
        assert sim.timesteps == 500
        assert sim.runs == 3


class TestExperiment:
    def test_construction(self, simple_model: gds_sim.Model) -> None:
        sim = gds_sim.Simulation(model=simple_model, timesteps=10)
        exp = gds_sim.Experiment(simulations=[sim])
        assert len(exp.simulations) == 1
        assert exp.processes is None
