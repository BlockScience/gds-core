"""Crosswalk Problem — Dynamical Analysis with gds-analysis.

Demonstrates reachability, admissibility enforcement, and metric
computation on the crosswalk Markov system.

Run: uv run python packages/gds-examples/games/crosswalk/analysis.py

This script shows how gds-analysis bridges the structural spec
(gds-framework) to runtime execution (gds-sim), enabling:
  1. Reachable set computation — R(x) from each state
  2. Reachability graph — multi-step state transitions
  3. Configuration space — strongly connected components
  4. Admissibility constraint enforcement at runtime
  5. State metric computation on trajectories
"""

import sys
from pathlib import Path

# Allow running as: uv run python packages/gds-examples/games/crosswalk/analysis.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gds_analysis.adapter import spec_to_model
from gds_analysis.metrics import trajectory_distances
from gds_analysis.reachability import (
    configuration_space,
    reachable_graph,
    reachable_set,
)

from crosswalk.model import build_spec
from gds.constraints import AdmissibleInputConstraint, StateMetric
from gds_sim import Simulation

# ── Behavioral functions ────────────────────────────────────────────


def observe_policy(state, params, **kw):
    return {
        "traffic_state": state.get("Street.traffic_state", 1),
        "luck": 1,
    }


def pedestrian_policy(state, params, **kw):
    return {"cross": 1, "position": params.get("crosswalk_location", 0.5)}


def safety_policy(state, params, **kw):
    return {"safe_crossing": 1, "cross": 1}


def transition_suf(state, params, *, signal=None, **kw):
    """Markov transition: Flowing/Stopped/Accident."""
    signal = signal or {}
    current = state.get("Street.traffic_state", 1)
    cross = signal.get("cross", 0)
    safe = signal.get("safe_crossing", 1)

    if current == -1:
        return "Street.traffic_state", 0  # Accident → Stopped (recovery)
    if cross == 0:
        return "Street.traffic_state", 1  # Don't cross → Flowing
    elif safe == 1:
        return "Street.traffic_state", 0  # Safe cross → Stopped
    else:
        return "Street.traffic_state", -1  # Jaywalk + bad luck → Accident


STATE_NAMES = {-1: "Accident", 0: "Stopped", 1: "Flowing"}


