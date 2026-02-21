"""Crosswalk Problem — discrete Markov state transitions with mechanism design.

Demonstrates the 4-role GDS pipeline
(BoundaryAction -> Policy -> ControlAction -> Mechanism)
applied to a stylized traffic safety problem from BlockScience (Zargham & Shorish).

A pedestrian on one side of a one-way street wants to reach a destination on the
other side. They decide whether to cross (s in {0,1}) and where (position p).
"Luck" (l in {0,1}) is an exogenous binary random variable: l=1 means safe
passage regardless, l=0 means the pedestrian trips or is unseen. Traffic evolves
as a discrete Markov chain over three states:

    Flowing (+1)  — traffic moves normally
    Stopped  (0)  — traffic halts (e.g., pedestrian crossing at crosswalk)
    Accident (-1) — collision or reversal (jaywalking + bad luck)

The crosswalk location k in [0, 1] is a **design parameter** (mechanism design).
A governance body (e.g., city) chooses k to minimize accident probability.
Placing k at the **median** of the pedestrian crossing distribution is optimal.

Transition rules (Markov matrix entries):
    - Cross at crosswalk (p = k)         -> Stopped safely
    - Jaywalk (p != k) with bad luck (l=0) -> Accident
    - Don't cross (s = 0)                -> Flowing continues

Analytical properties:
    - Reachability: the Accident state IS reachable when jaywalking is admissible
    - Controllability: choosing k (crosswalk placement) controls transition
      probabilities without forcing individual pedestrian behavior

Note: The "modified crosswalk" variant (where a driver stops mid-road and
becomes a pedestrian) violates GDS sufficiency conditions — the state
transition depends on the decision function itself, breaking the separation
between procedural and decision automation. This variant is intentionally
NOT modeled here, as it demonstrates the limits of GDS representation.

Concepts Covered:
    - Discrete state spaces with integer-valued TrafficState
    - All 4 block roles: BoundaryAction, Policy, ControlAction, Mechanism
    - Design parameters (Theta) as mechanism design levers
    - ControlAction for admissibility constraints (safe vs unsafe crossing)
    - Markov transition matrix semantics in the mechanism
    - Reachability and controllability as verification outcomes
    - Binary exogenous randomness (luck) as BoundaryAction input

Prerequisites: sir_epidemic (basic roles), insurance (ControlAction role)

GDS Decomposition:
    X  = traffic_state in {-1, 0, +1}  — accident, stopped, flowing
    U  = (luck, crossing_position)      — binary randomness + pedestrian location
    s  = cross in {0, 1}                — pedestrian's binary crossing decision
    g  = pedestrian_decision             — policy: observe -> (s, p)
    d  = safety_check                    — admissibility given crosswalk location k
    f  = traffic_transition              — Markov state update
    Theta = {crosswalk_location}         — design parameter k in [0, 1]

Composition: observe >> decide >> check >> transition
"""

from gds import entity, interface, space, state_var, typedef
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spec import GDSSpec, SpecWiring, Wire

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: TrafficState is the key type — a discrete integer
# {-1, 0, +1} representing accident, stopped, flowing. BinaryChoice
# models both luck (l in {0,1}) and the crossing decision (s in {0,1}).
# ══════════════════════════════════════════════════════════════════

TrafficState = typedef(
    "TrafficState",
    int,
    constraint=lambda x: x in {-1, 0, 1},
    description="Discrete traffic state: Flowing(+1), Stopped(0), Accident(-1)",
)

BinaryChoice = typedef(
    "BinaryChoice",
    int,
    constraint=lambda x: x in {0, 1},
    description="Binary choice: 0 = no, 1 = yes",
)

