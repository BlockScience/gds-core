"""VSM element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from typing import Literal

from pydantic import BaseModel, Field


class ProcessStep(BaseModel, frozen=True):
    """A processing stage in the value stream.

    Maps to: GDS Policy (decision logic g).
    """

    name: str
    cycle_time: float = Field(description="Time to process one unit")
    changeover_time: float = 0.0
    uptime: float = Field(default=1.0, ge=0.0, le=1.0)
    batch_size: int = 1
    operators: int = 1
    description: str = ""


class InventoryBuffer(BaseModel, frozen=True):
    """A WIP buffer between processing stages.

    Maps to: GDS Mechanism (state update f) + Entity (buffer state X).
    """

    name: str
    quantity: float = 0.0
    between: tuple[str, str] = Field(
        description="(upstream_step, downstream_step) this buffer sits between"
    )
    description: str = ""


class Supplier(BaseModel, frozen=True):
    """An external material source.

    Maps to: GDS BoundaryAction (exogenous input U).
    """

    name: str
    description: str = ""


class Customer(BaseModel, frozen=True):
    """An external demand sink.

    Maps to: GDS BoundaryAction (exogenous input U).
    """

    name: str
    takt_time: float = Field(description="Required pace of production")
    description: str = ""


class MaterialFlow(BaseModel, frozen=True):
    """A material movement between elements.

    Maps to: GDS Wiring.
    """

    source: str
    target: str
    flow_type: Literal["push", "pull"] = "push"


class InformationFlow(BaseModel, frozen=True):
    """A signal or kanban flow between elements.

    Maps to: GDS Wiring (signal channel).
    """

    source: str
    target: str
