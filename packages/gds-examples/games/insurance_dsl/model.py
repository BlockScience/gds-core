"""Insurance Contract -- OGS DSL version.

Reimplements the manual Insurance Contract model (insurance/) using the
gds-games (OGS) typed DSL. Instead of hand-wiring GDS blocks, this version
uses OGS atomic games (DecisionGame, CovariantFunction), OGS composition
operators (>>, .feedback()), and Pattern metadata to express the insurance
claim processing pipeline as a compositional game.

The raw GDS version demonstrates the 4-role taxonomy with ControlAction for
admissibility. In the OGS perspective, the premium calculation is a strategic
decision game: the insurer observes the risk score and decides on premium
and approval, receiving payout outcomes as utility feedback.

Concepts Covered:
    - OGS CovariantFunction for pure transformation (risk scoring, payout)
    - OGS DecisionGame for strategic insurer decision (premium calculation)
    - OGS FeedbackFlow for utility feedback (payout -> insurer decision)
    - OGS Pattern with TerminalCondition and ActionSpace metadata
    - compile_to_ir() for OGS PatternIR generation
    - compile_pattern_to_spec() for GDS spec projection
    - OGS verification via verify()
    - OGS report generation via generate_reports()

OGS Game Theory Decomposition:
    Players: Insurer (premium decision)
    Observations: Risk score from claim assessment
    Actions: {Approve, Deny} with premium level
    Utilities: Payout outcomes (premium collected vs claims paid)

    Composition: risk_assessment >> premium_decision >> payout_processing
        .feedback([payout outcome -> insurer utility])

Architecture (OGS perspective):
    X (observations):  Claim event data, risk score
    Y (choices):       Premium decision (approve/deny + amount)
    R (utilities):     Payout outcome for insurer
    S (coutilities):   Insurer experience for learning
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

# Risk Assessment: a pure covariant function that takes claim event data
# and produces a risk score. No strategic choice -- just computation.
risk_assessment = CovariantFunction(
    name="Risk Assessment",
    signature=Signature(
        x=(port("Claim Event"),),
        y=(port("Risk Score"),),
    ),
    logic=(
        "Evaluate the incoming claim event data and produce a normalized "
        "risk score in [0, 1]. Higher scores indicate riskier claims. "
        "Uses actuarial tables and claims history for assessment."
    ),
    color_code=1,
    tags={"domain": "Underwriting"},
)

# Premium Decision: the insurer's strategic decision game.
# Observes the risk score, decides on premium amount and approval.
# Receives payout outcome as utility feedback for learning.
# This maps to the ControlAction role in the raw GDS version.
premium_decision = DecisionGame(
    name="Premium Decision",
    signature=Signature(
        x=(port("Risk Score"),),
        y=(port("Premium Action"),),
        r=(port("Insurer Outcome"),),
        s=(port("Insurer Experience"),),
    ),
    logic=(
        "The insurer observes the risk score and decides: (1) whether to "
        "approve or deny the claim, and (2) the premium amount to charge. "
        "The decision is constrained by the base premium rate, deductible, "
        "and coverage limit parameters. Strategy may be rule-based or "
        "adaptive (reinforcement learning from payout outcomes)."
    ),
    color_code=2,
    tags={"domain": "Underwriting"},
)

# Payout Processing: a pure covariant function that takes the premium
# decision and computes the claim payout result. No strategic choice.
payout_processing = CovariantFunction(
    name="Payout Processing",
    signature=Signature(
        x=(port("Premium Action"),),
        y=(port("Insurer Outcome"),),
    ),
    logic=(
        "Given the insurer's premium decision (approve/deny + amount), "
        "compute the payout result: the claim amount minus deductible "
        "if approved, zero if denied. Updates reserve and premium pool."
    ),
    color_code=1,
    tags={"domain": "Claims"},
)


# ======================================================================
# Composition -- build the game tree
# ======================================================================


def build_game() -> FeedbackLoop:
    """Build the Insurance Contract as an OGS composite game.

    Composition structure:
        1. Sequential: risk assessment -> premium decision -> payout processing
        2. Feedback: payout outcome feeds back as utility to premium decision

    Returns:
        FeedbackLoop wrapping risk_assessment >> premium_decision >> payout
    """
    # Step 1: Sequential chain with explicit wiring
    assessment_to_decision = SequentialComposition(
        name="Assessment to Decision",
        first=risk_assessment,
        second=premium_decision,
        wiring=[
            Flow(
                source_game=risk_assessment,
                source_port="Risk Score",
                target_game=premium_decision,
                target_port="Risk Score",
            ),
        ],
    )

    claims_pipeline = SequentialComposition(
        name="Claims Pipeline",
        first=assessment_to_decision,
        second=payout_processing,
        wiring=[
            Flow(
                source_game=premium_decision,
                source_port="Premium Action",
                target_game=payout_processing,
                target_port="Premium Action",
            ),
        ],
    )

    # Step 2: Feedback loop -- payout outcome feeds back as insurer utility
    return FeedbackLoop(
        name="Insurance Contract",
        inner=claims_pipeline,
        feedback_wiring=[
            FeedbackFlow(
                source_game=payout_processing,
                source_port="Insurer Outcome",
                target_game=premium_decision,
                target_port="Insurer Outcome",
            ),
        ],
        signature=Signature(),
    )


# ======================================================================
# Pattern -- top-level specification unit with metadata
# ======================================================================


def build_pattern() -> Pattern:
    """Build the complete OGS Pattern for the Insurance Contract.

    Includes game tree, external inputs, terminal conditions,
    action spaces, and composition type metadata.
    """
    return Pattern(
        name="Insurance Contract",
        game=build_game(),
        inputs=[
            PatternInput(
                name="Claim Event Source",
                input_type=InputType.EXTERNAL_WORLD,
                schema_hint="amount: Currency, claim_count: int",
                target_game="Risk Assessment",
                flow_label="Claim Event",
            ),
        ],
        composition_type=CompositionType.FEEDBACK,
        terminal_conditions=[
            TerminalCondition(
                name="Claim Approved",
                actions={"Premium Decision": "Approve"},
                outcome="Claim is approved, payout processed",
                description="Insurer approves the claim after risk assessment",
                payoff_description="Payout = claim_amount - deductible",
            ),
            TerminalCondition(
                name="Claim Denied",
                actions={"Premium Decision": "Deny"},
                outcome="Claim is denied, no payout",
                description=(
                    "Insurer denies the claim due to high risk or policy limits"
                ),
                payoff_description="Payout = 0, premium retained",
            ),
        ],
        action_spaces=[
            ActionSpace(
                game="Premium Decision",
                actions=["Approve", "Deny"],
                constraints=["base_premium_rate", "deductible", "coverage_limit"],
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
    """Generate all OGS reports for the Insurance Contract pattern."""
    ir = build_ir()
    if output_dir is None:
        output_dir = Path(__file__).parent / "reports"
    return generate_reports(ir, output_dir)
