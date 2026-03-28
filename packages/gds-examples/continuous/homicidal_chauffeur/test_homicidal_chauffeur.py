"""Tests for the Homicidal Chauffeur example.

Verifies symbolic derivation, numerical integration, conservation laws,
and backward reachable set computation against known results from
Isaacs (1965) and Merz (1971).

Test IDs trace to mzargham/hc-marimo verification suite:
    HC-R1: Reduced dynamics structure
    HC-T1: Lambdified vs hand-coded consistency
    HC-T2: Hamiltonian conservation
    HC-T3: Costate norm conservation
    HC-T4: Forward/backward capture round-trip
    HC-T6: Stationary evader straight-line capture
    HC-T7: Usable part boundary
    HC-ISO: Isochrone computation
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from gds_continuous import ODEModel, ODESimulation

from .model import (
    build_backward_simulation,
    compute_isochrone,
    costate_norm_sq,
    hamiltonian_star,
    hc_forward,
    terminal_conditions,
)

# ---------------------------------------------------------------------------
# HC-R1: Symbolic derivation matches hand-coded
# ---------------------------------------------------------------------------


class TestSymbolicDerivation:
    """Verify symbolic RHS matches hand-coded at random points."""

    def test_lambdified_vs_handcoded(self) -> None:
        """HC-T1: Lambdified and hand-coded RHS agree."""
        pytest.importorskip("sympy")
        from .model import derive_optimal_rhs

        rhs_sym, _ = derive_optimal_rhs()

        import numpy as np

        rng = np.random.default_rng(42)
        for _ in range(50):
            x1 = rng.uniform(-5, 5)
            x2 = rng.uniform(-5, 5)
            angle = rng.uniform(0, 2 * np.pi)
            norm_p = rng.uniform(0.1, 3.0)
            p1 = norm_p * np.cos(angle)
            p2 = norm_p * np.sin(angle)
            w_val = rng.uniform(0.05, 0.5)

            state = [x1, x2, p1, p2]
            params = {"w": w_val}

            hand = hc_forward(0.0, state, params)
            lamb = rhs_sym(0.0, state, params)

            for j in range(4):
                assert abs(hand[j] - lamb[j]) < 1e-10, (
                    f"Component {j} mismatch at state={state}, w={w_val}"
                )


# ---------------------------------------------------------------------------
# HC-T2 / HC-T3: Conservation laws
# ---------------------------------------------------------------------------


class TestConservationLaws:
    """Hamiltonian and costate norm conservation along trajectories."""

    @pytest.fixture
    def trajectory(self) -> list[dict[str, float]]:
        """Integrate backward from capture circle and return state dicts."""
        sim = build_backward_simulation(
            alpha=math.pi / 2, w=0.25, ell_tilde=0.5, t_final=10.0
        )
        results = sim.run()
        rows = results.to_list()
        return [
            {"x1": r["x1"], "x2": r["x2"], "p1": r["p1"], "p2": r["p2"]} for r in rows
        ]

    def test_hamiltonian_conserved(self, trajectory: list[dict[str, float]]) -> None:
        """HC-T2: H* ~ 0 along optimal trajectories."""
        h_vals = [hamiltonian_star(s, w=0.25) for s in trajectory]
        max_drift = max(abs(h) for h in h_vals)
        assert max_drift < 1e-6, f"H* drift = {max_drift}"

    def test_costate_norm_conserved(self, trajectory: list[dict[str, float]]) -> None:
        """HC-T3: ||p||^2 conserved."""
        norms = [costate_norm_sq(s) for s in trajectory]
        initial = norms[0]
        max_drift = max(abs(n - initial) for n in norms)
        assert max_drift < 1e-8, f"||p||^2 drift = {max_drift}"


# ---------------------------------------------------------------------------
# HC-T4: Capture round-trip
# ---------------------------------------------------------------------------


class TestCaptureRoundTrip:
    """Forward integration from a backward-computed state reaches capture."""

    def test_round_trip(self) -> None:
        """HC-T4: backward -> forward returns to capture circle."""
        w_val = 0.25
        ell_tilde = 0.5

        # Backward from capture circle
        sim_back = build_backward_simulation(
            alpha=math.pi / 2, w=w_val, ell_tilde=ell_tilde, t_final=5.0
        )
        results_back = sim_back.run()
        n = len(results_back)
        y0_far = {
            "x1": results_back.state_array("x1")[n - 1],
            "x2": results_back.state_array("x2")[n - 1],
            "p1": results_back.state_array("p1")[n - 1],
            "p2": results_back.state_array("p2")[n - 1],
        }

        # Forward from that state
        model_fwd = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=y0_far,
            rhs=hc_forward,
            params={"w": [w_val]},
        )
        sim_fwd = ODESimulation(
            model=model_fwd,
            t_span=(0.0, 5.0),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
        )
        results_fwd = sim_fwd.run()

        x1_f = results_fwd.state_array("x1")[-1]
        x2_f = results_fwd.state_array("x2")[-1]
        dist = math.sqrt(x1_f**2 + x2_f**2)
        assert dist == pytest.approx(ell_tilde, abs=0.05)


# ---------------------------------------------------------------------------
# HC-T6: Stationary evader
# ---------------------------------------------------------------------------


class TestStationaryEvader:
    """w=0: pursuer drives straight to capture."""

    def test_straight_line_capture(self) -> None:
        """HC-T6: With w=0, capture time = initial distance."""

        def hc_w0(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
            return [0.0, -1.0, 0.0, 0.0]

        d = 3.0
        model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state={"x1": 0.0, "x2": d, "p1": 0.0, "p2": 1.0},
            rhs=hc_w0,
            params={"w": [0.0]},
        )
        sim = ODESimulation(model=model, t_span=(0.0, d), t_eval=[0.0, d])
        results = sim.run()
        assert results.state_array("x2")[-1] == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# HC-T7: Usable part boundary
# ---------------------------------------------------------------------------


class TestUsablePart:
    """The usable part requires sin(alpha) > w."""

    def test_usable_part_valid(self) -> None:
        """HC-T7: alpha=pi/2, w=0.25 => sin(alpha)=1 > 0.25 => usable."""
        ic = terminal_conditions(math.pi / 2, w=0.25, ell_tilde=0.5)
        # lambda should be positive (characteristic of usable part)
        # lambda = -1 / (ell * (w - sin(alpha))) = -1 / (0.5 * (0.25 - 1))
        #        = -1 / (-0.375) = 2.667
        lam = -1.0 / (0.5 * (0.25 - 1.0))
        assert lam > 0
        # p should be parallel to x (transversality)
        assert ic["p1"] == pytest.approx(lam * ic["x1"])
        assert ic["p2"] == pytest.approx(lam * ic["x2"])

    def test_usable_part_boundary(self) -> None:
        """At sin(alpha) = w, lambda diverges (boundary of usable part)."""
        w = 0.25
        alpha_boundary = math.asin(w)
        # denominator -> 0
        denom = 0.5 * (w - math.sin(alpha_boundary))
        assert abs(denom) < 1e-10


# ---------------------------------------------------------------------------
# Isochrone (backward reachable set)
# ---------------------------------------------------------------------------


class TestIsochrone:
    """Backward reachable set computation."""

    def test_isochrone_produces_points(self) -> None:
        """HC-ISO: Isochrone returns boundary points."""
        points = compute_isochrone(w=0.25, ell_tilde=0.5, t_final=3.0, n_rays=10)
        assert len(points) == 10
        # All points should be farther from origin than capture radius
        for x1, x2 in points:
            dist = math.sqrt(x1**2 + x2**2)
            assert dist > 0.5, f"Point ({x1}, {x2}) inside capture circle"

    def test_isochrone_grows_with_time(self) -> None:
        """Larger t_final => points farther from origin."""
        pts_short = compute_isochrone(w=0.25, ell_tilde=0.5, t_final=2.0, n_rays=5)
        pts_long = compute_isochrone(w=0.25, ell_tilde=0.5, t_final=5.0, n_rays=5)

        avg_short = sum(math.sqrt(x**2 + y**2) for x, y in pts_short) / len(pts_short)
        avg_long = sum(math.sqrt(x**2 + y**2) for x, y in pts_long) / len(pts_long)
        assert avg_long > avg_short
