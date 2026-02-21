"""Control system verification checks (CS-001..CS-006).

These operate on ControlModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_control.dsl.model import ControlModel


def check_cs001_undriven_states(model: ControlModel) -> list[Finding]:
    """CS-001: Every state is driven by at least one controller."""
    findings: list[Finding] = []
    driven_states: set[str] = set()
    for ctrl in model.controllers:
        driven_states.update(ctrl.drives)

    for state in model.states:
        driven = state.name in driven_states
        findings.append(
            Finding(
                check_id="CS-001",
                severity=Severity.WARNING,
                message=(
                    f"State {state.name!r} is not driven by any controller"
                    if not driven
                    else f"State {state.name!r} is driven by a controller"
                ),
                source_elements=[state.name],
                passed=driven,
            )
        )
    return findings


def check_cs002_unobserved_states(model: ControlModel) -> list[Finding]:
    """CS-002: Every state is observed by at least one sensor."""
    findings: list[Finding] = []
    observed_states: set[str] = set()
    for sensor in model.sensors:
        observed_states.update(sensor.observes)

    for state in model.states:
        observed = state.name in observed_states
        findings.append(
            Finding(
                check_id="CS-002",
                severity=Severity.WARNING,
                message=(
                    f"State {state.name!r} is not observed by any sensor"
                    if not observed
                    else f"State {state.name!r} is observed by a sensor"
                ),
                source_elements=[state.name],
                passed=observed,
            )
        )
    return findings


def check_cs003_unused_inputs(model: ControlModel) -> list[Finding]:
    """CS-003: Every input is read by at least one controller."""
    findings: list[Finding] = []
    read_names: set[str] = set()
    for ctrl in model.controllers:
        read_names.update(ctrl.reads)

    for inp in model.inputs:
        used = inp.name in read_names
        findings.append(
            Finding(
                check_id="CS-003",
                severity=Severity.WARNING,
                message=(
                    f"Input {inp.name!r} is not read by any controller"
                    if not used
                    else f"Input {inp.name!r} is read by a controller"
                ),
                source_elements=[inp.name],
                passed=used,
            )
        )
    return findings


def check_cs004_controller_read_validity(model: ControlModel) -> list[Finding]:
    """CS-004: Controller reads reference declared sensors/inputs."""
    findings: list[Finding] = []
    readable_names = model.sensor_names | model.input_names

    for ctrl in model.controllers:
        for read in ctrl.reads:
            valid = read in readable_names
            findings.append(
                Finding(
                    check_id="CS-004",
                    severity=Severity.ERROR,
                    message=(
                        f"Controller {ctrl.name!r} reads {read!r} "
                        f"{'which is' if valid else 'which is NOT'} "
                        f"a declared sensor or input"
                    ),
                    source_elements=[ctrl.name, read],
                    passed=valid,
                )
            )
    return findings


def check_cs005_controller_drive_validity(model: ControlModel) -> list[Finding]:
    """CS-005: Controller drives reference declared states."""
    findings: list[Finding] = []
    state_names = model.state_names

    for ctrl in model.controllers:
        for drive in ctrl.drives:
            valid = drive in state_names
            findings.append(
                Finding(
                    check_id="CS-005",
                    severity=Severity.ERROR,
                    message=(
                        f"Controller {ctrl.name!r} drives {drive!r} "
                        f"{'which is' if valid else 'which is NOT'} "
                        f"a declared state"
                    ),
                    source_elements=[ctrl.name, drive],
                    passed=valid,
                )
            )
    return findings


def check_cs006_sensor_observe_validity(model: ControlModel) -> list[Finding]:
    """CS-006: Sensor observes reference declared states."""
    findings: list[Finding] = []
    state_names = model.state_names

    for sensor in model.sensors:
        for obs in sensor.observes:
            valid = obs in state_names
            findings.append(
                Finding(
                    check_id="CS-006",
                    severity=Severity.ERROR,
                    message=(
                        f"Sensor {sensor.name!r} observes {obs!r} "
                        f"{'which is' if valid else 'which is NOT'} "
                        f"a declared state"
                    ),
                    source_elements=[sensor.name, obs],
                    passed=valid,
                )
            )
    return findings


ALL_CS_CHECKS = [
    check_cs001_undriven_states,
    check_cs002_unobserved_states,
    check_cs003_unused_inputs,
    check_cs004_controller_read_validity,
    check_cs005_controller_drive_validity,
    check_cs006_sensor_observe_validity,
]
