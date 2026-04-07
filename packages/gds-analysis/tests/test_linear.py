"""Tests for numerical linear systems analysis."""

import pytest

from gds_analysis.linear import (
    discretize,
    dlqr,
    eigenvalues,
    frequency_response,
    gain_margin,
    is_marginally_stable,
    is_stable,
    kalman,
    lqr,
    phase_margin,
)


# ---------------------------------------------------------------------------
# Stability analysis
# ---------------------------------------------------------------------------


class TestEigenvalues:
    def test_stable_diagonal(self) -> None:
        eigs = eigenvalues([[-1.0, 0.0], [0.0, -2.0]])
        reals = sorted([e.real for e in eigs])
        assert reals[0] == pytest.approx(-2.0, abs=1e-10)
        assert reals[1] == pytest.approx(-1.0, abs=1e-10)

    def test_unstable_system(self) -> None:
        eigs = eigenvalues([[1.0, 0.0], [0.0, -1.0]])
        reals = sorted([e.real for e in eigs])
        assert reals[0] == pytest.approx(-1.0, abs=1e-10)
        assert reals[1] == pytest.approx(1.0, abs=1e-10)

    def test_empty_system(self) -> None:
        assert eigenvalues([]) == []

    def test_complex_eigenvalues(self) -> None:
        # [[0, 1], [-1, 0]] has eigenvalues ±j
        eigs = eigenvalues([[0.0, 1.0], [-1.0, 0.0]])
        assert len(eigs) == 2
        for e in eigs:
            assert abs(e.real) < 1e-10
            assert abs(abs(e.imag) - 1.0) < 1e-10


class TestIsStable:
    def test_stable_continuous(self) -> None:
        assert is_stable([[-1.0, 0.0], [0.0, -2.0]])

    def test_unstable_continuous(self) -> None:
        assert not is_stable([[1.0, 0.0], [0.0, -1.0]])

    def test_marginally_stable_is_not_asymptotically_stable(self) -> None:
        # Pure oscillator: eigenvalues on imaginary axis
        assert not is_stable([[0.0, 1.0], [-1.0, 0.0]])

    def test_stable_discrete(self) -> None:
        # |λ| < 1 for discrete stability
        assert is_stable([[0.5, 0.0], [0.0, 0.3]], continuous=False)

    def test_unstable_discrete(self) -> None:
        assert not is_stable([[1.1, 0.0], [0.0, 0.5]], continuous=False)

    def test_empty_system(self) -> None:
        assert is_stable([])


class TestIsMarginallyStable:
    def test_oscillator(self) -> None:
        assert is_marginally_stable([[0.0, 1.0], [-1.0, 0.0]])

    def test_stable_is_not_marginal(self) -> None:
        assert not is_marginally_stable([[-1.0, 0.0], [0.0, -2.0]])


# ---------------------------------------------------------------------------
# Frequency response
# ---------------------------------------------------------------------------


class TestFrequencyResponse:
    def test_first_order_bode(self) -> None:
        """1/(s+1): -3dB at w=1, -45deg at w=1."""
        omega, mag_db, phase_deg = frequency_response(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            omega=[1.0],
        )

        assert len(omega) == 1
        assert mag_db[0] == pytest.approx(-3.01, abs=0.1)
        assert phase_deg[0] == pytest.approx(-45.0, abs=2.0)

    def test_auto_frequency_range(self) -> None:
        omega, mag_db, phase_deg = frequency_response(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
        )
        assert len(omega) == 500  # default n_points


class TestGainMargin:
    def test_known_system(self) -> None:
        """1/((s+1)(s+2)(s+3)): known gain margin."""
        # H(s) = 1/(s^3 + 6s^2 + 11s + 6)
        num = [1.0]
        den = [1.0, 6.0, 11.0, 6.0]
        gm_db, gm_freq = gain_margin(num, den)
        assert gm_db > 0  # System is stable, should have positive margin