def main():
    # ── 1. Build spec with structural annotations ─────────────────
    spec = build_spec()

    spec.register_admissibility(
        AdmissibleInputConstraint(
            name="valid_traffic_state",
            boundary_block="Observe Traffic",
            depends_on=[("Street", "traffic_state")],
            constraint=lambda state, signal: (
                signal.get("traffic_state", 0) in {-1, 0, 1}
            ),
            description="Traffic state must be in {-1, 0, +1}",
        )
    )
    spec.register_state_metric(
        StateMetric(
            name="state_change",
            variables=[("Street", "traffic_state")],
            metric_type="absolute",
            distance=lambda a, b: abs(
                a.get("Street.traffic_state", 0) - b.get("Street.traffic_state", 0)
            ),
        )
    )

    # ── 2. Build executable model ─────────────────────────────────
    model = spec_to_model(
        spec,
        policies={
            "Observe Traffic": observe_policy,
            "Pedestrian Decision": pedestrian_policy,
            "Safety Check": safety_policy,
        },
        sufs={"Traffic Transition": transition_suf},
        initial_state={"Street.traffic_state": 1},
        params={"crosswalk_location": [0.5]},
        enforce_constraints=True,
    )

    # ── 3. Reachable set from each state ──────────────────────────
    print("=" * 60)
    print("REACHABLE SET ANALYSIS")
    print("=" * 60)

    input_samples = [
        {"cross": 0, "safe_crossing": 1},  # Don't cross
        {"cross": 1, "safe_crossing": 1},  # Cross safely
        {"cross": 1, "safe_crossing": 0},  # Jaywalk (bad luck)
    ]

    for start_state in [1, 0, -1]:
        state = {"Street.traffic_state": start_state}
        reached = reachable_set(
            spec,
            model,
            state,
            input_samples=input_samples,
            state_key="Street.traffic_state",
        )
        reached_vals = sorted({r["Street.traffic_state"] for r in reached})
        reached_names = [STATE_NAMES[v] for v in reached_vals]
        print(f"  R({STATE_NAMES[start_state]:>8}) = {{{', '.join(reached_names)}}}")

    # ── 4. Reachability graph ─────────────────────────────────────
    print()
    print("=" * 60)
    print("REACHABILITY GRAPH (depth=2)")
    print("=" * 60)

    initials = [{"Street.traffic_state": s} for s in [1, 0, -1]]
    graph = reachable_graph(
        spec,
        model,
        initials,
        input_samples=input_samples,
        max_depth=2,
        state_key="Street.traffic_state",
    )
    for src, dsts in sorted(graph.items()):
        src_name = STATE_NAMES.get(src[1], str(src))
        dst_names = sorted({STATE_NAMES.get(d[1], str(d)) for d in dsts})
        print(f"  {src_name:>8} -> {{{', '.join(dst_names)}}}")

    # ── 5. Configuration space (SCCs) ─────────────────────────────
    print()
    print("=" * 60)
    print("CONFIGURATION SPACE (strongly connected components)")
    print("=" * 60)

    sccs = configuration_space(graph)
    for i, scc in enumerate(sccs):
        names = sorted(STATE_NAMES.get(s[1], str(s)) for s in scc)
        mutual = "mutually reachable" if len(scc) > 1 else "isolated"
        print(f"  SCC {i + 1}: {{{', '.join(names)}}} ({mutual})")

    if sccs:
        largest = sccs[0]
        print(
            f"\n  X_C (configuration space) = "
            f"{{{', '.join(sorted(STATE_NAMES.get(s[1], str(s)) for s in largest))}}}"
        )

    # ── 6. Simulate and compute metrics ───────────────────────────
    print()
    print("=" * 60)
    print("TRAJECTORY SIMULATION (20 timesteps)")
    print("=" * 60)

    sim = Simulation(model=model, timesteps=20, runs=1)
    trajectory = sim.run().to_list()

    for t, row in enumerate(trajectory[:10]):
        ts = row.get("Street.traffic_state", "?")
        print(f"  t={t:2d}: {STATE_NAMES.get(ts, str(ts))}")
    if len(trajectory) > 10:
        print(f"  ... ({len(trajectory) - 10} more steps)")

    # ── 7. State metric distances ─────────────────────────────────
    print()
    print("=" * 60)
    print("STATE METRIC: |delta(traffic_state)|")
    print("=" * 60)

    distances = trajectory_distances(spec, trajectory)
    dists = distances["state_change"]
    n_changes = sum(1 for d in dists if d > 0)
    print(f"  Total transitions: {len(dists)}")
    print(f"  State changes:     {n_changes}")
    print(f"  Max distance:      {max(dists) if dists else 0}")
    print(f"  Mean distance:     {sum(dists) / len(dists):.2f}" if dists else "")

    # ── Key analytical result ─────────────────────────────────────
    print()
    print("=" * 60)
    print("KEY RESULT")
    print("=" * 60)
    # Check: Flowing unreachable from Accident?
    accident_reached = reachable_set(
        spec,
        model,
        {"Street.traffic_state": -1},
        input_samples=input_samples,
        state_key="Street.traffic_state",
    )
    accident_reachable = {r["Street.traffic_state"] for r in accident_reached}
    if 1 not in accident_reachable:
        print("  VERIFIED: Flowing (+1) is unreachable from Accident (-1) in one step.")
        print("  This matches Paper Def 4.1: R(Accident) = {Accident, Stopped}")
    else:
        print("  WARNING: Flowing IS reachable from Accident (unexpected)")


if __name__ == "__main__":
    main()
