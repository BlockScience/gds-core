"""Tests for SymbolicControlModel construction and validation."""

from __future__ import annotations

import pytest

from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.symbolic import StateEquation, SymbolicControlModel
from gds_domains.symbolic.errors import SymbolicError


class TestValidConstruction:
    def test_inherits_control_model(self, decay_model: SymbolicControlModel) -> None:
        assert decay_model.name == "decay"
        assert len(decay_model.states) == 1
        assert len(decay_model.state_equations) == 1

    def test_compile_still_works(self, decay_model: SymbolicControlModel) -> None:
        """Structural GDS compilation is unaffected by symbolic annotations."""
        spec = decay_model.compile()
        assert spec.name == "decay"
        assert len(spec.blocks) > 0

    def test_compile_system_still_works(
        self, decay_model: SymbolicControlModel
    ) -> None:
        ir = decay_model.compile_system()
        assert ir.name == "decay"

    def test_multi_state(self, oscillator_model: SymbolicControlModel) -> None:
        assert len(oscillator_model.states) == 2
        assert len(oscillator_model.state_equations) == 2

    def test_symbolic_params(self, decay_model: SymbolicControlModel) -> None:
        assert decay_model.symbolic_params == ["k"]

    def test_no_equations_allowed(self) -> None:
        """A model with no state equations is valid (all dx/dt = 0)."""
        m = SymbolicControlModel(
            name="static",
            states=[State(name="x")],
            inputs=[Input(name="u")],
            sensors=[Sensor(name="obs", observes=["x"])],
            controllers=[
                Controller(name="ctrl", reads=["obs", "u"], drives=["x"]),
            ],
        )
        assert m.state_equations == []


class TestInvalidConstruction:
    def test_undeclared_state_in_equation(self) -> None:
        with pytest.raises(SymbolicError, match="undeclared state"):
            SymbolicControlModel(
                name="bad",
                states=[State(name="x")],
                inputs=[Input(name="u")],
                sensors=[Sensor(name="obs", observes=["x"])],
                controllers=[
                    Controller(name="ctrl", reads=["obs", "u"], drives=["x"]),
                ],
                state_equations=[
                    StateEquation(state_name="y", expr_str="x"),
                ],
            )

    def test_duplicate_state_equations(self) -> None:
        with pytest.raises(SymbolicError, match="Duplicate"):
            SymbolicControlModel(
                name="bad",
                states=[State(name="x")],
                inputs=[Input(name="u")],
                sensors=[Sensor(name="obs", observes=["x"])],
                controllers=[
                    Controller(name="ctrl", reads=["obs", "u"], drives=["x"]),
                ],
                state_equations=[
                    StateEquation(state_name="x", expr_str="1"),
                    StateEquation(state_name="x", expr_str="2"),
                ],
            )

    def test_param_conflicts_with_state(self) -> None:
        with pytest.raises(SymbolicError, match="conflicts"):
            SymbolicControlModel(
                name="bad",
                states=[State(name="x")],
                inputs=[Input(name="u")],
                sensors=[Sensor(name="obs", observes=["x"])],
                controllers=[
                    Controller(name="ctrl", reads=["obs", "u"], drives=["x"]),
                ],
                symbolic_params=["x"],
            )
