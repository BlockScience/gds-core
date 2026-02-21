"""Stock-flow element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class Stock(BaseModel, frozen=True):
    """A state accumulator in a stock-flow diagram.

    Maps to: GDS Mechanism (state update f) + Entity (state X).
    Emits a Level port; receives Rate ports from connected flows.
    """

    name: str
    initial: float | None = None
    units: str = ""
    non_negative: bool = True


class Flow(BaseModel, frozen=True):
    """A rate of change between stocks (or from/to clouds).

    Maps to: GDS Policy (rate computation g).
    Emits a Rate port; drains from source stock, fills target stock.
    """

    name: str
    source: str = ""
    target: str = ""


class Auxiliary(BaseModel, frozen=True):
    """An intermediate computation depending on other elements.

    Maps to: GDS Policy (decision logic g).
    Emits a Signal port; receives Level/Signal ports from inputs.
    """

    name: str
    inputs: list[str] = Field(default_factory=list)


class Converter(BaseModel, frozen=True):
    """An exogenous constant or parameter.

    Maps to: GDS BoundaryAction (exogenous input U).
    Emits a Signal port; has no internal inputs.
    """

    name: str
    units: str = ""
