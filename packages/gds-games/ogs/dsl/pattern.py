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

    def specialize(
        self,
        name: str,
        terminal_conditions: list[TerminalCondition] | None = None,
        action_spaces: list[ActionSpace] | None = None,
        initializations: list[StateInitialization] | None = None,
        inputs: list[PatternInput] | None = None,
        composition_type: CompositionType | None = None,
        source: str | None = None,
    ) -> Pattern:
        """Create a derived pattern that inherits this pattern's game tree.

        Produces a new ``Pattern`` with the same ``game`` composition tree,
        overriding only the fields explicitly provided.  ``inputs`` are
        inherited from the base pattern unless a replacement list is supplied,
        preventing the input-drift problem where derived patterns silently fall
        out of sync with their base.

        Args:
            name: Required name for the derived pattern.
            terminal_conditions: Domain-specific terminal conditions.  Replaces
                the base value if provided; otherwise inherits.
            action_spaces: Domain-specific action spaces.  Replaces the base
                value if provided; otherwise inherits.
            initializations: Domain-specific state initializations.  Replaces
                the base value if provided; otherwise inherits.
            inputs: If provided, replaces the inherited ``PatternInput`` list
                entirely.  If omitted, a copy of the base pattern's inputs is
                used.
            composition_type: Override the composition type.  Defaults to the
                base pattern's ``composition_type``.
            source: Override the provenance tag.  Defaults to the base
                pattern's ``source``.

        Returns:
            A new ``Pattern`` instance.  The ``game`` object is shared (not
            deep-copied) — modifications to the game tree after calling
            ``specialize()`` will affect both patterns.

        Example::

            from patterns.multi_party_agreement_zoomed_in import pattern as base

            resource_exchange = base.specialize(
                name="Multi-Party Resource Exchange",
                terminal_conditions=[
                    TerminalCondition(name="Agreement", actions={...}, outcome="..."),
                ],
                action_spaces=[
                    ActionSpace(game="Agent 1 Reactive Decision", actions=["accept", "reject"]),
                ],
                # inputs inherited from base automatically
            )
        """
        return Pattern(
            name=name,
            game=self.game,
            inputs=list(inputs) if inputs is not None else list(self.inputs),
            composition_type=composition_type
            if composition_type is not None
            else self.composition_type,
            terminal_conditions=terminal_conditions
            if terminal_conditions is not None
            else self.terminal_conditions,
            action_spaces=action_spaces
            if action_spaces is not None
            else self.action_spaces,
            initializations=initializations
            if initializations is not None
            else self.initializations,
            source=source if source is not None else self.source,
        )
