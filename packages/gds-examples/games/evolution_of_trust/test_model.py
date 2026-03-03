"""Tests for Evolution of Trust — iterated Prisoner's Dilemma.

Covers:
    - OGS game structure and IR compilation
    - Payoff matrix extraction (including negative values)
    - All 8 strategies in isolation
    - Tournament mechanics
    - Evolutionary dynamics
"""

import pytest

from evolution_of_trust.model import (
    P,
    R,
    S,
    T,
    build_game,
    build_ir,
    build_pattern,
    build_payoff_matrices,
    get_payoff,
)
from evolution_of_trust.strategies import (
    ALL_STRATEGIES,
    COOPERATE,
    DEFECT,
    AlwaysCooperate,
    AlwaysDefect,
    Detective,
    GrimTrigger,
    Pavlov,
    RandomStrategy,
    Strategy,
    TitForTat,
    TitForTwoTats,
)
from evolution_of_trust.tournament import (
    EvolutionSnapshot,
    MatchResult,
    head_to_head,
    play_match,
    play_round_robin,
    run_evolution,
)

# ======================================================================
# OGS Game Structure
# ======================================================================


class TestPayoffParameters:
    """Verify Nicky Case's payoff values and PD constraints."""

    def test_payoff_values(self):
        assert R == 2
        assert T == 3
        assert S == -1
        assert P == 0

    def test_pd_ordering(self):
        """T > R > P > S must hold for a valid PD."""
        assert T > R > P > S

    def test_cooperation_condition(self):
        """2R > T + S ensures mutual cooperation beats alternating exploitation."""
        assert 2 * R > T + S


class TestGameStructure:
    """Verify OGS composition tree builds correctly."""

    def test_build_game(self):
        game = build_game()
        assert game.name == "Prisoner's Dilemma"

    def test_build_pattern(self):
        pattern = build_pattern()
        assert pattern.name == "Evolution of Trust PD"
        assert len(pattern.terminal_conditions) == 4
        assert len(pattern.action_spaces) == 2

    def test_build_ir(self):
        ir = build_ir()
        assert ir is not None
        assert ir.action_spaces is not None
        assert len(ir.action_spaces) == 2

    def test_payoff_matrix_extraction(self):
        ir = build_ir()
        alice_payoffs, bob_payoffs = build_payoff_matrices(ir)
        # CC = (R, R) = (2, 2)
        assert alice_payoffs[0][0] == R
        assert bob_payoffs[0][0] == R
        # CD = (S, T) = (-1, 3)
        assert alice_payoffs[0][1] == S
        assert bob_payoffs[0][1] == T
        # DC = (T, S) = (3, -1)
        assert alice_payoffs[1][0] == T
        assert bob_payoffs[1][0] == S
        # DD = (P, P) = (0, 0)
        assert alice_payoffs[1][1] == P
        assert bob_payoffs[1][1] == P

    def test_negative_payoff_parsing(self):
        """Ensure _parse_payoff_description handles negative values."""
        ir = build_ir()
        alice_payoffs, bob_payoffs = build_payoff_matrices(ir)
        assert alice_payoffs[0][1] == -1  # S = -1
        assert bob_payoffs[1][0] == -1  # S = -1


class TestGetPayoff:
    """Verify direct payoff lookup."""

    def test_mutual_cooperation(self):
        assert get_payoff("Cooperate", "Cooperate") == (R, R)

    def test_mutual_defection(self):
        assert get_payoff("Defect", "Defect") == (P, P)

    def test_temptation(self):
        assert get_payoff("Defect", "Cooperate") == (T, S)

    def test_sucker(self):
        assert get_payoff("Cooperate", "Defect") == (S, T)


# ======================================================================
# Strategies
# ======================================================================


class TestStrategyProtocol:
    """All strategies satisfy the Strategy protocol."""

    @pytest.mark.parametrize("cls", ALL_STRATEGIES)
    def test_is_strategy(self, cls):
        instance = cls()
        assert isinstance(instance, Strategy)

    @pytest.mark.parametrize("cls", ALL_STRATEGIES)
    def test_has_name(self, cls):
        assert isinstance(cls().name, str)
        assert len(cls().name) > 0

    @pytest.mark.parametrize("cls", ALL_STRATEGIES)
    def test_has_description(self, cls):
        assert isinstance(cls().description, str)


class TestAlwaysCooperate:
    def test_always_cooperates(self):
        s = AlwaysCooperate()
        for i in range(10):
            assert s.choose([], i) == COOPERATE


class TestAlwaysDefect:
    def test_always_defects(self):
        s = AlwaysDefect()
        for i in range(10):
            assert s.choose([], i) == DEFECT


