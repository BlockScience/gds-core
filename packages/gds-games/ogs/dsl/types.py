"""Signature, port types, and domain enums for the open games DSL.

Wraps the generic GDS Interface with a backwards-compatible Signature
that accepts the (X, Y, R, S) convention from compositional game theory.

Also defines the four domain-vocabulary enums (CompositionType, GameType,
FlowType, InputType) that classify OGS components. These live here —
in the DSL layer — because they are domain concepts, not IR concepts.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from gds.types.interface import Interface, Port, port
from pydantic import model_validator

__all__ = [
    "CompositionType",
    "FlowType",
    "GameType",
    "InputType",
    "Port",
    "Signature",
    "port",
]


class CompositionType(str, Enum):
    """How games are composed within a pattern.

    Extends GDS composition types with game-theory naming.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    FEEDBACK = "feedback"
    CORECURSIVE = "corecursive"


class GameType(str, Enum):
    """Classification of an open game component by its port structure."""

    DECISION = "decision"
    FUNCTION_COVARIANT = "function_covariant"
    FUNCTION_CONTRAVARIANT = "function_contravariant"
    DELETION = "deletion"
    DUPLICATION = "duplication"
    COUNIT = "counit"


class FlowType(str, Enum):
    """Semantic classification of an information flow between components."""

    OBSERVATION = "observation"
    CHOICE_OBSERVATION = "choice_observation"
    UTILITY_COUTILITY = "utility_coutility"
    PRIMITIVE = "primitive"


class InputType(str, Enum):
    """Classification of external inputs that cross the pattern boundary."""

    SENSOR = "sensor"
    RESOURCE = "resource"
    INITIALIZATION = "initialization"
    EXTERNAL_WORLD = "external_world"


class Signature(Interface, frozen=True):
    """The ``(X, Y, R, S)`` 4-tuple boundary of an open game.

    Backwards-compatible constructor that maps game theory conventions
    to GDS directional pairs:

    - **x** → forward_in (observation inputs, covariant)
    - **y** → forward_out (decision outputs, covariant)
    - **r** → backward_in (utility inputs, contravariant)
    - **s** → backward_out (coutility outputs, contravariant)
    """

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            x: tuple[Port, ...] = (),
            y: tuple[Port, ...] = (),
            r: tuple[Port, ...] = (),
            s: tuple[Port, ...] = (),
            forward_in: tuple[Port, ...] = (),
            forward_out: tuple[Port, ...] = (),
            backward_in: tuple[Port, ...] = (),
            backward_out: tuple[Port, ...] = (),
        ) -> None: ...

    @model_validator(mode="before")
    @classmethod
    def _map_xyrs(cls, data: dict) -> dict:
        if isinstance(data, dict):
            mapping = {
                "x": "forward_in",
                "y": "forward_out",
                "r": "backward_in",
                "s": "backward_out",
            }
            for old, new in mapping.items():
                if old in data:
                    data[new] = data.pop(old)
        return data

    @property
    def x(self) -> tuple[Port, ...]:
        return self.forward_in

    @property
    def y(self) -> tuple[Port, ...]:
        return self.forward_out

    @property
    def r(self) -> tuple[Port, ...]:
        return self.backward_in

    @property
    def s(self) -> tuple[Port, ...]:
        return self.backward_out
