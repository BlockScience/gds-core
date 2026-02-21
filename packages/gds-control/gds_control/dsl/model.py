"""ControlModel — declarative container for state-space control systems.

Users declare states, inputs, sensors, and controllers. The model validates
structural integrity at construction time, then compiles to GDS specs on demand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.errors import CSValidationError

if TYPE_CHECKING:
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec


class ControlModel(BaseModel):
    """A complete state-space control system declaration.

    Validates at construction:
    1. At least one state
    2. No duplicate names across all elements
    3. Sensor observes references declared state names
    4. Controller reads references declared sensor/input names
    5. Controller drives references declared state names
    """

    name: str
    states: list[State]
    inputs: list[Input] = Field(default_factory=list)
    sensors: list[Sensor] = Field(default_factory=list)
    controllers: list[Controller] = Field(default_factory=list)
    description: str = ""

    @model_validator(mode="after")
    def _validate_structure(self) -> Self:
        errors: list[str] = []

        # 1. At least one state
        if not self.states:
            errors.append("Model must have at least one state")

        # 2. No duplicate names
        all_names: list[str] = []
        for s in self.states:
            all_names.append(s.name)
        for i in self.inputs:
            all_names.append(i.name)
        for s in self.sensors:
            all_names.append(s.name)
        for c in self.controllers:
            all_names.append(c.name)

        seen: set[str] = set()
        for n in all_names:
            if n in seen:
                errors.append(f"Duplicate element name: {n!r}")
            seen.add(n)

        state_names = {s.name for s in self.states}
        sensor_names = {s.name for s in self.sensors}
        input_names = {i.name for i in self.inputs}
        readable_names = sensor_names | input_names

        # 3. Sensor observes references declared state names
        for sensor in self.sensors:
            for obs in sensor.observes:
                if obs not in state_names:
                    errors.append(
                        f"Sensor {sensor.name!r} observes {obs!r} "
                        f"which is not a declared state"
                    )

        # 4. Controller reads references declared sensor/input names
        for ctrl in self.controllers:
            for read in ctrl.reads:
                if read not in readable_names:
                    errors.append(
                        f"Controller {ctrl.name!r} reads {read!r} "
                        f"which is not a declared sensor or input"
                    )

        # 5. Controller drives references declared state names
        for ctrl in self.controllers:
            for drive in ctrl.drives:
                if drive not in state_names:
                    errors.append(
                        f"Controller {ctrl.name!r} drives {drive!r} "
                        f"which is not a declared state"
                    )

        if errors:
            raise CSValidationError(
                f"ControlModel {self.name!r} validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    # ── Convenience properties ──────────────────────────────

    @property
    def element_names(self) -> set[str]:
        """All element names in the model."""
        names: set[str] = set()
        for s in self.states:
            names.add(s.name)
        for i in self.inputs:
            names.add(i.name)
        for s in self.sensors:
            names.add(s.name)
        for c in self.controllers:
            names.add(c.name)
        return names

    @property
    def state_names(self) -> set[str]:
        return {s.name for s in self.states}

    @property
    def sensor_names(self) -> set[str]:
        return {s.name for s in self.sensors}

    @property
    def input_names(self) -> set[str]:
        return {i.name for i in self.inputs}

    # ── Compilation ─────────────────────────────────────────

    def compile(self) -> GDSSpec:
        """Compile this model to a GDS specification."""
        from gds_control.dsl.compile import compile_model

        return compile_model(self)

    def compile_system(self) -> SystemIR:
        """Compile this model to a flat SystemIR for verification + visualization."""
        from gds_control.dsl.compile import compile_to_system

        return compile_to_system(self)
