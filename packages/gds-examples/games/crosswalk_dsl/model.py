"""Crosswalk Problem -- OGS DSL version.

Reimplements the manual Crosswalk model (crosswalk/) using the gds-games
(OGS) typed DSL. The crosswalk problem is a mechanism design model: a
pedestrian decides whether to cross a one-way street, a safety check
applies the crosswalk location parameter, and a Markov state transition
determines the traffic outcome.

In the OGS perspective, the pedestrian's crossing decision is a strategic
game: they observe traffic conditions and decide whether to cross and
where. The safety check and traffic transition are pure covariant
functions that process the decision deterministically.

The crosswalk location (k in [0, 1]) is a *design parameter* -- a
governance body chooses k to minimize accident probability. This
mechanism design aspect is captured as a constraint on the safety
check's action space.

Concepts Covered:
    - OGS DecisionGame for strategic pedestrian choice (cross/don't cross)
    - OGS CovariantFunction for deterministic processing (safety, transition)
    - Pure sequential composition (>>) -- no feedback loops
    - OGS Pattern with TerminalCondition for Markov outcomes
    - Design parameters as action space constraints
    - compile_to_ir() for OGS PatternIR generation
    - compile_pattern_to_spec() for GDS spec projection

OGS Game Theory Decomposition:
    Players: Pedestrian (crossing decision)
    Observations: Traffic state, luck (exogenous randomness)
    Actions: {Cross, Don't Cross} with position p in [0, 1]
    Outcomes: Flowing (+1), Stopped (0), Accident (-1)

    Composition: pedestrian_decision >> safety_check >> traffic_transition

Architecture (OGS perspective):
    X (observations):  Traffic state + luck
    Y (choices):       Cross/don't cross + position
    R (utilities):     Traffic outcome (safe passage or accident)
    S (coutilities):   Pedestrian experience for learning
"""

from pathlib import Path

from ogs import (
    compile_pattern_to_spec,
    compile_to_ir,
    generate_reports,
    verify,
)
from ogs.dsl.composition import (
    Flow,
    SequentialComposition,
)
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.dsl.pattern import (
    ActionSpace,
    Pattern,
    PatternInput,
    TerminalCondition,
)
from ogs.dsl.types import CompositionType, InputType, Signature, port
from ogs.ir.models import PatternIR
from ogs.verification.findings import VerificationReport

# ======================================================================
# Atomic Games -- leaf nodes of the composition tree
# ======================================================================

# Pedestrian Decision: the strategic agent in this model.
# Observes traffic conditions and exogenous luck, decides whether to
# cross and at what position. The crossing decision (s in {0, 1})
# and position (p in [0, 1]) are the action outputs.
pedestrian_decision = DecisionGame(
    name="Pedestrian Decision",
    signature=Signature(
        x=(port("Observation Signal"),),
        y=(port("Crossing Decision"),),
        r=(port("Traffic Outcome"),),
        s=(port("Pedestrian Experience"),),
    ),
    logic=(
        "Pedestrian observes the current traffic state and luck factor. "
        "Decides whether to cross (s=0: stay, s=1: cross) and where "
        "(position p in [0,1]). Rational pedestrians prefer p=k "
        "(crosswalk location) for safe crossing."
    ),
    color_code=1,
    tags={"domain": "Pedestrian"},
)

# Safety Check: a pure covariant function that determines if crossing
# is safe given the crosswalk location k. This maps to ControlAction
# in the raw GDS version -- admissibility enforcement.
# - Crossing at crosswalk (p == k): always safe
# - Jaywalking (p != k) with bad luck (l=0): unsafe
# - Not crossing (s=0): always safe
safety_check = CovariantFunction(
    name="Safety Check",
    signature=Signature(
        x=(port("Crossing Decision"),),
        y=(port("Safety Signal"),),
    ),
    logic=(
        "Given the pedestrian's crossing decision and the crosswalk "
        "location parameter k, determine if the crossing is safe. "
        "Crossing at crosswalk (position == k) is always safe. "
        "Jaywalking with bad luck leads to an accident."
    ),
    color_code=2,
    tags={"domain": "Infrastructure"},
)

# Traffic Transition: a pure covariant function implementing the Markov
# state transition. Takes the safety signal and produces the new traffic
# state. This maps to the Mechanism in the raw GDS version.
# Transition rules:
#   safe crossing -> Stopped (0)
#   unsafe crossing + bad luck -> Accident (-1)
#   no crossing -> Flowing (+1)
traffic_transition = CovariantFunction(
    name="Traffic Transition",
    signature=Signature(
        x=(port("Safety Signal"),),
        y=(port("Traffic Outcome"),),
    ),
    logic=(
        "Markov state transition: given the safety assessment, compute "
        "the next traffic state. Safe crossing -> Stopped (0). "
        "Unsafe jaywalking -> Accident (-1). No crossing -> Flowing (+1)."
    ),
    color_code=3,
    tags={"domain": "Environment"},
)


