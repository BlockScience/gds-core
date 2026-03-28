"""End-to-end integration test: SIR epidemic with gds-analysis.

Demonstrates the full pipeline:
  spec (gds-framework) → adapter (gds-analysis) → simulate (gds-sim)
  → metrics + reachability (gds-analysis)

Uses the SIR epidemic model from gds-examples as the structural spec,
with behavioral functions defined here.
"""

import math

from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    interface,
    typedef,
)
from gds.constraints import AdmissibleInputConstraint, StateMetric
from gds_sim import Simulation

from gds_analysis.adapter import spec_to_model
from gds_analysis.metrics import trajectory_distances
from gds_analysis.reachability import (
    configuration_space,
    reachable_graph,
    reachable_set,
)

# ---------------------------------------------------------------------------
# Structural spec (R1 — from gds-framework)
# ---------------------------------------------------------------------------

Count = typedef("Count", int, constraint=lambda x: x >= 0)
Rate = typedef("Rate", float, constraint=lambda x: x > 0)


def _build_sir_spec() -> GDSSpec:
    """Minimal SIR spec for integration testing."""
    import gds

    entity_s = gds.entity("Susceptible", count=gds.state_var(Count, symbol="S"))
    entity_i = gds.entity("Infected", count=gds.state_var(Count, symbol="I"))
    entity_r = gds.entity("Recovered", count=gds.state_var(Count, symbol="R"))

    contact = BoundaryAction(
        name="Contact Process",
        interface=interface(forward_out=["Contact Signal"]),
        params_used=["contact_rate"],
    )
    policy = Policy(
        name="Infection Policy",
        interface=interface(
            forward_in=["Contact Signal"],
            forward_out=["Susceptible Delta", "Infected Delta", "Recovered Delta"],
        ),
        params_used=["beta", "gamma"],
    )
    update_s = Mechanism(
        name="Update Susceptible",
        interface=interface(forward_in=["Susceptible Delta"]),
        updates=[("Susceptible", "count")],
    )
    update_i = Mechanism(
        name="Update Infected",
        interface=interface(forward_in=["Infected Delta"]),
        updates=[("Infected", "count")],
    )
    update_r = Mechanism(
        name="Update Recovered",
        interface=interface(forward_in=["Recovered Delta"]),
        updates=[("Recovered", "count")],
    )

    spec = GDSSpec(name="SIR Epidemic")
    spec.collect(Count, Rate, entity_s, entity_i, entity_r)
    spec.collect(contact, policy, update_s, update_i, update_r)
    spec.register_parameter("beta", Rate)
    spec.register_parameter("gamma", Rate)
    spec.register_parameter("contact_rate", Rate)
    spec.register_wiring(
        SpecWiring(
            name="SIR Pipeline",
            block_names=[
                "Contact Process",
                "Infection Policy",
                "Update Susceptible",
                "Update Infected",
                "Update Recovered",
            ],
            wires=[
                Wire(source="Contact Process", target="Infection Policy"),
                Wire(source="Infection Policy", target="Update Susceptible"),
                Wire(source="Infection Policy", target="Update Infected"),
                Wire(source="Infection Policy", target="Update Recovered"),
            ],
        )
    )
    return spec


# ---------------------------------------------------------------------------
# Behavioral functions (R3 — user-supplied)
# ---------------------------------------------------------------------------


def contact_policy(state, params, **kw):
    """BoundaryAction: emit the exogenous contact rate."""
    return {"contact_rate": params.get("contact_rate", 5.0)}


def infection_policy(state, params, **kw):
    """Policy: compute population deltas from SIR dynamics.

    dS = -beta * S * I / N
    dI = beta * S * I / N - gamma * I
    dR = gamma * I
    """
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
    s = state.get("Susceptible.count", 0.0)
    return "Susceptible.count", max(0.0, s + signal.get("delta_s", 0.0))


def suf_infected(state, params, *, signal=None, **kw):
    signal = signal or {}
    i = state.get("Infected.count", 0.0)
    return "Infected.count", max(0.0, i + signal.get("delta_i", 0.0))


