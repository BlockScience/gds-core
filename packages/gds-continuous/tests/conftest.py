"""Shared fixtures for gds-continuous tests."""

from __future__ import annotations

from typing import Any

import pytest

from gds_continuous.model import ODEModel, ODESimulation

# ---------------------------------------------------------------------------
# ODE functions (plain callables)
# ---------------------------------------------------------------------------


def exponential_decay(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """dx/dt = -k*x. Exact solution: x(t) = x0 * exp(-k*t)."""
    k = params.get("k", 1.0)
    return [-k * y[0]]


def harmonic_oscillator(
    t: float, y: list[float], params: dict[str, Any]
) -> list[float]:
    """dx/dt = v, dv/dt = -omega^2 * x. Exact: x(t) = x0*cos(omega*t)."""
    omega = params.get("omega", 1.0)
    return [y[1], -(omega**2) * y[0]]


def lotka_volterra(t: float, y: list[float], params: dict[str, Any]) -> list[float]:
    """Predator-prey: dx/dt = alpha*x - beta*x*y, dy/dt = delta*x*y - gamma*y."""
    alpha = params.get("alpha", 1.0)
    beta = params.get("beta", 0.1)
    delta = params.get("delta", 0.075)
    gamma = params.get("gamma", 1.5)
    x, prey = y[0], y[1]
    return [
        alpha * x - beta * x * prey,
        delta * x * prey - gamma * prey,
    ]


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def decay_model() -> ODEModel:
    """Single-variable exponential decay model."""
    return ODEModel(
        state_names=["x"],
        initial_state={"x": 1.0},
        rhs=exponential_decay,
        params={"k": [1.0]},
    )


@pytest.fixture
def oscillator_model() -> ODEModel:
    """Two-variable harmonic oscillator model."""
    return ODEModel(
        state_names=["x", "v"],
        initial_state={"x": 1.0, "v": 0.0},
        rhs=harmonic_oscillator,
        params={"omega": [1.0]},
    )


@pytest.fixture
def decay_sim(decay_model: ODEModel) -> ODESimulation:
    """Decay simulation: t=[0, 5], 101 eval points."""
    import numpy as np

    return ODESimulation(
        model=decay_model,
        t_span=(0.0, 5.0),
        t_eval=list(np.linspace(0, 5, 101)),
    )


@pytest.fixture
def oscillator_sim(oscillator_model: ODEModel) -> ODESimulation:
    """Oscillator simulation: t=[0, 2*pi], 201 eval points."""
    import numpy as np

    return ODESimulation(
        model=oscillator_model,
        t_span=(0.0, 2 * np.pi),
        t_eval=list(np.linspace(0, 2 * np.pi, 201)),
    )
