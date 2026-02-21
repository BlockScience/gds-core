"""Parameter system for GDS specifications.

Parameters define the configuration space Θ at the specification level.
GDS does not define how Θ is sampled, assigned, or optimized — only
structural typing and reference validation.

Key distinction:
- **State (X)** changes during execution → Entity + StateVariable
- **Parameters (Θ)** are fixed during a trajectory → ParameterDef + ParameterSchema
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gds.types.typedef import TypeDef  # noqa: TC001


class ParameterDef(BaseModel):
    """Schema definition for a single parameter.

    Defines one dimension of Θ structurally — type, constraints, and bounds.
    No values, no binding, no execution semantics.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    typedef: TypeDef
    description: str = ""
    bounds: tuple[Any, Any] | None = None

    def check_value(self, value: Any) -> bool:
        """Check if a value satisfies this parameter's type and constraints."""
        if not self.typedef.check_value(value):
            return False
        if self.bounds is not None:
            low, high = self.bounds
            if not (low <= value <= high):
                return False
        return True


class ParameterSchema(BaseModel):
    """Defines the parameter space Θ at specification level.

    Immutable registry of parameter definitions.
    GDS does not interpret values — only validates structural references.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    parameters: dict[str, ParameterDef] = Field(default_factory=dict)

    def add(self, param: ParameterDef) -> ParameterSchema:
        """Return new schema with added parameter (immutable)."""
        if param.name in self.parameters:
            raise ValueError(f"Parameter '{param.name}' already registered")
        new_params = dict(self.parameters)
        new_params[param.name] = param
        return self.model_copy(update={"parameters": new_params})

    def get(self, name: str) -> ParameterDef:
        """Get a parameter definition by name."""
        return self.parameters[name]

    def names(self) -> set[str]:
        """Return all parameter names."""
        return set(self.parameters.keys())

    def validate_references(self, ref_names: set[str]) -> list[str]:
        """Validate that all referenced parameter names exist in schema.

        Returns list of error strings (empty = all references valid).
        """
        errors: list[str] = []
        for name in sorted(ref_names):
            if name not in self.parameters:
                errors.append(f"Referenced parameter '{name}' not defined in schema")
        return errors

    def __len__(self) -> int:
        return len(self.parameters)

    def __contains__(self, name: str) -> bool:
        return name in self.parameters
