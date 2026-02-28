"""DependencyModel — declarative container for dependency graphs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.common.errors import SWValidationError
from gds_software.dependency.elements import Dep, Layer, Module

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class DependencyModel(BaseModel):
    """A complete dependency graph declaration.

    Validates at construction:
    1. At least one module
    2. No duplicate module names
    3. Dep source/target reference declared modules
    """

    name: str
    modules: list[Module]
    deps: list[Dep] = Field(default_factory=list)
    layers: list[Layer] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one module
        if not self.modules:
            errors.append("Dependency graph must have at least one module")

        # 2. No duplicate names
        names: list[str] = [m.name for m in self.modules]
        seen: set[str] = set()
        for n in names:
            if n in seen:
                errors.append(f"Duplicate module name: {n!r}")
            seen.add(n)

        module_names = set(names)

        # 3. Dep source/target reference declared modules
        for dep in self.deps:
            if dep.source not in module_names:
                errors.append(
                    f"Dependency source {dep.source!r} is not a declared module"
                )
            if dep.target not in module_names:
                errors.append(
                    f"Dependency target {dep.target!r} is not a declared module"
                )

        if errors:
            raise SWValidationError(
                f"DependencyModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def module_names(self) -> set[str]:
        return {m.name for m in self.modules}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        from gds_software.dependency.compile import compile_dep

        return compile_dep(self)

    def compile_system(self) -> SystemIR:
        from gds_software.dependency.compile import compile_dep_to_system

        return compile_dep_to_system(self)
