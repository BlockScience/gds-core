"""Runtime-constrained type definitions.

TypeDef is the atom of the GDS type system — a named type with optional
runtime constraints. Unlike MSML's Type class (which is just a label),
TypeDef carries actual validation logic.
"""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ConstraintKind = Literal[
    "non_negative",  # x >= 0
    "positive",  # x > 0
    "probability",  # 0 <= x <= 1
    "bounded",  # low <= x <= high (needs constraint_bounds)
    "enum",  # x in {...} (needs constraint_values)
]


class TypeDef(BaseModel):
    """A named, constrained type used in spaces and state.

    Each TypeDef wraps a Python type with an optional constraint predicate.
    ``check_value()`` checks both the Python type and the constraint at runtime.

    The optional ``constraint_kind`` field enables lossless round-tripping of
    common constraint patterns through OWL/SHACL export.  When set, the
    OWL exporter emits SHACL property shapes instead of an opaque
    ``hasConstraint: true`` boolean, promoting the constraint from R3 (lossy)
    to R2 (structurally representable).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    python_type: type
    description: str = ""
    constraint: Callable[[Any], bool] | None = None
    units: str | None = None
    constraint_kind: ConstraintKind | None = None
    constraint_bounds: tuple[float, float] | None = None
    constraint_values: tuple[Any, ...] | None = None

    def check_value(self, value: Any) -> bool:
        """Check if a value satisfies this type definition."""
        if not isinstance(value, self.python_type):
            return False
        if self.constraint is None:
            return True
        try:
            return bool(self.constraint(value))
        except Exception:
            return False


# ── Built-in types ──────────────────────────────────────────

Probability = TypeDef(
    name="Probability",
    python_type=float,
    constraint=lambda x: 0.0 <= x <= 1.0,
    description="A value in [0, 1]",
    constraint_kind="probability",
)

NonNegativeFloat = TypeDef(
    name="NonNegativeFloat",
    python_type=float,
    constraint=lambda x: x >= 0,
    constraint_kind="non_negative",
)

PositiveInt = TypeDef(
    name="PositiveInt",
    python_type=int,
    constraint=lambda x: x > 0,
    constraint_kind="positive",
)

TokenAmount = TypeDef(
    name="TokenAmount",
    python_type=float,
    constraint=lambda x: x >= 0,
    units="tokens",
    constraint_kind="non_negative",
)

AgentID = TypeDef(name="AgentID", python_type=str)

Timestamp = TypeDef(
    name="Timestamp",
    python_type=float,
    constraint=lambda x: x >= 0,
    units="seconds",
    constraint_kind="non_negative",
)
