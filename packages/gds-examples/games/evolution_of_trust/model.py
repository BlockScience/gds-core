"""Iterated Prisoner's Dilemma — OGS game structure for Evolution of Trust.

Builds the same OGS composition tree as prisoners_dilemma_nash but with
Nicky Case's payoff parameters (R=2, T=3, S=-1, P=0) from "The Evolution
of Trust" (https://ncase.me/trust/).

Concepts Covered:
    - Building a 2-player normal-form game from OGS primitives
    - Non-zero-sum payoff matrices with negative values
    - Payoff lookup for iterated play (used by tournament.py)

OGS Game Theory Decomposition:
    Players: Alice, Bob
    Actions: {Cooperate, Defect}
    Payoff Matrix: (R, T, S, P) = (2, 3, -1, 0)
    Composition: (alice_decision | bob_decision) >> payoff_computation
        .feedback([payoff -> decisions])

References:
    - Nicky Case, "The Evolution of Trust" (2017): https://ncase.me/trust/
    - GitHub issue: https://github.com/BlockScience/gds-core/issues/77
"""

import re

from ogs.dsl.compile import compile_to_ir
from ogs.dsl.composition import (
    FeedbackFlow,
    FeedbackLoop,
    Flow,
    ParallelComposition,
    SequentialComposition,
)
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.dsl.pattern import ActionSpace, Pattern, PatternInput, TerminalCondition
from ogs.dsl.types import CompositionType, InputType, Signature, port
from ogs.ir.models import PatternIR

# ======================================================================
# Payoff parameters — Nicky Case's version: T > R > P > S, 2R > T + S
# ======================================================================

R = 2  # Reward (mutual cooperation)
T = 3  # Temptation (defect while other cooperates)
S = -1  # Sucker (cooperate while other defects)
P = 0  # Punishment (mutual defection)

# ======================================================================
# Atomic Games — OGS primitives
# ======================================================================

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
        "from {Cooperate, Defect}."
    ),
    tags={"domain": "Alice"},
)

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
        "from {Cooperate, Defect}. Symmetric to Alice."
    ),
    tags={"domain": "Bob"},
)

payoff_computation = CovariantFunction(
    name="Payoff Computation",
    signature=Signature(
        x=(port("Alice Action"), port("Bob Action")),
        y=(port("Alice Payoff"), port("Bob Payoff")),
    ),
    logic=(
        "Given both players' actions, look up the payoff matrix: "
        "CC=(R,R), CD=(S,T), DC=(T,S), DD=(P,P) where "
        f"R={R}, T={T}, S={S}, P={P}."
    ),
    tags={"domain": "Environment"},
)

# ======================================================================
# Composition — build the game tree
# ======================================================================


def build_game() -> FeedbackLoop:
    """Build the Prisoner's Dilemma as an OGS composite game.

    Structure: (Alice | Bob) >> Payoff .feedback([payoff -> decisions])
    """
    decisions = ParallelComposition(
        name="Simultaneous Decisions",
        left=alice_decision,
        right=bob_decision,
    )

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
# Pattern — top-level specification with metadata
# ======================================================================


def build_pattern() -> Pattern:
    """Build the complete OGS Pattern for the iterated PD."""
    return Pattern(
        name="Evolution of Trust PD",
        game=build_game(),
        inputs=[
            PatternInput(
                name="Payoff Matrix",
                input_type=InputType.EXTERNAL_WORLD,
                schema_hint=f"(R, T, S, P) = ({R}, {T}, {S}, {P})",
                target_game="Payoff Computation",
                flow_label="Payoff Matrix",
            ),
        ],
        composition_type=CompositionType.FEEDBACK,
        terminal_conditions=[
            TerminalCondition(
                name="Mutual Cooperation",
                actions={
                    "Alice Decision": "Cooperate",
                    "Bob Decision": "Cooperate",
                },
                outcome="Both players cooperate (Pareto optimal)",
                description="Pareto optimum — both receive reward",
                payoff_description=f"R={R} each",
            ),
            TerminalCondition(
                name="Mutual Defection",
                actions={
                    "Alice Decision": "Defect",
                    "Bob Decision": "Defect",
                },
                outcome="Both players defect (Nash equilibrium)",
                description="Dominant strategy equilibrium — zero payoff",
                payoff_description=f"P={P} each",
            ),
            TerminalCondition(
                name="Alice Exploits",
                actions={
                    "Alice Decision": "Defect",
                    "Bob Decision": "Cooperate",
                },
                outcome="Alice defects while Bob cooperates",
                description="Alice gets temptation payoff, Bob gets sucker payoff",
                payoff_description=f"T={T} for Alice, S={S} for Bob",
            ),
            TerminalCondition(
                name="Bob Exploits",
                actions={
                    "Alice Decision": "Cooperate",
                    "Bob Decision": "Defect",
                },
                outcome="Bob defects while Alice cooperates",
                description="Bob gets temptation payoff, Alice gets sucker payoff",
                payoff_description=f"T={T} for Bob, S={S} for Alice",
            ),
        ],
        action_spaces=[
            ActionSpace(game="Alice Decision", actions=["Cooperate", "Defect"]),
            ActionSpace(game="Bob Decision", actions=["Cooperate", "Defect"]),
        ],
        source="dsl",
    )


