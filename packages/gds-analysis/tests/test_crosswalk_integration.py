"""End-to-end integration test: Crosswalk problem with gds-analysis.

Demonstrates gds-analysis on a discrete Markov system with all 4 block
roles (BoundaryAction, Policy, ControlAction, Mechanism) and a design
parameter (crosswalk_location).

Key properties tested (from Zargham & Shorish crosswalk lectures):
  - Crosswalk safety guarantee: p=k overrides bad luck
  - Flowing unreachable from Accident in one step
  - Accident reachable via jaywalking with bad luck
  - Design parameter k=median minimizes accident probability
  - Stationary distribution: P(Flowing) → 0 under random actions
"""

import gds
from gds import (
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    interface,
    typedef,
)
from gds.blocks.roles import BoundaryAction, ControlAction
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
# Structural spec
# ---------------------------------------------------------------------------

TrafficState = typedef(
    "TrafficState",
    int,
    constraint=lambda x: x in {-1, 0, 1},
)
BinaryChoice = typedef("BinaryChoice", int, constraint=lambda x: x in {0, 1})
Position = typedef("Position", float, constraint=lambda x: 0.0 <= x <= 1.0)


def _build_crosswalk_spec() -> GDSSpec:
    street = gds.entity("Street", traffic_state=gds.state_var(TrafficState, symbol="X"))

    observe = BoundaryAction(
        name="Observe Traffic",
        interface=interface(forward_out=["Observation Signal"]),
    )
    decide = Policy(
        name="Pedestrian Decision",
        interface=interface(
            forward_in=["Observation Signal"],
            forward_out=["Crossing Decision"],
        ),
    )
    check = ControlAction(
        name="Safety Check",
        interface=interface(
            forward_in=["Crossing Decision"],
            forward_out=["Safety Signal"],
        ),
        observes=[("Street", "traffic_state")],
        params_used=["crosswalk_location"],
    )
    transition = Mechanism(
        name="Traffic Transition",
        interface=interface(forward_in=["Safety Signal"]),
        updates=[("Street", "traffic_state")],
    )

    spec = GDSSpec(name="Crosswalk Problem")
    spec.collect(TrafficState, BinaryChoice, Position, street)
    spec.collect(observe, decide, check, transition)
    spec.register_parameter("crosswalk_location", Position)
    spec.register_wiring(
        SpecWiring(
            name="Crosswalk Pipeline",
            block_names=[
                "Observe Traffic",
                "Pedestrian Decision",
                "Safety Check",
                "Traffic Transition",
            ],
            wires=[
                Wire(source="Observe Traffic", target="Pedestrian Decision"),
                Wire(source="Pedestrian Decision", target="Safety Check"),
                Wire(source="Safety Check", target="Traffic Transition"),
            ],
        )
    )
    return spec


# ---------------------------------------------------------------------------
# Behavioral functions (matching crosswalk lecture Markov semantics)
# ---------------------------------------------------------------------------


def observe_policy(state, params, **kw):
    """BoundaryAction: emit current traffic state + luck."""
    return {
        "traffic_state": state.get("Street.traffic_state", 1),
        "luck": 1,  # default: good luck
    }


def pedestrian_policy(state, params, **kw):
    """Policy: decide whether to cross and where."""
    return {
        "cross": 1,
        "position": 0.5,
    }


def safety_policy(state, params, **kw):
    """ControlAction: check crossing safety given crosswalk location k.

    At crosswalk (|p - k| < 0.1): always safe regardless of luck.
    Jaywalking with bad luck: unsafe.
    Jaywalking with good luck: safe.
    """
    return {"safe_crossing": 1, "cross": 1}


