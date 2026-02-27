"""Prisoner's Dilemma via OGS DSL — compositional game theory formulation.

Reimplements the manual Prisoner's Dilemma example using the gds-games (OGS)
typed DSL. Instead of hand-wiring GDS blocks, this version uses OGS atomic
games (DecisionGame, CovariantFunction), OGS composition operators (>>, |,
.feedback(), .corecursive()), and Pattern metadata to express the same
two-player iterated game.

Concepts Covered:
    - OGS DecisionGame for strategic choices (Cooperate/Defect)
    - OGS CovariantFunction for payoff computation (pure function)
    - OGS FeedbackFlow for utility feedback (outcome -> decision)
    - OGS Pattern with TerminalCondition and ActionSpace metadata
    - compile_to_ir() for OGS PatternIR generation
    - compile_pattern_to_spec() for GDS spec projection
    - OGS verification via verify()
    - OGS report generation via generate_reports()

OGS Game Theory Decomposition:
    Players: Alice, Bob
    Actions: {Cooperate, Defect}
    Payoff Matrix: (R, T, S, P) = (3, 5, 0, 1)
    Composition: (alice_decision | bob_decision) >> payoff_computation
        .feedback([payoff -> decisions])
    Temporal: .corecursive([payoff -> decisions]) for iterated play

Architecture (OGS perspective):
    X (observations):  Previous round payoffs
    Y (choices):       Cooperate / Defect decisions
    R (utilities):     Realized payoffs from the payoff matrix
    S (coutilities):   Experience fed back for learning
"""

from pathlib import Path

