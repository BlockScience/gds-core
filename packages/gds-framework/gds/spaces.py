"""Typed product spaces — the shapes of signals flowing between blocks.

A Space defines a named collection of typed fields. In GDS terms, these are
the action spaces / signal spaces. Unlike MSML's Space (which has a schema
that's never validated), this Space actually checks data against its type
definitions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gds.types.typedef import TypeDef  # noqa: TC001


class Space(BaseModel):
    """A typed product space — defines the shape of data flowing between blocks.

    Each field in the schema maps a name to a TypeDef. ``validate_data()`` checks
    a data dict against the schema, returning a list of error strings.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    fields: dict[str, TypeDef] = Field(default_factory=dict)
    description: str = ""

    def validate_data(self, data: dict[str, Any]) -> list[str]:
        """Validate a data dict against this space's field schema.

        Returns a list of error strings (empty means valid).
        """
        errors: list[str] = []
        for field_name, typedef in self.fields.items():
            if field_name not in data:
                errors.append(f"Missing field: {field_name}")
            elif not typedef.check_value(data[field_name]):
                errors.append(
                    f"{field_name}: expected {typedef.name}, "
                    f"got {type(data[field_name]).__name__} "
                    f"with value {data[field_name]!r}"
                )
        extra_fields = set(data.keys()) - set(self.fields.keys())
        if extra_fields:
            errors.append(f"Unexpected fields: {extra_fields}")
        return errors

    def is_compatible(self, other: Space) -> bool:
        """Check if another space has the same structure (field names and types)."""
        if set(self.fields.keys()) != set(other.fields.keys()):
            return False
        return all(self.fields[k] == other.fields[k] for k in self.fields)


# ── Sentinel spaces ────────────────────────────────────────

EMPTY = Space(name="empty", description="No data flows through this port")
TERMINAL = Space(name="terminal", description="Signal terminates here (state write)")
