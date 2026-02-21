"""SIR Epidemic Model — pure sequential (>>) composition.

Demonstrates the simplest GDS pattern: a linear pipeline from
exogenous contact events through infection policy to parallel
state updates for Susceptible, Infected, and Recovered populations.

Concepts Covered:
    - TypeDef with runtime constraints (non-negative counts, positive rates)
    - Entity / StateVariable for state space X
    - Space for typed inter-block communication
    - BoundaryAction, Policy, Mechanism — the 3 core block roles
    - Sequential composition (>>) and parallel composition (|)
    - GDSSpec registration and SpecWiring
    - compile_system() to produce SystemIR

Prerequisites: None — start here.

GDS Decomposition:
    X  = (S, I, R)          — susceptible, infected, recovered counts
    U  = contact_rate        — exogenous contact signal
    g  = infection_policy    — computes deltas from contact rate + params
    f  = (update_s, update_i, update_r)  — applies deltas to X
    Θ  = {beta, gamma, contact_rate}

Composition: contact >> infection_policy >> (update_s | update_i | update_r)
"""

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: These define the value constraints for state variables,
# parameters, and space fields. TypeDef wraps a Python type + optional
# constraint predicate for runtime validation.
# ══════════════════════════════════════════════════════════════════

# Constrains population values: S, I, R must never go negative.
Count = TypeDef(
    name="Count",
    python_type=int,
    constraint=lambda x: x >= 0,
    description="Non-negative population count",
)

# Parameters beta and gamma are positive real rates.
Rate = TypeDef(
    name="Rate",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Positive rate parameter",
)

