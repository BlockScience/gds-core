"""DFD element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class ExternalEntity(BaseModel, frozen=True):
    """An external actor that produces or consumes data.

    Maps to: GDS BoundaryAction (exogenous input U).
    Emits a Signal port; has no internal inputs.
    """

    name: str
    description: str = ""


class Process(BaseModel, frozen=True):
    """A data transformation or processing step.

    Maps to: GDS Policy (decision logic g).
    Receives data flows as input, produces data flows as output.
    """

    name: str
    description: str = ""


class DataStore(BaseModel, frozen=True):
    """A data repository or database.

    Maps to: GDS Mechanism (state update f) + Entity (state X).
    Receives write flows, emits content for read flows.
    """

    name: str
    description: str = ""


class DataFlow(BaseModel, frozen=True):
    """A directed data flow between DFD elements.

    Maps to: GDS Wiring (connects elements).
    The source and target reference element names.
    """

    name: str
    source: str
    target: str
    data: str = Field(default="", description="Description of data carried")
