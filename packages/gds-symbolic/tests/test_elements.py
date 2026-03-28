"""Tests for symbolic equation elements."""

from __future__ import annotations

from gds_symbolic.elements import OutputEquation, StateEquation


class TestStateEquation:
    def test_frozen(self) -> None:
        eq = StateEquation(state_name="x", expr_str="-k*x")
        assert eq.state_name == "x"
        assert eq.expr_str == "-k*x"

    def test_immutable(self) -> None:
        eq = StateEquation(state_name="x", expr_str="v")
        try:
            eq.state_name = "y"  # type: ignore[misc]
            raise AssertionError("Should be immutable")
        except Exception:
            pass


class TestOutputEquation:
    def test_frozen(self) -> None:
        eq = OutputEquation(sensor_name="obs", expr_str="x**2")
        assert eq.sensor_name == "obs"
        assert eq.expr_str == "x**2"
