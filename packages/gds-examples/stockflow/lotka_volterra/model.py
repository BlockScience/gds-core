"""Lotka-Volterra Predator-Prey — temporal loop with parallel mechanisms.

Demonstrates .loop() for forward temporal iteration across timesteps.
Population signals from parallel prey/predator update mechanisms feed
back into the rate computation at the next timestep.

Concepts Covered:
    - .loop() composition for cross-timestep temporal feedback
    - COVARIANT flow direction (forward_out → forward_in across time)
    - Mechanism with forward_out — emitting signals after state update
    - exit_condition parameter for loop termination
    - Contrast with .feedback() (within-timestep, see thermostat)

Prerequisites: sir_epidemic (basic roles, >>), thermostat (feedback concept)

GDS Decomposition:
    X  = (x, y)             — prey population, predator population
    U  = population_signal   — observed population levels (exogenous seed)
    g  = compute_rates       — Lotka-Volterra rate equations
    f  = (update_prey, update_predator)  — applies rates to X
    Θ  = {prey_birth_rate, predation_rate, predator_death_rate,
           predator_efficiency}

Composition: (observe >> compute >> (update_prey | update_pred)).loop(
    [Population Signal -> Compute Rates]
)
"""

from gds.blocks.composition import Wiring
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: Population is float (continuous ODE approximation),
# constrained non-negative. GrowthRate constrains Θ parameters.
# ══════════════════════════════════════════════════════════════════

# Continuous approximation — float, not int, because Lotka-Volterra
# uses differential equations where populations are real-valued.
Population = TypeDef(
    name="Population",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Non-negative population count (continuous approximation)",
)

