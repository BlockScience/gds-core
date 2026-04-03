"""Parameter space definitions for search."""

from __future__ import annotations

import itertools
import math
from abc import ABC, abstractmethod
from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_psuu.errors import PsuuValidationError
from gds_psuu.types import ParamPoint  # noqa: TC001

if TYPE_CHECKING:
    from gds.parameters import ParameterSchema


class Continuous(BaseModel):
    """A continuous parameter dimension with min/max bounds."""

    model_config = ConfigDict(frozen=True)

    min_val: float
    max_val: float

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.min_val >= self.max_val:
            raise PsuuValidationError(
                f"min_val ({self.min_val}) must be less than max_val ({self.max_val})"
            )
        if not math.isfinite(self.min_val) or not math.isfinite(self.max_val):
            raise PsuuValidationError("Bounds must be finite")
        return self


class Integer(BaseModel):
    """An integer parameter dimension with min/max bounds (inclusive)."""

    model_config = ConfigDict(frozen=True)

    min_val: int
    max_val: int

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.min_val >= self.max_val:
            raise PsuuValidationError(
                f"min_val ({self.min_val}) must be less than max_val ({self.max_val})"
            )
        return self


class Discrete(BaseModel):
    """A discrete parameter dimension with explicit allowed values."""

    model_config = ConfigDict(frozen=True)

    values: tuple[Any, ...]

    @model_validator(mode="after")
    def _validate_values(self) -> Self:
        if len(self.values) < 1:
            raise PsuuValidationError("Discrete dimension must have at least 1 value")
        return self


Dimension = Continuous | Integer | Discrete


@dataclass(frozen=True)
class SchemaViolation:
    """A single incompatibility between a sweep dimension and declared schema."""

    param: str
    violation_type: str  # "missing_from_schema", "out_of_bounds", "type_mismatch"
    message: str


