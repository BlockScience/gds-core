"""Iterated Prisoner's Dilemma with Learning — parallel | and .loop().

Demonstrates parallel composition for simultaneous agent decisions,
temporal loop for multi-round learning, and 3 entities (Alice, Bob, Game).

Concepts Covered:
    - Nested parallel composition: (A | B) | C for grouping
    - Multi-entity state space X with 3 entities
    - Mechanism with forward_out for temporal feedback (see lotka_volterra)
    - Complex composition tree: nested | + >> + .loop()
    - Multiple temporal wirings in a single .loop() call

Prerequisites: sir_epidemic (roles, >>), lotka_volterra (.loop(), COVARIANT)

GDS Decomposition:
    X  = (s_A, U_A, s_B, U_B, t) — strategies, scores, round number
    U  = game_config               — exogenous payoff matrix (R, T, S, P)
    g  = (alice_decision, bob_decision)  — independent policy functions
    f  = (payoff_realization, alice_world_model, bob_world_model)
    Θ  = {}  (payoff matrix is exogenous input, not a parameter here)

Composition:
    input_phase = payoff_setting | (alice_decision | bob_decision)
    world_updates = alice_world_model | bob_world_model
    pipeline = input_phase >> payoff_realization >> world_updates
    system = pipeline.loop([world models -> decisions])
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
# GDS Mapping: Strategy uses a bounded constraint [0, 1] — the first
# example with a two-sided constraint. RoundNumber is a positive int.
# ══════════════════════════════════════════════════════════════════

Score = TypeDef(
    name="Score",
    python_type=float,
    description="Cumulative payoff score",
)

# Two-sided constraint: cooperation probability must be in [0, 1].
Strategy = TypeDef(
    name="Strategy",
    python_type=float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="Cooperation probability in [0, 1]",
)

RoundNumber = TypeDef(
    name="RoundNumber",
    python_type=int,
    constraint=lambda x: x > 0,
    description="Current game round (positive integer)",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Three entities contribute 5 state variables total.
# This is the most complex X in the examples: two symmetric agents
# (Alice, Bob) each with strategy + score, plus a shared Game entity.
# ══════════════════════════════════════════════════════════════════

# Alice and Bob are symmetric — same variables, different symbols.
alice = Entity(
    name="Alice",
    variables={
        "strategy_state": StateVariable(
            name="strategy_state", typedef=Strategy, symbol="s_A"
        ),
        "score": StateVariable(name="score", typedef=Score, symbol="U_A"),
    },
    description="Player Alice with adaptive strategy",
)

bob = Entity(
    name="Bob",
    variables={
        "strategy_state": StateVariable(
            name="strategy_state", typedef=Strategy, symbol="s_B"
        ),
        "score": StateVariable(name="score", typedef=Score, symbol="U_B"),
    },
    description="Player Bob with adaptive strategy",
)

# Shared environment state — tracks which round we're in.
game = Entity(
    name="Game",
    variables={
        "round_number": StateVariable(
            name="round_number", typedef=RoundNumber, symbol="t"
        ),
    },
    description="Game state tracking round progression",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Four distinct spaces for different signal types.
# WorldModelSpace carries temporal feedback (mechanism → policy
# across timesteps), similar to PopulationSignalSpace in lotka_volterra.
# ══════════════════════════════════════════════════════════════════

# Exogenous payoff matrix parameters (Reward, Temptation, Sucker, Punishment).
game_config_space = Space(
    name="GameConfigSpace",
    fields={"reward": Score, "temptation": Score, "sucker": Score, "punishment": Score},
    description="Payoff matrix parameters (R, T, S, P)",
)

# Player action signal — probability of cooperation.
action_space = Space(
    name="ActionSpace",
    fields={"cooperate_prob": Strategy},
    description="Player action (probability of cooperation)",
)

# Round payoff result for a player.
payoff_space = Space(
    name="PayoffSpace",
    fields={"payoff": Score},
    description="Round payoff for a player",
)

# Updated strategy — flows temporally back to the decision policy.
world_model_space = Space(
    name="WorldModelSpace",
    fields={"strategy": Strategy},
    description="Player's updated world model / strategy state",
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition with symmetric agent structure
# GDS Mapping: The key pattern here is symmetric duplication —
# Alice and Bob have identical roles (Policy for decisions, Mechanism
# for world model updates) but separate blocks with distinct ports.
# Payoff Realization is a single Mechanism that updates BOTH players
# plus the Game entity — it has 3 updates, the most of any example.
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: exogenous payoff matrix (R, T, S, P values).
payoff_setting = BoundaryAction(
    name="Payoff Matrix Setting",
    interface=Interface(
        forward_out=(port("Game Config"),),
    ),
    tags={"domain": "Environment"},
)

# Symmetric policies: Alice and Bob make independent decisions based on
# their world models. Each receives temporal feedback from its own
# world model mechanism via .loop() (see build_system).
alice_decision = Policy(
    name="Alice Decision",
    interface=Interface(
        forward_in=(port("Alice World Model"),),
        forward_out=(port("Alice Action"),),
    ),
    tags={"domain": "Alice"},
)

bob_decision = Policy(
    name="Bob Decision",
    interface=Interface(
        forward_in=(port("Bob World Model"),),
        forward_out=(port("Bob Action"),),
    ),
    tags={"domain": "Bob"},
)

# Central mechanism: takes both actions + game config, computes payoffs.
# Updates 3 state variables across 2 entities — the most complex
# Mechanism in the examples.
payoff_realization = Mechanism(
    name="Payoff Realization",
    interface=Interface(
        forward_in=(
            port("Alice Action"),
            port("Bob Action"),
            port("Game Config"),
        ),
        forward_out=(port("Alice Payoff"), port("Bob Payoff")),
    ),
    updates=[("Alice", "score"), ("Bob", "score"), ("Game", "round_number")],
    tags={"domain": "Environment"},
)

# World model mechanisms: update strategy state AND emit temporal signal.
# forward_out enables .loop() — same pattern as lotka_volterra's mechanisms.
alice_world_model = Mechanism(
    name="Alice World Model Update",
    interface=Interface(
        forward_in=(port("Alice Payoff"),),
        forward_out=(port("Alice World Model"),),
    ),
    updates=[("Alice", "strategy_state")],
    tags={"domain": "Alice"},
)

bob_world_model = Mechanism(
    name="Bob World Model Update",
    interface=Interface(
        forward_in=(port("Bob Payoff"),),
        forward_out=(port("Bob World Model"),),
    ),
    updates=[("Bob", "strategy_state")],
    tags={"domain": "Bob"},
)


def build_spec() -> GDSSpec:
    """Build the complete Prisoner's Dilemma specification.

    Note: no parameters registered (Θ = {}) — the payoff matrix is
    modeled as exogenous input (BoundaryAction) rather than as
    parameters. This is a design choice: parameters are fixed across
    a simulation run, while BoundaryAction inputs can vary per timestep.
    """
    spec = GDSSpec(
        name="Iterated Prisoners Dilemma",
        description=(
            "Two-player iterated PD with adaptive strategies and temporal learning"
        ),
    )

    # Types
    spec.register_type(Score)
    spec.register_type(Strategy)
    spec.register_type(RoundNumber)

    # Spaces
    spec.register_space(game_config_space)
    spec.register_space(action_space)
    spec.register_space(payoff_space)
    spec.register_space(world_model_space)

    # Entities
    spec.register_entity(alice)
    spec.register_entity(bob)
    spec.register_entity(game)

    # Blocks
    spec.register_block(payoff_setting)
    spec.register_block(alice_decision)
    spec.register_block(bob_decision)
    spec.register_block(payoff_realization)
    spec.register_block(alice_world_model)
    spec.register_block(bob_world_model)

    # Wiring — includes temporal feedback (world model → decision)
    spec.register_wiring(
        SpecWiring(
            name="Game Round",
            block_names=[
                "Payoff Matrix Setting",
                "Alice Decision",
                "Bob Decision",
                "Payoff Realization",
                "Alice World Model Update",
                "Bob World Model Update",
            ],
            wires=[
                Wire(
                    source="Payoff Matrix Setting",
                    target="Payoff Realization",
                    space="GameConfigSpace",
                ),
                Wire(
                    source="Alice Decision",
                    target="Payoff Realization",
                    space="ActionSpace",
                ),
                Wire(
                    source="Bob Decision",
                    target="Payoff Realization",
                    space="ActionSpace",
                ),
                Wire(
                    source="Payoff Realization",
                    target="Alice World Model Update",
                    space="PayoffSpace",
                ),
                Wire(
                    source="Payoff Realization",
                    target="Bob World Model Update",
                    space="PayoffSpace",
                ),
                # Temporal feedback: world model updates → decision policies
                Wire(
                    source="Alice World Model Update",
                    target="Alice Decision",
                    space="WorldModelSpace",
                ),
                Wire(
                    source="Bob World Model Update",
                    target="Bob Decision",
                    space="WorldModelSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the Prisoner's Dilemma system with temporal loop.

    Composition tree (most complex in the examples):
      1. Nested parallel: (alice | bob) groups symmetric decisions
      2. Outer parallel: payoff_setting | decisions — independent inputs
      3. Sequential: input_phase >> payoff >> world_updates
      4. .loop() with two COVARIANT wirings for per-agent temporal feedback

    The nesting (A | B) | C is semantically flat — parallel composition
    is associative. But it communicates intent: Alice and Bob form a
    logical group of "decision makers" distinct from the environment.
    """
    # Step 1: Group symmetric agent decisions
    decisions = alice_decision | bob_decision
    # Step 2: Independent inputs — payoff matrix and decisions run in parallel
    input_phase = payoff_setting | decisions
    # Step 3: Group symmetric world model updates
    world_updates = alice_world_model | bob_world_model
    # Step 4: Sequential pipeline for one game round
    pipeline = input_phase >> payoff_realization >> world_updates
    # Step 5: Temporal loop — world models feed back to decisions
    system = pipeline.loop(
        [
            Wiring(
                source_block="Alice World Model Update",
                source_port="Alice World Model",
                target_block="Alice Decision",
                target_port="Alice World Model",
                direction=FlowDirection.COVARIANT,
            ),
            Wiring(
                source_block="Bob World Model Update",
                source_port="Bob World Model",
                target_block="Bob Decision",
                target_port="Bob World Model",
                direction=FlowDirection.COVARIANT,
            ),
        ],
        exit_condition="max_rounds_reached",
    )
    return compile_system(name="Iterated Prisoners Dilemma", root=system)
