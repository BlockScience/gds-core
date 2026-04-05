"""Tests for Nash equilibrium computation on the Prisoner's Dilemma."""

import numpy as np

from gds_domains.games.ir.models import PatternIR
from prisoners_dilemma_nash.model import (
    P,
    R,
    S,
    T,
    analyze_game,
    build_ir,
    build_payoff_matrices,
    compute_nash_equilibria,
    verify_terminal_conditions,
)

# ======================================================================
# TestPayoffMatrix — matrix construction from PatternIR
# ======================================================================


class TestPayoffMatrix:
    """Test payoff matrix extraction from PatternIR metadata."""

    def setup_method(self):
        self.ir = build_ir()
        self.alice_payoffs, self.bob_payoffs = build_payoff_matrices(self.ir)

    def test_matrix_shape(self):
        assert self.alice_payoffs.shape == (2, 2)
        assert self.bob_payoffs.shape == (2, 2)

    def test_alice_payoffs_values(self):
        """Alice's payoff matrix: rows=Alice actions, cols=Bob actions.

        (Cooperate, Cooperate) = R=3
        (Cooperate, Defect)    = S=0
        (Defect, Cooperate)    = T=5
        (Defect, Defect)       = P=1
        """
        assert self.alice_payoffs[0, 0] == R  # CC
        assert self.alice_payoffs[0, 1] == S  # CD
        assert self.alice_payoffs[1, 0] == T  # DC
        assert self.alice_payoffs[1, 1] == P  # DD

    def test_bob_payoffs_values(self):
        """Bob's payoff matrix (symmetric game, transposed perspective).

        (Cooperate, Cooperate) = R=3
        (Cooperate, Defect)    = T=5  (Bob defects, gets temptation)
        (Defect, Cooperate)    = S=0  (Bob cooperates while Alice defects)
        (Defect, Defect)       = P=1
        """
        assert self.bob_payoffs[0, 0] == R  # CC
        assert self.bob_payoffs[0, 1] == T  # CD (Bob gets T)
        assert self.bob_payoffs[1, 0] == S  # DC (Bob gets S)
        assert self.bob_payoffs[1, 1] == P  # DD

    def test_payoff_ordering(self):
        """Standard PD requires T > R > P > S."""
        assert T > R > P > S

    def test_cooperation_temptation(self):
        """2R > T + S ensures mutual cooperation is socially optimal."""
        assert 2 * R > T + S


# ======================================================================
# TestNashEquilibria — support enumeration finds correct NE
# ======================================================================


class TestNashEquilibria:
    """Test Nash equilibrium computation via Nashpy."""

    def setup_method(self):
        self.ir = build_ir()
        self.equilibria = compute_nash_equilibria(self.ir)

    def test_exactly_one_equilibrium(self):
        """PD has exactly one Nash equilibrium: (Defect, Defect)."""
        assert len(self.equilibria) == 1

    def test_equilibrium_is_pure_strategy(self):
        """The NE is a pure strategy (no mixing)."""
        alice_strat, bob_strat = self.equilibria[0]
        assert np.isclose(np.max(alice_strat), 1.0)
        assert np.isclose(np.max(bob_strat), 1.0)

    def test_equilibrium_is_defect_defect(self):
        """Both players defect at equilibrium.

        Action order from action_spaces: [Cooperate, Defect]
        So index 1 = Defect for both players.
        """
        alice_strat, bob_strat = self.equilibria[0]
        assert np.argmax(alice_strat) == 1  # Defect
        assert np.argmax(bob_strat) == 1  # Defect


# ======================================================================
# TestEquilibriumVerification — computed NE matches declared metadata
# ======================================================================


class TestEquilibriumVerification:
    """Test cross-referencing computed equilibria against TerminalConditions."""

    def setup_method(self):
        self.ir = build_ir()
        self.equilibria = compute_nash_equilibria(self.ir)
        self.verification = verify_terminal_conditions(self.ir, self.equilibria)

    def test_one_declared_equilibrium(self):
        """Only 'Mutual Defection' is declared as Nash equilibrium."""
        assert len(self.verification["declared_equilibria"]) == 1
        assert self.verification["declared_equilibria"][0].name == "Mutual Defection"

    def test_one_computed_equilibrium(self):
        """Nashpy finds exactly one pure-strategy NE."""
        assert len(self.verification["computed_equilibria"]) == 1

    def test_computed_matches_declared(self):
        """Computed NE matches the declared 'Mutual Defection' terminal condition."""
        assert len(self.verification["matches"]) == 1
        assert self.verification["matches"][0].name == "Mutual Defection"

    def test_no_mismatches(self):
        """No declared equilibria fail to match computed ones."""
        assert len(self.verification["mismatches"]) == 0


