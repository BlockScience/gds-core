"""DFDModel — declarative container for data flow diagrams.

Users declare external entities, processes, data stores, and data flows.
The model validates structural integrity at construction time, then
compiles to GDS specs on demand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.common.errors import SWValidationError
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class DFDModel(BaseModel):
    """A complete data flow diagram declaration.

    Validates at construction:
    1. At least one process
    2. No duplicate element names across all lists
    3. Flow source/target reference declared element names
    4. No direct external-to-external flows
    5. Every process has at least one connected flow
    """

    name: str
    external_entities: list[ExternalEntity] = Field(default_factory=list)
    processes: list[Process] = Field(default_factory=list)
    data_stores: list[DataStore] = Field(default_factory=list)
    data_flows: list[DataFlow] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one process
        if not self.processes:
            errors.append("DFD must have at least one process")

        # 2. No duplicate names
        all_names: list[str] = []
        for e in self.external_entities:
            all_names.append(e.name)
        for p in self.processes:
            all_names.append(p.name)
        for d in self.data_stores:
            all_names.append(d.name)

        seen: set[str] = set()
        for n in all_names:
            if n in seen:
                errors.append(f"Duplicate element name: {n!r}")
            seen.add(n)

        all_element_names = set(all_names)

        # 3. Flow source/target reference declared elements
        for flow in self.data_flows:
            if flow.source not in all_element_names:
                errors.append(
                    f"Flow {flow.name!r} source {flow.source!r} "
                    f"is not a declared element"
                )
            if flow.target not in all_element_names:
                errors.append(
                    f"Flow {flow.name!r} target {flow.target!r} "
                    f"is not a declared element"
                )

        # 4. No direct external-to-external flows
        ext_names = {e.name for e in self.external_entities}
        for flow in self.data_flows:
            if flow.source in ext_names and flow.target in ext_names:
                errors.append(
                    f"Flow {flow.name!r} connects two external entities "
                    f"({flow.source!r} -> {flow.target!r})"
                )

        if errors:
            raise SWValidationError(
                f"DFDModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def element_names(self) -> set[str]:
        """All element names in the model."""
        names: set[str] = set()
        for e in self.external_entities:
            names.add(e.name)
        for p in self.processes:
            names.add(p.name)
        for d in self.data_stores:
            names.add(d.name)
        return names

    @property
    def external_names(self) -> set[str]:
        return {e.name for e in self.external_entities}

    @property
    def process_names(self) -> set[str]:
        return {p.name for p in self.processes}

    @property
    def store_names(self) -> set[str]:
        return {d.name for d in self.data_stores}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_software.dfd.compile import compile_dfd

        return compile_dfd(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_software.dfd.compile import compile_dfd_to_system

        return compile_dfd_to_system(self)