class Constraint(BaseModel, ABC):
    """Base class for parameter space constraints."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @abstractmethod
    def is_feasible(self, point: ParamPoint) -> bool:
        """Return True if the point satisfies this constraint."""


class LinearConstraint(Constraint):
    """Linear inequality constraint: sum(coeff_i * x_i) <= bound."""

    coefficients: dict[str, float]
    bound: float

    @model_validator(mode="after")
    def _validate_nonempty(self) -> Self:
        if not self.coefficients:
            raise PsuuValidationError(
                "LinearConstraint must have at least 1 coefficient"
            )
        return self

    def is_feasible(self, point: ParamPoint) -> bool:
        total = sum(coeff * point[name] for name, coeff in self.coefficients.items())
        return total <= self.bound


class FunctionalConstraint(Constraint):
    """Arbitrary feasibility predicate over a parameter point."""

    fn: Callable[[ParamPoint], bool]

    def is_feasible(self, point: ParamPoint) -> bool:
        return self.fn(point)


class ParameterSpace(BaseModel):
    """Defines the searchable parameter space as a mapping of named dimensions."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    params: dict[str, Dimension]
    constraints: tuple[Constraint, ...] = ()

    @model_validator(mode="after")
    def _validate_nonempty(self) -> Self:
        if not self.params:
            raise PsuuValidationError("ParameterSpace must have at least 1 parameter")
        return self

    @model_validator(mode="after")
    def _validate_constraint_params(self) -> Self:
        param_names = set(self.params.keys())
        for constraint in self.constraints:
            if isinstance(constraint, LinearConstraint):
                unknown = set(constraint.coefficients.keys()) - param_names
                if unknown:
                    raise PsuuValidationError(
                        f"LinearConstraint references unknown params: {unknown}"
                    )
        return self

    @property
    def dimension_names(self) -> list[str]:
        """Ordered list of parameter names."""
        return list(self.params.keys())

    def is_feasible(self, point: ParamPoint) -> bool:
        """Check if a parameter point satisfies all constraints."""
        return all(c.is_feasible(point) for c in self.constraints)

    def grid_points(self, n_steps: int) -> list[ParamPoint]:
        """Generate a grid of parameter points.

        For Continuous: ``n_steps`` evenly spaced values between min and max.
        For Integer: all integers in [min_val, max_val] (ignores n_steps).
        For Discrete: all values.

        Points that violate constraints are excluded.
        """
        axes: list[list[Any]] = []
        for dim in self.params.values():
            if isinstance(dim, Continuous):
                if n_steps < 2:
                    raise PsuuValidationError(
                        "n_steps must be >= 2 for Continuous dimensions"
                    )
                step = (dim.max_val - dim.min_val) / (n_steps - 1)
                axes.append([dim.min_val + i * step for i in range(n_steps)])
            elif isinstance(dim, Integer):
                axes.append(list(range(dim.min_val, dim.max_val + 1)))
            elif isinstance(dim, Discrete):
                axes.append(list(dim.values))
        names = self.dimension_names
        all_points = [
            dict(zip(names, combo, strict=True)) for combo in itertools.product(*axes)
        ]
        if self.constraints:
            return [p for p in all_points if self.is_feasible(p)]
        return all_points

    @classmethod
    def from_parameter_schema(cls, schema: ParameterSchema) -> ParameterSpace:
        """Create a ParameterSpace from a GDS ParameterSchema.

        Maps ParameterDef entries to Dimensions:

        - ``float`` with bounds -> ``Continuous``
        - ``int`` with bounds -> ``Integer``
        - No bounds -> raises ``ValueError`` (bounds required for sweep)
        - Unsupported type -> raises ``TypeError``

        Requires ``gds-framework`` to be installed.
        """
        from gds.parameters import ParameterSchema as _Schema

        if not isinstance(schema, _Schema):
            raise TypeError(f"Expected ParameterSchema, got {type(schema).__name__}")

        params: dict[str, Dimension] = {}
        for name, pdef in schema.parameters.items():
            if pdef.bounds is None:
                raise ValueError(
                    f"Parameter {name!r} has no bounds declared — "
                    f"cannot create sweep dimension without bounds"
                )
            low, high = pdef.bounds
            py_type = pdef.typedef.python_type
            is_float = py_type is float or (
                isinstance(py_type, type) and issubclass(py_type, float)
            )
            is_int = py_type is int or (
                isinstance(py_type, type) and issubclass(py_type, int)
            )
            if is_float:
                params[name] = Continuous(min_val=float(low), max_val=float(high))
            elif is_int:
                params[name] = Integer(min_val=int(low), max_val=int(high))
            else:
                raise TypeError(
                    f"Parameter {name!r} has type {py_type.__name__} — "
                    f"only float and int are supported for automatic "
                    f"dimension creation"
                )
        return cls(params=params)

    def validate_against_schema(self, schema: ParameterSchema) -> list[SchemaViolation]:
        """Check that this space respects the declared parameter schema.

        Returns a list of violations. Empty list means the space is
        compatible with the schema.

        Requires ``gds-framework`` to be installed.
        """
        from gds.parameters import ParameterSchema as _Schema

        if not isinstance(schema, _Schema):
            raise TypeError(f"Expected ParameterSchema, got {type(schema).__name__}")

        violations: list[SchemaViolation] = []

        for name, dim in self.params.items():
            # Check parameter exists in schema
            pdef = schema.parameters.get(name)
            if pdef is None:
                violations.append(
                    SchemaViolation(
                        param=name,
                        violation_type="missing_from_schema",
                        message=(
                            f"Parameter {name!r} is swept but not "
                            f"declared in the schema"
                        ),
                    )
                )
                continue

            # Check type compatibility
            py_type = pdef.typedef.python_type
            if isinstance(dim, Continuous) and py_type is not float:
                violations.append(
                    SchemaViolation(
                        param=name,
                        violation_type="type_mismatch",
                        message=(
                            f"Parameter {name!r}: Continuous dimension "
                            f"but declared type is {py_type.__name__}"
                        ),
                    )
                )
            elif isinstance(dim, Integer) and py_type is not int:
                violations.append(
                    SchemaViolation(
                        param=name,
                        violation_type="type_mismatch",
                        message=(
                            f"Parameter {name!r}: Integer dimension "
                            f"but declared type is {py_type.__name__}"
                        ),
                    )
                )

            # Check bounds compatibility
            if pdef.bounds is not None and isinstance(dim, (Continuous, Integer)):
                schema_low, schema_high = pdef.bounds
                if dim.min_val < schema_low:
                    violations.append(
                        SchemaViolation(
                            param=name,
                            violation_type="out_of_bounds",
                            message=(
                                f"Parameter {name!r}: sweep min "
                                f"{dim.min_val} < declared lower "
                                f"bound {schema_low}"
                            ),
                        )
                    )
                if dim.max_val > schema_high:
                    violations.append(
                        SchemaViolation(
                            param=name,
                            violation_type="out_of_bounds",
                            message=(
                                f"Parameter {name!r}: sweep max "
                                f"{dim.max_val} > declared upper "
                                f"bound {schema_high}"
                            ),
                        )
                    )

            # Check typedef constraint at sweep boundaries
            if pdef.typedef.constraint is not None and isinstance(
                dim, (Continuous, Integer)
            ):
                if not pdef.typedef.check_value(dim.min_val):
                    violations.append(
                        SchemaViolation(
                            param=name,
                            violation_type="out_of_bounds",
                            message=(
                                f"Parameter {name!r}: sweep min "
                                f"{dim.min_val} fails typedef constraint"
                            ),
                        )
                    )
                if not pdef.typedef.check_value(dim.max_val):
                    violations.append(
                        SchemaViolation(
                            param=name,
                            violation_type="out_of_bounds",
                            message=(
                                f"Parameter {name!r}: sweep max "
                                f"{dim.max_val} fails typedef constraint"
                            ),
                        )
                    )

        return violations
