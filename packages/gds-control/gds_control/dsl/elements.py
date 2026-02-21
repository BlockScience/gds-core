"""Control system element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
The compiler maps these to GDS role blocks (BoundaryAction, Policy, Mechanism).
"""

from pydantic import BaseModel, Field


class State(BaseModel, frozen=True):
    """A plant state variable.

    Maps to: GDS Mechanism (state update f) + Entity (state X).
    Receives control ports from driving controllers, emits state port.
    """

    name: str
    initial: float | None = None


class Input(BaseModel, frozen=True):
    """Exogenous signal — reference setpoint or disturbance.

    Maps to: GDS BoundaryAction (exogenous input U).
    Emits a reference port; has no internal inputs.
    """

    name: str


class Sensor(BaseModel, frozen=True):
    """Observation: reads state variables, emits measurement.

    Maps to: GDS Policy (observation g).
    Receives state ports from observed states, emits measurement port.
    """

    name: str
    observes: list[str] = Field(default_factory=list)


class Controller(BaseModel, frozen=True):
    """Control law: reads sensors/inputs, emits control signal.

    Maps to: GDS Policy (decision logic g).
    Receives measurement/reference ports, emits control port.
    """

    name: str
    reads: list[str] = Field(default_factory=list)
    drives: list[str] = Field(default_factory=list)
