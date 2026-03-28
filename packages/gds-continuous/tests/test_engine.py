"""Tests for the ODE integration engine."""

from __future__ import annotations

import math
from typing import Any

import pytest

from gds_continuous.model import ODEModel, ODESimulation
from gds_continuous.results import ODEResults


class TestExponentialDecay:
    """dx/dt = -k*x, exact solution: x(t) = x0 * exp(-k*t)."""

    def test_basic_integration(self, decay_sim: ODESimulation) -> None:
        results = decay_sim.run()
        assert isinstance(results, ODEResults)
        assert len(results) == 101

    def test_accuracy(self, decay_sim: ODESimulation) -> None:
        results = decay_sim.run()
        times = results.times
        x_vals = results.state_array("x")

        for t, x in zip(times, x_vals, strict=True):
            expected = math.exp(-t)
            assert abs(x - expected) < 1e-5, f"t={t}: got {x}, expected {expected}"

    def test_initial_state_preserved(self, decay_sim: ODESimulation) -> None:
        results = decay_sim.run()
        assert results.state_array("x")[0] == pytest.approx(1.0)

    def test_final_state_decayed(self, decay_sim: ODESimulation) -> None:
        results = decay_sim.run()
        x_final = results.state_array("x")[-1]
        assert x_final == pytest.approx(math.exp(-5.0), abs=1e-5)


class TestHarmonicOscillator:
    """dx/dt = v, dv/dt = -omega^2*x. Exact: x(t) = cos(t), v(t) = -sin(t)."""

    def test_basic_integration(self, oscillator_sim: ODESimulation) -> None:
        results = oscillator_sim.run()
        assert isinstance(results, ODEResults)
        assert len(results) == 201

    def test_position_accuracy(self, oscillator_sim: ODESimulation) -> None:
        results = oscillator_sim.run()
        times = results.times
        x_vals = results.state_array("x")

        for t, x in zip(times, x_vals, strict=True):
            expected = math.cos(t)
            assert abs(x - expected) < 1e-4, f"t={t}: got {x}, expected {expected}"

    def test_velocity_accuracy(self, oscillator_sim: ODESimulation) -> None:
        results = oscillator_sim.run()
        times = results.times
        v_vals = results.state_array("v")

        for t, v in zip(times, v_vals, strict=True):
            expected = -math.sin(t)
            assert abs(v - expected) < 1e-4, f"t={t}: got {v}, expected {expected}"

    def test_energy_conservation(self, oscillator_sim: ODESimulation) -> None:
        """Total energy E = 0.5*(x^2 + v^2) should be conserved."""
        results = oscillator_sim.run()
        x_vals = results.state_array("x")
        v_vals = results.state_array("v")

        e0 = 0.5 * (x_vals[0] ** 2 + v_vals[0] ** 2)
        for i in range(len(x_vals)):
            e = 0.5 * (x_vals[i] ** 2 + v_vals[i] ** 2)
            assert e == pytest.approx(e0, abs=1e-6)


class TestParameterSweep:
    """Parameter sweep across multiple subsets."""

    def test_two_decay_rates(self) -> None:
        def decay(t: float, y: list[float], p: dict[str, Any]) -> list[float]:
            return [-p["k"] * y[0]]

        model = ODEModel(
            state_names=["x"],
            initial_state={"x": 1.0},
            rhs=decay,
            params={"k": [1.0, 2.0]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, 1.0),
            t_eval=[0.0, 1.0],
        )
        results = sim.run()

        # 2 subsets * 2 time points = 4 rows
        assert len(results) == 4

        rows = results.to_list()
        # subset=0 (k=1): x(1) = exp(-1)
        subset0_final = [r for r in rows if r["subset"] == 0 and r["time"] == 1.0]
        assert len(subset0_final) == 1
        assert subset0_final[0]["x"] == pytest.approx(math.exp(-1.0), abs=1e-5)

        # subset=1 (k=2): x(1) = exp(-2)
        subset1_final = [r for r in rows if r["subset"] == 1 and r["time"] == 1.0]
        assert len(subset1_final) == 1
        assert subset1_final[0]["x"] == pytest.approx(math.exp(-2.0), abs=1e-5)


class TestMultipleRuns:
    """Multiple runs of the same model."""

    def test_deterministic_runs_identical(self, decay_sim: ODESimulation) -> None:
        sim = ODESimulation(
            model=decay_sim.model,
            t_span=decay_sim.t_span,
            t_eval=[0.0, 1.0],
            runs=3,
        )
        results = sim.run()
        # 1 subset * 3 runs * 2 time points = 6 rows
        assert len(results) == 6

        rows = results.to_list()
        run0 = [r["x"] for r in rows if r["run"] == 0]
        run1 = [r["x"] for r in rows if r["run"] == 1]
        run2 = [r["x"] for r in rows if r["run"] == 2]
        assert run0 == run1 == run2


class TestSolverSelection:
    """Different solver methods."""

    @pytest.mark.parametrize("solver", ["RK45", "RK23", "DOP853"])
    def test_explicit_solvers(self, decay_model: ODEModel, solver: str) -> None:
        sim = ODESimulation(
            model=decay_model,
            t_span=(0.0, 1.0),
            t_eval=[0.0, 0.5, 1.0],
            solver=solver,  # type: ignore[arg-type]
        )
        results = sim.run()
        assert len(results) == 3
        x_final = results.state_array("x")[-1]
        assert x_final == pytest.approx(math.exp(-1.0), abs=1e-4)

    @pytest.mark.parametrize("solver", ["Radau", "BDF"])
    def test_implicit_solvers(self, decay_model: ODEModel, solver: str) -> None:
        sim = ODESimulation(
            model=decay_model,
            t_span=(0.0, 1.0),
            t_eval=[0.0, 0.5, 1.0],
            solver=solver,  # type: ignore[arg-type]
        )
        results = sim.run()
        assert len(results) == 3
        x_final = results.state_array("x")[-1]
        assert x_final == pytest.approx(math.exp(-1.0), abs=1e-4)


class TestEventDetection:
    """Event function support."""

    def test_terminal_event_stops_integration(self) -> None:
        """Integrate x' = 1 until x crosses 5.0."""

        def rhs(t: float, y: list[float], p: dict[str, Any]) -> list[float]:
            return [1.0]

        def x_crosses_5(t: float, y: list[float], p: dict[str, Any]) -> float:
            return y[0] - 5.0

        x_crosses_5.terminal = True  # type: ignore[attr-defined]

        model = ODEModel(
            state_names=["x"],
            initial_state={"x": 0.0},
            rhs=rhs,
            events=[x_crosses_5],
        )
        sim = ODESimulation(model=model, t_span=(0.0, 100.0))
        results = sim.run()

        # Integration should stop near t=5
        final_time = results.times[-1]
        assert final_time == pytest.approx(5.0, abs=0.01)
        assert results.state_array("x")[-1] == pytest.approx(5.0, abs=0.01)


class TestAutoTimePoints:
    """Integration without explicit t_eval."""

    def test_auto_eval_points(self, decay_model: ODEModel) -> None:
        sim = ODESimulation(
            model=decay_model,
            t_span=(0.0, 1.0),
        )
        results = sim.run()
        assert len(results) > 2
        assert results.times[0] == pytest.approx(0.0)
        assert results.times[-1] == pytest.approx(1.0)
