"""CausalLoopModel — declarative container for causal loop diagrams.

Users declare variables and causal links. The model validates structural
integrity at construction time, then compiles to GDS specs on demand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_business.cld.elements import CausalLink, Variable
from gds_business.common.errors import BizValidationError

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class CausalLoopModel(BaseModel):
    """A complete causal loop diagram declaration.

    Validates at construction:
    1. At least one variable
    2. No duplicate variable names
    3. Link source/target reference declared variables
    4. No self-loops
    """

    name: str
    variables: list[Variable]
    links: list[CausalLink] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one variable
        if not self.variables:
            errors.append("CLD must have at least one variable")

        # 2. No duplicate names
        names: list[str] = [v.name for v in self.variables]
        seen: set[str] = set()
        for n in names:
            if n in seen:
                errors.append(f"Duplicate variable name: {n!r}")
            seen.add(n)

        var_names = set(names)

        # 3. Link source/target reference declared variables
        for link in self.links:
            if link.source not in var_names:
                errors.append(f"Link source {link.source!r} is not a declared variable")
            if link.target not in var_names:
                errors.append(f"Link target {link.target!r} is not a declared variable")

        # 4. No self-loops
        for link in self.links:
            if link.source == link.target:
                errors.append(f"Self-loop detected: {link.source!r} -> {link.target!r}")

        if errors:
            raise BizValidationError(
                f"CausalLoopModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def variable_names(self) -> set[str]:
        return {v.name for v in self.variables}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_business.cld.compile import compile_cld

        return compile_cld(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_business.cld.compile import compile_cld_to_system

        return compile_cld_to_system(self)
