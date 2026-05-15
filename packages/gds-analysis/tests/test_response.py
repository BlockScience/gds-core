"""Tests for step/impulse response computation and metrics."""

import math

import pytest

from gds_analysis.response import StepMetrics, step_response_metrics


class TestStepResponseMetrics:
    def test_first_order_no_overshoot(self) -> None:
        """First-order system 1/(s+1): no overshoot, known time constants."""
        # Generate 1 - e^{-t} response
        n = 1000
        t_max = 10.0
        times = [i * t_max / (n - 1) for i in range(n)]
        values = [1.0 - math.exp(-t) for t in times]

        metrics = step_response_metrics(times, values, setpoint=1.0)

        # Rise time (10% to 90%): for 1-e^{-t}, t_10 = -ln(0.9) ≈ 0.105,
        # t_90 = -ln(0.1) ≈ 2.303, rise time ≈ 2.197
        assert metrics.rise_time == pytest.approx(2.197, abs=0.05)

        # No overshoot
        assert metrics.overshoot_pct == pytest.approx(0.0, abs=0.1)

        # Settling time (2% band): 1 - e^{-t} within 0.02 of 1.0
        # e^{-t} < 0.02 → t > -ln(0.02) ≈ 3.912
        assert metrics.settling_time == pytest.approx(3.91, abs=0.15)

        # Steady-state
        assert metrics.steady_state_value == pytest.approx(1.0, abs=0.01)
        assert metrics.steady_state_error == pytest.approx(0.0, abs=0.01)

    def test_underdamped_overshoot(self) -> None:
        """Second-order underdamped: known overshoot formula."""
        zeta = 0.3
        wn = 2.0
        wd = wn * math.sqrt(1 - zeta**2)

        n = 2000
        t_max = 10.0
        times = [i * t_max / (n - 1) for i in range(n)]
        values = [
            1.0 - math.exp(-zeta * wn * t) / math.sqrt(1 - zeta**2)
            * math.sin(wd * t + math.acos(zeta))
            for t in times
        ]

        metrics = step_response_metrics(times, values, setpoint=1.0)

        # Analytical overshoot: exp(-pi*zeta/sqrt(1-zeta^2)) * 100
        expected_os = math.exp(-math.pi * zeta / math.sqrt(1 - zeta**2)) * 100
        assert metrics.overshoot_pct == pytest.approx(expected_os, abs=2.0)

    def test_steady_state_error(self) -> None:
        """System that settles to 0.95 instead of 1.0."""
        n = 500
        times = [i * 10.0 / (n - 1) for i in range(n)]
        values = [0.95 * (1.0 - math.exp(-t)) for t in times]

        metrics = step_response_metrics(times, values, setpoint=1.0)
        assert metrics.steady_state_error == pytest.approx(0.05, abs=0.02)

    def test_too_few_points(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            step_response_metrics([0.0], [0.0])

    def test_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            step_response_metrics([0.0, 1.0], [0.0])

    def test_constant_response(self) -> None:
        """Constant response — degenerate but shouldn't crash."""
        times = [0.0, 1.0, 2.0, 3.0, 4.0]
        values = [1.0, 1.0, 1.0, 1.0, 1.0]
        metrics = step_response_metrics(times, values, setpoint=1.0)
        assert metrics.rise_time == 0.0
        assert metrics.overshoot_pct == 0.0

    def test_dataclass_fields(self) -> None:
        """Verify StepMetrics has all required fields."""
        m = StepMetrics(
            rise_time=1.0,
            settling_time=2.0,
            overshoot_pct=10.0,
            peak_time=1.5,
            peak_value=1.1,
            steady_state_value=1.0,
            steady_state_error=0.0,
        )
        assert m.rise_time == 1.0
        assert m.settling_time == 2.0
        assert m.overshoot_pct == 10.0


class TestStepResponse:
    """Tests for step_response() — requires scipy."""

    def test_first_order_final_value(self) -> None:
        """1/(s+1) step response should approach 1.0."""
        from gds_analysis.response import step_response

        times, outputs = step_response(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            t_span=(0.0, 10.0), n_points=500,
        )

        assert len(times) == 500
        assert len(outputs) == 1
        # Final value should be close to 1.0
        assert outputs[0][-1] == pytest.approx(1.0, abs=0.01)
        # Initial value should be close to 0.0
        assert outputs[0][0] == pytest.approx(0.0, abs=0.01)

    def test_double_integrator_ramp(self) -> None:
        """1/s^2 step response is a parabola (t^2/2)."""
        from gds_analysis.response import step_response

        times, outputs = step_response(
            A=[[0.0, 1.0], [0.0, 0.0]],
            B=[[0.0], [1.0]],
            C=[[1.0, 0.0]],
            D=[[0.0]],
            t_span=(0.0, 5.0), n_points=500,
        )

        # At t=1, output ≈ 0.5; at t=2, output ≈ 2.0
        idx_t1 = 100  # t ≈ 1.0
        idx_t2 = 200  # t ≈ 2.0
        t1 = times[idx_t1]
        t2 = times[idx_t2]
        assert outputs[0][idx_t1] == pytest.approx(t1**2 / 2, abs=0.05)
        assert outputs[0][idx_t2] == pytest.approx(t2**2 / 2, abs=0.1)


class TestImpulseResponse:
    def test_first_order_decay(self) -> None:
        """1/(s+1) impulse response = e^{-t}."""
        from gds_analysis.response import impulse_response

        times, outputs = impulse_response(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            t_span=(0.0, 10.0), n_points=500,
        )

        assert len(times) == 500
        # Initial value should be close to 1.0
        assert outputs[0][0] == pytest.approx(1.0, abs=0.1)
        # Should decay toward 0
        assert outputs[0][-1] == pytest.approx(0.0, abs=0.01)