class TestTitForTat:
    def test_cooperates_first(self):
        s = TitForTat()
        assert s.choose([], 0) == COOPERATE

    def test_copies_opponent(self):
        s = TitForTat()
        assert s.choose([(COOPERATE, DEFECT)], 1) == DEFECT
        assert s.choose([(COOPERATE, DEFECT), (DEFECT, COOPERATE)], 2) == COOPERATE


class TestGrimTrigger:
    def test_cooperates_initially(self):
        s = GrimTrigger()
        assert s.choose([], 0) == COOPERATE

    def test_defects_after_opponent_defects(self):
        s = GrimTrigger()
        assert s.choose([(COOPERATE, DEFECT)], 1) == DEFECT

    def test_never_forgives(self):
        s = GrimTrigger()
        s.choose([(COOPERATE, DEFECT)], 1)  # triggers
        # Even if opponent cooperates again, grim stays defecting
        assert s.choose([(COOPERATE, DEFECT), (DEFECT, COOPERATE)], 2) == DEFECT


class TestDetective:
    def test_probe_sequence(self):
        s = Detective()
        assert s.choose([], 0) == COOPERATE
        assert s.choose([(COOPERATE, COOPERATE)], 1) == DEFECT
        h = [(COOPERATE, COOPERATE), (DEFECT, COOPERATE)]
        assert s.choose(h, 2) == COOPERATE
        h = [(COOPERATE, COOPERATE), (DEFECT, COOPERATE), (COOPERATE, COOPERATE)]
        assert s.choose(h, 3) == COOPERATE

    def test_exploits_naive_cooperator(self):
        """If opponent never defects during probe, Detective exploits."""
        s = Detective()
        h = [
            (COOPERATE, COOPERATE),
            (DEFECT, COOPERATE),
            (COOPERATE, COOPERATE),
            (COOPERATE, COOPERATE),
        ]
        assert s.choose(h, 4) == DEFECT
        h.append((DEFECT, COOPERATE))
        assert s.choose(h, 5) == DEFECT

    def test_falls_back_to_tft(self):
        """If opponent retaliates during probe, Detective plays TfT."""
        s = Detective()
        h = [
            (COOPERATE, COOPERATE),
            (DEFECT, DEFECT),  # opponent retaliated
            (COOPERATE, COOPERATE),
            (COOPERATE, COOPERATE),
        ]
        # Opponent defected in round 1 → not exploitable → TfT
        assert s.choose(h, 4) == COOPERATE  # TfT: copies last opponent (C)
        h.append((COOPERATE, DEFECT))
        assert s.choose(h, 5) == DEFECT  # TfT: copies last opponent (D)


class TestTitForTwoTats:
    def test_cooperates_initially(self):
        s = TitForTwoTats()
        assert s.choose([], 0) == COOPERATE
        assert s.choose([(COOPERATE, DEFECT)], 1) == COOPERATE

    def test_tolerates_single_defection(self):
        s = TitForTwoTats()
        h = [(COOPERATE, COOPERATE), (COOPERATE, DEFECT)]
        assert s.choose(h, 2) == COOPERATE

    def test_retaliates_after_two_defections(self):
        s = TitForTwoTats()
        h = [(COOPERATE, DEFECT), (COOPERATE, DEFECT)]
        assert s.choose(h, 2) == DEFECT


class TestPavlov:
    def test_cooperates_first(self):
        s = Pavlov()
        assert s.choose([], 0) == COOPERATE

    def test_stays_on_cc(self):
        s = Pavlov()
        assert s.choose([(COOPERATE, COOPERATE)], 1) == COOPERATE

    def test_stays_on_dd(self):
        """Both defected -> same action -> stay."""
        s = Pavlov()
        assert s.choose([(DEFECT, DEFECT)], 1) == DEFECT

    def test_switches_on_cd(self):
        s = Pavlov()
        assert s.choose([(COOPERATE, DEFECT)], 1) == DEFECT

    def test_switches_on_dc(self):
        s = Pavlov()
        assert s.choose([(DEFECT, COOPERATE)], 1) == COOPERATE


class TestRandomStrategy:
    def test_deterministic_with_seed(self):
        s1 = RandomStrategy(seed=123)
        s2 = RandomStrategy(seed=123)
        for i in range(20):
            assert s1.choose([], i) == s2.choose([], i)

    def test_produces_both_actions(self):
        s = RandomStrategy(seed=42)
        actions = {s.choose([], i) for i in range(50)}
        assert COOPERATE in actions
        assert DEFECT in actions


# ======================================================================
# Tournament
# ======================================================================