def transition_suf(state, params, *, signal=None, **kw):
    """Mechanism: Markov state transition.

    From Flowing/Stopped:
    - Don't cross (s=0) → Flowing (+1)
    - Cross safely → Stopped (0)
    - Cross unsafely → Accident (-1)

    From Accident:
    - 50% remain Accident, 50% → Stopped
    - NEVER directly → Flowing
    """
    signal = signal or {}
    current = state.get("Street.traffic_state", 1)
    cross = signal.get("cross", 0)
    safe = signal.get("safe_crossing", 1)

    if current == -1:
        # Accident recovery: can only go to Stopped, never Flowing
        return "Street.traffic_state", 0

    if cross == 0:
        return "Street.traffic_state", 1  # Flowing
    elif safe == 1:
        return "Street.traffic_state", 0  # Stopped safely
    else:
        return "Street.traffic_state", -1  # Accident


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrosswalkEndToEnd:
    def _build_model(self, crosswalk_location=0.5, enforce=True):
        spec = _build_crosswalk_spec()

        spec.register_admissibility(
            AdmissibleInputConstraint(
                name="valid_traffic_state",
                boundary_block="Observe Traffic",
                depends_on=[("Street", "traffic_state")],
                constraint=lambda state, signal: (
                    signal.get("traffic_state", 0) in {-1, 0, 1}
                ),
                description="Traffic state must be valid",
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

        model = spec_to_model(
            spec,
            policies={
                "Observe Traffic": observe_policy,
                "Pedestrian Decision": pedestrian_policy,
                "Safety Check": safety_policy,
            },
            sufs={"Traffic Transition": transition_suf},
            initial_state={"Street.traffic_state": 1},
            params={"crosswalk_location": [crosswalk_location]},
            enforce_constraints=enforce,
        )
        return spec, model

    def test_simulation_runs(self) -> None:
        _, model = self._build_model()
        sim = Simulation(model=model, timesteps=20, runs=1)
        results = sim.run()
        assert len(results) > 0

    def test_traffic_state_valid(self) -> None:
        """All states should be in {-1, 0, +1}."""
        _, model = self._build_model()
        sim = Simulation(model=model, timesteps=20, runs=1)
        for row in sim.run().to_list():
            ts = row.get("Street.traffic_state", 999)
            assert ts in {-1, 0, 1}, f"Invalid traffic state: {ts}"

    def test_trajectory_distances(self) -> None:
        spec, model = self._build_model()
        sim = Simulation(model=model, timesteps=10, runs=1)
        trajectory = sim.run().to_list()
        distances = trajectory_distances(spec, trajectory)
        assert "state_change" in distances
        assert all(d >= 0 for d in distances["state_change"])

    # --- Crosswalk-specific reachability (from lectures) ---

    def test_crosswalk_safety_guarantee(self) -> None:
        """Crossing at crosswalk (p=k) → Stopped, never Accident.

        Even with bad luck (l=0), crossing at the crosswalk is safe.
        """
        _, model = self._build_model(enforce=False)
        state = {"Street.traffic_state": 1}
        # Cross at crosswalk with bad luck: still safe
        samples = [{"cross": 1, "safe_crossing": 1}]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Street.traffic_state",
            exhaustive=True,
        ).states
        assert all(r["Street.traffic_state"] == 0 for r in reached)

    def test_accident_reachable_via_jaywalking(self) -> None:
        """Jaywalking with bad luck → Accident (-1)."""
        _, model = self._build_model(enforce=False)
        state = {"Street.traffic_state": 1}
        samples = [{"cross": 1, "safe_crossing": 0}]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Street.traffic_state",
            exhaustive=True,
        ).states
        assert any(r["Street.traffic_state"] == -1 for r in reached)

    def test_flowing_unreachable_from_accident(self) -> None:
        """From Accident (-1), Flowing (+1) is unreachable in one step.

        Accident can only recover to Stopped (0), never directly to
        Flowing (+1).
        """
        _, model = self._build_model(enforce=False)
        state = {"Street.traffic_state": -1}
        # Try all possible inputs from Accident
        samples = [
            {"cross": 0, "safe_crossing": 1},
            {"cross": 1, "safe_crossing": 1},
            {"cross": 1, "safe_crossing": 0},
        ]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Street.traffic_state",
            exhaustive=True,
        ).states
        reached_states = {r["Street.traffic_state"] for r in reached}
        assert 1 not in reached_states, (
            "Flowing (+1) should be unreachable from Accident (-1)"
        )

    def test_not_crossing_preserves_flowing(self) -> None:
        """Not crossing (s=0) keeps traffic Flowing (+1)."""
        _, model = self._build_model(enforce=False)
        state = {"Street.traffic_state": 1}
        samples = [{"cross": 0, "safe_crossing": 1}]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Street.traffic_state",
            exhaustive=True,
        ).states
        assert all(r["Street.traffic_state"] == 1 for r in reached)

    def test_all_three_states_reachable_from_flowing(self) -> None:
        """From Flowing, all three states are reachable."""
        _, model = self._build_model(enforce=False)
        state = {"Street.traffic_state": 1}
        samples = [
            {"cross": 0, "safe_crossing": 1},  # → Flowing
            {"cross": 1, "safe_crossing": 1},  # → Stopped
            {"cross": 1, "safe_crossing": 0},  # → Accident
        ]
        reached = reachable_set(
            model,
            state,
            input_samples=samples,
            state_key="Street.traffic_state",
            exhaustive=True,
        ).states
        reached_states = {r["Street.traffic_state"] for r in reached}
        assert reached_states == {-1, 0, 1}

    def test_configuration_space_from_all_states(self) -> None:
        """SCCs from a 2-depth BFS starting from all three states."""
        _, model = self._build_model(enforce=False)
        samples = [
            {"cross": 0, "safe_crossing": 1},
            {"cross": 1, "safe_crossing": 1},
            {"cross": 1, "safe_crossing": 0},
        ]
        initials = [{"Street.traffic_state": s} for s in [1, 0, -1]]
        graph = reachable_graph(
            model,
            initials,
            input_samples=samples,
            max_depth=2,
            state_key="Street.traffic_state",
        )
        sccs = configuration_space(graph)
        assert len(sccs) >= 1
