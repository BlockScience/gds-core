"""State machine element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class State(BaseModel, frozen=True):
    """A state in a state machine.

    Maps to: GDS Entity (state X) + StateVariable.
    """

    name: str
    is_initial: bool = False
    is_final: bool = False
    description: str = ""


class Guard(BaseModel, frozen=True):
    """A boolean condition on a transition.

    Guards are evaluated at transition time — they restrict when
    a transition may fire.
    """

    condition: str
    description: str = ""


class Transition(BaseModel, frozen=True):
    """A directed transition between states.

    Maps to: GDS Policy (guard evaluation) + Mechanism (state update).
    """

    name: str
    source: str
    target: str
    event: str
    guard: Guard | None = None
    action: str = ""


class Event(BaseModel, frozen=True):
    """An external or internal event that triggers transitions.

    Maps to: GDS BoundaryAction (exogenous input U).
    """

    name: str
    description: str = ""


class Region(BaseModel, frozen=True):
    """An orthogonal region in a hierarchical state machine.

    Maps to: GDS ParallelComposition — regions execute concurrently.
    """

    name: str
    states: list[str] = Field(default_factory=list)
    description: str = ""
