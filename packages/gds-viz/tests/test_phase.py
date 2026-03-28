"""Tests for phase portrait visualization."""

from __future__ import annotations

from typing import Any

import pytest

matplotlib = pytest.importorskip("matplotlib")
numpy = pytest.importorskip("numpy")

from gds_continuous import ODEModel  # noqa: E402
from gds_viz.phase import (  # noqa: E402
    PhasePlotConfig,
    compute_trajectories,
    compute_vector_field,
    phase_portrait,
    trajectory_plot,
    vector_field_plot,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _oscillator_rhs(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """dx/dt = v, dv/dt = -x."""
    return [y[1], -y[0]]


@pytest.fixture
def oscillator() -> ODEModel:
    return ODEModel(
        state_names=["x", "v"],
        initial_state={"x": 1.0, "v": 0.0},
        rhs=_oscillator_rhs,
    )


@pytest.fixture
def config() -> PhasePlotConfig:
    return PhasePlotConfig(
        x_var="x",
        y_var="v",
        x_range=(-3.0, 3.0),
        y_range=(-3.0, 3.0),
        resolution=10,
    )


# ---------------------------------------------------------------------------
# Vector field
# ---------------------------------------------------------------------------


class TestComputeVectorField:
    def test_shape(self, oscillator: ODEModel, config: PhasePlotConfig) -> None:
        _X, _Y, _dX, _dY = compute_vector_field(oscillator, config)
        assert _X.shape == (10, 10)
        assert _dX.shape == (10, 10)

    def test_values_at_origin(
        self, oscillator: ODEModel, config: PhasePlotConfig
    ) -> None:
        """At (0,0): dx/dt=0, dv/dt=0."""

        cfg = PhasePlotConfig(
            x_var="x",
            y_var="v",
            x_range=(-1, 1),
            y_range=(-1, 1),
            resolution=3,
        )
        _X, _Y, _dX, _dY = compute_vector_field(oscillator, cfg)
        # Center point (idx 1,1 in a 3x3 grid)
        assert _dX[1, 1] == pytest.approx(0.0, abs=1e-10)
        assert _dY[1, 1] == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# Trajectories
# ---------------------------------------------------------------------------


class TestComputeTrajectories:
    def test_returns_results(self, oscillator: ODEModel) -> None:
        ics = [{"x": 1.0, "v": 0.0}, {"x": 0.0, "v": 1.0}]
        results = compute_trajectories(oscillator, ics, t_span=(0, 3))
        assert len(results) == 2
        assert len(results[0]) > 2

    def test_trajectory_is_circular(self, oscillator: ODEModel) -> None:
        """Harmonic oscillator: x^2 + v^2 = const."""
        ics = [{"x": 1.0, "v": 0.0}]
        results = compute_trajectories(oscillator, ics, t_span=(0, 6.28))
        xs = results[0].state_array("x")
        vs = results[0].state_array("v")
        r0 = xs[0] ** 2 + vs[0] ** 2
        for x, v in zip(xs, vs, strict=True):
            assert x**2 + v**2 == pytest.approx(r0, abs=1e-4)


# ---------------------------------------------------------------------------
# Plot functions (smoke tests — verify they return Figure, don't check pixels)
# ---------------------------------------------------------------------------


class TestVectorFieldPlot:
    def test_returns_figure(
        self, oscillator: ODEModel, config: PhasePlotConfig
    ) -> None:
        import matplotlib.pyplot as plt

        fig = vector_field_plot(oscillator, config)
        assert fig is not None
        plt.close(fig)


class TestTrajectoryPlot:
    def test_returns_figure(self, oscillator: ODEModel) -> None:
        import matplotlib.pyplot as plt

        ics = [{"x": 1.0, "v": 0.0}]
        results = compute_trajectories(oscillator, ics, t_span=(0, 3))
        fig = trajectory_plot(results, "x", "v")
        assert fig is not None
        plt.close(fig)


class TestPhasePortrait:
    def test_vector_field_only(self, oscillator: ODEModel) -> None:
        import matplotlib.pyplot as plt

        fig = phase_portrait(
            oscillator,
            "x",
            "v",
            x_range=(-3, 3),
            y_range=(-3, 3),
            resolution=8,
            title="Oscillator",
        )
        assert fig is not None
        plt.close(fig)

    def test_with_trajectories(self, oscillator: ODEModel) -> None:
        import matplotlib.pyplot as plt

        ics = [
            {"x": 1.0, "v": 0.0},
            {"x": 2.0, "v": 0.0},
        ]
        fig = phase_portrait(
            oscillator,
            "x",
            "v",
            x_range=(-3, 3),
            y_range=(-3, 3),
            initial_conditions=ics,
            resolution=8,
        )
        assert fig is not None
        plt.close(fig)

    def test_with_nullclines(self, oscillator: ODEModel) -> None:
        import matplotlib.pyplot as plt

        fig = phase_portrait(
            oscillator,
            "x",
            "v",
            x_range=(-3, 3),
            y_range=(-3, 3),
            show_nullclines=True,
            resolution=15,
        )
        assert fig is not None
        plt.close(fig)

    def test_high_dimensional_with_fixed(self) -> None:
        """3D system projected to 2D via fixed_states."""
        import matplotlib.pyplot as plt

        def lorenz(t: float, y: list[float], p: dict[str, Any]) -> list[float]:
            sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
            return [
                sigma * (y[1] - y[0]),
                y[0] * (rho - y[2]) - y[1],
                y[0] * y[1] - beta * y[2],
            ]

        model = ODEModel(
            state_names=["x", "y", "z"],
            initial_state={"x": 1.0, "y": 1.0, "z": 1.0},
            rhs=lorenz,
        )
        fig = phase_portrait(
            model,
            "x",
            "y",
            x_range=(-20, 20),
            y_range=(-30, 30),
            fixed_states={"z": 25.0},
            resolution=8,
        )
        assert fig is not None
        plt.close(fig)