def suf_recovered(state, params, *, signal=None, **kw):
    signal = signal or {}
    r = state.get("Recovered.count", 0.0)
    return "Recovered.count", max(0.0, r + signal.get("delta_r", 0.0))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSIREndToEnd:
    """Full pipeline: spec → model → simulate → analyze."""

    def _build_sir_model(self, enforce_constraints=True):
        spec = _build_sir_spec()

        # Add structural annotations
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
            params={
                "beta": [0.3],
                "gamma": [0.1],
                "contact_rate": [5.0],
            },
            enforce_constraints=enforce_constraints,
        )
        return spec, model

    def test_simulation_runs(self) -> None:
        _, model = self._build_sir_model()
        sim = Simulation(model=model, timesteps=50, runs=1)
        results = sim.run()
        rows = results.to_list()
        assert len(rows) > 0

    def test_population_conserved(self) -> None:
        """S + I + R should remain constant (= 1000)."""
        _, model = self._build_sir_model()
        sim = Simulation(model=model, timesteps=50, runs=1)
        results = sim.run()
        for row in results.to_list():
            s = row.get("Susceptible.count", 0.0)
            i = row.get("Infected.count", 0.0)
            r = row.get("Recovered.count", 0.0)
            total = s + i + r
            assert abs(total - 1000.0) < 1e-6, f"Population not conserved: {total}"

    def test_epidemic_progresses(self) -> None:
        """Infected count should rise from initial 1."""
        _, model = self._build_sir_model()
        sim = Simulation(model=model, timesteps=50, runs=1)
        rows = sim.run().to_list()
        peak_infected = max(row.get("Infected.count", 0) for row in rows)
        assert peak_infected > 1

    def test_trajectory_distances(self) -> None:
        """StateMetric distances should be non-negative."""
        spec, model = self._build_sir_model()
        sim = Simulation(model=model, timesteps=20, runs=1)
        trajectory = sim.run().to_list()
        distances = trajectory_distances(spec, trajectory)
        assert "population_distance" in distances
        assert all(d >= 0 for d in distances["population_distance"])

    def test_reachable_set(self) -> None:
        """R(x) from initial state with varied contact rates."""
        _, model = self._build_sir_model(enforce_constraints=False)
        state = {
            "Susceptible.count": 999.0,
            "Infected.count": 1.0,
            "Recovered.count": 0.0,
        }
        samples = [
            {"contact_rate": c, "delta_s": 0, "delta_i": 0, "delta_r": 0}
            for c in [1.0, 5.0, 10.0, 20.0]
        ]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Infected.count",
        ).states
        assert len(reached) >= 1

    def test_reachability_graph(self) -> None:
        """Build a small reachability graph from initial state."""
        _, model = self._build_sir_model(enforce_constraints=False)
        initial = {
            "Susceptible.count": 999.0,
            "Infected.count": 1.0,
            "Recovered.count": 0.0,
        }
        samples = [
            {"delta_s": -1, "delta_i": 1, "delta_r": 0},
            {"delta_s": 0, "delta_i": -1, "delta_r": 1},
        ]
        graph = reachable_graph(
            model,
            [initial],
            input_samples=samples,
            max_depth=2,
            state_key="Infected.count",
        )
        assert len(graph) >= 1

    def test_configuration_space(self) -> None:
        """SCCs should exist in the reachability graph."""
        _, model = self._build_sir_model(enforce_constraints=False)
        initial = {
            "Susceptible.count": 999.0,
            "Infected.count": 1.0,
            "Recovered.count": 0.0,
        }
        samples = [
            {"delta_s": -1, "delta_i": 1, "delta_r": 0},
            {"delta_s": 0, "delta_i": -1, "delta_r": 1},
        ]
        graph = reachable_graph(
            model,
            [initial],
            input_samples=samples,
            max_depth=2,
            state_key="Infected.count",
        )
        sccs = configuration_space(graph)
        assert len(sccs) >= 1

    def test_constraint_enforcement(self) -> None:
        """Constraint guard should allow valid contact rates."""
        _, model = self._build_sir_model(enforce_constraints=True)
        sim = Simulation(model=model, timesteps=5, runs=1)
        results = sim.run()
        assert len(results) > 0
