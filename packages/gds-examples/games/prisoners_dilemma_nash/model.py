"""Nash Equilibrium computation for the Prisoner's Dilemma via Nashpy.

Builds the Prisoner's Dilemma directly from OGS primitives (DecisionGame,
CovariantFunction, composition operators, Pattern metadata), then uses
Nashpy to compute Nash equilibria and verify them against the hand-annotated
terminal conditions.

Concepts Covered:
    - Building a 2-player normal-form game from OGS primitives
    - Extracting payoff matrices from PatternIR metadata
    - Nashpy integration for Nash equilibrium computation (support enumeration)
    - Cross-referencing computed equilibria against declared TerminalConditions
    - Dominance and Pareto optimality analysis

Prerequisites:
    - nashpy>=0.0.41 (install via: uv sync --all-packages --extra nash)

OGS Game Theory Decomposition:
    Players: Alice, Bob
    Actions: {Cooperate, Defect}
    Payoff Matrix: (R, T, S, P) = (3, 5, 0, 1)
    Composition: (alice_decision | bob_decision) >> payoff_computation
        .feedback([payoff -> decisions])

References:
    - GitHub issue: https://github.com/BlockScience/gds-core/issues/77
"""

import re

import nashpy as nash
import numpy as np
from numpy.typing import NDArray

from gds_domains.games.dsl.compile import compile_to_ir
from gds_domains.games.dsl.composition import (
    FeedbackFlow,
    FeedbackLoop,
    Flow,
    ParallelComposition,
    SequentialComposition,
)
from gds_domains.games.dsl.games import CovariantFunction, DecisionGame
from gds_domains.games.dsl.pattern import (
    ActionSpace,
    Pattern,
    PatternInput,
    TerminalCondition,
)
from gds_domains.games.dsl.types import CompositionType, InputType, Signature, port
from gds_domains.games.ir.models import PatternIR

# ======================================================================
# Payoff parameters — standard PD: T > R > P > S, 2R > T + S
# ======================================================================

