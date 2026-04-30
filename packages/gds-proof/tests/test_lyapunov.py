"""Tests for Lyapunov stability proofs and passivity certificates."""

from gds_proof.analysis.lyapunov import (
    find_quadratic_lyapunov,
    lyapunov_candidate,
    passivity_certificate,
    quadratic_lyapunov,
)


class TestLyapunovCandidate:
    def test_stable_linear_continuous(self) -> None:
        """dx/dt = -x, V = x^2: should prove stable."""
        result = lyapunov_candidate(
            V_expr="x**2",
            state_transition={"x": "-x"},
            state_symbols=["x"],
            continuous=True,
        )
        assert result.positive_definite == "PROVED"
        assert result.decreasing == "PROVED"
        assert result.stable is True

    def test_unstable_linear_continuous(self) -> None:
        """dx/dt = x, V = x^2: dV/dt = 2x^2 > 0, should fail decrease."""
        result = lyapunov_candidate(
            V_expr="x**2",
            state_transition={"x": "x"},
            state_symbols=["x"],
            continuous=True,
        )
        assert result.positive_definite == "PROVED"
        assert result.decreasing == "FAILED"
        assert result.stable is False

    def test_2d_stable(self) -> None:
        """dx/dt = [-x, -2y], V = x^2 + y^2."""
        result = lyapunov_candidate(
            V_expr="x**2 + y**2",
            state_transition={"x": "-x", "y": "-2*y"},
            state_symbols=["x", "y"],
            continuous=True,
        )
        assert result.positive_definite == "PROVED"
        assert result.decreasing == "PROVED"
        assert result.stable is True

    def test_discrete_stable(self) -> None:
        """x' = 0.5*x, V = x^2: V(f(x)) - V(x) = 0.25x^2 - x^2 = -0.75x^2 < 0."""
        result = lyapunov_candidate(
            V_expr="x**2",
            state_transition={"x": "0.5*x"},
            state_symbols=["x"],
            continuous=False,
        )
        assert result.positive_definite == "PROVED"
        assert result.decreasing == "PROVED"
        assert result.stable is True

    def test_discrete_unstable(self) -> None:
        """x' = 2*x, V = x^2: V(f(x)) = 4x^2 > x^2."""
        result = lyapunov_candidate(
            V_expr="x**2",
            state_transition={"x": "2*x"},
            state_symbols=["x"],
            continuous=False,
        )
        assert result.stable is False

    def test_details_populated(self) -> None:
        result = lyapunov_candidate(
            V_expr="x**2",
            state_transition={"x": "-x"},
            state_symbols=["x"],
        )
        assert len(result.details) > 0
        assert result.dV_expr is not None


class TestQuadraticLyapunov:
    def test_stable_diagonal(self) -> None:
        """A = [[-1, 0], [0, -2]], P = I: A'P + PA = diag(-2, -4) < 0."""
        result = quadratic_lyapunov(
            P=[[1.0, 0.0], [0.0, 1.0]],
            A=[[-1.0, 0.0], [0.0, -2.0]],
        )
        assert result.positive_definite == "PROVED"
        assert result.decreasing == "PROVED"
        assert result.stable is True

    def test_unstable_system(self) -> None:
        """A = [[1, 0], [0, -1]], P = I: A'P + PA = diag(2, -2) not neg def."""
        result = quadratic_lyapunov(
            P=[[1.0, 0.0], [0.0, 1.0]],
            A=[[1.0, 0.0], [0.0, -1.0]],
        )
        assert result.decreasing == "FAILED"
        assert result.stable is False

    def test_custom_state_symbols(self) -> None:
        result = quadratic_lyapunov(
            P=[[1.0, 0.0], [0.0, 1.0]],
            A=[[-1.0, 0.0], [0.0, -2.0]],
            state_symbols=["pos", "vel"],
        )
        assert result.stable is True
        assert "pos" in str(result.candidate)


class TestFindQuadraticLyapunov:
    def test_stable_system(self) -> None:
        """Should find P for a stable system."""
        result = find_quadratic_lyapunov(A=[[-1.0, 0.0], [0.0, -2.0]])
        assert result is not None
        P, lyap_result = result
        assert lyap_result.stable is True
        # P should be 2x2
        assert len(P) == 2
        assert len(P[0]) == 2

    def test_unstable_system(self) -> None:
        """Should return None for an unstable system."""
        result = find_quadratic_lyapunov(A=[[1.0, 0.0], [0.0, -1.0]])
        assert result is None

    def test_with_custom_Q(self) -> None:
        result = find_quadratic_lyapunov(
            A=[[-1.0, 0.0], [0.0, -2.0]],
            Q=[[2.0, 0.0], [0.0, 2.0]],
        )
        assert result is not None

    def test_empty_system(self) -> None:
        assert find_quadratic_lyapunov(A=[]) is None


class TestPassivityCertificate:
    def test_damped_spring(self) -> None:
        """Spring-mass-damper: V = 0.5*(k*x^2 + m*v^2), supply = u*v.

        dx/dt = v, dv/dt = (-k*x - b*v + u) / m
        With k=1, m=1, b=1:
        dV/dt = k*x*v + m*v*(-k*x - b*v + u)/m
              = k*x*v + v*(-k*x - b*v + u)
              = k*x*v - k*x*v - b*v^2 + u*v
              = -b*v^2 + u*v
        Supply rate = u*v
        Dissipation = dV/dt - supply = -b*v^2 <= 0 ✓
        """
        result = passivity_certificate(
            V_expr="x**2/2 + v**2/2",
            supply_rate="u*y_out",
            state_transition={"x": "v", "v": "-x - v + u"},
            output_map={"y_out": "v"},
            state_symbols=["x", "v"],
            input_symbols=["u"],
        )

        assert result.dissipation_proved == "PROVED"
        assert result.passive is True

    def test_details_populated(self) -> None:
        result = passivity_certificate(
            V_expr="x**2",
            supply_rate="u*y",
            state_transition={"x": "-x + u"},
            output_map={"y": "x"},
            state_symbols=["x"],
            input_symbols=["u"],
        )
        assert len(result.details) > 0
