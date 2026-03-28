"""Nash equilibrium computation for 2-player normal-form games.

Extracts payoff matrices from PatternIR terminal conditions and
action spaces, then delegates to Nashpy for equilibrium solving.

Requires ``nashpy`` (optional dependency)::

    uv add gds-games[nash]

Example::

    from ogs.equilibrium import compute_nash, extract_payoff_matrices

    matrices = extract_payoff_matrices(pattern_ir)
    equilibria = compute_nash(pattern_ir)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ogs.ir.models import PatternIR


def _require_nashpy() -> None:
    """Raise ImportError if nashpy is not installed."""
    try:
        import nashpy  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "nashpy is required for equilibrium computation. "
            "Install with: uv add gds-games[nash]"
        ) from exc


@dataclass(frozen=True)
class PayoffMatrices:
    """Payoff matrices for a 2-player normal-form game.

    ``A[i, j]`` is player 1's payoff when player 1 plays action ``i``
    and player 2 plays action ``j``. ``B[i, j]`` is player 2's payoff.
    """

    A: Any  # numpy ndarray, shape (m, n)
    B: Any  # numpy ndarray, shape (m, n)
    player1: str
    player2: str
    actions1: list[str]
    actions2: list[str]


@dataclass(frozen=True)
class NashResult:
    """A Nash equilibrium in mixed strategies.

    ``sigma1[i]`` is the probability player 1 assigns to action ``i``.
    ``sigma2[j]`` is the probability player 2 assigns to action ``j``.
    """

    sigma1: Any  # numpy ndarray, shape (m,)
    sigma2: Any  # numpy ndarray, shape (n,)
    player1: str
    player2: str
    actions1: list[str]
    actions2: list[str]

    def support(self) -> tuple[list[str], list[str]]:
        """Actions played with positive probability."""

        s1 = [a for a, p in zip(self.actions1, self.sigma1, strict=True) if p > 1e-10]
        s2 = [a for a, p in zip(self.actions2, self.sigma2, strict=True) if p > 1e-10]
        return s1, s2

    def expected_payoffs(self, matrices: PayoffMatrices) -> tuple[float, float]:
        """Compute expected payoffs under this equilibrium."""

        u1 = float(self.sigma1 @ matrices.A @ self.sigma2)
        u2 = float(self.sigma1 @ matrices.B @ self.sigma2)
        return u1, u2


def extract_payoff_matrices(ir: PatternIR) -> PayoffMatrices:
    """Extract payoff matrices from a PatternIR with 2 players.

    Requires:
    - Exactly 2 action spaces defined
    - Terminal conditions covering all joint action profiles
    - Each terminal condition has numeric ``payoffs`` for both players

    Raises
    ------
    ValueError
        If the PatternIR does not represent a valid 2-player normal-form game.
    """
    try:
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "numpy is required for payoff matrix extraction. "
            "Install with: uv add gds-games[nash]"
        ) from exc

    if not ir.action_spaces or len(ir.action_spaces) != 2:
        msg = f"Expected exactly 2 action spaces, got {len(ir.action_spaces or [])}"
        raise ValueError(msg)

    if not ir.terminal_conditions:
        msg = "No terminal conditions defined"
        raise ValueError(msg)

    p1_space = ir.action_spaces[0]
    p2_space = ir.action_spaces[1]
    player1 = p1_space.game
    player2 = p2_space.game
    actions1 = p1_space.actions
    actions2 = p2_space.actions

    m, n = len(actions1), len(actions2)
    A = np.zeros((m, n))
    B = np.zeros((m, n))

    # Build lookup from (action1, action2) -> terminal condition
    populated: set[tuple[int, int]] = set()
    for tc in ir.terminal_conditions:
        if player1 not in tc.actions or player2 not in tc.actions:
            msg = (
                f"Terminal condition '{tc.name}' missing actions "
                f"for {player1} and/or {player2}. "
                f"Got actions: {list(tc.actions.keys())}"
            )
            raise ValueError(msg)
        a1 = tc.actions[player1]
        a2 = tc.actions[player2]
        if a1 not in actions1:
            msg = (
                f"Terminal condition '{tc.name}': "
                f"unrecognized action '{a1}' for {player1}. "
                f"Valid actions: {actions1}"
            )
            raise ValueError(msg)
        if a2 not in actions2:
            msg = (
                f"Terminal condition '{tc.name}': "
                f"unrecognized action '{a2}' for {player2}. "
                f"Valid actions: {actions2}"
            )
            raise ValueError(msg)

        i = actions1.index(a1)
        j = actions2.index(a2)

        if player1 not in tc.payoffs or player2 not in tc.payoffs:
            msg = (
                f"Terminal condition '{tc.name}' missing numeric payoffs "
                f"for {player1} and/or {player2}. "
                f"Set payoffs={{'{player1}': ..., '{player2}': ...}}"
            )
            raise ValueError(msg)

        A[i, j] = tc.payoffs[player1]
        B[i, j] = tc.payoffs[player2]
        populated.add((i, j))

    # Validate that all action profile entries are populated
    expected = {(i, j) for i in range(m) for j in range(n)}
    missing = expected - populated
    if missing:
        missing_profiles = [
            f"({actions1[i]}, {actions2[j]})" for i, j in sorted(missing)
        ]
        msg = (
            f"Incomplete payoff matrix: {len(missing)} of "
            f"{m * n} action profiles have no terminal condition. "
            f"Missing: {', '.join(missing_profiles)}"
        )
        raise ValueError(msg)

    return PayoffMatrices(
        A=A,
        B=B,
        player1=player1,
        player2=player2,
        actions1=actions1,
        actions2=actions2,
    )


def compute_nash(
    ir: PatternIR,
    *,
    method: str = "support_enumeration",
) -> list[NashResult]:
    """Compute Nash equilibria for a 2-player normal-form game.

    Parameters
    ----------
    ir
        A PatternIR with exactly 2 action spaces and complete
        terminal conditions with numeric payoffs.
    method
        Nashpy solver method: ``"support_enumeration"`` (default),
        ``"vertex_enumeration"``, or ``"lemke_howson"``.

    Returns
    -------
    List of NashResult, one per equilibrium found.
    """
    _require_nashpy()
    import nashpy

    matrices = extract_payoff_matrices(ir)
    game = nashpy.Game(matrices.A, matrices.B)

    if method == "support_enumeration":
        raw = list(game.support_enumeration())
    elif method == "vertex_enumeration":
        raw = list(game.vertex_enumeration())
    elif method == "lemke_howson":
        raw = [game.lemke_howson(initial_label=0)]
    else:
        msg = f"Unknown method '{method}'. Use 'support_enumeration', 'vertex_enumeration', or 'lemke_howson'"
        raise ValueError(msg)

    results = []
    for sigma1, sigma2 in raw:
        results.append(
            NashResult(
                sigma1=sigma1,
                sigma2=sigma2,
                player1=matrices.player1,
                player2=matrices.player2,
                actions1=matrices.actions1,
                actions2=matrices.actions2,
            )
        )
    return results