# ======================================================================
# Composition -- build the game tree
# ======================================================================


def build_game() -> SequentialComposition:
    """Build the Crosswalk Problem as an OGS composite game.

    Composition structure:
        pedestrian_decision >> safety_check >> traffic_transition

    Pure sequential pipeline -- no feedback loops. The pedestrian
    makes a one-shot crossing decision each timestep.

    Returns:
        SequentialComposition of the three-stage pipeline.
    """
    # Step 1: Pedestrian decision to safety check
    decision_to_safety = SequentialComposition(
        name="Decision to Safety",
        first=pedestrian_decision,
        second=safety_check,
        wiring=[
            Flow(
                source_game=pedestrian_decision,
                source_port="Crossing Decision",
                target_game=safety_check,
                target_port="Crossing Decision",
            ),
        ],
    )

    # Step 2: Safety check to traffic transition
    return SequentialComposition(
        name="Crosswalk Pipeline",
        first=decision_to_safety,
        second=traffic_transition,
        wiring=[
            Flow(
                source_game=safety_check,
                source_port="Safety Signal",
                target_game=traffic_transition,
                target_port="Safety Signal",
            ),
        ],
    )


# ======================================================================
# Pattern -- top-level specification unit with metadata
# ======================================================================


def build_pattern() -> Pattern:
    """Build the complete OGS Pattern for the Crosswalk Problem.

    Includes game tree, external inputs, terminal conditions
    (Markov outcomes), action spaces, and design parameter constraints.
    """
    return Pattern(
        name="Crosswalk Problem",
        game=build_game(),
        inputs=[
            PatternInput(
                name="Traffic Observation",
                input_type=InputType.SENSOR,
                schema_hint=("traffic_state: {-1, 0, +1}, luck: {0, 1}"),
                target_game="Pedestrian Decision",
                flow_label="Observation Signal",
            ),
        ],
        composition_type=CompositionType.SEQUENTIAL,
        terminal_conditions=[
            TerminalCondition(
                name="Safe Crossing",
                actions={"Pedestrian Decision": "Cross at crosswalk"},
                outcome="Pedestrian crosses safely, traffic stops",
                description=(
                    "Crossing at crosswalk location (p=k) guarantees safe passage"
                ),
                payoff_description="Traffic state -> Stopped (0)",
            ),
            TerminalCondition(
                name="Jaywalking Accident",
                actions={"Pedestrian Decision": "Cross away from crosswalk"},
                outcome="Accident due to jaywalking with bad luck",
                description=(
                    "Jaywalking (p != k) with bad luck (l=0) leads to accident"
                ),
                payoff_description="Traffic state -> Accident (-1)",
            ),
            TerminalCondition(
                name="No Crossing",
                actions={"Pedestrian Decision": "Don't cross"},
                outcome="Traffic continues flowing normally",
                description=("Pedestrian stays on the sidewalk, traffic is unaffected"),
                payoff_description="Traffic state -> Flowing (+1)",
            ),
        ],
        action_spaces=[
            ActionSpace(
                game="Pedestrian Decision",
                actions=["Cross", "Don't Cross"],
                constraints=["crosswalk_location"],
            ),
        ],
        source="dsl",
    )


# ======================================================================
# Compilation -- DSL to IR and GDS projection
# ======================================================================


def build_ir() -> PatternIR:
    """Compile the Pattern to OGS PatternIR."""
    return compile_to_ir(build_pattern())


def build_spec():
    """Compile the Pattern to a GDS spec via the OGS-to-GDS bridge."""
    return compile_pattern_to_spec(build_pattern())


# ======================================================================
# Verification
# ======================================================================


def run_verification() -> VerificationReport:
    """Run all OGS verification checks (plus delegated GDS checks)."""
    ir = build_ir()
    return verify(ir, include_gds_checks=True)


# ======================================================================
# Reports
# ======================================================================


def run_reports(output_dir: Path | None = None) -> list[Path]:
    """Generate all OGS reports for the Crosswalk Problem pattern."""
    ir = build_ir()
    if output_dir is None:
        output_dir = Path(__file__).parent / "reports"
    return generate_reports(ir, output_dir)
