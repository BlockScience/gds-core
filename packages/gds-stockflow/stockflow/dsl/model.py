"""StockFlowModel — declarative container for stock-flow diagrams.

Users declare stocks, flows, auxiliaries, and converters. The model validates
structural integrity at construction time, then compiles to GDS specs on demand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.errors import SFValidationError

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class StockFlowModel(BaseModel):
    """A complete stock-flow diagram declaration.

    Validates at construction:
    1. No duplicate element names across all lists
    2. Flow source/target reference declared stock names (or empty for cloud)
    3. Every flow has at least one of source or target
    4. Auxiliary inputs reference declared element names
    5. At least one stock exists
    """

    name: str
    stocks: list[Stock]
    flows: list[Flow] = Field(default_factory=list)
    auxiliaries: list[Auxiliary] = Field(default_factory=list)
    converters: list[Converter] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 5. At least one stock
        if not self.stocks:
            errors.append("Model must have at least one stock")

        # 1. No duplicate names
        all_names: list[str] = []
        for s in self.stocks:
            all_names.append(s.name)
        for f in self.flows:
            all_names.append(f.name)
        for a in self.auxiliaries:
            all_names.append(a.name)
        for c in self.converters:
            all_names.append(c.name)

        seen: set[str] = set()
        for n in all_names:
            if n in seen:
                errors.append(f"Duplicate element name: {n!r}")
            seen.add(n)

        stock_names = {s.name for s in self.stocks}

        # 2 & 3. Flow source/target validation
        for f in self.flows:
            if not f.source and not f.target:
                errors.append(
                    f"Flow {f.name!r} must have at least one of source or target"
                )
            if f.source and f.source not in stock_names:
                errors.append(
                    f"Flow {f.name!r} source {f.source!r} is not a declared stock"
                )
            if f.target and f.target not in stock_names:
                errors.append(
                    f"Flow {f.name!r} target {f.target!r} is not a declared stock"
                )

        # 4. Auxiliary inputs reference declared elements
        all_element_names = set(all_names)
        for a in self.auxiliaries:
            for inp in a.inputs:
                if inp not in all_element_names:
                    errors.append(
                        f"Auxiliary {a.name!r} input {inp!r} is not a declared element"
                    )

        if errors:
            raise SFValidationError(
                f"StockFlowModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def element_names(self) -> set[str]:
        """All element names in the model."""
        names: set[str] = set()
        for s in self.stocks:
            names.add(s.name)
        for f in self.flows:
            names.add(f.name)
        for a in self.auxiliaries:
            names.add(a.name)
        for c in self.converters:
            names.add(c.name)
        return names

    @property
    def stock_names(self) -> set[str]:
        return {s.name for s in self.stocks}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from stockflow.dsl.compile import compile_model

        return compile_model(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from stockflow.dsl.compile import compile_to_system

        return compile_to_system(self)
