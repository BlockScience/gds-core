"""ComponentModel — declarative container for UML component diagrams.

Users declare components with interfaces and connectors between them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.common.errors import SWValidationError
from gds_software.component.elements import Component, Connector, InterfaceDef

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class ComponentModel(BaseModel):
    """A complete component diagram declaration.

    Validates at construction:
    1. At least one component
    2. No duplicate component names
    3. Connector source/target reference declared components
    4. Connector interfaces reference declared interfaces on their components
    """

    name: str
    components: list[Component]
    interfaces: list[InterfaceDef] = Field(default_factory=list)
    connectors: list[Connector] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one component
        if not self.components:
            errors.append("Component diagram must have at least one component")

        # 2. No duplicate names
        names: list[str] = [c.name for c in self.components]
        seen: set[str] = set()
        for n in names:
            if n in seen:
                errors.append(f"Duplicate component name: {n!r}")
            seen.add(n)

        comp_names = set(names)
        comp_map = {c.name: c for c in self.components}

        # 3 & 4. Connector validation
        for conn in self.connectors:
            if conn.source not in comp_names:
                errors.append(
                    f"Connector {conn.name!r} source {conn.source!r} "
                    f"is not a declared component"
                )
            elif conn.source_interface not in comp_map[conn.source].provides:
                errors.append(
                    f"Connector {conn.name!r} source interface "
                    f"{conn.source_interface!r} is not provided by {conn.source!r}"
                )

            if conn.target not in comp_names:
                errors.append(
                    f"Connector {conn.name!r} target {conn.target!r} "
                    f"is not a declared component"
                )
            elif conn.target_interface not in comp_map[conn.target].requires:
                errors.append(
                    f"Connector {conn.name!r} target interface "
                    f"{conn.target_interface!r} is not required by {conn.target!r}"
                )

        if errors:
            raise SWValidationError(
                f"ComponentModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def component_names(self) -> set[str]:
        return {c.name for c in self.components}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        from gds_software.component.compile import compile_component

        return compile_component(self)

    def compile_system(self) -> SystemIR:
        from gds_software.component.compile import compile_component_to_system

        return compile_component_to_system(self)
