"""Tests for Nash equilibrium computation."""

from __future__ import annotations

import pytest

nashpy = pytest.importorskip("nashpy")
numpy = pytest.importorskip("numpy")

import numpy as np  # noqa: E402

from ogs.dsl.pattern import ActionSpace, TerminalCondition  # noqa: E402
from ogs.equilibrium import (  # noqa: E402
    compute_nash,
    extract_payoff_matrices,
)
from ogs.ir.models import CompositionType, PatternIR  # noqa: E402


def _prisoners_dilemma_ir() -> PatternIR:
    """Prisoner's Dilemma: classic 2x2 game.

    Payoff matrix (row=P1, col=P2):
              Cooperate  Defect
    Cooperate   (3,3)     (0,5)
    Defect      (5,0)     (1,1)

    Unique Nash equilibrium: (Defect, Defect) with payoffs (1, 1).
    """
    return PatternIR(
        composition_type=CompositionType.SEQUENTIAL,
        source_canvas="test",
        name="prisoners_dilemma",
        games=[],
        flows=[],
        action_spaces=[
            ActionSpace(game="Player1", actions=["Cooperate", "Defect"]),
            ActionSpace(game="Player2", actions=["Cooperate", "Defect"]),
        ],
        terminal_conditions=[
            TerminalCondition(
                name="CC",
                actions={"Player1": "Cooperate", "Player2": "Cooperate"},
                outcome="mutual_cooperation",
                payoffs={"Player1": 3.0, "Player2": 3.0},
            ),
            TerminalCondition(
                name="CD",
                actions={"Player1": "Cooperate", "Player2": "Defect"},
                outcome="sucker",
                payoffs={"Player1": 0.0, "Player2": 5.0},
            ),
            TerminalCondition(
                name="DC",
                actions={"Player1": "Defect", "Player2": "Cooperate"},
                outcome="temptation",
                payoffs={"Player1": 5.0, "Player2": 0.0},
            ),
            TerminalCondition(
                name="DD",
                actions={"Player1": "Defect", "Player2": "Defect"},
                outcome="mutual_defection",
                payoffs={"Player1": 1.0, "Player2": 1.0},
            ),
        ],
    )


def _matching_pennies_ir() -> PatternIR:
    """Matching Pennies: no pure NE, unique mixed NE at (0.5, 0.5).

              Heads   Tails
    Heads     (1,-1)  (-1,1)
    Tails     (-1,1)  (1,-1)
    """
    return PatternIR(
        composition_type=CompositionType.SEQUENTIAL,
        source_canvas="test",
        name="matching_pennies",
        games=[],
        flows=[],
        action_spaces=[
            ActionSpace(game="Row", actions=["Heads", "Tails"]),
            ActionSpace(game="Col", actions=["Heads", "Tails"]),
        ],
        terminal_conditions=[
            TerminalCondition(
                name="HH",
                actions={"Row": "Heads", "Col": "Heads"},
                outcome="match_heads",
                payoffs={"Row": 1.0, "Col": -1.0},
            ),
            TerminalCondition(
                name="HT",
                actions={"Row": "Heads", "Col": "Tails"},
                outcome="mismatch",
                payoffs={"Row": -1.0, "Col": 1.0},
            ),
            TerminalCondition(
                name="TH",
                actions={"Row": "Tails", "Col": "Heads"},
                outcome="mismatch",
                payoffs={"Row": -1.0, "Col": 1.0},
            ),
            TerminalCondition(
                name="TT",
                actions={"Row": "Tails", "Col": "Tails"},
                outcome="match_tails",
                payoffs={"Row": 1.0, "Col": -1.0},
            ),
        ],
    )


