"""Tests for Jacobian linearization."""

from __future__ import annotations

import pytest

sympy = pytest.importorskip("sympy")

from gds_symbolic import SymbolicControlModel  # noqa: E402, TC001
from gds_symbolic.linearize import LinearizedSystem  # noqa: E402


class TestLinearizeDecay:
    """dx/dt = -k*x. A = [[-k]], B = [[0]]."""

    def test_a_matrix(self, decay_model: SymbolicControlModel) -> None:
        lin = decay_model.linearize(x0=[0.0], u0=[0.0], param_values={"k": 2.0})
        assert isinstance(lin, LinearizedSystem)
        assert lin.A == [[-2.0]]

    def test_b_matrix(self, decay_model: SymbolicControlModel) -> None:
        lin = decay_model.linearize(x0=[0.0], u0=[0.0], param_values={"k": 1.0})
        # dx/dt = -k*x has no input dependence
        assert lin.B == [[0.0]]

    def test_state_names(self, decay_model: SymbolicControlModel) -> None:
        lin = decay_model.linearize(x0=[0.0], u0=[0.0])
        assert lin.state_names == ["x"]
        assert lin.input_names == ["u"]


class TestLinearizeOscillator:
    """dx/dt = v, dv/dt = -omega^2*x + force.

    A = [[0, 1], [-omega^2, 0]]
    B = [[0], [1]]
    """

    def test_a_matrix(self, oscillator_model: SymbolicControlModel) -> None:
        lin = oscillator_model.linearize(
            x0=[0.0, 0.0], u0=[0.0], param_values={"omega": 3.0}
        )
        assert lin.A[0] == [pytest.approx(0.0), pytest.approx(1.0)]
        assert lin.A[1] == [pytest.approx(-9.0), pytest.approx(0.0)]

    def test_b_matrix(self, oscillator_model: SymbolicControlModel) -> None:
        lin = oscillator_model.linearize(
            x0=[0.0, 0.0], u0=[0.0], param_values={"omega": 1.0}
        )
        # df1/d(force) = 0, df2/d(force) = 1
        assert [[pytest.approx(0.0)], [pytest.approx(1.0)]] == lin.B

    def test_dimensions(self, oscillator_model: SymbolicControlModel) -> None:
        lin = oscillator_model.linearize(
            x0=[0.0, 0.0], u0=[0.0], param_values={"omega": 1.0}
        )
        assert len(lin.A) == 2
        assert len(lin.A[0]) == 2
        assert len(lin.B) == 2
        assert len(lin.B[0]) == 1


class TestLinearizeVanDerPol:
    """dx/dt = v, dv/dt = mu*(1-x^2)*v - x.

    At origin (x=0, v=0):
    A = [[0, 1], [-1, mu]]
    """

    def test_a_at_origin(self, van_der_pol_model: SymbolicControlModel) -> None:
        lin = van_der_pol_model.linearize(
            x0=[0.0, 0.0], u0=[0.0], param_values={"mu": 2.0}
        )
        assert lin.A[0] == [pytest.approx(0.0), pytest.approx(1.0)]
        assert lin.A[1] == [pytest.approx(-1.0), pytest.approx(2.0)]

    def test_a_away_from_origin(self, van_der_pol_model: SymbolicControlModel) -> None:
        """At x=1, v=0, mu=1: A[1] = [-1, 0]."""
        lin = van_der_pol_model.linearize(
            x0=[1.0, 0.0], u0=[0.0], param_values={"mu": 1.0}
        )
        # df2/dx = -2*mu*x*v - 1 = -2*1*1*0 - 1 = -1
        assert lin.A[1][0] == pytest.approx(-1.0)
        # df2/dv = mu*(1-x^2) = 1*(1-1) = 0
        assert lin.A[1][1] == pytest.approx(0.0)


class TestLinearizeOutputEquations:
    """Test C and D matrices from output equations."""

    def test_empty_outputs(self, decay_model: SymbolicControlModel) -> None:
        """No output equations → empty C, D."""
        lin = decay_model.linearize(x0=[0.0], u0=[0.0])
        assert lin.C == []
        assert lin.D == []
        assert lin.output_names == []
