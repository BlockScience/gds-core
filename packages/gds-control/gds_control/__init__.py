"""State-space control DSL over GDS semantics — control theory with formal guarantees.

Declare states, inputs, sensors, and controllers as plain data models.
The compiler maps them to GDS role blocks, entities, and composition trees.
All downstream GDS tooling works immediately — canonical projection,
semantic checks, SpecQuery, serialization, gds-viz.
"""

__version__ = "0.1.0"

# ── DSL declarations ────────────────────────────────────────
from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.errors import CSCompilationError, CSError, CSValidationError
from gds_control.dsl.model import ControlModel
from gds_control.dsl.types import ElementType

# ── Compilation ─────────────────────────────────────────────
from gds_control.dsl.compile import (
    ControlSpace,
    ControlType,
    MeasurementSpace,
    MeasurementType,
    ReferenceSpace,
    ReferenceType,
    StateSpace,
    StateType,
    compile_model,
    compile_to_system,
)

# ── Verification ────────────────────────────────────────────
from gds_control.verification.checks import (
    ALL_CS_CHECKS,
    check_cs001_undriven_states,
    check_cs002_unobserved_states,
    check_cs003_unused_inputs,
    check_cs004_controller_read_validity,
    check_cs005_controller_drive_validity,
    check_cs006_sensor_observe_validity,
)
from gds_control.verification.engine import verify

# ── Re-exports from gds-framework ──────────────────────────
from gds.verification.findings import Finding, Severity, VerificationReport

__all__ = [
    # DSL
    "State",
    "Input",
    "Sensor",
    "Controller",
    "ControlModel",
    "ElementType",
    # Errors
    "CSError",
    "CSValidationError",
    "CSCompilationError",
    # Compilation
    "compile_model",
    "compile_to_system",
    # Semantic types and spaces
    "StateType",
    "ReferenceType",
    "MeasurementType",
    "ControlType",
    "StateSpace",
    "ReferenceSpace",
    "MeasurementSpace",
    "ControlSpace",
    # Verification
    "verify",
    "ALL_CS_CHECKS",
    "check_cs001_undriven_states",
    "check_cs002_unobserved_states",
    "check_cs003_unused_inputs",
    "check_cs004_controller_read_validity",
    "check_cs005_controller_drive_validity",
    "check_cs006_sensor_observe_validity",
    # Re-exports
    "Finding",
    "Severity",
    "VerificationReport",
]
