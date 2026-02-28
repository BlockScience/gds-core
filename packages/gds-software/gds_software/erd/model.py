"""ERDModel — declarative container for entity-relationship diagrams."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.common.errors import SWValidationError
from gds_software.erd.elements import ERDEntity, ERDRelationship

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class ERDModel(BaseModel):
    """A complete entity-relationship diagram declaration.

    Validates at construction:
    1. At least one entity
    2. No duplicate entity names
    3. Relationship source/target reference declared entities
    4. No duplicate attribute names within an entity
    """

    name: str
    entities: list[ERDEntity]
    relationships: list[ERDRelationship] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one entity
        if not self.entities:
            errors.append("ERD must have at least one entity")

        # 2. No duplicate entity names
        names: list[str] = [e.name for e in self.entities]
        seen: set[str] = set()
        for n in names:
            if n in seen:
                errors.append(f"Duplicate entity name: {n!r}")
            seen.add(n)

        entity_names = set(names)

        # 3. Relationship source/target
        for rel in self.relationships:
            if rel.source not in entity_names:
                errors.append(
                    f"Relationship {rel.name!r} source {rel.source!r} "
                    f"is not a declared entity"
                )
            if rel.target not in entity_names:
                errors.append(
                    f"Relationship {rel.name!r} target {rel.target!r} "
                    f"is not a declared entity"
                )

        # 4. No duplicate attribute names within an entity
        for entity in self.entities:
            attr_seen: set[str] = set()
            for attr in entity.attributes:
                if attr.name in attr_seen:
                    errors.append(
                        f"Entity {entity.name!r} has duplicate attribute {attr.name!r}"
                    )
                attr_seen.add(attr.name)

        if errors:
            raise SWValidationError(
                f"ERDModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def entity_names(self) -> set[str]:
        return {e.name for e in self.entities}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        from gds_software.erd.compile import compile_erd

        return compile_erd(self)

    def compile_system(self) -> SystemIR:
        from gds_software.erd.compile import compile_erd_to_system

        return compile_erd_to_system(self)