StreetPosition = typedef(
    "StreetPosition",
    float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="Position along the street, normalized to [0, 1]",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Single entity, single variable — the simplest state
# space, but with rich discrete dynamics. X = traffic_state.
# ══════════════════════════════════════════════════════════════════

street = entity(
    "Street",
    description="One-way street with traffic state",
    traffic_state=state_var(TrafficState, symbol="X"),
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Three spaces form a linear signal chain. Each space
# carries data forward through the pipeline — no backward or
# temporal wiring in this model.
# ══════════════════════════════════════════════════════════════════

observation_space = space(
    "ObservationSpace",
    description="Observed traffic state and exogenous luck",
    traffic_state=TrafficState,
    luck=BinaryChoice,
)

crossing_decision_space = space(
    "CrossingDecisionSpace",
    description="Pedestrian's crossing decision",
    cross=BinaryChoice,
    position=StreetPosition,
)

safety_signal_space = space(
    "SafetySignalSpace",
    description="Safety assessment: is crossing safe?",
    safe_crossing=BinaryChoice,
    cross=BinaryChoice,
)

# ══════════════════════════════════════════════════════════════════
# Blocks — complete 4-role taxonomy
# GDS Mapping: All 4 block roles in a single linear pipeline:
#   BoundaryAction — exogenous observation (U)
#   Policy         — pedestrian decision (g)
#   ControlAction  — safety check (d) with crosswalk_location param
#   Mechanism      — Markov state transition (f)
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: exogenous traffic observation — no forward_in.
observe_traffic = BoundaryAction(
    name="Observe Traffic",
    interface=interface(forward_out=["Observation Signal"]),
    tags={"domain": "Environment"},
)

# Policy: pedestrian decides whether and where to cross.
pedestrian_decision = Policy(
    name="Pedestrian Decision",
    interface=interface(
        forward_in=["Observation Signal"],
        forward_out=["Crossing Decision"],
    ),
    tags={"domain": "Pedestrian"},
)

# ControlAction: checks if crossing is safe given crosswalk location k.
# Crossing at the crosswalk (position == k) is always safe; jaywalking
# with bad luck is dangerous. Uses params_used to reference Theta.
safety_check = ControlAction(
    name="Safety Check",
    interface=interface(
        forward_in=["Crossing Decision"],
        forward_out=["Safety Signal"],
    ),
    params_used=["crosswalk_location"],
    tags={"domain": "Infrastructure"},
)

# Mechanism: Markov state transition — updates traffic_state.
# Terminal block (no forward_out).
traffic_transition = Mechanism(
    name="Traffic Transition",
    interface=interface(forward_in=["Safety Signal"]),
    updates=[("Street", "traffic_state")],
    tags={"domain": "Environment"},
)


def build_spec() -> GDSSpec:
    """Build the complete crosswalk problem specification.

    Pure sequential spec — all wires flow forward. The ControlAction
    (Safety Check) uses crosswalk_location as a design parameter,
    demonstrating mechanism design in the GDS framework.
    """
    spec = GDSSpec(
        name="Crosswalk Problem",
        description="Discrete Markov traffic model with crosswalk mechanism design",
    )

    spec.collect(
        # Types
        TrafficState,
        BinaryChoice,
        StreetPosition,
        # Spaces
        observation_space,
        crossing_decision_space,
        safety_signal_space,
        # Entities
        street,
        # Blocks
        observe_traffic,
        pedestrian_decision,
        safety_check,
        traffic_transition,
    )

    # Parameters — Theta: design parameter for mechanism design
    spec.register_parameter("crosswalk_location", StreetPosition)

    # Wiring — pure forward sequential chain
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
                Wire(
                    source="Observe Traffic",
                    target="Pedestrian Decision",
                    space="ObservationSpace",
                ),
                Wire(
                    source="Pedestrian Decision",
                    target="Safety Check",
                    space="CrossingDecisionSpace",
                ),
                Wire(
                    source="Safety Check",
                    target="Traffic Transition",
                    space="SafetySignalSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the crosswalk system.

    Pure sequential composition — observe >> decide >> check >> transition.
    The >> operator auto-wires by token overlap between adjacent blocks.
    """
    pipeline = (
        observe_traffic >> pedestrian_decision >> safety_check >> traffic_transition
    )
    return compile_system(name="Crosswalk Problem", root=pipeline)
