"""Tests for the DC Motor Control Tutorial (Lessons 1-8)."""

import pytest

# ---------------------------------------------------------------------------
# Lesson 1: Plant model
# ---------------------------------------------------------------------------


class TestLesson1Plant:
    def test_model_has_two_states(self) -> None:
        from gds_examples.control_tutorial.lesson1_plant import build_model

        model = build_model()
        assert len(model.states) == 2
        assert {s.name for s in model.states} == {"theta", "omega"}

    def test_model_has_one_input(self) -> None:
        from gds_examples.control_tutorial.lesson1_plant import build_model

        model = build_model()
        assert len(model.inputs) == 1
        assert model.inputs[0].name == "V"

    def test_spec_validates(self) -> None:
        from gds_examples.control_tutorial.lesson1_plant import build_spec

        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == []

    def test_system_compiles(self) -> None:
        from gds_examples.control_tutorial.lesson1_plant import build_system

        system = build_system()
        assert len(system.blocks) > 0

    def test_open_loop_simulation_runs(self) -> None:
        from gds_examples.control_tutorial.lesson1_plant import simulate_open_loop

        times, theta, omega = simulate_open_loop(voltage=1.0, t_end=1.0)
        assert len(times) > 10
        # Motor should spin up: omega > 0 at end
        assert omega[-1] > 0
        # Position should increase
        assert theta[-1] > 0


# ---------------------------------------------------------------------------
# Lesson 2: P control
# ---------------------------------------------------------------------------


class TestLesson2PControl:
    def test_model_builds(self) -> None:
        from gds_examples.control_tutorial.lesson2_p_control import build_model

        model = build_model()
        assert len(model.states) == 2
        assert "Kp" in model.symbolic_params

    def test_step_response_converges(self) -> None:
        from gds_examples.control_tutorial.lesson2_p_control import (
            simulate_p_control,
        )

        _times, theta = simulate_p_control(kp=5.0, theta_ref=1.0, t_end=5.0)
        # Should approach setpoint (with some SSE for P control)
        assert theta[-1] > 0.5

    def test_step_metrics_reasonable(self) -> None:
        from gds_examples.control_tutorial.lesson2_p_control import (
            analyze_step_response,
        )

        _t, _y, metrics = analyze_step_response(kp=5.0)
        assert metrics.rise_time > 0
        assert metrics.settling_time > 0
        assert metrics.overshoot_pct >= 0


# ---------------------------------------------------------------------------
# Lesson 3: PID + transfer functions
# ---------------------------------------------------------------------------


class TestLesson3PIDTransfer:
    def test_linearization_dimensions(self) -> None:
        from gds_examples.control_tutorial.lesson3_pid_transfer import (
            get_plant_linearization,
        )

        ls = get_plant_linearization()
        assert len(ls.A) == 2
        assert len(ls.A[0]) == 2
        assert len(ls.B) == 2
        assert len(ls.B[0]) == 1

    def test_transfer_function_order(self) -> None:
        from gds_examples.control_tutorial.lesson3_pid_transfer import (
            analyze_transfer_function,
        )

        tf, _p, _z, _ctrl, _obs = analyze_transfer_function()
        # Plant TF denominator should be order 2
        assert len(tf.den) == 3

    def test_plant_is_controllable(self) -> None:
        from gds_examples.control_tutorial.lesson3_pid_transfer import (
            analyze_transfer_function,
        )

        _tf, _p, _z, ctrl, obs = analyze_transfer_function()
        assert ctrl is True
        assert obs is True

    def test_open_loop_poles_stable(self) -> None:
        """Open-loop motor has poles at 0 and -b/J — marginally stable."""
        from gds_examples.control_tutorial.lesson3_pid_transfer import (
            analyze_transfer_function,
        )

        _tf, plant_poles, _z, _ctrl, _obs = analyze_transfer_function()
        assert len(plant_poles) == 2
        # One pole at 0, one at -10
        reals = sorted([p.real for p in plant_poles])
        assert reals[0] == pytest.approx(-10.0, abs=0.5)
        assert reals[1] == pytest.approx(0.0, abs=0.1)

    def test_pid_eliminates_sse(self) -> None:
        from gds_analysis.response import step_response_metrics
        from gds_examples.control_tutorial.lesson3_pid_transfer import simulate_pid

        times, theta = simulate_pid(kp=10.0, ki=5.0, kd=0.5, t_end=10.0)
        metrics = step_response_metrics(times, theta, setpoint=1.0)
        assert metrics.steady_state_error < 0.05


# ---------------------------------------------------------------------------
# Lesson 4: Disturbance + sensitivity
# ---------------------------------------------------------------------------


class TestLesson4Disturbance:
    def test_sensitivity_functions_exist(self) -> None:
        from gds_examples.control_tutorial.lesson4_disturbance import (
            analyze_sensitivity,
        )

        gang = analyze_sensitivity()
        assert set(gang.keys()) == {"S", "T", "CS", "PS", "KS", "KPS"}

    def test_s_plus_t_dc_equals_one(self) -> None:
        from gds_examples.control_tutorial.lesson4_disturbance import (
            analyze_sensitivity,
        )

        gang = analyze_sensitivity()
        s_dc = gang["S"].num[-1] / gang["S"].den[-1]
        t_dc = gang["T"].num[-1] / gang["T"].den[-1]
        assert s_dc + t_dc == pytest.approx(1.0, abs=1e-8)

    def test_feedforward_reduces_disturbance(self) -> None:
        from gds_examples.control_tutorial.lesson4_disturbance import (
            simulate_disturbance,
        )

        _t_fb, y_fb = simulate_disturbance(use_feedforward=False)
        _t_ff, y_ff = simulate_disturbance(use_feedforward=True)

        mid = len(y_fb) // 2
        dev_fb = max(abs(v - 1.0) for v in y_fb[mid:])
        dev_ff = max(abs(v - 1.0) for v in y_ff[mid:])
        assert dev_ff < dev_fb


