"""Pattern metadata models — terminal conditions, action spaces, and the
top-level Pattern that wraps a game tree with external metadata.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ogs.dsl.base import OpenGame
from ogs.dsl.types import CompositionType, InputType


class PatternInput(BaseModel):
    """An external input that crosses the pattern boundary.

    Links to a target game via ``target_game`` and ``flow_label``
    so the compiler can generate input→game flows automatically.
    """

    name: str
    input_type: InputType
    schema_hint: str = ""
    target_game: str = ""
    flow_label: str = ""


class TerminalCondition(BaseModel):
    """A condition under which a corecursive loop should terminate.

    Each terminal condition specifies a combination of actions from
    named games (or agents) that triggers termination, along with the
    resulting outcome and optional payoff description.
    """

    name: str
    actions: dict[str, str]
    outcome: str
    description: str = ""
    payoff_description: str = ""


class ActionSpace(BaseModel):
    """The set of available actions for a decision game, with optional constraints."""

    game: str
    actions: list[str]
    constraints: list[str] = Field(default_factory=list)


class StateInitialization(BaseModel):
    """An initial state variable for simulation in mathematical notation."""

    symbol: str
    space: str
    description: str = ""
    game: str = ""


class Pattern(BaseModel):
    """A complete named composite pattern — the top-level specification unit."""

    name: str
    game: OpenGame
    inputs: list[PatternInput] = []
    composition_type: CompositionType = CompositionType.FEEDBACK
    terminal_conditions: list[TerminalCondition] | None = None
    action_spaces: list[ActionSpace] | None = None
    initializations: list[StateInitialization] | None = None
    source: str = "dsl"