# ======================================================================
# TestDominance — Defect is strictly dominant for both players
# ======================================================================


class TestDominance:
    """Test dominant strategy analysis."""

    def setup_method(self):
        self.ir = build_ir()
        self.analysis = analyze_game(self.ir)

    def test_alice_dominant_strategy(self):
        """Defect strictly dominates Cooperate for Alice."""
        assert self.analysis["alice_dominant_strategy"] == "Defect"

    def test_bob_dominant_strategy(self):
        """Defect strictly dominates Cooperate for Bob."""
        assert self.analysis["bob_dominant_strategy"] == "Defect"


# ======================================================================
# TestParetoOptimality — Mutual Cooperation is Pareto optimal
# ======================================================================


class TestParetoOptimality:
    """Test Pareto optimality analysis."""

    def setup_method(self):
        self.ir = build_ir()
        self.analysis = analyze_game(self.ir)
        self.pareto = self.analysis["pareto_optimal"]

    def test_mutual_cooperation_is_pareto_optimal(self):
        """(Cooperate, Cooperate) with payoff (3,3) is Pareto optimal."""
        cc = [
            o
            for o in self.pareto
            if o["alice_action"] == "Cooperate" and o["bob_action"] == "Cooperate"
        ]
        assert len(cc) == 1

    def test_mutual_defection_is_not_pareto_optimal(self):
        """(Defect, Defect) with payoff (1,1) is Pareto dominated by (3,3)."""
        dd = [
            o
            for o in self.pareto
            if o["alice_action"] == "Defect" and o["bob_action"] == "Defect"
        ]
        assert len(dd) == 0

    def test_asymmetric_outcomes_are_pareto_optimal(self):
        """(Defect, Cooperate) and (Cooperate, Defect) are Pareto optimal."""
        dc = [
            o
            for o in self.pareto
            if o["alice_action"] == "Defect" and o["bob_action"] == "Cooperate"
        ]
        cd = [
            o
            for o in self.pareto
            if o["alice_action"] == "Cooperate" and o["bob_action"] == "Defect"
        ]
        assert len(dc) == 1
        assert len(cd) == 1

    def test_three_pareto_optimal_outcomes(self):
        """PD has exactly 3 Pareto optimal outcomes (all except DD)."""
        assert len(self.pareto) == 3


# ======================================================================
# TestIntegration — full pipeline from OGS primitives to Nash analysis
# ======================================================================


class TestIntegration:
    """Test the full pipeline: build_ir() -> compute -> verify."""

    def test_full_pipeline(self):
        """End-to-end: OGS primitives -> PatternIR -> Nash -> verify."""
        ir = build_ir()
        assert isinstance(ir, PatternIR)

        equilibria = compute_nash_equilibria(ir)
        assert len(equilibria) == 1

        verification = verify_terminal_conditions(ir, equilibria)
        assert len(verification["matches"]) == 1
        assert len(verification["mismatches"]) == 0

    def test_analyze_game_returns_complete_results(self):
        """analyze_game() returns all expected keys."""
        ir = build_ir()
        result = analyze_game(ir)

        expected_keys = {
            "players",
            "alice_payoffs",
            "bob_payoffs",
            "equilibria",
            "alice_dominant_strategy",
            "bob_dominant_strategy",
            "pareto_optimal",
            "verification",
        }
        assert set(result.keys()) == expected_keys

    def test_dilemma_structure(self):
        """The PD dilemma: NE is not Pareto optimal.

        This is the defining characteristic of the Prisoner's Dilemma:
        the Nash equilibrium (Defect, Defect) is Pareto dominated by
        (Cooperate, Cooperate).
        """
        ir = build_ir()
        result = analyze_game(ir)

        # NE is (Defect, Defect)
        ne_profiles = result["verification"]["computed_equilibria"]
        assert len(ne_profiles) == 1
        assert ne_profiles[0] == {
            "Alice Decision": "Defect",
            "Bob Decision": "Defect",
        }

        # But (Defect, Defect) is NOT Pareto optimal
        pareto_actions = [
            (o["alice_action"], o["bob_action"]) for o in result["pareto_optimal"]
        ]
        assert ("Defect", "Defect") not in pareto_actions

        # While (Cooperate, Cooperate) IS Pareto optimal
        assert ("Cooperate", "Cooperate") in pareto_actions
