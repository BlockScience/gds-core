"""Tests for backward reachable set computation."""

from __future__ import annotations

import math
from typing import Any

import pytest

gds_continuous = pytest.importorskip("gds_continuous")
numpy = pytest.importorskip("numpy")

from gds_analysis.backward_reachability import (  # noqa: E402
    BackwardReachableSet,
    backward_reachable_set,
    extract_isochrones,
)

# ---------------------------------------------------------------------------
# Test dynamics
# ---------------------------------------------------------------------------


def simple_decay(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """dx/dt = -x (exponential decay toward origin)."""
    return [-y[0]]


def harmonic(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """2D harmonic oscillator: dx1/dt = x2, dx2/dt = -x1."""
    return [y[1], -y[0]]


def hc_forward(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """Homicidal Chauffeur forward dynamics (simplified 2D)."""
    import numpy as np

    x1, x2, p1, p2 = y
    w = params.get("w", 0.25)
    norm_p = math.sqrt(p1**2 + p2**2)
    if norm_p < 1e-15:
        return [0.0, 0.0, 0.0, 0.0]
    sigma = p2 * x1 - p1 * x2
    phi = -float(np.sign(sigma))
    return [
        float(-phi * x2 + w * p1 / norm_p),
        float(phi * x1 + w * p2 / norm_p - 1.0),
        float(-phi * p2),
        float(phi * p1),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackwardReachableSet:
    def test_1d_decay(self) -> None:
        """Backward from x=0.5 should reach x > 0.5 (decay runs backward)."""
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 0.5}],
            integration_time=1.0,
            params={},
        )
        assert isinstance(brs, BackwardReachableSet)
        assert brs.n_trajectories == 1
        assert brs.state_names == ["x"]

        # Final backward state should be > 0.5 (since decay goes toward 0)
        _, states = brs.trajectories[0]
        final_x = states[-1]["x"]
        assert final_x > 0.5

    def test_multiple_target_points(self) -> None:
        """Multiple targets produce multiple trajectories."""
        targets = [{"x": 0.3}, {"x": 0.5}, {"x": 0.7}]
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=targets,
            integration_time=1.0,
        )
        assert brs.n_trajectories == 3
        assert len(brs.trajectories) == 3

    def test_2d_harmonic(self) -> None:
        """2D backward reachable set from the unit circle."""
        targets = [
            {"x1": math.cos(a), "x2": math.sin(a)}
            for a in [0, math.pi / 2, math.pi, 3 * math.pi / 2]
        ]
        brs = backward_reachable_set(
            dynamics=harmonic,
            state_names=["x1", "x2"],
            target_points=targets,
            integration_time=2.0,
        )
        assert brs.n_trajectories == 4
        # Harmonic oscillator conserves energy — backward states
        # should still be on the unit circle (approximately)
        for _, states in brs.trajectories:
            final = states[-1]
            r = math.sqrt(final["x1"] ** 2 + final["x2"] ** 2)
            assert r == pytest.approx(1.0, abs=0.01)

    def test_hc_capture_circle(self) -> None:
        """HC backward from capture circle produces reasonable trajectories."""
        w = 0.25
        ell = 0.5
        alpha = math.pi / 2
        x1_T = ell * math.cos(alpha)
        x2_T = ell * math.sin(alpha)
        lam = -1.0 / (ell * (w - math.sin(alpha)))
        target = {
            "x1": x1_T,
            "x2": x2_T,
            "p1": lam * x1_T,
            "p2": lam * x2_T,
        }

        brs = backward_reachable_set(
            dynamics=hc_forward,
            state_names=["x1", "x2", "p1", "p2"],
            target_points=[target],
            integration_time=5.0,
            params={"w": w},
            rtol=1e-10,
            atol=1e-12,
        )
        assert brs.n_trajectories == 1
        _, states = brs.trajectories[0]
        # Should have moved away from capture circle
        final = states[-1]
        dist = math.sqrt(final["x1"] ** 2 + final["x2"] ** 2)
        assert dist > ell  # farther than capture radius

    def test_custom_t_eval(self) -> None:
        """Custom evaluation points are respected."""
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 1.0}],
            integration_time=2.0,
            t_eval=[0.0, 0.5, 1.0, 1.5, 2.0],
        )
        _, states = brs.trajectories[0]
        assert len(states) == 5


class TestExtractIsochrones:
    def test_extract_at_times(self) -> None:
        """Isochrones extracted at requested times."""
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 0.5}, {"x": 1.0}],
            integration_time=2.0,
            t_eval=[0.0, 0.5, 1.0, 1.5, 2.0],
        )
        isos = extract_isochrones(brs, [0.0, 1.0, 2.0])
        assert len(isos) == 3
        # Each isochrone should have 2 points (one per trajectory)
        for iso in isos:
            assert len(iso.points) == 2

    def test_isochrone_times_match(self) -> None:
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 1.0}],
            integration_time=3.0,
            t_eval=[0.0, 1.0, 2.0, 3.0],
        )
        isos = extract_isochrones(brs, [1.0, 2.0])
        assert isos[0].time == 1.0
        assert isos[1].time == 2.0

    def test_isochrone_values_increase_backward(self) -> None:
        """For decay, backward isochrones at later times should be farther."""
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 0.5}],
            integration_time=3.0,
            t_eval=[0.0, 1.0, 2.0, 3.0],
        )
        isos = extract_isochrones(brs, [0.0, 1.0, 2.0, 3.0])
        xs = [iso.points[0]["x"] for iso in isos]
        # Each successive isochrone should be farther from origin
        for i in range(len(xs) - 1):
            assert xs[i + 1] > xs[i]

    def test_tolerance_filtering(self) -> None:
        """Points outside tolerance are excluded."""
        brs = backward_reachable_set(
            dynamics=simple_decay,
            state_names=["x"],
            target_points=[{"x": 1.0}],
            integration_time=1.0,
            t_eval=[0.0, 1.0],
        )
        # Request isochrone at t=0.5 — no eval point there
        isos = extract_isochrones(brs, [0.5], tolerance=0.01)
        assert isos[0].points == []  # nothing within tolerance
