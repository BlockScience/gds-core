"""C4Model — declarative container for C4 architecture models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.c4.elements import (
    C4Component,
    C4Relationship,
    Container,
    ExternalSystem,
    Person,
)
from gds_software.common.errors import SWValidationError

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class C4Model(BaseModel):
    """A complete C4 architecture model declaration.

    Validates at construction:
    1. No duplicate element names
    2. Relationship source/target reference declared elements
    3. Component containers reference declared containers
    """

    name: str
    persons: list[Person] = Field(default_factory=list)
    external_systems: list[ExternalSystem] = Field(default_factory=list)
    containers: list[Container] = Field(default_factory=list)
    components: list[C4Component] = Field(default_factory=list)
    relationships: list[C4Relationship] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. No duplicate names
        all_names: list[str] = []
        for p in self.persons:
            all_names.append(p.name)
        for e in self.external_systems:
            all_names.append(e.name)
        for c in self.containers:
            all_names.append(c.name)
        for c in self.components:
            all_names.append(c.name)

        seen: set[str] = set()
        for n in all_names:
            if n in seen:
                errors.append(f"Duplicate element name: {n!r}")
            seen.add(n)

        all_element_names = set(all_names)
        container_names = {c.name for c in self.containers}

        # 2. Relationship source/target reference declared elements
        for rel in self.relationships:
            if rel.source not in all_element_names:
                errors.append(
                    f"Relationship {rel.name!r} source {rel.source!r} "
                    f"is not a declared element"
                )
            if rel.target not in all_element_names:
                errors.append(
                    f"Relationship {rel.name!r} target {rel.target!r} "
                    f"is not a declared element"
                )

        # 3. Component containers reference declared containers
        for comp in self.components:
            if comp.container not in container_names:
                errors.append(
                    f"Component {comp.name!r} container {comp.container!r} "
                    f"is not a declared container"
                )

        if errors:
            raise SWValidationError(
                f"C4Model {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def element_names(self) -> set[str]:
        names: set[str] = set()
        for p in self.persons:
            names.add(p.name)
        for e in self.external_systems:
            names.add(e.name)
        for c in self.containers:
            names.add(c.name)
        for c in self.components:
            names.add(c.name)
        return names

    @property
    def person_names(self) -> set[str]:
        return {p.name for p in self.persons}

    @property
    def external_system_names(self) -> set[str]:
        return {e.name for e in self.external_systems}

    @property
    def container_names(self) -> set[str]:
        return {c.name for c in self.containers}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        from gds_software.c4.compile import compile_c4

        return compile_c4(self)

    def compile_system(self) -> SystemIR:
        from gds_software.c4.compile import compile_c4_to_system

        return compile_c4_to_system(self)
