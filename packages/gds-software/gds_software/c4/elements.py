"""C4 model element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
"""

from pydantic import BaseModel, Field


class Person(BaseModel, frozen=True):
    """A person that interacts with the system.

    Maps to: GDS BoundaryAction (exogenous input).
    """

    name: str
    description: str = ""


class ExternalSystem(BaseModel, frozen=True):
    """An external system that the system interacts with.

    Maps to: GDS BoundaryAction (exogenous input).
    """

    name: str
    description: str = ""


class Container(BaseModel, frozen=True):
    """A deployable unit (API, database, web app, etc).

    Maps to: GDS Policy (if stateless) or Mechanism (if stateful/database).
    """

    name: str
    technology: str = ""
    stateful: bool = False
    description: str = ""


class C4Component(BaseModel, frozen=True):
    """A component within a container.

    Maps to: GDS Policy or Mechanism based on stateful flag.
    """

    name: str
    container: str = Field(description="Parent container name")
    technology: str = ""
    stateful: bool = False
    description: str = ""


class C4Relationship(BaseModel, frozen=True):
    """A directed relationship between C4 elements.

    Maps to: GDS Wiring.
    """

    name: str
    source: str
    target: str
    technology: str = ""
    description: str = ""