# ---------------------------------------------------------------------------
# Lesson 5: Delay + margins
# ---------------------------------------------------------------------------


class TestLesson5Delay:
    def test_pade_approximation_order(self) -> None:
        from gds_domains.symbolic.delay import pade_approximation

        pade = pade_approximation(0.05, order=3)
        assert len(pade.num) == 4  # order 3 -> degree 3 -> 4 coefficients
        assert len(pade.den) == 4

    def test_delay_reduces_margins(self) -> None:
        from gds_examples.control_tutorial.lesson5_delay import compare_margins

        margins = compare_margins(delays=[0.0, 0.05])
        # No-delay margin should be better than delayed margin
        no_delay = margins[0]
        with_delay = margins[1]

        # At least one margin should degrade
        if no_delay["pm_deg"] != float("inf") and with_delay["pm_deg"] != float("inf"):
            assert with_delay["pm_deg"] < no_delay["pm_deg"]

    def test_nyquist_data_computable(self) -> None:
        from gds_examples.control_tutorial.lesson5_delay import get_nyquist_data

        real, imag = get_nyquist_data(delay=0.05)
        assert len(real) > 0
        assert len(imag) > 0


# ---------------------------------------------------------------------------
# Lesson 6: LQR
# ---------------------------------------------------------------------------


class TestLesson6LQR:
    def test_lqr_gain_shape(self) -> None:
        from gds_examples.control_tutorial.lesson6_lqr import design_lqr

        K, _P, _E = design_lqr()
        assert len(K) == 1  # single input
        assert len(K[0]) == 2  # two states

    def test_closed_loop_stable(self) -> None:
        from gds_examples.control_tutorial.lesson6_lqr import design_lqr

        _K, _P, E = design_lqr()
        assert all(e.real < 0 for e in E)

    def test_lqr_step_response(self) -> None:
        from gds_analysis.response import step_response_metrics
        from gds_examples.control_tutorial.lesson6_lqr import (
            design_lqr,
            simulate_lqr,
        )

        K, _P, _E = design_lqr()
        times, theta = simulate_lqr(K, t_end=3.0)
        metrics = step_response_metrics(times, theta, setpoint=1.0)
        assert metrics.overshoot_pct < 50

    def test_gain_schedule_varies(self) -> None:
        from gds_examples.control_tutorial.lesson6_lqr import run_gain_schedule

        schedule = run_gain_schedule()
        assert len(schedule) == 3
        # Velocity gains (K2) should differ across operating points
        # (K1 position gain converges but K2 varies with inertia)
        k2_values = [s[1][0][1] for s in schedule]
        assert k2_values[0] != pytest.approx(k2_values[2], abs=0.01)


# ---------------------------------------------------------------------------
# Lesson 7: Discretization
# ---------------------------------------------------------------------------


class TestLesson7Discrete:
    def test_dlqr_closed_loop_stable(self) -> None:
        """Closed-loop discrete system should have eigenvalues inside unit circle."""
        from gds_examples.control_tutorial.lesson7_discrete import design_dlqr

        _Kd, _Pd, Ed = design_dlqr(dt=0.01)
        assert all(abs(e) < 1.0 for e in Ed)

    def test_discrete_eigenvalues_inside_unit_circle(self) -> None:
        from gds_examples.control_tutorial.lesson7_discrete import design_dlqr

        _Kd, _Pd, Ed = design_dlqr(dt=0.01)
        assert all(abs(e) < 1.0 for e in Ed)

    def test_discrete_sim_runs(self) -> None:
        from gds_examples.control_tutorial.lesson7_discrete import simulate_discrete

        times, theta = simulate_discrete(dt=0.01, n_steps=100)
        assert len(times) > 50
        # Should approach setpoint
        assert theta[-1] > 0.5

    def test_dlqr_gain_computed(self) -> None:
        from gds_examples.control_tutorial.lesson7_discrete import design_dlqr

        Kd, _Pd, Ed = design_dlqr(dt=0.01)
        assert len(Kd) == 1
        assert len(Kd[0]) == 2
        assert all(abs(e) < 1.0 for e in Ed)


# ---------------------------------------------------------------------------
# Lesson 8: Lyapunov
# ---------------------------------------------------------------------------


class TestLesson8Lyapunov:
    def test_find_lyapunov_succeeds(self) -> None:
        from gds_examples.control_tutorial.lesson8_lyapunov import (
            prove_quadratic_lyapunov,
        )

        result = prove_quadratic_lyapunov()
        assert result is not None
        _P, lyap = result
        assert lyap.stable is True

    def test_quadratic_lyapunov_proved(self) -> None:
        from gds_examples.control_tutorial.lesson8_lyapunov import (
            prove_quadratic_lyapunov,
        )

        result = prove_quadratic_lyapunov()
        assert result is not None
        _P, lyap = result
        assert lyap.positive_definite == "PROVED"
        assert lyap.decreasing == "PROVED"

    def test_custom_candidate(self) -> None:
        from gds_examples.control_tutorial.lesson8_lyapunov import (
            verify_custom_lyapunov,
        )

        result = verify_custom_lyapunov()
        # V = theta^2 + omega^2 may or may not prove stable
        # but should at least be positive definite
        assert result.positive_definite == "PROVED"
        assert result.dV_expr is not None

    def test_passivity_certificate(self) -> None:
        from gds_examples.control_tutorial.lesson8_lyapunov import prove_passivity

        result = prove_passivity()
        assert result.passive is True
        assert result.dissipation_proved == "PROVED"
