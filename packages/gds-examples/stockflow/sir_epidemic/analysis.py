"""SIR Epidemic — Dynamical Analysis with gds-analysis.

Demonstrates reachability and metric computation on a continuous-state
epidemiological model.

Run: uv run python packages/gds-examples/stockflow/sir_epidemic/analysis.py

Shows:
  1. Structural spec with AdmissibleInputConstraint + StateMetric
  2. Adapter: GDSSpec → gds_sim.Model
  3. Trajectory simulation with constraint enforcement
  4. Population distance metrics over time
  5. Reachable states from initial conditions
"""

import math
import sys
from pathlib import Path

# Allow standalone execution with correct import paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gds_analysis.adapter import spec_to_model
from gds_analysis.metrics import trajectory_distances
from gds_analysis.reachability import reachable_set

from gds.constraints import AdmissibleInputConstraint, StateMetric
from gds_sim import Simulation
from sir_epidemic.model import build_spec

# ── Behavioral functions ────────────────────────────────────────────


def contact_policy(state, params, **kw):
    return {"contact_rate": params.get("contact_rate", 5.0)}


def infection_policy(state, params, **kw):
    """SIR dynamics: dS/dt = -beta*S*I/N, dI/dt = beta*S*I/N - gamma*I."""
    s = state.get("Susceptible.count", 0.0)
    i = state.get("Infected.count", 0.0)
    r = state.get("Recovered.count", 0.0)
    n = s + i + r or 1.0
    beta = params.get("beta", 0.3)
    gamma = params.get("gamma", 0.1)

    new_infections = beta * s * i / n
    recoveries = gamma * i
    return {
        "delta_s": -new_infections,
        "delta_i": new_infections - recoveries,
        "delta_r": recoveries,
    }


def suf_susceptible(state, params, *, signal=None, **kw):
    signal = signal or {}
    return "Susceptible.count", max(
        0.0, state.get("Susceptible.count", 0.0) + signal.get("delta_s", 0.0)
    )


def suf_infected(state, params, *, signal=None, **kw):
    signal = signal or {}
    return "Infected.count", max(
        0.0, state.get("Infected.count", 0.0) + signal.get("delta_i", 0.0)
    )


def suf_recovered(state, params, *, signal=None, **kw):
    signal = signal or {}
    return "Recovered.count", max(
        0.0, state.get("Recovered.count", 0.0) + signal.get("delta_r", 0.0)
    )


def main():
    # ── 1. Build spec with structural annotations ─────────────────
    spec = build_spec()

    spec.register_admissibility(
        AdmissibleInputConstraint(
            name="contact_rate_positive",
            boundary_block="Contact Process",
            depends_on=[],
            constraint=lambda state, signal: signal.get("contact_rate", 0) > 0,
            description="Contact rate must be positive",
        )
    )
    spec.register_state_metric(
        StateMetric(
            name="population_distance",
            variables=[
                ("Susceptible", "count"),
                ("Infected", "count"),
                ("Recovered", "count"),
            ],
            metric_type="euclidean",
            distance=lambda a, b: math.sqrt(
                sum((a.get(k, 0) - b.get(k, 0)) ** 2 for k in set(a) | set(b))
            ),
        )
    )

    # ── 2. Build executable model ─────────────────────────────────
    model = spec_to_model(
        spec,
        policies={
            "Contact Process": contact_policy,
            "Infection Policy": infection_policy,
        },
        sufs={
            "Update Susceptible": suf_susceptible,
            "Update Infected": suf_infected,
            "Update Recovered": suf_recovered,
        },
        initial_state={
            "Susceptible.count": 999.0,
            "Infected.count": 1.0,
            "Recovered.count": 0.0,
        },
        params={"beta": [0.3], "gamma": [0.1], "contact_rate": [5.0]},
        enforce_constraints=True,
    )

    # ── 3. Simulate ───────────────────────────────────────────────
    print("=" * 60)
    print("SIR EPIDEMIC SIMULATION (50 timesteps)")
    print("=" * 60)

    sim = Simulation(model=model, timesteps=50, runs=1)
    trajectory = sim.run().to_list()

    peak_i = 0.0
    peak_t = 0
    for t, row in enumerate(trajectory):
        s = row.get("Susceptible.count", 0.0)
        i = row.get("Infected.count", 0.0)
        r = row.get("Recovered.count", 0.0)
        if i > peak_i:
            peak_i = i
            peak_t = t
        if t % 10 == 0 or t == len(trajectory) - 1:
            print(f"  t={t:3d}: S={s:7.1f}  I={i:7.1f}  R={r:7.1f}")

    print(f"\n  Peak infected: {peak_i:.1f} at t={peak_t}")

    # ── 4. Population conservation check ──────────────────────────
    print()
    print("=" * 60)
    print("POPULATION CONSERVATION")
    print("=" * 60)

    violations = 0
    for row in trajectory:
        total = (
            row.get("Susceptible.count", 0)
            + row.get("Infected.count", 0)
            + row.get("Recovered.count", 0)
        )
        if abs(total - 1000.0) > 1e-6:
            violations += 1

    if violations == 0:
        print("  VERIFIED: S + I + R = 1000 at every timestep")
    else:
        print(f"  WARNING: {violations} timesteps violated conservation")

    # ── 5. Trajectory distances ───────────────────────────────────
    print()
    print("=" * 60)
    print("STATE METRIC: Euclidean distance between successive states")
    print("=" * 60)

    distances = trajectory_distances(spec, trajectory)
    dists = distances["population_distance"]
    print(f"  Transitions:    {len(dists)}")
    print(f"  Max distance:   {max(dists):.2f}")
    print(f"  Mean distance:  {sum(dists) / len(dists):.2f}")
    print(f"  Final distance: {dists[-1]:.2f} (convergence indicator)")

    # ── 6. Reachable set from initial state ───────────────────────
    print()
    print("=" * 60)
    print("REACHABLE SET from (S=999, I=1, R=0)")
    print("=" * 60)

    initial = {
        "Susceptible.count": 999.0,
        "Infected.count": 1.0,
        "Recovered.count": 0.0,
    }
    # Vary the infection dynamics by overriding policy outputs
    samples = [
        {"delta_s": -d, "delta_i": d - 0.1, "delta_r": 0.1}
        for d in [0.0, 0.3, 1.0, 5.0, 10.0]
    ]
    reached = reachable_set(
        model,
        initial,
        input_samples=samples,
        state_key="Infected.count",
    ).states
    print(f"  {len(reached)} distinct next states found:")
    for r in sorted(reached, key=lambda x: x.get("Infected.count", 0)):
        s = r.get("Susceptible.count", 0)
        i = r.get("Infected.count", 0)
        rc = r.get("Recovered.count", 0)
        print(f"    S={s:.1f}  I={i:.1f}  R={rc:.1f}")


if __name__ == "__main__":
    main()