from ogs import (
    compile_pattern_to_spec,
    compile_to_ir,
    generate_reports,
    verify,
)
from ogs.dsl.composition import (
    FeedbackFlow,
    FeedbackLoop,
    Flow,
    ParallelComposition,
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
# Atomic Games — leaf nodes of the composition tree
# ======================================================================

# Alice's decision game: observes previous payoff, chooses Cooperate/Defect.
alice_decision = DecisionGame(
    name="Alice Decision",
    signature=Signature(
        x=(port("Alice Observation"),),
        y=(port("Alice Action"),),
        r=(port("Alice Payoff"),),
        s=(port("Alice Experience"),),
    ),
    logic=(
        "Alice observes her previous round payoff and chooses an action "
        "from {Cooperate, Defect}. Strategy may be adaptive (tit-for-tat, "
        "reinforcement learning) or fixed (always cooperate)."
    ),
    color_code=1,
    tags={"domain": "Alice"},
)

# Bob's decision game: symmetric to Alice.
bob_decision = DecisionGame(
    name="Bob Decision",
    signature=Signature(
        x=(port("Bob Observation"),),
        y=(port("Bob Action"),),
        r=(port("Bob Payoff"),),
        s=(port("Bob Experience"),),
    ),
    logic=(
        "Bob observes his previous round payoff and chooses an action "
        "from {Cooperate, Defect}. Symmetric to Alice's decision game."
    ),
    color_code=1,
    tags={"domain": "Bob"},
)

# Payoff computation: a pure covariant function that takes both actions
# and produces payoffs. No strategic choice involved — just matrix lookup.
payoff_computation = CovariantFunction(
    name="Payoff Computation",
    signature=Signature(
        x=(port("Alice Action"), port("Bob Action")),
        y=(port("Alice Payoff"), port("Bob Payoff")),
    ),
    logic=(
        "Given both players' actions, look up the payoff matrix: "
        "CC=(R,R), CD=(S,T), DC=(T,S), DD=(P,P) where "
        "R=3 (reward), T=5 (temptation), S=0 (sucker), P=1 (punishment)."
    ),
    color_code=2,
    tags={"domain": "Environment"},
)


# ======================================================================
# Composition — build the game tree
# ======================================================================


def build_game() -> FeedbackLoop:
    """Build the Prisoner's Dilemma as an OGS composite game.

    Composition structure:
        1. Parallel: Alice and Bob decide independently
        2. Sequential: decisions feed into payoff computation
        3. Feedback: payoffs feed back as utilities to decisions

    Returns:
        FeedbackLoop wrapping (alice | bob) >> payoff_computation
    """
    # Step 1: Parallel independent decisions
    decisions = ParallelComposition(
        name="Simultaneous Decisions",
        left=alice_decision,
        right=bob_decision,
    )

    # Step 2: Sequential into payoff computation with explicit wiring
    # (token overlap handles "Alice Action" -> "Alice Action" etc.)
    game_round = SequentialComposition(
        name="Game Round",
        first=decisions,
        second=payoff_computation,
        wiring=[
            Flow(
                source_game=alice_decision,
                source_port="Alice Action",
                target_game=payoff_computation,
                target_port="Alice Action",
            ),
            Flow(
                source_game=bob_decision,
                source_port="Bob Action",
                target_game=payoff_computation,
                target_port="Bob Action",
            ),
        ],
    )

    # Step 3: Feedback loop — payoffs feed back as utilities
    return FeedbackLoop(
        name="Prisoner's Dilemma",
        inner=game_round,
        feedback_wiring=[
            FeedbackFlow(
                source_game=payoff_computation,
                source_port="Alice Payoff",
                target_game=alice_decision,
                target_port="Alice Payoff",
            ),
            FeedbackFlow(
                source_game=payoff_computation,
                source_port="Bob Payoff",
                target_game=bob_decision,
                target_port="Bob Payoff",
            ),
        ],
        signature=Signature(),
    )


# ======================================================================
# Pattern — top-level specification unit with metadata
# ======================================================================


def build_pattern() -> Pattern:
    """Build the complete OGS Pattern for Prisoner's Dilemma.

    Includes game tree, external inputs, terminal conditions,
    action spaces, and composition type metadata.
    """
    return Pattern(
        name="Iterated Prisoners Dilemma",
        game=build_game(),
        inputs=[
            PatternInput(
                name="Payoff Matrix",
                input_type=InputType.EXTERNAL_WORLD,
                schema_hint="(R, T, S, P) = (3, 5, 0, 1)",
                target_game="Payoff Computation",
                flow_label="Payoff Matrix",
            ),
        ],
        composition_type=CompositionType.FEEDBACK,
        terminal_conditions=[
            TerminalCondition(
                name="Mutual Cooperation",
                actions={"Alice Decision": "Cooperate", "Bob Decision": "Cooperate"},
                outcome="Both players cooperate (Pareto optimal)",
                description="Nash equilibrium is not reached; Pareto optimum instead",
                payoff_description="R=3 each",
            ),
            TerminalCondition(
                name="Mutual Defection",
                actions={"Alice Decision": "Defect", "Bob Decision": "Defect"},
                outcome="Both players defect (Nash equilibrium)",
                description="Dominant strategy equilibrium — suboptimal",
                payoff_description="P=1 each",
            ),
            TerminalCondition(
                name="Alice Exploits",
                actions={"Alice Decision": "Defect", "Bob Decision": "Cooperate"},
                outcome="Alice defects while Bob cooperates",
                description="Alice gets temptation payoff, Bob gets sucker payoff",
                payoff_description="T=5 for Alice, S=0 for Bob",
            ),
            TerminalCondition(
                name="Bob Exploits",
                actions={"Alice Decision": "Cooperate", "Bob Decision": "Defect"},
                outcome="Bob defects while Alice cooperates",
                description="Bob gets temptation payoff, Alice gets sucker payoff",
                payoff_description="T=5 for Bob, S=0 for Alice",
            ),
        ],
        action_spaces=[
            ActionSpace(
                game="Alice Decision",
                actions=["Cooperate", "Defect"],
            ),
            ActionSpace(
                game="Bob Decision",
                actions=["Cooperate", "Defect"],
            ),
        ],
        source="dsl",
    )


# ======================================================================
# Compilation — DSL to IR and GDS projection
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
    """Generate all OGS reports for the Prisoner's Dilemma pattern."""
    ir = build_ir()
    if output_dir is None:
        output_dir = Path(__file__).parent / "reports"
    return generate_reports(ir, output_dir)
