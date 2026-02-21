"""Entity and state variable models.

In GDS terms, the full state space X is the product of all entity states:
    X = Entity_1.state x Entity_2.state x ... x Entity_n.state

Entities correspond to actors, resources, registries — anything that
persists across timesteps and has mutable state.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gds.tagged import Tagged
from gds.types.typedef import TypeDef  # noqa: TC001


class StateVariable(BaseModel):
    """A single typed variable within an entity's state.

    Each variable has a TypeDef (with runtime constraints),
    a human-readable description, and an optional math symbol.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    typedef: TypeDef
    description: str = ""
    symbol: str = ""

    def check_value(self, value: Any) -> bool:
        """Check if a value satisfies this variable's type definition."""
        return self.typedef.check_value(value)


class Entity(Tagged):
    """A named component of the system state.

    In GDS terms, the full state space X is the product of all entity
    state spaces. Entities correspond to actors, resources, registries —
    anything that persists across timesteps.
    """

    name: str
    variables: dict[str, StateVariable] = Field(default_factory=dict)
    description: str = ""
    model_config = ConfigDict(frozen=True)

    def validate_state(self, data: dict[str, Any]) -> list[str]:
        """Validate a state snapshot for this entity.

        Returns a list of error strings (empty means valid).
        """
        errors: list[str] = []
        for vname, var in self.variables.items():
            if vname not in data:
                errors.append(f"{self.name}.{vname}: missing")
            elif not var.check_value(data[vname]):
                errors.append(f"{self.name}.{vname}: type/constraint violation")
        return errors
