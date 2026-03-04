"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest

import gds_sim

# ── Helper functions (new-style signatures) ──────────────────────────


def policy_growth(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> dict[str, Any]:
    return {"births": state["population"] * params.get("birth_rate", 0.03)}


def policy_death(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> dict[str, Any]:
    return {"deaths": state["population"] * params.get("death_rate", 0.01)}


def suf_population(
    state: dict[str, Any],
    params: dict[str, Any],
    *,
    signal: dict[str, Any] | None = None,
    **kw: Any,
) -> tuple[str, Any]:
    signal = signal or {}
    births = signal.get("births", 0)
    deaths = signal.get("deaths", 0)
    return "population", state["population"] + births - deaths


def suf_food(
    state: dict[str, Any],
    params: dict[str, Any],
    *,
    signal: dict[str, Any] | None = None,
    **kw: Any,
) -> tuple[str, Any]:
    consumption = state["population"] * 0.001
    return "food", state["food"] - consumption


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def simple_model() -> gds_sim.Model:
    return gds_sim.Model(
        initial_state={"population": 100.0, "food": 50.0},
        state_update_blocks=[
            {
                "policies": {"growth": policy_growth, "death": policy_death},
                "variables": {"population": suf_population},
            },
            {
                "policies": {},
                "variables": {"food": suf_food},
            },
        ],
    )


@pytest.fixture
def sweep_model() -> gds_sim.Model:
    return gds_sim.Model(
        initial_state={"population": 100.0, "food": 50.0},
        state_update_blocks=[
            {
                "policies": {"growth": policy_growth},
                "variables": {"population": suf_population},
            },
        ],
        params={"birth_rate": [0.03, 0.05], "death_rate": [0.01]},
    )
