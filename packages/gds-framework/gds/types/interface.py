"""Interface and Port types for the GDS block model.

Every Block has an Interface with four directional port slots:
  - forward_in:   domain inputs (covariant, forward)
  - forward_out:  codomain outputs (covariant, forward)
  - backward_in:  backward inputs (contravariant)
  - backward_out: backward outputs (contravariant)
"""

from __future__ import annotations

from pydantic import BaseModel

from gds.types.tokens import tokenize


class Port(BaseModel, frozen=True):
    """A named, typed connection point on a block's interface."""

    name: str
    type_tokens: frozenset[str]


class Interface(BaseModel, frozen=True):
    """The directional-pair boundary of a Block.

    Four port slots organized by direction:
      forward_in  — domain inputs (covariant)
      forward_out — codomain outputs (covariant)
      backward_in — backward inputs (contravariant)
      backward_out — backward outputs (contravariant)
    """

    forward_in: tuple[Port, ...] = ()
    forward_out: tuple[Port, ...] = ()
    backward_in: tuple[Port, ...] = ()
    backward_out: tuple[Port, ...] = ()


def port(name: str) -> Port:
    """Create a Port from a human-readable name, auto-tokenizing for type checking."""
    return Port(name=name, type_tokens=tokenize(name))