def build_ir() -> PatternIR:
    """Compile the Pattern to OGS PatternIR."""
    return compile_to_ir(build_pattern())


# ======================================================================
# Payoff matrix construction from PatternIR
# ======================================================================


def build_payoff_matrices(
    ir: PatternIR,
) -> tuple[list[list[float]], list[list[float]]]:
    """Construct payoff matrices from PatternIR metadata.

    Returns:
        Tuple of (alice_payoffs, bob_payoffs) as nested lists.
        Rows = Alice's actions, Cols = Bob's actions.
    """
    assert ir.action_spaces is not None, "PatternIR must have action_spaces"
    assert ir.terminal_conditions is not None, "PatternIR must have terminal_conditions"

    players = {asp.game: asp.actions for asp in ir.action_spaces}
    alice_actions = players["Alice Decision"]
    bob_actions = players["Bob Decision"]

    n_alice = len(alice_actions)
    n_bob = len(bob_actions)
    alice_payoffs = [[0.0] * n_bob for _ in range(n_alice)]
    bob_payoffs = [[0.0] * n_bob for _ in range(n_alice)]

    for tc in ir.terminal_conditions:
        alice_action = tc.actions["Alice Decision"]
        bob_action = tc.actions["Bob Decision"]
        row = alice_actions.index(alice_action)
        col = bob_actions.index(bob_action)

        a_pay, b_pay = _parse_payoff_description(tc.payoff_description)
        alice_payoffs[row][col] = a_pay
        bob_payoffs[row][col] = b_pay

    return alice_payoffs, bob_payoffs


def _parse_payoff_description(desc: str) -> tuple[float, float]:
    """Parse payoff_description into (alice_payoff, bob_payoff).

    Handles two formats:
        - "X=N each" -> (N, N)
        - "X=N for Alice, Y=M for Bob" -> (N, M)

    Supports negative values (e.g., S=-1).
    """
    each_match = re.match(r"[A-Z]=(-?\d+(?:\.\d+)?)\s+each", desc)
    if each_match:
        val = float(each_match.group(1))
        return val, val

    values: dict[str, float] = {}
    for match in re.finditer(r"[A-Z]=(-?\d+(?:\.\d+)?)\s+for\s+(\w+)", desc):
        val = float(match.group(1))
        player = match.group(2)
        values[player] = val

    if "Alice" in values and "Bob" in values:
        return values["Alice"], values["Bob"]

    raise ValueError(f"Cannot parse payoff_description: {desc!r}")


# ======================================================================
# Direct payoff lookup (used by tournament code)
# ======================================================================


def get_payoff(action_a: str, action_b: str) -> tuple[int, int]:
    """Get payoff for a pair of actions.

    Args:
        action_a: First player's action ("Cooperate" or "Defect").
        action_b: Second player's action ("Cooperate" or "Defect").

    Returns:
        Tuple of (payoff_a, payoff_b).
    """
    _payoff_table: dict[tuple[str, str], tuple[int, int]] = {
        ("Cooperate", "Cooperate"): (R, R),
        ("Cooperate", "Defect"): (S, T),
        ("Defect", "Cooperate"): (T, S),
        ("Defect", "Defect"): (P, P),
    }
    return _payoff_table[(action_a, action_b)]