def _battle_of_sexes_ir() -> PatternIR:
    """Battle of the Sexes: two pure NE + one mixed NE.

              Opera  Football
    Opera     (3,2)   (0,0)
    Football  (0,0)   (2,3)
    """
    return PatternIR(
        composition_type=CompositionType.SEQUENTIAL,
        source_canvas="test",
        name="battle_of_sexes",
        games=[],
        flows=[],
        action_spaces=[
            ActionSpace(game="Alice", actions=["Opera", "Football"]),
            ActionSpace(game="Bob", actions=["Opera", "Football"]),
        ],
        terminal_conditions=[
            TerminalCondition(
                name="OO",
                actions={"Alice": "Opera", "Bob": "Opera"},
                outcome="opera",
                payoffs={"Alice": 3.0, "Bob": 2.0},
            ),
            TerminalCondition(
                name="OF",
                actions={"Alice": "Opera", "Bob": "Football"},
                outcome="mismatch",
                payoffs={"Alice": 0.0, "Bob": 0.0},
            ),
            TerminalCondition(
                name="FO",
                actions={"Alice": "Football", "Bob": "Opera"},
                outcome="mismatch",
                payoffs={"Alice": 0.0, "Bob": 0.0},
            ),
            TerminalCondition(
                name="FF",
                actions={"Alice": "Football", "Bob": "Football"},
                outcome="football",
                payoffs={"Alice": 2.0, "Bob": 3.0},
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractPayoffMatrices:
    def test_prisoners_dilemma(self) -> None:
        matrices = extract_payoff_matrices(_prisoners_dilemma_ir())
        assert matrices.player1 == "Player1"
        assert matrices.player2 == "Player2"
        assert matrices.actions1 == ["Cooperate", "Defect"]
        # A[0,0]=3 (CC), A[0,1]=0 (CD), A[1,0]=5 (DC), A[1,1]=1 (DD)
        assert matrices.A[0, 0] == 3.0
        assert matrices.A[0, 1] == 0.0
        assert matrices.A[1, 0] == 5.0
        assert matrices.A[1, 1] == 1.0

    def test_symmetric_payoffs(self) -> None:
        """Matching Pennies: A = -B (zero-sum)."""
        matrices = extract_payoff_matrices(_matching_pennies_ir())
        np.testing.assert_array_equal(matrices.A, -matrices.B)

    def test_wrong_player_count(self) -> None:
        ir = PatternIR(
            composition_type=CompositionType.SEQUENTIAL,
            source_canvas="test",
            name="bad",
            games=[],
            flows=[],
            action_spaces=[ActionSpace(game="P1", actions=["a"])],
        )
        with pytest.raises(ValueError, match="exactly 2"):
            extract_payoff_matrices(ir)

    def test_missing_payoffs(self) -> None:
        ir = PatternIR(
            composition_type=CompositionType.SEQUENTIAL,
            source_canvas="test",
            name="bad",
            games=[],
            flows=[],
            action_spaces=[
                ActionSpace(game="P1", actions=["a"]),
                ActionSpace(game="P2", actions=["b"]),
            ],
            terminal_conditions=[
                TerminalCondition(
                    name="ab",
                    actions={"P1": "a", "P2": "b"},
                    outcome="x",
                    # no payoffs field
                ),
            ],
        )
        with pytest.raises(ValueError, match="missing numeric payoffs"):
            extract_payoff_matrices(ir)


class TestComputeNash:
    def test_prisoners_dilemma_unique_ne(self) -> None:
        """PD has unique NE: (Defect, Defect)."""
        results = compute_nash(_prisoners_dilemma_ir())
        assert len(results) == 1
        ne = results[0]
        # Pure strategy: Defect (index 1) has probability 1
        assert ne.sigma1[1] == pytest.approx(1.0)
        assert ne.sigma2[1] == pytest.approx(1.0)

    def test_matching_pennies_mixed_ne(self) -> None:
        """Matching Pennies: unique NE at (0.5, 0.5)."""
        results = compute_nash(_matching_pennies_ir())
        assert len(results) == 1
        ne = results[0]
        assert ne.sigma1[0] == pytest.approx(0.5)
        assert ne.sigma1[1] == pytest.approx(0.5)
        assert ne.sigma2[0] == pytest.approx(0.5)
        assert ne.sigma2[1] == pytest.approx(0.5)

    def test_battle_of_sexes_multiple_ne(self) -> None:
        """Battle of Sexes: 3 NE (2 pure + 1 mixed)."""
        results = compute_nash(_battle_of_sexes_ir())
        assert len(results) == 3

    def test_support(self) -> None:
        """Mixed NE in Matching Pennies: both actions in support."""
        results = compute_nash(_matching_pennies_ir())
        s1, s2 = results[0].support()
        assert set(s1) == {"Heads", "Tails"}
        assert set(s2) == {"Heads", "Tails"}

    def test_expected_payoffs(self) -> None:
        """PD NE payoffs: (1, 1)."""
        ir = _prisoners_dilemma_ir()
        matrices = extract_payoff_matrices(ir)
        results = compute_nash(ir)
        u1, u2 = results[0].expected_payoffs(matrices)
        assert u1 == pytest.approx(1.0)
        assert u2 == pytest.approx(1.0)

    def test_vertex_enumeration(self) -> None:
        """Alternative solver method."""
        results = compute_nash(_prisoners_dilemma_ir(), method="vertex_enumeration")
        assert len(results) >= 1

    def test_unknown_method(self) -> None:
        with pytest.raises(ValueError, match="Unknown method"):
            compute_nash(_prisoners_dilemma_ir(), method="bogus")