R = 3  # Reward (mutual cooperation)
T = 5  # Temptation (defect while other cooperates)
S = 0  # Sucker (cooperate while other defects)
P = 1  # Punishment (mutual defection)

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
    """Build the complete OGS Pattern for Prisoner's Dilemma."""
    return Pattern(
        name="Prisoners Dilemma Nash",
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
                description="Pareto optimum but not an equilibrium",
                payoff_description=f"R={R} each",
            ),
            TerminalCondition(
                name="Mutual Defection",
                actions={
                    "Alice Decision": "Defect",
                    "Bob Decision": "Defect",
                },
                outcome="Both players defect (Nash equilibrium)",
                description="Dominant strategy equilibrium — suboptimal",
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
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Construct payoff matrices from PatternIR metadata.

    Extracts player actions from action_spaces and payoff values from
    terminal_conditions to build the bimatrix game representation.

    Args:
        ir: Compiled PatternIR with action_spaces and terminal_conditions.

    Returns:
        Tuple of (alice_payoffs, bob_payoffs) as 2D numpy arrays.
        Rows = Alice's actions, Cols = Bob's actions.
    """
    assert ir.action_spaces is not None, "PatternIR must have action_spaces"
    assert ir.terminal_conditions is not None, "PatternIR must have terminal_conditions"

    players = {asp.game: asp.actions for asp in ir.action_spaces}
    alice_actions = players["Alice Decision"]
    bob_actions = players["Bob Decision"]

    n_alice = len(alice_actions)
    n_bob = len(bob_actions)
    alice_payoffs = np.zeros((n_alice, n_bob))
    bob_payoffs = np.zeros((n_alice, n_bob))

    for tc in ir.terminal_conditions:
        alice_action = tc.actions["Alice Decision"]
        bob_action = tc.actions["Bob Decision"]
        row = alice_actions.index(alice_action)
        col = bob_actions.index(bob_action)

        a_pay, b_pay = _parse_payoff_description(tc.payoff_description)
        alice_payoffs[row, col] = a_pay
        bob_payoffs[row, col] = b_pay

    return alice_payoffs, bob_payoffs


def _parse_payoff_description(desc: str) -> tuple[float, float]:
    """Parse payoff_description into (alice_payoff, bob_payoff).

    Handles two formats:
        - "X=N each" -> (N, N)
        - "X=N for Alice, Y=M for Bob" -> (N, M)
    """
    each_match = re.match(r"[A-Z]=(\d+(?:\.\d+)?)\s+each", desc)
    if each_match:
        val = float(each_match.group(1))
        return val, val

    values: dict[str, float] = {}
    for match in re.finditer(r"[A-Z]=(\d+(?:\.\d+)?)\s+for\s+(\w+)", desc):
        val = float(match.group(1))
        player = match.group(2)
        values[player] = val

    if "Alice" in values and "Bob" in values:
        return values["Alice"], values["Bob"]

    raise ValueError(f"Cannot parse payoff_description: {desc!r}")


# ======================================================================
# Nash equilibrium computation
# ======================================================================


def compute_nash_equilibria(
    ir: PatternIR,
) -> list[tuple[NDArray[np.float64], NDArray[np.float64]]]:
    """Compute all Nash equilibria from a PatternIR using support enumeration.

    Args:
        ir: Compiled PatternIR with action_spaces and terminal_conditions.

    Returns:
        List of (alice_strategy, bob_strategy) tuples. Each strategy is a
        probability distribution over actions.
    """
    alice_payoffs, bob_payoffs = build_payoff_matrices(ir)
    game = nash.Game(alice_payoffs, bob_payoffs)
    return list(game.support_enumeration())


# ======================================================================
# Verification against declared terminal conditions
# ======================================================================


def verify_terminal_conditions(
    ir: PatternIR,
    equilibria: list[tuple[NDArray[np.float64], NDArray[np.float64]]],
) -> dict:
    """Cross-reference computed equilibria against declared TerminalConditions.

    Args:
        ir: Compiled PatternIR.
        equilibria: List of computed Nash equilibria.

    Returns:
        Dict with declared_equilibria, computed_equilibria, matches, mismatches.
    """
    assert ir.action_spaces is not None
    assert ir.terminal_conditions is not None

    players = {asp.game: asp.actions for asp in ir.action_spaces}
    alice_actions = players["Alice Decision"]
    bob_actions = players["Bob Decision"]

    computed_profiles: list[dict[str, str]] = []
    for alice_strat, bob_strat in equilibria:
        if _is_pure_strategy(alice_strat) and _is_pure_strategy(bob_strat):
            alice_idx = int(np.argmax(alice_strat))
            bob_idx = int(np.argmax(bob_strat))
            computed_profiles.append(
                {
                    "Alice Decision": alice_actions[alice_idx],
                    "Bob Decision": bob_actions[bob_idx],
                }
            )

    declared_ne = [
        tc
        for tc in ir.terminal_conditions
        if "nash equilibrium" in tc.outcome.lower()
        or "nash equilibrium" in tc.description.lower()
    ]

    matches = []
    mismatches = []
    for tc in declared_ne:
        if tc.actions in computed_profiles:
            matches.append(tc)
        else:
            mismatches.append(tc)

    return {
        "declared_equilibria": declared_ne,
        "computed_equilibria": computed_profiles,
        "matches": matches,
        "mismatches": mismatches,
    }


def _is_pure_strategy(strategy: NDArray[np.float64]) -> bool:
    """Check if a strategy is pure (exactly one action with probability 1)."""
    return bool(np.isclose(np.max(strategy), 1.0) and np.sum(strategy > 0.5) == 1)


# ======================================================================
# Game analysis — dominance and Pareto optimality
# ======================================================================


def analyze_game(ir: PatternIR) -> dict:
    """Full game-theoretic analysis of a PatternIR.

    Computes payoff matrices, Nash equilibria, dominant strategies,
    Pareto optimal outcomes, and verification against terminal conditions.
    """
    assert ir.action_spaces is not None
    assert ir.terminal_conditions is not None

    players = {asp.game: asp.actions for asp in ir.action_spaces}
    alice_actions = players["Alice Decision"]
    bob_actions = players["Bob Decision"]

    alice_payoffs, bob_payoffs = build_payoff_matrices(ir)
    game = nash.Game(alice_payoffs, bob_payoffs)
    equilibria = list(game.support_enumeration())

    alice_dominant = _find_dominant_strategy(alice_payoffs, alice_actions)
    bob_dominant = _find_dominant_strategy(bob_payoffs.T, bob_actions)

    pareto_optimal = _find_pareto_optimal(
        alice_payoffs, bob_payoffs, alice_actions, bob_actions
    )

    verification = verify_terminal_conditions(ir, equilibria)

    return {
        "players": players,
        "alice_payoffs": alice_payoffs,
        "bob_payoffs": bob_payoffs,
        "equilibria": equilibria,
        "alice_dominant_strategy": alice_dominant,
        "bob_dominant_strategy": bob_dominant,
        "pareto_optimal": pareto_optimal,
        "verification": verification,
    }


def _find_dominant_strategy(
    payoff_matrix: NDArray[np.float64], actions: list[str]
) -> str | None:
    """Find a strictly dominant strategy if one exists."""
    n = payoff_matrix.shape[0]
    for i in range(n):
        dominates_all = True
        for j in range(n):
            if i == j:
                continue
            if not np.all(payoff_matrix[i] > payoff_matrix[j]):
                dominates_all = False
                break
        if dominates_all:
            return actions[i]
    return None


def _find_pareto_optimal(
    alice_payoffs: NDArray[np.float64],
    bob_payoffs: NDArray[np.float64],
    alice_actions: list[str],
    bob_actions: list[str],
) -> list[dict]:
    """Find all Pareto optimal outcomes."""
    n_alice, n_bob = alice_payoffs.shape
    outcomes = []
    for i in range(n_alice):
        for j in range(n_bob):
            outcomes.append(
                {
                    "alice_action": alice_actions[i],
                    "bob_action": bob_actions[j],
                    "alice_payoff": alice_payoffs[i, j],
                    "bob_payoff": bob_payoffs[i, j],
                }
            )

    pareto = []
    for outcome in outcomes:
        dominated = False
        for other in outcomes:
            if other is outcome:
                continue
            at_least_as_good = (
                other["alice_payoff"] >= outcome["alice_payoff"]
                and other["bob_payoff"] >= outcome["bob_payoff"]
            )
            strictly_better = (
                other["alice_payoff"] > outcome["alice_payoff"]
                or other["bob_payoff"] > outcome["bob_payoff"]
            )
            if at_least_as_good and strictly_better:
                dominated = True
                break
        if not dominated:
            pareto.append(outcome)

    return pareto


# ======================================================================
# Convenience entry points
# ======================================================================


def run_analysis() -> dict:
    """Run the full Nash equilibrium analysis on the Prisoner's Dilemma."""
    ir = build_ir()
    return analyze_game(ir)
