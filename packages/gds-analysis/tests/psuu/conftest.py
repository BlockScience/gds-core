"""Shared fixtures for gds-psuu tests."""

from __future__ import annotations

import pytest
from gds_sim import Model, StateUpdateBlock

from gds_analysis.psuu import (
    KPI,
    Continuous,
    Discrete,
    ParameterSpace,
    final_state_mean,
)


def _growth_policy(state: dict, params: dict, **kw: object) -> dict:
    return {"delta": state["population"] * params.get("growth_rate", 0.05)}


def _update_population(
    state: dict, params: dict, *, signal: dict | None = None, **kw: object
) -> tuple[str, float]:
    delta = signal["delta"] if signal else 0.0
    return ("population", state["population"] + delta)


@pytest.fixture
def simple_model() -> Model:
    """A deterministic growth model with one state variable."""
    return Model(
        initial_state={"population": 100.0},
        state_update_blocks=[
            StateUpdateBlock(
                policies={"growth": _growth_policy},
                variables={"population": _update_population},
            )
        ],
    )


@pytest.fixture
def simple_space() -> ParameterSpace:
    """A small parameter space with one continuous and one discrete dim."""
    return ParameterSpace(
        params={
            "growth_rate": Continuous(min_val=0.01, max_val=0.1),
            "strategy": Discrete(values=("A", "B")),
        }
    )


@pytest.fixture
def simple_kpi() -> KPI:
    """A KPI that computes mean final population."""
    return KPI(name="final_pop", fn=lambda r: final_state_mean(r, "population"))
