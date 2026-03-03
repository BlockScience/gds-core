"""Strategy implementations for the iterated Prisoner's Dilemma.

Eight strategies inspired by Nicky Case's "The Evolution of Trust":
    - AlwaysCooperate (Always Cooperate)
    - AlwaysDefect (Always Cheat)
    - TitForTat (Copycat)
    - GrimTrigger (Grudger)
    - Detective (Detective)
    - TitForTwoTats (Copykitten)
    - Pavlov (Simpleton)
    - RandomStrategy (Random)

Each strategy implements a common Protocol: choose(history, round_num) -> action.
"""

from __future__ import annotations

import random
from typing import ClassVar, Protocol, runtime_checkable

COOPERATE = "Cooperate"
DEFECT = "Defect"


@runtime_checkable
class Strategy(Protocol):
    """Protocol for iterated PD strategies."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        """Choose an action given the history of (my_action, opponent_action) pairs."""
        ...

    def reset(self) -> None:
        """Reset internal state for a new match."""
        ...


class AlwaysCooperate:
    """Always cooperates regardless of opponent's actions."""

    name = "Always Cooperate"
    description = "Always plays Cooperate. Naive but maximizes mutual benefit."

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        return COOPERATE

    def reset(self) -> None:
        pass


class AlwaysDefect:
    """Always defects regardless of opponent's actions."""

    name = "Always Defect"
    description = (
        "Always plays Defect. Exploits cooperators "
        "but earns nothing from other defectors."
    )

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        return DEFECT

    def reset(self) -> None:
        pass


class TitForTat:
    """Cooperate first, then copy opponent's last move.

    Nicky Case name: Copycat.
    """

    name = "Tit for Tat"
    description = (
        "Cooperates first, then copies opponent's last move. "
        "Simple, forgiving, retaliatory."
    )

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        if not history:
            return COOPERATE
        return history[-1][1]  # opponent's last action

    def reset(self) -> None:
        pass


class GrimTrigger:
    """Cooperate until opponent defects once, then defect forever.

    Nicky Case name: Grudger.
    """

    name = "Grim Trigger"
    description = (
        "Cooperates until opponent defects once, then defects forever. Unforgiving."
    )

    def __init__(self) -> None:
        self._triggered = False

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        if self._triggered:
            return DEFECT
        if history and history[-1][1] == DEFECT:
            self._triggered = True
            return DEFECT
        return COOPERATE

    def reset(self) -> None:
        self._triggered = False


class Detective:
    """Plays C, D, C, C to probe; then Always Defect or Tit-for-Tat.

    If opponent never defected during the probe (rounds 0-3), switches to
    Always Defect (exploiting a cooperator). Otherwise, plays Tit-for-Tat.

    Nicky Case name: Detective.
    """

    name = "Detective"
    description = (
        "Probes with C,D,C,C. If opponent never retaliates, exploits with "
        "Always Defect. Otherwise, falls back to Tit-for-Tat."
    )

    _probe_sequence: ClassVar[list[str]] = [
        COOPERATE,
        DEFECT,
        COOPERATE,
        COOPERATE,
    ]

    def __init__(self) -> None:
        self._exploit = False

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        if round_num < 4:
            return self._probe_sequence[round_num]

        # After probe phase: check if opponent ever defected in rounds 0-3
        if round_num == 4:
            opponent_defected = any(h[1] == DEFECT for h in history[:4])
            self._exploit = not opponent_defected

        if self._exploit:
            return DEFECT
        # Tit-for-Tat fallback
        return history[-1][1] if history else COOPERATE

    def reset(self) -> None:
        self._exploit = False


class TitForTwoTats:
    """Cooperate unless opponent defected in both of the last two rounds.

    More forgiving than Tit-for-Tat — tolerates a single defection.

    Nicky Case name: Copykitten.
    """

    name = "Tit for Two Tats"
    description = (
        "Cooperates unless opponent defected in both of the last 2 rounds. "
        "More forgiving than Tit-for-Tat."
    )

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        if len(history) < 2:
            return COOPERATE
        if history[-1][1] == DEFECT and history[-2][1] == DEFECT:
            return DEFECT
        return COOPERATE

    def reset(self) -> None:
        pass


class Pavlov:
    """Win-stay, lose-shift.

    Cooperates first. If last round was a "win" (CC or DD outcome gave
    a non-negative payoff for Pavlov relative to expectation), repeat;
    otherwise switch. Simplified: repeat if both played the same action
    last round, switch if they differed.

    Nicky Case name: Simpleton.
    """

    name = "Pavlov"
    description = (
        "Win-stay, lose-shift. Repeats last action if both played the same; "
        "switches if they differed."
    )

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        if not history:
            return COOPERATE
        my_last, opp_last = history[-1]
        if my_last == opp_last:
            return my_last  # stay
        # shift
        return DEFECT if my_last == COOPERATE else COOPERATE

    def reset(self) -> None:
        pass


class RandomStrategy:
    """Randomly cooperates or defects with equal probability.

    Uses a seeded RNG for reproducibility.

    Nicky Case name: Random.
    """

    name = "Random"
    description = "Cooperates or defects with 50/50 probability."

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    def choose(self, history: list[tuple[str, str]], round_num: int) -> str:
        return COOPERATE if self._rng.random() < 0.5 else DEFECT

    def reset(self) -> None:
        self._rng = random.Random(self._seed)


ALL_STRATEGIES: list[type] = [
    AlwaysCooperate,
    AlwaysDefect,
    TitForTat,
    GrimTrigger,
    Detective,
    TitForTwoTats,
    Pavlov,
    RandomStrategy,
]