# Distinct from Rate to make the exogenous signal semantically clear.
ContactRate = TypeDef(
    name="ContactRate",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Average contacts per individual per timestep",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Each Entity contributes dimensions to the global state
# vector X. An Entity groups related StateVariables — here each
# compartment has a single "count" variable with a mathematical symbol.
# ══════════════════════════════════════════════════════════════════

# X₁ = S (susceptible count) — decreases when individuals become infected
susceptible = Entity(
    name="Susceptible",
    variables={
        "count": StateVariable(name="count", typedef=Count, symbol="S"),
    },
    description="Susceptible population compartment",
)

# X₂ = I (infected count) — increases from infection, decreases from recovery
infected = Entity(
    name="Infected",
    variables={
        "count": StateVariable(name="count", typedef=Count, symbol="I"),
    },
    description="Infected population compartment",
)

# X₃ = R (recovered count) — absorbing state, only increases
recovered = Entity(
    name="Recovered",
    variables={
        "count": StateVariable(name="count", typedef=Count, symbol="R"),
    },
    description="Recovered population compartment",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Spaces define the data that flows along wires between
# blocks. Each Space has named fields, each typed by a TypeDef.
# Spaces are NOT state — they are transient signals within a timestep.
# ══════════════════════════════════════════════════════════════════

# Carries the exogenous contact rate from BoundaryAction to Policy.
contact_signal_space = Space(
    name="ContactSignalSpace",
    fields={"contact_rate": ContactRate},
    description="Signal carrying the effective contact rate",
)

# Carries computed population deltas from Policy to each Mechanism.
# All three mechanisms receive the same Space type but different values.
delta_space = Space(
    name="DeltaSpace",
    fields={"delta": Count},
    description="Population change signal",
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition (boundary → policy → mechanism)
# GDS Mapping: Blocks are the computational units. Each has a specific
# role that constrains its interface:
#   BoundaryAction: no forward_in (exogenous input U)
#   Policy:         forward_in → forward_out (decision function g)
#   Mechanism:      forward_in only, writes state (state update f)
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: the system's boundary with the external world.
# No forward_in ports — it only emits (the contact rate is exogenous).
# This models U in the GDS: external inputs the system cannot control.
contact_process = BoundaryAction(
    name="Contact Process",
    interface=Interface(
        forward_out=(port("Contact Signal"),),
    ),
    params_used=["contact_rate"],  # References Θ — the contact rate parameter
    tags={"domain": "Observation"},
)

# Policy: the decision function g that maps observations + params to actions.
# Takes the contact signal and computes population deltas using beta/gamma.
# One forward_in (contact rate), three forward_out (one delta per compartment).
infection_policy = Policy(
    name="Infection Policy",
    interface=Interface(
        forward_in=(port("Contact Signal"),),
        forward_out=(
            port("Susceptible Delta"),
            port("Infected Delta"),
            port("Recovered Delta"),
        ),
    ),
    params_used=["beta", "gamma"],  # Infection rate and recovery rate from Θ
    tags={"domain": "Decision"},
)

# Mechanism: state update function f — writes to exactly one entity.
# Mechanisms have forward_in only (no backward ports, no forward_out).
# The `updates` field declares WHICH state variables this block modifies.
# Each mechanism below applies a delta to one compartment of X.
update_susceptible = Mechanism(
    name="Update Susceptible",
    interface=Interface(
        forward_in=(port("Susceptible Delta"),),
    ),
    updates=[("Susceptible", "count")],  # f: S' = S + delta_S
    tags={"domain": "State Update"},
)

update_infected = Mechanism(
    name="Update Infected",
    interface=Interface(
        forward_in=(port("Infected Delta"),),
    ),
    updates=[("Infected", "count")],  # f: I' = I + delta_I
    tags={"domain": "State Update"},
)

update_recovered = Mechanism(
    name="Update Recovered",
    interface=Interface(
        forward_in=(port("Recovered Delta"),),
    ),
    updates=[("Recovered", "count")],  # f: R' = R + delta_R
    tags={"domain": "State Update"},
)


def build_spec() -> GDSSpec:
    """Build the complete SIR epidemic specification.

    GDSSpec is the central registry that holds all model components:
    types, spaces, entities, blocks, parameters, and wiring. Registration
    order doesn't matter for correctness, but grouping by category
    (types → spaces → entities → blocks → parameters → wiring) aids
    readability. Semantic verification checks (SC-001..SC-007) run
    against this spec to validate completeness, determinism, etc.
    """
    spec = GDSSpec(
        name="SIR Epidemic", description="Susceptible-Infected-Recovered model"
    )

    # Types
    spec.register_type(Count)
    spec.register_type(Rate)
    spec.register_type(ContactRate)

    # Spaces
    spec.register_space(contact_signal_space)
    spec.register_space(delta_space)

    # Entities
    spec.register_entity(susceptible)
    spec.register_entity(infected)
    spec.register_entity(recovered)

    # Blocks
    spec.register_block(contact_process)
    spec.register_block(infection_policy)
    spec.register_block(update_susceptible)
    spec.register_block(update_infected)
    spec.register_block(update_recovered)

    # Parameters — the configuration space Θ
    spec.register_parameter("beta", Rate)
    spec.register_parameter("gamma", Rate)
    spec.register_parameter("contact_rate", ContactRate)

    # Wiring — explicit data flow connections between blocks
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
                Wire(
                    source="Contact Process",
                    target="Infection Policy",
                    space="ContactSignalSpace",
                ),
                Wire(
                    source="Infection Policy",
                    target="Update Susceptible",
                    space="DeltaSpace",
                ),
                Wire(
                    source="Infection Policy",
                    target="Update Infected",
                    space="DeltaSpace",
                ),
                Wire(
                    source="Infection Policy",
                    target="Update Recovered",
                    space="DeltaSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the SIR epidemic system.

    Composition uses two operators:
      |  (parallel) — three mechanisms run independently, no data sharing
      >> (sequential) — output ports of left block match input ports of right

    The >> operator auto-wires by token overlap: "Contact Signal" out from
    contact_process matches "Contact Signal" in on infection_policy. The
    compiler flattens this tree into SystemIR (flat blocks + wirings).
    """
    # Step 1: Parallel composition — all three updates run independently
    mechanisms = update_susceptible | update_infected | update_recovered
    # Step 2: Sequential pipeline — contact >> policy >> mechanisms
    pipeline = contact_process >> infection_policy >> mechanisms
    # Step 3: Compile — flattens composition tree into SystemIR
    return compile_system(name="SIR Epidemic", root=pipeline)
