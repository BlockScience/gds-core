"""gds-control — DEPRECATED: use gds_domains.control instead."""

import warnings

warnings.warn(
    "Import from gds_domains.control instead of gds_control. "
    "The gds-control package will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "0.99.0"

from gds_domains.control import (  # noqa: F401, E402
    ALL_CS_CHECKS,
    CSCompilationError,
    CSError,
    CSValidationError,
    Controller,
    ControlModel,
    ControlSpace,
    ControlType,
    Finding,
    Input,
    MeasurementSpace,
    MeasurementType,
    ReferenceSpace,
    ReferenceType,
    Sensor,
    Severity,
    State,
    StateSpace,
    StateType,
    VerificationReport,
    check_cs001_undriven_states,
    check_cs002_unobserved_states,
    check_cs003_unused_inputs,
    check_cs004_controller_read_validity,
    check_cs005_controller_drive_validity,
    check_cs006_sensor_observe_validity,
    compile_model,
    compile_to_system,
    verify,
)
from gds_domains.control import ElementType  # noqa: F401, E402

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
