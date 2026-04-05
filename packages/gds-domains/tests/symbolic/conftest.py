"""Shared fixtures for gds-symbolic tests."""

from __future__ import annotations

import pytest

from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.symbolic import StateEquation, SymbolicControlModel


@pytest.fixture
def decay_model() -> SymbolicControlModel:
    """Single-state exponential decay: dx/dt = -k*x."""
    return SymbolicControlModel(
        name="decay",
        states=[State(name="x")],
        inputs=[Input(name="u")],
        sensors=[Sensor(name="obs", observes=["x"])],
        controllers=[
            Controller(name="ctrl", reads=["obs", "u"], drives=["x"]),
        ],
        state_equations=[
            StateEquation(state_name="x", expr_str="-k*x"),
        ],
        symbolic_params=["k"],
    )


@pytest.fixture
def oscillator_model() -> SymbolicControlModel:
    """Harmonic oscillator: dx/dt = v, dv/dt = -omega**2 * x."""
    return SymbolicControlModel(
        name="oscillator",
        states=[State(name="x"), State(name="v")],
        inputs=[Input(name="force")],
        sensors=[
            Sensor(name="pos_sensor", observes=["x"]),
            Sensor(name="vel_sensor", observes=["v"]),
        ],
        controllers=[
            Controller(
                name="actuator",
                reads=["pos_sensor", "vel_sensor", "force"],
                drives=["x", "v"],
            ),
        ],
        state_equations=[
            StateEquation(state_name="x", expr_str="v"),
            StateEquation(state_name="v", expr_str="-omega**2 * x + force"),
        ],
        symbolic_params=["omega"],
    )


@pytest.fixture
def van_der_pol_model() -> SymbolicControlModel:
    """Van der Pol oscillator: dx/dt = v, dv/dt = mu*(1-x**2)*v - x."""
    return SymbolicControlModel(
        name="van_der_pol",
        states=[State(name="x"), State(name="v")],
        inputs=[Input(name="u")],
        sensors=[Sensor(name="obs", observes=["x"])],
        controllers=[
            Controller(name="ctrl", reads=["obs", "u"], drives=["x", "v"]),
        ],
        state_equations=[
            StateEquation(state_name="x", expr_str="v"),
            StateEquation(state_name="v", expr_str="mu*(1 - x**2)*v - x"),
        ],
        symbolic_params=["mu"],
    )