# All four Θ parameters share this type — positive real growth/death rates.
GrowthRate = TypeDef(
    name="GrowthRate",
    python_type=float,
    constraint=lambda x: x > 0,
    description="Positive growth/death rate parameter",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Two entities, each with one variable — similar to
# sir_epidemic's compartment pattern. The symbols x and y match
# the standard Lotka-Volterra notation.
# ══════════════════════════════════════════════════════════════════

prey = Entity(
    name="Prey",
    variables={
        "population": StateVariable(name="population", typedef=Population, symbol="x"),
    },
    description="Prey species population",
)

predator = Entity(
    name="Predator",
    variables={
        "population": StateVariable(name="population", typedef=Population, symbol="y"),
    },
    description="Predator species population",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: PopulationSignalSpace carries BOTH populations in a
# single signal — used for the temporal loop back to compute_rates.
# RateSpace carries a single computed rate delta.
# ══════════════════════════════════════════════════════════════════

# Multi-field space: carries both populations together so the policy
# can compute interaction terms (predation depends on BOTH x and y).
population_signal_space = Space(
    name="PopulationSignalSpace",
    fields={"prey": Population, "predator": Population},
)

# Single-field space: each mechanism receives its specific rate of change.
rate_space = Space(
    name="RateSpace",
    fields={"rate": Population},
    description="Computed rate of change for a population",
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition with temporal output from mechanisms
# GDS Mapping: Key difference from sir_epidemic — the mechanisms here
# have forward_out ports. After updating state, they emit the new
# population signal that feeds back to compute_rates at the NEXT
# timestep via .loop(). This is what makes the system temporal.
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: provides initial population observation (timestep 0 seed).
observe_populations = BoundaryAction(
    name="Observe Populations",
    interface=Interface(
        forward_out=(port("Population Signal"),),
    ),
    tags={"domain": "Shared"},
)

# Policy: implements the Lotka-Volterra rate equations.
# dx/dt = alpha*x - beta*x*y   (prey growth minus predation)
# dy/dt = delta*x*y - gamma*y  (predator growth minus death)
compute_rates = Policy(
    name="Compute Rates",
    interface=Interface(
        forward_in=(port("Population Signal"),),
        forward_out=(port("Prey Rate"), port("Predator Rate")),
    ),
    params_used=[
        "prey_birth_rate",  # alpha: prey natural growth
        "predation_rate",  # beta: prey loss from predation
        "predator_death_rate",  # gamma: predator natural death
        "predator_efficiency",  # delta: predator gain from predation
    ],
    tags={"domain": "Shared"},
)

# Mechanism WITH forward_out: unlike sir_epidemic's mechanisms (which
# are pure sinks), these emit a population signal AFTER updating state.
# This forward_out is what gets wired back via .loop() — the updated
# population becomes input to compute_rates at the next timestep.
update_prey = Mechanism(
    name="Update Prey",
    interface=Interface(
        forward_in=(port("Prey Rate"),),
        forward_out=(port("Population Signal"),),  # Temporal output
    ),
    updates=[("Prey", "population")],
    tags={"domain": "Prey"},
)

update_predator = Mechanism(
    name="Update Predator",
    interface=Interface(
        forward_in=(port("Predator Rate"),),
        forward_out=(port("Population Signal"),),  # Temporal output
    ),
    updates=[("Predator", "population")],
    tags={"domain": "Predator"},
)


def build_spec() -> GDSSpec:
    """Build the complete Lotka-Volterra specification.

    The wiring includes temporal feedback wires: Update Prey/Predator →
    Compute Rates. In SpecWiring these are regular Wire entries — the
    temporal nature is expressed in the composition tree via .loop().
    """
    spec = GDSSpec(
        name="Lotka-Volterra",
        description="Predator-prey dynamics with temporal population feedback",
    )

    # Types
    spec.register_type(Population)
    spec.register_type(GrowthRate)

    # Spaces
    spec.register_space(population_signal_space)
    spec.register_space(rate_space)

    # Entities
    spec.register_entity(prey)
    spec.register_entity(predator)

    # Blocks
    spec.register_block(observe_populations)
    spec.register_block(compute_rates)
    spec.register_block(update_prey)
    spec.register_block(update_predator)

    # Parameters — Θ: the four Lotka-Volterra rate constants
    spec.register_parameter("prey_birth_rate", GrowthRate)
    spec.register_parameter("predation_rate", GrowthRate)
    spec.register_parameter("predator_death_rate", GrowthRate)
    spec.register_parameter("predator_efficiency", GrowthRate)

    # Wiring — includes temporal feedback wires (mechanism → policy)
    spec.register_wiring(
        SpecWiring(
            name="Population Dynamics",
            block_names=[
                "Observe Populations",
                "Compute Rates",
                "Update Prey",
                "Update Predator",
            ],
            wires=[
                Wire(
                    source="Observe Populations",
                    target="Compute Rates",
                    space="PopulationSignalSpace",
                ),
                Wire(source="Compute Rates", target="Update Prey", space="RateSpace"),
                Wire(
                    source="Compute Rates", target="Update Predator", space="RateSpace"
                ),
                # Temporal feedback: updated populations feed back at next timestep
                Wire(
                    source="Update Prey",
                    target="Compute Rates",
                    space="PopulationSignalSpace",
                ),
                Wire(
                    source="Update Predator",
                    target="Compute Rates",
                    space="PopulationSignalSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the Lotka-Volterra system with temporal loop.

    Step-by-step composition:
      1. Parallel mechanisms with | (same as sir_epidemic)
      2. Sequential pipeline with >> (same as sir_epidemic)
      3. .loop() wraps the pipeline for cross-timestep iteration

    .loop() vs .feedback() (thermostat):
      - .feedback() = within-timestep backward flow (CONTRAVARIANT)
      - .loop()     = across-timestep forward flow (COVARIANT only)
    .loop() enforces COVARIANT direction — temporal feedback must flow
    forward in time. It also accepts an exit_condition string naming
    the termination predicate.
    """
    # Step 1: Parallel composition — prey and predator update independently
    updates = update_prey | update_predator
    # Step 2: Sequential pipeline within one timestep
    inner = observe_populations >> compute_rates >> updates
    # Step 3: Temporal loop — mechanism outputs feed back to policy inputs
    # at the NEXT timestep. Two COVARIANT wirings: one per species.
    system = inner.loop(
        [
            Wiring(
                source_block="Update Prey",
                source_port="Population Signal",
                target_block="Compute Rates",
                target_port="Population Signal",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Update Predator",
                source_port="Population Signal",
                target_block="Compute Rates",
                target_port="Population Signal",
                direction=FlowDirection.COVARIANT,
            ),
        ],
        exit_condition="population_extinct",
    )
    return compile_system(name="Lotka-Volterra", root=system)