class TestPhaseMargin:
    def test_known_system(self) -> None:
        """1/(s+1): infinite phase margin (gain never reaches 0dB at
        a frequency where phase is problematic)."""
        num = [1.0]
        den = [1.0, 1.0]
        pm_deg, pm_freq = phase_margin(num, den)
        # For 1/(s+1), gain is always < 0dB, so phase margin is infinite
        assert pm_deg == float("inf")


# ---------------------------------------------------------------------------
# Discretization
# ---------------------------------------------------------------------------


class TestDiscretize:
    def test_tustin_preserves_stability(self) -> None:
        """Stable continuous system → stable discrete system."""
        Ad, Bd, Cd, Dd = discretize(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            dt=0.1, method="tustin",
        )
        assert is_stable(Ad, continuous=False)

    def test_zoh(self) -> None:
        """ZOH discretization of 1/(s+1) with dt=0.1."""
        Ad, Bd, Cd, Dd = discretize(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            dt=0.1, method="zoh",
        )
        # A_d = e^{A*dt} = e^{-0.1} ≈ 0.9048
        assert Ad[0][0] == pytest.approx(0.9048, abs=0.01)
        assert is_stable(Ad, continuous=False)

    def test_euler(self) -> None:
        Ad, Bd, Cd, Dd = discretize(
            A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
            dt=0.1, method="euler",
        )
        # Forward Euler: Ad = I + dt*A = [[0.9]]
        assert Ad[0][0] == pytest.approx(0.9, abs=0.01)

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="Unknown discretization method"):
            discretize(
                A=[[-1.0]], B=[[1.0]], C=[[1.0]], D=[[0.0]],
                dt=0.1, method="invalid",
            )


# ---------------------------------------------------------------------------
# Controller synthesis
# ---------------------------------------------------------------------------


class TestLQR:
    def test_double_integrator(self) -> None:
        """LQR on double integrator should produce stable closed-loop."""
        A = [[0.0, 1.0], [0.0, 0.0]]
        B = [[0.0], [1.0]]
        Q = [[1.0, 0.0], [0.0, 1.0]]
        R = [[1.0]]

        K, P, E = lqr(A, B, Q, R)

        # K should be 1x2
        assert len(K) == 1
        assert len(K[0]) == 2

        # Closed-loop should be stable
        assert all(e.real < 0 for e in E)

    def test_scalar_system(self) -> None:
        """Simple scalar system: dx/dt = -x + u, Q=1, R=1."""
        K, P, E = lqr(
            A=[[-1.0]], B=[[1.0]], Q=[[1.0]], R=[[1.0]],
        )
        assert len(K) == 1
        assert len(K[0]) == 1
        assert E[0].real < 0


class TestDLQR:
    def test_discrete_double_integrator(self) -> None:
        """Discrete LQR on discretized double integrator."""
        # First discretize
        Ad, Bd, Cd, Dd = discretize(
            A=[[0.0, 1.0], [0.0, 0.0]],
            B=[[0.0], [1.0]],
            C=[[1.0, 0.0]],
            D=[[0.0]],
            dt=0.1, method="zoh",
        )

        Q = [[1.0, 0.0], [0.0, 1.0]]
        R = [[1.0]]

        K, P, E = dlqr(Ad, Bd, Q, R)

        # Closed-loop eigenvalues inside unit circle
        assert all(abs(e) < 1.0 for e in E)


class TestKalman:
    def test_observer_gain(self) -> None:
        """Kalman filter for simple observable system."""
        A = [[-1.0, 0.0], [0.0, -2.0]]
        C = [[1.0, 0.0]]
        Q_proc = [[1.0, 0.0], [0.0, 1.0]]
        R_meas = [[0.1]]

        L, P = kalman(A, C, Q_proc, R_meas)

        # L should be 2x1 (n x p)
        assert len(L) == 2
        assert len(L[0]) == 1

        # Observer poles = eigenvalues of A - LC should be stable
        import numpy as np

        A_obs = np.array(A) - np.array(L) @ np.array(C)
        eigs = np.linalg.eigvals(A_obs)
        assert all(e.real < 0 for e in eigs)
