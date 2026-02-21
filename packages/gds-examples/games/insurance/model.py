"""Insurance Contract Model — ControlAction for admissibility.

Demonstrates the ControlAction role, which reads state and emits
control signals (unlike Mechanism which writes state, and unlike
BoundaryAction which has no forward inputs).

Concepts Covered:
    - ControlAction role — the 4th and final block role
    - Complete 4-role taxonomy: BoundaryAction, Policy, ControlAction, Mechanism
    - Pure sequential pipeline (no feedback or temporal loops)
    - Mechanism with forward_out for chaining (Claim Payout → Reserve Update)
    - params_used on ControlAction (Θ for admissibility constraints)

Prerequisites: sir_epidemic (basic roles, >>)

GDS Decomposition:
    X  = (R, P, C, H)      — insurer reserve, premium pool,
                              policyholder coverage, claims history
    U  = claim_event        — exogenous claim arrival
    g  = risk_assessment    — policy: scores risk from claim data
    d  = premium_calculation — control action: admissibility decision
    f  = (claim_payout, reserve_update)  — state updates
    Θ  = {base_premium_rate, deductible, coverage_limit}

Composition: claim >> risk >> premium >> payout >> reserve_update
"""

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: Four types cover the insurance domain. RiskScore uses
# a two-sided constraint [0, 1] (like Strategy in prisoners_dilemma).
# PremiumRate is a parameter type — only used in Θ, not in state.
# ══════════════════════════════════════════════════════════════════

Currency = TypeDef(
    name="Currency",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Non-negative monetary amount",
)

# Two-sided constraint: normalized probability score.
RiskScore = TypeDef(
    name="RiskScore",
    python_type=float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="Normalized risk score in [0, 1]",
)

ClaimCount = TypeDef(
    name="ClaimCount",
    python_type=int,
    constraint=lambda x: x >= 0,
    description="Number of claims filed",
)

