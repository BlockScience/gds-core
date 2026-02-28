"""ERD element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class Cardinality(StrEnum):
    """Relationship cardinality."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class Attribute(BaseModel, frozen=True):
    """An attribute of an ERD entity.

    Maps to: GDS StateVariable within an Entity.
    """

    name: str
    type: str = "string"
    is_primary_key: bool = False
    is_nullable: bool = True
    description: str = ""


class ERDEntity(BaseModel, frozen=True):
    """An entity in an ER diagram.

    Maps to: GDS Entity with StateVariables for each attribute.
    """

    name: str
    attributes: list[Attribute] = Field(default_factory=list)
    description: str = ""


class ERDRelationship(BaseModel, frozen=True):
    """A relationship between ERD entities.

    Maps to: GDS Mechanism + SpecWiring (cross-entity updates).
    """

    name: str
    source: str
    target: str
    cardinality: Cardinality = Cardinality.ONE_TO_MANY
    description: str = ""
