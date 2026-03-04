"""Tests for multi-process execution."""

from __future__ import annotations

from typing import Any

import gds_sim


def _policy(state: dict[str, Any], params: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return {"delta": params.get("rate", 1)}


def _suf(
    state: dict[str, Any],
    params: dict[str, Any],
    *,
    signal: dict[str, Any] | None = None,
    **kw: Any,
) -> tuple[str, Any]:
    signal = signal or {}
    return "x", state["x"] + signal.get("delta", 0)


class TestExperimentExecution:
    def test_single_process(self) -> None:
        model = gds_sim.Model(
            initial_state={"x": 0.0},
            state_update_blocks=[
                {"policies": {"p": _policy}, "variables": {"x": _suf}}
            ],
            params={"rate": [1, 2]},
        )
        sim = gds_sim.Simulation(model=model, timesteps=10, runs=1)
        exp = gds_sim.Experiment(simulations=[sim], processes=1)
        results = exp.run()
        rows = results.to_list()
        subsets = {r["subset"] for r in rows}
        assert subsets == {0, 1}

    def test_matches_sequential(self) -> None:
        """Parallel results should match single-process results."""
        model = gds_sim.Model(
            initial_state={"x": 0.0},
            state_update_blocks=[
                {"policies": {"p": _policy}, "variables": {"x": _suf}}
            ],
            params={"rate": [1, 3]},
        )
        sim_seq = gds_sim.Simulation(model=model, timesteps=20, runs=2)
        sim_par = gds_sim.Simulation(model=model, timesteps=20, runs=2)

        exp_seq = gds_sim.Experiment(simulations=[sim_seq], processes=1)
        exp_par = gds_sim.Experiment(simulations=[sim_par], processes=2)

        rows_seq = exp_seq.run().to_list()
        rows_par = exp_par.run().to_list()

        # Same number of rows
        assert len(rows_seq) == len(rows_par)

        # Sort both by (subset, run, timestep, substep) for comparison
        def sort_key(r: dict[str, Any]) -> tuple[int, ...]:
            return (r["subset"], r["run"], r["timestep"], r["substep"])

        rows_seq.sort(key=sort_key)
        rows_par.sort(key=sort_key)

        for s, p in zip(rows_seq, rows_par, strict=True):
            assert s["x"] == p["x"], (
                f"Mismatch at t={s['timestep']}: {s['x']} != {p['x']}"
            )
            assert s["subset"] == p["subset"]
            assert s["run"] == p["run"]

    def test_multiple_simulations(self) -> None:
        model1 = gds_sim.Model(
            initial_state={"x": 0.0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _suf}}],
        )
        model2 = gds_sim.Model(
            initial_state={"x": 100.0},
            state_update_blocks=[{"policies": {}, "variables": {"x": _suf}}],
        )
        sim1 = gds_sim.Simulation(model=model1, timesteps=5)
        sim2 = gds_sim.Simulation(model=model2, timesteps=5)
        exp = gds_sim.Experiment(simulations=[sim1, sim2], processes=1)
        results = exp.run()
        assert len(results) == 12  # (1 + 5) * 2