# Only used to type the base_premium_rate parameter in Θ.
PremiumRate = TypeDef(
    name="PremiumRate",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Base premium rate",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Two entities representing the two sides of the contract.
# Insurer tracks financial reserves; Policyholder tracks coverage and
# claims history. Together they form X = (R, P, C, H).
# ══════════════════════════════════════════════════════════════════

# Financial state of the insurance company.
insurer = Entity(
    name="Insurer",
    variables={
        "reserve": StateVariable(name="reserve", typedef=Currency, symbol="R"),
        "premium_pool": StateVariable(
            name="premium_pool", typedef=Currency, symbol="P"
        ),
    },
    description="Insurance company with reserve and premium pool",
)

# State of the insured party.
policyholder = Entity(
    name="Policyholder",
    variables={
        "coverage": StateVariable(name="coverage", typedef=Currency, symbol="C"),
        "claims_history": StateVariable(
            name="claims_history", typedef=ClaimCount, symbol="H"
        ),
    },
    description="Insurance policyholder",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Four spaces form a linear signal chain. Each space
# carries data forward through the pipeline — no backward or
# temporal wiring in this model.
# ══════════════════════════════════════════════════════════════════

claim_event_space = Space(
    name="ClaimEventSpace",
    fields={"amount": Currency, "claim_count": ClaimCount},
)

risk_score_space = Space(
    name="RiskScoreSpace",
    fields={"score": RiskScore},
)

premium_decision_space = Space(
    name="PremiumDecisionSpace",
    fields={"premium": Currency, "approved": RiskScore},
)

payout_result_space = Space(
    name="PayoutResultSpace",
    fields={"payout": Currency},
)

# ══════════════════════════════════════════════════════════════════
# Blocks — complete 4-role taxonomy
# GDS Mapping: This is the only example using all 4 block roles:
#   BoundaryAction — exogenous claim events (U)
#   Policy         — risk assessment (g: observation → decision input)
#   ControlAction  — premium calculation (d: admissibility/control)
#   Mechanism      — claim payout + reserve update (f: state transitions)
#
# ControlAction vs Policy: both have forward_in and forward_out.
# ControlAction represents an admissibility or control decision that
# constrains the action space (e.g., "is this claim approved?"),
# while Policy represents the core decision logic. In GDS theory,
# ControlAction maps to the decision variable D.
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: exogenous claim arrival — no forward_in.
claim_arrival = BoundaryAction(
    name="Claim Arrival",
    interface=Interface(
        forward_out=(port("Claim Event"),),
    ),
    tags={"domain": "Claims"},
)

# Policy: evaluates risk from claim data. Pure observation → assessment.
risk_assessment = Policy(
    name="Risk Assessment",
    interface=Interface(
        forward_in=(port("Claim Event"),),
        forward_out=(port("Risk Score"),),
    ),
    tags={"domain": "Underwriting"},
)

# ControlAction: the distinctive role in this example.
# Takes the risk score and applies admissibility rules (deductible,
# coverage limit) to produce a premium decision. Uses params_used
# to reference Θ — the control action's behavior is parameterized.
premium_calculation = ControlAction(
    name="Premium Calculation",
    interface=Interface(
        forward_in=(port("Risk Score"),),
        forward_out=(port("Premium Decision"),),
    ),
    params_used=["base_premium_rate", "deductible", "coverage_limit"],
    tags={"domain": "Underwriting"},
)

# Mechanism with forward_out: applies payout to policyholder state and
# emits a result signal for the next mechanism in the chain.
# Similar to lotka_volterra's mechanisms that emit temporal signals,
# but here the forward_out is consumed within the SAME timestep.
claim_payout = Mechanism(
    name="Claim Payout",
    interface=Interface(
        forward_in=(port("Premium Decision"),),
        forward_out=(port("Payout Result"),),
    ),
    updates=[("Policyholder", "claims_history"), ("Policyholder", "coverage")],
    tags={"domain": "Claims"},
)

# Terminal mechanism: pure sink (no forward_out), writes insurer state.
reserve_update = Mechanism(
    name="Reserve Update",
    interface=Interface(
        forward_in=(port("Payout Result"),),
    ),
    updates=[("Insurer", "reserve"), ("Insurer", "premium_pool")],
    tags={"domain": "Reserves"},
)


def build_spec() -> GDSSpec:
    """Build the complete insurance contract specification.

    This is a pure sequential spec — all wires flow forward with no
    feedback or temporal loops. The ControlAction (Premium Calculation)
    is the key differentiator, demonstrating how admissibility
    constraints fit into the GDS role taxonomy.
    """
    spec = GDSSpec(
        name="Insurance Contract",
        description="Claim processing pipeline with risk-based premium control",
    )

    # Types
    spec.register_type(Currency)
    spec.register_type(RiskScore)
    spec.register_type(ClaimCount)
    spec.register_type(PremiumRate)

    # Spaces
    spec.register_space(claim_event_space)
    spec.register_space(risk_score_space)
    spec.register_space(premium_decision_space)
    spec.register_space(payout_result_space)

    # Entities
    spec.register_entity(insurer)
    spec.register_entity(policyholder)

    # Blocks
    spec.register_block(claim_arrival)
    spec.register_block(risk_assessment)
    spec.register_block(premium_calculation)
    spec.register_block(claim_payout)
    spec.register_block(reserve_update)

    # Parameters — Θ: admissibility constraints for the ControlAction
    spec.register_parameter("base_premium_rate", PremiumRate)
    spec.register_parameter("deductible", Currency)
    spec.register_parameter("coverage_limit", Currency)

    # Wiring — pure forward sequential chain
    spec.register_wiring(
        SpecWiring(
            name="Claims Pipeline",
            block_names=[
                "Claim Arrival",
                "Risk Assessment",
                "Premium Calculation",
                "Claim Payout",
                "Reserve Update",
            ],
            wires=[
                Wire(
                    source="Claim Arrival",
                    target="Risk Assessment",
                    space="ClaimEventSpace",
                ),
                Wire(
                    source="Risk Assessment",
                    target="Premium Calculation",
                    space="RiskScoreSpace",
                ),
                Wire(
                    source="Premium Calculation",
                    target="Claim Payout",
                    space="PremiumDecisionSpace",
                ),
                Wire(
                    source="Claim Payout",
                    target="Reserve Update",
                    space="PayoutResultSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the insurance contract system.

    Pure sequential composition — the simplest build_system in the
    examples (alongside sir_epidemic). No .feedback() or .loop() needed.
    The >> operator auto-wires by token overlap between adjacent blocks.
    """
    pipeline = (
        claim_arrival
        >> risk_assessment
        >> premium_calculation
        >> claim_payout
        >> reserve_update
    )
    return compile_system(name="Insurance Contract", root=pipeline)
