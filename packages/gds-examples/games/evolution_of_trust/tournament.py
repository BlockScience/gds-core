"""Tournament and evolutionary dynamics for the iterated Prisoner's Dilemma.

Provides:
    - play_match: Run a single iterated match between two strategies
    - play_round_robin: All-pairs tournament with scoring
    - run_evolution: Evolutionary dynamics — population shifts over generations
    - head_to_head: Detailed analysis of two strategies facing off
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from evolution_of_trust.model import get_payoff
from evolution_of_trust.strategies import COOPERATE, DEFECT, Strategy


@dataclass(frozen=True)
class MatchResult:
    """Result of an iterated match between two strategies."""

    strategy_a: str
    strategy_b: str
    score_a: int
    score_b: int
    rounds: int
    history: list[tuple[str, str]]  # (action_a, action_b) per round


@dataclass(frozen=True)
class TournamentResult:
    """Result of a round-robin tournament."""

    scores: dict[str, int]  # total score per strategy
    matches: list[MatchResult]
    rounds_per_match: int

    @property
    def avg_scores(self) -> dict[str, float]:
        """Average score per match for each strategy."""
        match_counts: dict[str, int] = {}
        for m in self.matches:
            match_counts[m.strategy_a] = match_counts.get(m.strategy_a, 0) + 1
            match_counts[m.strategy_b] = match_counts.get(m.strategy_b, 0) + 1
        return {
            name: score / match_counts[name]
            for name, score in self.scores.items()
            if match_counts.get(name, 0) > 0
        }


@dataclass(frozen=True)
class EvolutionSnapshot:
    """Population state at a given generation."""

    generation: int
    populations: dict[str, int]  # strategy name -> population count
    avg_scores: dict[str, float]  # from that generation's tournament


def play_match(
    a: Strategy,
    b: Strategy,
    rounds: int = 10,
    noise: float = 0.0,
    rng: random.Random | None = None,
) -> MatchResult:
    """Play an iterated match between two strategies.

    Args:
        a: First strategy instance.
        b: Second strategy instance.
        rounds: Number of rounds to play.
        noise: Probability of an action being flipped (trembling hand).
        rng: Random number generator for noise.

    Returns:
        MatchResult with scores and full history.
    """
    if rng is None:
        rng = random.Random()

    a.reset()
    b.reset()

    history_a: list[tuple[str, str]] = []
    history_b: list[tuple[str, str]] = []
    match_history: list[tuple[str, str]] = []
    score_a = 0
    score_b = 0

    for round_num in range(rounds):
        action_a = a.choose(history_a, round_num)
        action_b = b.choose(history_b, round_num)

        # Apply noise
        if noise > 0:
            if rng.random() < noise:
                action_a = DEFECT if action_a == COOPERATE else COOPERATE
            if rng.random() < noise:
                action_b = DEFECT if action_b == COOPERATE else COOPERATE

        payoff_a, payoff_b = get_payoff(action_a, action_b)
        score_a += payoff_a
        score_b += payoff_b

        history_a.append((action_a, action_b))
        history_b.append((action_b, action_a))
        match_history.append((action_a, action_b))

    return MatchResult(
        strategy_a=a.name,
        strategy_b=b.name,
        score_a=score_a,
        score_b=score_b,
        rounds=rounds,
        history=match_history,
    )


def play_round_robin(
    strategies: list[Strategy],
    rounds_per_match: int = 10,
    noise: float = 0.0,
    rng: random.Random | None = None,
) -> TournamentResult:
    """Play a round-robin tournament among all strategies.

    Includes self-play (each strategy plays against a fresh copy of itself).

    Args:
        strategies: List of strategy instances.
        rounds_per_match: Rounds per match.
        noise: Noise probability.
        rng: Random number generator.

    Returns:
        TournamentResult with aggregate scores.
    """
    if rng is None:
        rng = random.Random()

    scores: dict[str, int] = {s.name: 0 for s in strategies}
    matches: list[MatchResult] = []

    for i, a in enumerate(strategies):
        for b in strategies[i:]:
            result = play_match(a, b, rounds_per_match, noise, rng)
            matches.append(result)
            scores[result.strategy_a] += result.score_a
            scores[result.strategy_b] += result.score_b

    return TournamentResult(
        scores=scores,
        matches=matches,
        rounds_per_match=rounds_per_match,
    )


def run_evolution(
    initial_populations: dict[str, int],
    strategy_factories: dict[str, type],
    generations: int = 20,
    rounds_per_match: int = 10,
    noise: float = 0.0,
    seed: int = 42,
) -> list[EvolutionSnapshot]:
    """Run evolutionary dynamics over multiple generations.

    Each generation:
    1. Play a round-robin tournament among all living strategies
    2. Bottom performer loses one member; top performer gains one
    3. Extinct strategies are removed

    Args:
        initial_populations: Strategy name -> starting population count.
        strategy_factories: Strategy name -> class (for instantiation).
        generations: Number of generations to simulate.
        rounds_per_match: Rounds per match.
        noise: Noise probability.
        seed: Random seed.

    Returns:
        List of EvolutionSnapshot, one per generation (including gen 0).
    """
    rng = random.Random(seed)
    populations = dict(initial_populations)
    total_pop = sum(populations.values())

    snapshots: list[EvolutionSnapshot] = [
        EvolutionSnapshot(
            generation=0,
            populations=dict(populations),
            avg_scores={name: 0.0 for name in populations},
        )
    ]

    for gen in range(1, generations + 1):
        # Build strategy instances weighted by population
        living = {name: count for name, count in populations.items() if count > 0}
        if len(living) <= 1:
            snapshots.append(
                EvolutionSnapshot(
                    generation=gen,
                    populations=dict(populations),
                    avg_scores={name: 0.0 for name in populations},
                )
            )
            continue

        # Create one instance per strategy type for the tournament
        instances = []
        for name in living:
            instances.append(strategy_factories[name]())

        tournament = play_round_robin(instances, rounds_per_match, noise, rng)

        # Weight scores by population for evolutionary pressure
        weighted_avg: dict[str, float] = {}
        for name in living:
            avg = tournament.avg_scores.get(name, 0.0)
            weighted_avg[name] = avg

        # Find worst and best performers
        sorted_strats = sorted(weighted_avg.items(), key=lambda x: x[1])
        worst_name = sorted_strats[0][0]
        best_name = sorted_strats[-1][0]

        # Transfer one unit from worst to best
        if populations[worst_name] > 0:
            populations[worst_name] -= 1
            populations[best_name] = populations.get(best_name, 0) + 1

        # Ensure total population is preserved
        assert sum(populations.values()) == total_pop

        snapshots.append(
            EvolutionSnapshot(
                generation=gen,
                populations=dict(populations),
                avg_scores=weighted_avg,
            )
        )

    return snapshots


def head_to_head(
    a: Strategy,
    b: Strategy,
    rounds: int = 10,
    noise: float = 0.0,
    seed: int = 42,
) -> dict:
    """Detailed head-to-head analysis of two strategies.

    Returns:
        Dict with match result, round-by-round breakdown, and cumulative scores.
    """
    rng = random.Random(seed)
    result = play_match(a, b, rounds, noise, rng)

    cumulative_a: list[int] = []
    cumulative_b: list[int] = []
    running_a = 0
    running_b = 0

    round_details: list[dict] = []
    for i, (act_a, act_b) in enumerate(result.history):
        pay_a, pay_b = get_payoff(act_a, act_b)
        running_a += pay_a
        running_b += pay_b
        cumulative_a.append(running_a)
        cumulative_b.append(running_b)
        round_details.append(
            {
                "round": i + 1,
                "action_a": act_a,
                "action_b": act_b,
                "payoff_a": pay_a,
                "payoff_b": pay_b,
                "cumulative_a": running_a,
                "cumulative_b": running_b,
            }
        )

    return {
        "result": result,
        "round_details": round_details,
        "cumulative_a": cumulative_a,
        "cumulative_b": cumulative_b,
    }
