"""ValueStreamModel — declarative container for value stream maps.

Users declare process steps, inventory buffers, suppliers, customers,
material flows, and information flows. The model validates structural
integrity at construction time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_business.common.errors import BizValidationError
from gds_business.vsm.elements import (
    Customer,
    InformationFlow,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class ValueStreamModel(BaseModel):
    """A complete value stream map declaration.

    Validates at construction:
    1. At least one process step
    2. No duplicate element names
    3. Flow source/target reference declared elements
    4. Buffer between references declared steps
    """

    name: str
    steps: list[ProcessStep]
    buffers: list[InventoryBuffer] = Field(default_factory=list)
    suppliers: list[Supplier] = Field(default_factory=list)
    customers: list[Customer] = Field(default_factory=list)
    material_flows: list[MaterialFlow] = Field(default_factory=list)
    information_flows: list[InformationFlow] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one process step
        if not self.steps:
            errors.append("VSM must have at least one process step")

        # 2. No duplicate element names
        all_names: list[str] = []
        for s in self.steps:
            all_names.append(s.name)
        for b in self.buffers:
            all_names.append(b.name)
        for s in self.suppliers:
            all_names.append(s.name)
        for c in self.customers:
            all_names.append(c.name)

        seen: set[str] = set()
        for n in all_names:
            if n in seen:
                errors.append(f"Duplicate element name: {n!r}")
            seen.add(n)

        all_element_names = set(all_names)

        # 3. Flow source/target reference declared elements
        for flow in self.material_flows:
            if flow.source not in all_element_names:
                errors.append(
                    f"MaterialFlow source {flow.source!r} is not a declared element"
                )
            if flow.target not in all_element_names:
                errors.append(
                    f"MaterialFlow target {flow.target!r} is not a declared element"
                )

        for flow in self.information_flows:
            if flow.source not in all_element_names:
                errors.append(
                    f"InformationFlow source {flow.source!r} is not a declared element"
                )
            if flow.target not in all_element_names:
                errors.append(
                    f"InformationFlow target {flow.target!r} is not a declared element"
                )

        # 4. Buffer between references declared steps
        step_names = {s.name for s in self.steps}
        for buf in self.buffers:
            upstream, downstream = buf.between
            if upstream not in step_names:
                errors.append(
                    f"Buffer {buf.name!r} upstream step {upstream!r} "
                    f"is not a declared step"
                )
            if downstream not in step_names:
                errors.append(
                    f"Buffer {buf.name!r} downstream step {downstream!r} "
                    f"is not a declared step"
                )

        if errors:
            raise BizValidationError(
                f"ValueStreamModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def element_names(self) -> set[str]:
        names: set[str] = set()
        for s in self.steps:
            names.add(s.name)
        for b in self.buffers:
            names.add(b.name)
        for s in self.suppliers:
            names.add(s.name)
        for c in self.customers:
            names.add(c.name)
        return names

    @property
    def step_names(self) -> set[str]:
        return {s.name for s in self.steps}

    @property
    def buffer_names(self) -> set[str]:
        return {b.name for b in self.buffers}

    @property
    def supplier_names(self) -> set[str]:
        return {s.name for s in self.suppliers}

    @property
    def customer_names(self) -> set[str]:
        return {c.name for c in self.customers}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_business.vsm.compile import compile_vsm

        return compile_vsm(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_business.vsm.compile import compile_vsm_to_system

        return compile_vsm_to_system(self)
