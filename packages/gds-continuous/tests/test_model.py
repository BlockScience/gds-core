"""Tests for ODEModel, ODESimulation, ODEExperiment construction and validation."""

from __future__ import annotations

from typing import Any

import pytest

from gds_continuous.model import ODEExperiment, ODEModel, ODESimulation


def _trivial_rhs(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    return [0.0]


class TestODEModelValid:
    """Valid construction cases."""

    def test_single_state(self) -> None:
        m = ODEModel(
            state_names=["x"],
            initial_state={"x": 0.0},
            rhs=_trivial_rhs,
        )
        assert m.state_names == ["x"]
        assert m.y0() == [0.0]

    def test_multi_state(self) -> None:
        def rhs(t: float, y: list[float], p: dict) -> list[float]:
            return [0.0, 0.0, 0.0]

        m = ODEModel(
            state_names=["x", "v", "a"],
            initial_state={"x": 1.0, "v": 2.0, "a": 3.0},
            rhs=rhs,
        )
        assert m.y0() == [1.0, 2.0, 3.0]

    def test_param_sweep_expansion(self) -> None:
        m = ODEModel(
            state_names=["x"],
            initial_state={"x": 0.0},
            rhs=_trivial_rhs,
            params={"a": [1, 2], "b": [10, 20]},
        )
        assert len(m._param_subsets) == 4

    def test_no_params_single_subset(self) -> None:
        m = ODEModel(
            state_names=["x"],
            initial_state={"x": 0.0},
            rhs=_trivial_rhs,
        )
        assert m._param_subsets == [{}]

    def test_state_order_preserved(self) -> None:
        def rhs(t: float, y: list[float], p: dict) -> list[float]:
            return [0.0, 0.0]

        m = ODEModel(
            state_names=["beta", "alpha"],
            initial_state={"beta": 10.0, "alpha": 20.0},
            rhs=rhs,
        )
        assert m._state_order == ["beta", "alpha"]
        assert m.y0() == [10.0, 20.0]

    def test_with_output_fn(self) -> None:
        def out_fn(t: float, y: list[float], p: dict) -> list[float]:
            return [y[0] ** 2]

        m = ODEModel(
            state_names=["x"],
            initial_state={"x": 1.0},
            rhs=_trivial_rhs,
            output_fn=out_fn,
            output_names=["x_squared"],
        )
        assert m.output_names == ["x_squared"]


class TestODEModelInvalid:
    """Construction validation errors."""

    def test_missing_initial_state_key(self) -> None:
        with pytest.raises(ValueError, match="missing keys"):
            ODEModel(
                state_names=["x", "v"],
                initial_state={"x": 0.0},
                rhs=_trivial_rhs,
            )

    def test_extra_initial_state_key(self) -> None:
        with pytest.raises(ValueError, match="extra keys"):
            ODEModel(
                state_names=["x"],
                initial_state={"x": 0.0, "y": 1.0},
                rhs=_trivial_rhs,
            )

    def test_output_fn_without_names(self) -> None:
        def out_fn(t: float, y: list[float], p: dict) -> list[float]:
            return [y[0]]

        with pytest.raises(ValueError, match="output_names must be provided"):
            ODEModel(
                state_names=["x"],
                initial_state={"x": 0.0},
                rhs=_trivial_rhs,
                output_fn=out_fn,
            )


class TestODESimulation:
    """ODESimulation construction."""

    def test_defaults(self, decay_model: ODEModel) -> None:
        sim = ODESimulation(model=decay_model, t_span=(0.0, 1.0))
        assert sim.solver == "RK45"
        assert sim.rtol == 1e-6
        assert sim.atol == 1e-9
        assert sim.runs == 1
        assert sim.t_eval is None

    def test_custom_solver(self, decay_model: ODEModel) -> None:
        sim = ODESimulation(
            model=decay_model,
            t_span=(0.0, 1.0),
            solver="Radau",
            rtol=1e-8,
            atol=1e-12,
        )
        assert sim.solver == "Radau"
        assert sim.rtol == 1e-8


class TestODEExperiment:
    """ODEExperiment construction."""

    def test_multi_simulation(self, decay_model: ODEModel) -> None:
        sim1 = ODESimulation(model=decay_model, t_span=(0.0, 1.0))
        sim2 = ODESimulation(model=decay_model, t_span=(0.0, 5.0))
        exp = ODEExperiment(simulations=[sim1, sim2])
        assert len(exp.simulations) == 2
