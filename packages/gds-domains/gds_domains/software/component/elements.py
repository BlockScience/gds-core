"""Component diagram element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class InterfaceDef(BaseModel, frozen=True):
    """A named interface that a component provides or requires.

    Interfaces define the contract between components.
    """

    name: str
    description: str = ""


class Component(BaseModel, frozen=True):
    """A software component with provided and required interfaces.

    Maps to: GDS Policy (if stateless) or Mechanism (if stateful).
    """

    name: str
    provides: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    stateful: bool = False
    description: str = ""


class Connector(BaseModel, frozen=True):
    """A connector between component interfaces.

    Maps to: GDS Wiring.
    Connects a provided interface to a required interface.
    """

    name: str
    source: str
    source_interface: str
    target: str
    target_interface: str
