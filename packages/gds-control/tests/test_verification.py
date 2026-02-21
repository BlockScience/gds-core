"""Tests for control system verification checks (CS-001..CS-006)."""

import pytest

from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.model import ControlModel
from gds_control.verification.checks import (
    check_cs001_undriven_states,
    check_cs002_unobserved_states,
    check_cs003_unused_inputs,
    check_cs004_controller_read_validity,
    check_cs005_controller_drive_validity,
    check_cs006_sensor_observe_validity,
)
from gds_control.verification.engine import verify


@pytest.fixture
def healthy_model():
    """A model where all checks pass."""
    return ControlModel(
        name="healthy",
        states=[State(name="x")],
        inputs=[Input(name="r")],
        sensors=[Sensor(name="y", observes=["x"])],
        controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
    )


@pytest.fixture
def undriven_model():
    """A model with an undriven state."""
    return ControlModel(
        name="undriven",
        states=[State(name="x"), State(name="z")],
        inputs=[Input(name="r")],
        sensors=[
            Sensor(name="y", observes=["x"]),
            Sensor(name="w", observes=["z"]),
        ],
        controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
    )


class TestCS001UndrivenStates:
    def test_all_driven(self, healthy_model):
        findings = check_cs001_undriven_states(healthy_model)
        assert all(f.passed for f in findings)

    def test_undriven_state(self, undriven_model):
        findings = check_cs001_undriven_states(undriven_model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "z" in failed[0].source_elements


class TestCS002UnobservedStates:
    def test_all_observed(self, healthy_model):
        findings = check_cs002_unobserved_states(healthy_model)
        assert all(f.passed for f in findings)

    def test_unobserved_state(self):
        model = ControlModel(
            name="unobserved",
            states=[State(name="x"), State(name="z")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y"], drives=["x", "z"])],
        )
        findings = check_cs002_unobserved_states(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "z" in failed[0].source_elements


class TestCS003UnusedInputs:
    def test_all_used(self, healthy_model):
        findings = check_cs003_unused_inputs(healthy_model)
        assert all(f.passed for f in findings)

    def test_unused_input(self):
        model = ControlModel(
            name="unused",
            states=[State(name="x")],
            inputs=[Input(name="r"), Input(name="d")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )
        findings = check_cs003_unused_inputs(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "d" in failed[0].source_elements


class TestCS004ControllerReadValidity:
    def test_valid_reads(self, healthy_model):
        findings = check_cs004_controller_read_validity(healthy_model)
        assert all(f.passed for f in findings)

    def test_no_controllers_no_findings(self):
        model = ControlModel(
            name="no_ctrl",
            states=[State(name="x")],
        )
        findings = check_cs004_controller_read_validity(model)
        assert findings == []


class TestCS005ControllerDriveValidity:
    def test_valid_drives(self, healthy_model):
        findings = check_cs005_controller_drive_validity(healthy_model)
        assert all(f.passed for f in findings)

    def test_no_controllers_no_findings(self):
        model = ControlModel(
            name="no_ctrl",
            states=[State(name="x")],
        )
        findings = check_cs005_controller_drive_validity(model)
        assert findings == []


class TestCS006SensorObserveValidity:
    def test_valid_observes(self, healthy_model):
        findings = check_cs006_sensor_observe_validity(healthy_model)
        assert all(f.passed for f in findings)

    def test_no_sensors_no_findings(self):
        model = ControlModel(
            name="no_sensor",
            states=[State(name="x")],
        )
        findings = check_cs006_sensor_observe_validity(model)
        assert findings == []


class TestVerifyEngine:
    def test_healthy_model_all_pass(self, healthy_model):
        report = verify(healthy_model)
        failed = [f for f in report.findings if not f.passed]
        # G-002 (no-input blocks) expected for BoundaryAction — filter those
        error_failures = [
            f for f in failed if f.severity.value == "error" and f.check_id != "G-002"
        ]
        assert error_failures == [], [f.message for f in error_failures]

    def test_cs_only(self, healthy_model):
        report = verify(healthy_model, include_gds_checks=False)
        cs_findings = [f for f in report.findings if f.check_id.startswith("CS-")]
        assert len(cs_findings) > 0
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(gds_findings) == 0
