"""Tests for cadCAD signature auto-detection and wrapping."""

from __future__ import annotations

from typing import Any

import gds_sim
from gds_sim.compat import _positional_count, adapt_policy, adapt_suf

# ── cadCAD-style functions (4-arg policy, 5-arg SUF) ─────────────────


def cadcad_policy(
    params: dict[str, Any],
    substep: int,
    state_history: list[Any],
    previous_state: dict[str, Any],
) -> dict[str, Any]:
    return {"step_size": params.get("rate", 1)}


def cadcad_suf(
    params: dict[str, Any],
    substep: int,
    state_history: list[Any],
    previous_state: dict[str, Any],
    policy_input: dict[str, Any],
) -> tuple[str, Any]:
    return "a", previous_state["a"] + policy_input.get("step_size", 0)


# ── New-style functions ──────────────────────────────────────────────


def new_policy(
    state: dict[str, Any], params: dict[str, Any], **kw: Any
) -> dict[str, Any]:
    return {"step_size": params.get("rate", 1)}


def new_suf(
    state: dict[str, Any],
    params: dict[str, Any],
    *,
    signal: dict[str, Any] | None = None,
    **kw: Any,
) -> tuple[str, Any]:
    signal = signal or {}
    return "a", state["a"] + signal.get("step_size", 0)


class TestPositionalCount:
    def test_four_arg(self) -> None:
        assert _positional_count(cadcad_policy) == 4

    def test_five_arg(self) -> None:
        assert _positional_count(cadcad_suf) == 5

    def test_two_arg_new_policy(self) -> None:
        assert _positional_count(new_policy) == 2

    def test_two_arg_new_suf(self) -> None:
        assert _positional_count(new_suf) == 2


class TestAdaptPolicy:
    def test_wraps_cadcad_policy(self) -> None:
        adapted = adapt_policy(cadcad_policy)
        result = adapted({"a": 1}, {"rate": 5}, timestep=1, substep=0)
        assert result == {"step_size": 5}

    def test_passes_through_new_policy(self) -> None:
        adapted = adapt_policy(new_policy)
        assert adapted is new_policy


class TestAdaptSuf:
    def test_wraps_cadcad_suf(self) -> None:
        adapted = adapt_suf(cadcad_suf)
        key, val = adapted(
            {"a": 10}, {}, signal={"step_size": 3}, timestep=1, substep=0
        )
        assert key == "a"
        assert val == 13

    def test_passes_through_new_suf(self) -> None:
        adapted = adapt_suf(new_suf)
        assert adapted is new_suf


class TestEndToEnd:
    def test_cadcad_functions_in_model(self) -> None:
        """cadCAD-style functions should work seamlessly in a Model."""
        model = gds_sim.Model(
            initial_state={"a": 1.0, "b": 2.0},
            state_update_blocks=[
                {"policies": {"p": cadcad_policy}, "variables": {"a": cadcad_suf}},
            ],
            params={"rate": [1, 2]},
        )
        sim = gds_sim.Simulation(model=model, timesteps=5)
        rows = sim.run().to_list()

        # Subset 0: rate=1, a increments by 1 each step
        subset0_final = next(r for r in rows if r["subset"] == 0 and r["timestep"] == 5)
        assert subset0_final["a"] == 6.0  # 1 + 5*1

        # Subset 1: rate=2, a increments by 2 each step
        subset1_final = next(r for r in rows if r["subset"] == 1 and r["timestep"] == 5)
        assert subset1_final["a"] == 11.0  # 1 + 5*2
