"""Tagged mixin — inert semantic annotations for GDS objects.

Tags are a minimal ``dict[str, str]`` on spec-layer objects. They carry no
semantics within gds-framework — they exist solely for downstream consumers
(visualization, documentation, domain packages).

Tags are stripped at compile time: ``SystemIR`` / ``BlockIR`` have no tags
field. Verification checks never read tags. Composition operators ignore them.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field


class Tagged(BaseModel):
    """Mixin providing inert semantic tags.

    Tags never affect compilation, verification, or composition.
    They are stripped at compile time and do not appear in SystemIR.
    """

    tags: dict[str, str] = Field(default_factory=dict)

    def with_tag(self, key: str, value: str) -> Self:
        """Return new instance with added tag."""
        new_tags = dict(self.tags)
        new_tags[key] = value
        return self.model_copy(update={"tags": new_tags})

    def with_tags(self, **tags: str) -> Self:
        """Return new instance with multiple tags added."""
        new_tags = dict(self.tags)
        new_tags.update(tags)
        return self.model_copy(update={"tags": new_tags})

    def has_tag(self, key: str, value: str | None = None) -> bool:
        """Check if tag exists (and optionally has specific value)."""
        if key not in self.tags:
            return False
        if value is not None:
            return self.tags[key] == value
        return True

    def get_tag(self, key: str, default: str | None = None) -> str | None:
        """Get tag value or default."""
        return self.tags.get(key, default)
