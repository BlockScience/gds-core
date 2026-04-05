"""Tests for symbolic ODE compilation (sympify + lambdify)."""

from __future__ import annotations

import math

import pytest

sympy = pytest.importorskip("sympy")

from gds_domains.symbolic import SymbolicControlModel  # noqa: E402


class TestCompileToODE:
    def test_decay_rhs(self, decay_model: SymbolicControlModel) -> None:
        ode_fn, state_order = decay_model.to_ode_function()
        assert state_order == ["x"]

        # dx/dt = -k*x at x=1, k=2 => -2
        result = ode_fn(0.0, [1.0], {"k": 2.0})
        assert result == [pytest.approx(-2.0)]

    def test_decay_rhs_different_params(
        self, decay_model: SymbolicControlModel
    ) -> None:
        ode_fn, _ = decay_model.to_ode_function()

        # k=0.5, x=4 => -0.5*4 = -2
        result = ode_fn(0.0, [4.0], {"k": 0.5})
        assert result == [pytest.approx(-2.0)]

    def test_oscillator_rhs(self, oscillator_model: SymbolicControlModel) -> None:
        ode_fn, state_order = oscillator_model.to_ode_function()
        assert state_order == ["x", "v"]

        # At x=1, v=0, omega=1, force=0: dx/dt=0, dv/dt=-1
        result = ode_fn(0.0, [1.0, 0.0], {"omega": 1.0, "force": 0.0})
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(-1.0)

    def test_oscillator_with_force(
        self, oscillator_model: SymbolicControlModel
    ) -> None:
        ode_fn, _ = oscillator_model.to_ode_function()

        # At x=0, v=0, omega=1, force=5: dx/dt=0, dv/dt=5
        result = ode_fn(0.0, [0.0, 0.0], {"omega": 1.0, "force": 5.0})
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(5.0)

    def test_van_der_pol_rhs(self, van_der_pol_model: SymbolicControlModel) -> None:
        ode_fn, state_order = van_der_pol_model.to_ode_function()
        assert state_order == ["x", "v"]

        # At x=0, v=1, mu=1: dx/dt=1, dv/dt=mu*(1-0)*1 - 0 = 1
        result = ode_fn(0.0, [0.0, 1.0], {"mu": 1.0})
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(1.0)

    def test_missing_equation_defaults_to_zero(self) -> None:
        """States without equations get dx/dt = 0."""
        from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
        from gds_domains.symbolic import StateEquation

        m = SymbolicControlModel(
            name="partial",
            states=[State(name="x"), State(name="y")],
            inputs=[Input(name="u")],
            sensors=[
                Sensor(name="obs_x", observes=["x"]),
                Sensor(name="obs_y", observes=["y"]),
            ],
            controllers=[
                Controller(
                    name="ctrl",
                    reads=["obs_x", "obs_y", "u"],
                    drives=["x", "y"],
                ),
            ],
            state_equations=[
                StateEquation(state_name="x", expr_str="1.0"),
                # y has no equation
            ],
        )
        ode_fn, _order = m.to_ode_function()
        result = ode_fn(0.0, [0.0, 0.0], {})
        assert result == [pytest.approx(1.0), pytest.approx(0.0)]


class TestIntegrationWithGDSContinuous:
    """Compile symbolic model and run through gds-continuous."""

    def test_decay_integration(self, decay_model: SymbolicControlModel) -> None:
        from gds_continuous import ODEModel, ODESimulation

        ode_fn, state_order = decay_model.to_ode_function()

        model = ODEModel(
            state_names=state_order,
            initial_state={"x": 1.0},
            rhs=ode_fn,
            params={"k": [1.0]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, 3.0),
            t_eval=[0.0, 1.0, 2.0, 3.0],
        )
        results = sim.run()

        x_vals = results.state_array("x")
        for i, t in enumerate([0.0, 1.0, 2.0, 3.0]):
            expected = math.exp(-t)
            assert x_vals[i] == pytest.approx(expected, abs=1e-4)

    def test_oscillator_integration(
        self, oscillator_model: SymbolicControlModel
    ) -> None:
        from gds_continuous import ODEModel, ODESimulation

        ode_fn, state_order = oscillator_model.to_ode_function()

        model = ODEModel(
            state_names=state_order,
            initial_state={"x": 1.0, "v": 0.0},
            rhs=ode_fn,
            params={"omega": [1.0], "force": [0.0]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, math.pi),
            t_eval=[0.0, math.pi / 2, math.pi],
        )
        results = sim.run()

        x_vals = results.state_array("x")
        # x(0)=1, x(pi/2)=0, x(pi)=-1
        assert x_vals[0] == pytest.approx(1.0, abs=1e-4)
        assert x_vals[1] == pytest.approx(0.0, abs=1e-3)
        assert x_vals[2] == pytest.approx(-1.0, abs=1e-3)
