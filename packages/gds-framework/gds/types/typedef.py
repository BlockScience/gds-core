"""Runtime-constrained type definitions.

TypeDef is the atom of the GDS type system — a named type with optional
runtime constraints. Unlike MSML's Type class (which is just a label),
TypeDef carries actual validation logic.
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict


class TypeDef(BaseModel):
    """A named, constrained type used in spaces and state.

    Each TypeDef wraps a Python type with an optional constraint predicate.
    ``check_value()`` checks both the Python type and the constraint at runtime.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    python_type: type
    description: str = ""
    constraint: Callable[[Any], bool] | None = None
    units: str | None = None

    def check_value(self, value: Any) -> bool:
        """Check if a value satisfies this type definition."""
        if not isinstance(value, self.python_type):
            return False
        return self.constraint is None or self.constraint(value)


# ── Built-in types ──────────────────────────────────────────

Probability = TypeDef(
    name="Probability",
    python_type=float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="A value in [0, 1]",
)

NonNegativeFloat = TypeDef(
    name="NonNegativeFloat",
    python_type=float,
    constraint=lambda x: x >= 0,
)

PositiveInt = TypeDef(
    name="PositiveInt",
    python_type=int,
    constraint=lambda x: x > 0,
)

TokenAmount = TypeDef(
    name="TokenAmount",
    python_type=float,
    constraint=lambda x: x >= 0,
    units="tokens",
)

AgentID = TypeDef(name="AgentID", python_type=str)

Timestamp = TypeDef(
    name="Timestamp",
    python_type=float,
    constraint=lambda x: x >= 0,
    units="seconds",
)
