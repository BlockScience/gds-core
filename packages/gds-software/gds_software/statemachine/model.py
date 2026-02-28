"""StateMachineModel — declarative container for state machines.

Users declare states, events, transitions, and optional regions.
The model validates structural integrity at construction time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_software.common.errors import SWValidationError
from gds_software.statemachine.elements import Event, Region, State, Transition

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class StateMachineModel(BaseModel):
    """A complete state machine declaration.

    Validates at construction:
    1. At least one state
    2. Exactly one initial state
    3. No duplicate state/event names
    4. Transition source/target reference declared states
    5. Transition events reference declared events
    6. Region states reference declared states (if regions used)
    """

    name: str
    states: list[State]
    events: list[Event] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    regions: list[Region] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one state
        if not self.states:
            errors.append("State machine must have at least one state")

        # 2. Exactly one initial state
        initial_states = [s for s in self.states if s.is_initial]
        if len(initial_states) == 0:
            errors.append("State machine must have exactly one initial state")
        elif len(initial_states) > 1:
            names = [s.name for s in initial_states]
            errors.append(f"State machine has multiple initial states: {names}")

        # 3. No duplicate names
        state_names_list: list[str] = [s.name for s in self.states]
        seen: set[str] = set()
        for n in state_names_list:
            if n in seen:
                errors.append(f"Duplicate state name: {n!r}")
            seen.add(n)

        event_names_list: list[str] = [e.name for e in self.events]
        seen_events: set[str] = set()
        for n in event_names_list:
            if n in seen_events:
                errors.append(f"Duplicate event name: {n!r}")
            seen_events.add(n)

        state_names = set(state_names_list)
        event_names = set(event_names_list)

        # 4. Transition source/target reference declared states
        for t in self.transitions:
            if t.source not in state_names:
                errors.append(
                    f"Transition {t.name!r} source {t.source!r} is not a declared state"
                )
            if t.target not in state_names:
                errors.append(
                    f"Transition {t.name!r} target {t.target!r} is not a declared state"
                )

        # 5. Transition events reference declared events
        for t in self.transitions:
            if t.event not in event_names:
                errors.append(
                    f"Transition {t.name!r} event {t.event!r} is not a declared event"
                )

        # 6. Region states reference declared states
        for region in self.regions:
            for s in region.states:
                if s not in state_names:
                    errors.append(
                        f"Region {region.name!r} references undeclared state {s!r}"
                    )

        if errors:
            raise SWValidationError(
                f"StateMachineModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def state_names(self) -> set[str]:
        return {s.name for s in self.states}

    @property
    def event_names(self) -> set[str]:
        return {e.name for e in self.events}

    @property
    def initial_state(self) -> State:
        return next(s for s in self.states if s.is_initial)

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_software.statemachine.compile import compile_sm

        return compile_sm(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_software.statemachine.compile import compile_sm_to_system

        return compile_sm_to_system(self)
