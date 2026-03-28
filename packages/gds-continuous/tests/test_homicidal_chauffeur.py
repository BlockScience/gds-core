"""Homicidal Chauffeur differential game — integration verification.

Recreates the key numerical results from mzargham/hc-marimo using
gds-continuous, proving the ODE engine handles a real differential
game from Isaacs (1951).

The 4D characteristic ODE system:
    ẋ₁ = -φ*x₂ + w*sin(ψ*)     φ* = -sign(σ), σ = p₂x₁ - p₁x₂
    ẋ₂ =  φ*x₁ + w*cos(ψ*) - 1  ψ* = atan2(p₁, p₂)
    ṗ₁ = -φ*p₂
    ṗ₂ =  φ*p₁

References:
    - R. Isaacs, Differential Games (1965), pp. 297–350
    - A.W. Merz, PhD Thesis, Stanford (1971)
    - github.com/mzargham/hc-marimo
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from gds_continuous import ODEModel, ODESimulation


# ---------------------------------------------------------------------------
# HC dynamics as ODEFunction callables
# ---------------------------------------------------------------------------


def hc_forward(
    t: float, y: list[float], params: dict[str, Any]
) -> list[float]:
    """Forward 4D characteristic ODE for the Homicidal Chauffeur."""
    x1, x2, p1, p2 = y
    w = params["w"]

    norm_p = math.sqrt(p1**2 + p2**2)
    if norm_p < 1e-15:
        return [0.0, 0.0, 0.0, 0.0]

    sigma = p2 * x1 - p1 * x2
    phi_star = -np.sign(sigma)

    x1d = -phi_star * x2 + w * p1 / norm_p
    x2d = phi_star * x1 + w * p2 / norm_p - 1.0
    p1d = -phi_star * p2
    p2d = phi_star * p1
    return [float(x1d), float(x2d), float(p1d), float(p2d)]


def hc_backward(
    t: float, y: list[float], params: dict[str, Any]
) -> list[float]:
    """Backward integration (negate forward dynamics)."""
    fwd = hc_forward(t, y, params)
    return [-v for v in fwd]


def compute_terminal_conditions(
    alpha: float, w_val: float, ell_tilde: float
) -> list[float]:
    """Terminal conditions on the capture circle for backward integration."""
    x1_T = ell_tilde * math.cos(alpha)
    x2_T = ell_tilde * math.sin(alpha)
    lam = -1.0 / (ell_tilde * (w_val - math.sin(alpha)))
    p1_T = lam * x1_T
    p2_T = lam * x2_T
    return [x1_T, x2_T, p1_T, p2_T]


def hamiltonian_star(
    x1: float, x2: float, p1: float, p2: float, w: float
) -> float:
    """Optimal Hamiltonian H* along a trajectory point."""
    sigma = p2 * x1 - p1 * x2
    norm_p = math.sqrt(p1**2 + p2**2)
    return -abs(sigma) + w * norm_p - p2 + 1.0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHamiltonianConservation:
    """H* should remain ~0 along optimal trajectories (T2 from hc-marimo)."""

    def test_h_star_conserved(self) -> None:
        w_val = 0.25
        ell_tilde = 0.5
        alpha = math.pi / 2  # sin(pi/2) = 1 > 0.25 = w → usable

        y0 = compute_terminal_conditions(alpha, w_val, ell_tilde)

        model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=dict(zip(["x1", "x2", "p1", "p2"], y0)),
            rhs=hc_backward,
            params={"w": [w_val]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, 10.0),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
            max_step=0.02,
        )
        results = sim.run()

        x1s = results.state_array("x1")
        x2s = results.state_array("x2")
        p1s = results.state_array("p1")
        p2s = results.state_array("p2")

        h_vals = [
            hamiltonian_star(x1s[i], x2s[i], p1s[i], p2s[i], w_val)
            for i in range(len(results))
        ]
        max_drift = max(abs(h) for h in h_vals)
        assert max_drift < 1e-6, f"H* drift = {max_drift}"


class TestCostateNormConservation:
    """||p||^2 must be conserved along trajectories (T3 from hc-marimo)."""

    def test_norm_conserved(self) -> None:
        w_val = 0.25
        ell_tilde = 0.5
        alpha = math.pi / 2

        y0 = compute_terminal_conditions(alpha, w_val, ell_tilde)

        model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=dict(zip(["x1", "x2", "p1", "p2"], y0)),
            rhs=hc_backward,
            params={"w": [w_val]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, 10.0),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
            max_step=0.02,
        )
        results = sim.run()

        p1s = results.state_array("p1")
        p2s = results.state_array("p2")
        norms = [p1s[i] ** 2 + p2s[i] ** 2 for i in range(len(results))]
        initial_norm = norms[0]

        max_drift = max(abs(n - initial_norm) for n in norms)
        assert max_drift < 1e-8, f"||p||^2 drift = {max_drift}"


class TestCaptureCondition:
    """Forward integration from known initial state should reach capture
    circle (T4 from hc-marimo)."""

    def test_forward_reaches_capture(self) -> None:
        w_val = 0.25
        ell_tilde = 0.5
        alpha = math.pi / 2

        # Get terminal conditions, then integrate backward to find
        # an initial state far from capture circle
        y0_terminal = compute_terminal_conditions(alpha, w_val, ell_tilde)

        model_back = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=dict(zip(["x1", "x2", "p1", "p2"], y0_terminal)),
            rhs=hc_backward,
            params={"w": [w_val]},
        )
        sim_back = ODESimulation(
            model=model_back,
            t_span=(0.0, 5.0),
            solver="RK45",
            rtol=1e-10,
            atol=1e-12,
        )
        results_back = sim_back.run()

        # Take the final backward state as initial for forward
        n = len(results_back)
        y0_far = [
            results_back.state_array("x1")[n - 1],
            results_back.state_array("x2")[n - 1],
            results_back.state_array("p1")[n - 1],
            results_back.state_array("p2")[n - 1],
        ]

        model_fwd = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=dict(zip(["x1", "x2", "p1", "p2"], y0_far)),
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

        # Final position should be near the capture circle
        x1_final = results_fwd.state_array("x1")[-1]
        x2_final = results_fwd.state_array("x2")[-1]
        dist = math.sqrt(x1_final**2 + x2_final**2)
        assert dist == pytest.approx(ell_tilde, abs=0.05), (
            f"Final distance {dist} not near capture radius {ell_tilde}"
        )


class TestStationaryEvader:
    """w=0 (stationary evader): straight-line capture (T6 from hc-marimo)."""

    def test_w_zero_straight_capture(self) -> None:
        """With w=0 and evader on the x2-axis, pursuer drives straight down."""

        def hc_w0(
            t: float, y: list[float], params: dict[str, Any]
        ) -> list[float]:
            x1, x2, p1, p2 = y
            # With w=0: ẋ₁ = -φ*x₂, ẋ₂ = φ*x₁ - 1
            # For straight approach from above: φ=0, ẋ₂ = -1
            return [0.0, -1.0, 0.0, 0.0]

        initial_dist = 3.0
        model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state={"x1": 0.0, "x2": initial_dist, "p1": 0.0, "p2": 1.0},
            rhs=hc_w0,
            params={"w": [0.0]},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, initial_dist),
            t_eval=[0.0, initial_dist],
        )
        results = sim.run()

        x2_final = results.state_array("x2")[-1]
        assert x2_final == pytest.approx(0.0, abs=1e-6)


class TestParameterSweep:
    """Sweep over w values using gds-continuous parameter sweep."""

    def test_sweep_over_w(self) -> None:
        alpha = math.pi / 2
        ell_tilde = 0.5
        w_values = [0.1, 0.2, 0.3]

        # Use w=0.2 for terminal conditions (all w values have sin(pi/2)>w)
        y0 = compute_terminal_conditions(alpha, 0.2, ell_tilde)

        model = ODEModel(
            state_names=["x1", "x2", "p1", "p2"],
            initial_state=dict(zip(["x1", "x2", "p1", "p2"], y0)),
            rhs=hc_backward,
            params={"w": w_values},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, 3.0),
            t_eval=[0.0, 1.0, 2.0, 3.0],
            solver="RK45",
        )
        results = sim.run()

        # 3 subsets * 4 time points = 12 rows
        assert len(results) == 12

        rows = results.to_list()
        subsets = {r["subset"] for r in rows}
        assert subsets == {0, 1, 2}