class TestPlayMatch:
    def test_cooperators_get_max_reward(self):
        a = AlwaysCooperate()
        b = AlwaysCooperate()
        result = play_match(a, b, rounds=10)
        assert result.score_a == R * 10
        assert result.score_b == R * 10

    def test_defector_exploits_cooperator(self):
        a = AlwaysDefect()
        b = AlwaysCooperate()
        result = play_match(a, b, rounds=10)
        assert result.score_a == T * 10
        assert result.score_b == S * 10

    def test_mutual_defection(self):
        a = AlwaysDefect()
        b = AlwaysDefect()
        result = play_match(a, b, rounds=10)
        assert result.score_a == P * 10
        assert result.score_b == P * 10

    def test_history_length(self):
        result = play_match(AlwaysCooperate(), AlwaysDefect(), rounds=5)
        assert len(result.history) == 5

    def test_noise_flips_actions(self):
        """With noise=1.0, all actions should be flipped."""
        import random as _random

        rng = _random.Random(42)
        result = play_match(
            AlwaysCooperate(),
            AlwaysCooperate(),
            rounds=10,
            noise=1.0,
            rng=rng,
        )
        # With noise=1.0, cooperate flips to defect
        defects = sum(1 for a, b in result.history if a == DEFECT or b == DEFECT)
        assert defects > 0


class TestRoundRobin:
    def test_all_strategies_scored(self):
        strategies = [AlwaysCooperate(), AlwaysDefect(), TitForTat()]
        result = play_round_robin(strategies, rounds_per_match=5)
        for s in strategies:
            assert s.name in result.scores

    def test_includes_self_play(self):
        strategies = [AlwaysCooperate(), AlwaysDefect()]
        result = play_round_robin(strategies, rounds_per_match=5)
        # 2 strategies: self-play A vs A, A vs B, B vs B = 3 matches
        assert len(result.matches) == 3

    def test_avg_scores(self):
        strategies = [AlwaysCooperate(), AlwaysDefect()]
        result = play_round_robin(strategies, rounds_per_match=5)
        avg = result.avg_scores
        assert len(avg) == 2
        for score in avg.values():
            assert isinstance(score, float)


# ======================================================================
# Evolution
# ======================================================================


class TestEvolution:
    def test_population_preserved(self):
        pops = {"Always Cooperate": 5, "Always Defect": 5}
        factories = {"Always Cooperate": AlwaysCooperate, "Always Defect": AlwaysDefect}
        snapshots = run_evolution(pops, factories, generations=10, rounds_per_match=5)
        total = sum(pops.values())
        for snap in snapshots:
            assert sum(snap.populations.values()) == total

    def test_generation_count(self):
        pops = {"Always Cooperate": 5, "Always Defect": 5}
        factories = {"Always Cooperate": AlwaysCooperate, "Always Defect": AlwaysDefect}
        snapshots = run_evolution(pops, factories, generations=10, rounds_per_match=5)
        assert len(snapshots) == 11  # gen 0 through gen 10

    def test_defectors_dominate_cooperators(self):
        """Always Defect should outcompete Always Cooperate in evolution."""
        pops = {"Always Cooperate": 5, "Always Defect": 5}
        factories = {"Always Cooperate": AlwaysCooperate, "Always Defect": AlwaysDefect}
        snapshots = run_evolution(pops, factories, generations=10, rounds_per_match=5)
        final = snapshots[-1].populations
        assert final["Always Defect"] > final["Always Cooperate"]

    def test_snapshot_structure(self):
        pops = {"Always Cooperate": 3, "Always Defect": 3, "Tit for Tat": 4}
        factories = {
            "Always Cooperate": AlwaysCooperate,
            "Always Defect": AlwaysDefect,
            "Tit for Tat": TitForTat,
        }
        snapshots = run_evolution(pops, factories, generations=5, rounds_per_match=5)
        for snap in snapshots:
            assert isinstance(snap, EvolutionSnapshot)
            assert isinstance(snap.generation, int)
            assert isinstance(snap.populations, dict)


# ======================================================================
# Head-to-Head
# ======================================================================


class TestHeadToHead:
    def test_returns_round_details(self):
        result = head_to_head(TitForTat(), AlwaysDefect(), rounds=5)
        assert len(result["round_details"]) == 5
        assert result["round_details"][0]["round"] == 1

    def test_cumulative_scores(self):
        result = head_to_head(AlwaysCooperate(), AlwaysCooperate(), rounds=5)
        assert result["cumulative_a"][-1] == R * 5
        assert result["cumulative_b"][-1] == R * 5

    def test_match_result_included(self):
        result = head_to_head(TitForTat(), GrimTrigger(), rounds=10)
        assert isinstance(result["result"], MatchResult)
