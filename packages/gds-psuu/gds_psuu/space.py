"""Parameter space definitions for search."""

from __future__ import annotations

import itertools
import math
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from gds_psuu.errors import PsuuValidationError

if TYPE_CHECKING:
    from gds_psuu.types import ParamPoint


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


class ParameterSpace(BaseModel):
    """Defines the searchable parameter space as a mapping of named dimensions."""

    model_config = ConfigDict(frozen=True)

    params: dict[str, Dimension]

    @model_validator(mode="after")
    def _validate_nonempty(self) -> Self:
        if not self.params:
            raise PsuuValidationError("ParameterSpace must have at least 1 parameter")
        return self

    @property
    def dimension_names(self) -> list[str]:
        """Ordered list of parameter names."""
        return list(self.params.keys())

    def grid_points(self, n_steps: int) -> list[ParamPoint]:
        """Generate a grid of parameter points.

        For Continuous: ``n_steps`` evenly spaced values between min and max.
        For Integer: all integers in [min_val, max_val] (ignores n_steps).
        For Discrete: all values.
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
        return [
            dict(zip(names, combo, strict=True)) for combo in itertools.product(*axes)
        ]
