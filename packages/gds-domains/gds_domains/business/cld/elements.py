"""CLD element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (Policy).
"""

from typing import Literal

from pydantic import BaseModel


class Variable(BaseModel, frozen=True):
    """A system variable in a causal loop diagram.

    Maps to: GDS Policy (signal relay).
    """

    name: str
    description: str = ""


class CausalLink(BaseModel, frozen=True):
    """A directed causal influence between variables.

    Maps to: GDS Wiring.
    Polarity "+" means same-direction influence (reinforcing),
    "-" means opposite-direction influence (balancing).
    """

    source: str
    target: str
    polarity: Literal["+", "-"]
    delay: bool = False
