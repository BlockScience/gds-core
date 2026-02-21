"""Integration tests: declare → compile → verify → canonical for standard models."""

import pytest

from gds.canonical import project_canonical

from gds_control.dsl.compile import compile_model, compile_to_system
from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.model import ControlModel
from gds_control.verification.engine import verify


@pytest.fixture
def siso_model():
    """Standard SISO feedback system."""
    return ControlModel(
        name="SISO Feedback",
        states=[State(name="x", initial=0.0)],
        inputs=[Input(name="r")],
        sensors=[Sensor(name="y", observes=["x"])],
        controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
    )


@pytest.fixture
def mimo_model():
    """Standard 2x2 MIMO system."""
    return ControlModel(
        name="MIMO",
        states=[State(name="x1"), State(name="x2")],
        inputs=[Input(name="r1"), Input(name="r2")],
        sensors=[
            Sensor(name="y1", observes=["x1"]),
            Sensor(name="y2", observes=["x2"]),
        ],
        controllers=[
            Controller(name="K1", reads=["y1", "r1"], drives=["x1"]),
            Controller(name="K2", reads=["y2", "r2"], drives=["x2"]),
        ],
    )


@pytest.fixture
def open_loop_model():
    """Open-loop system: input drives state directly, sensor reads state."""
    return ControlModel(
        name="Open Loop",
        states=[State(name="x")],
        inputs=[Input(name="u")],
        sensors=[Sensor(name="y", observes=["x"])],
        controllers=[Controller(name="K", reads=["u"], drives=["x"])],
    )


class TestSISOIntegration:
    def test_compile_and_canonical(self, siso_model):
        spec = compile_model(siso_model)
        canonical = project_canonical(spec)

        assert len(canonical.state_variables) == 1
        assert len(canonical.boundary_blocks) == 1
        assert len(canonical.mechanism_blocks) == 1
        assert len(canonical.control_blocks) == 0
        assert len(canonical.policy_blocks) == 2  # sensor + controller

    def test_verify_no_errors(self, siso_model):
        report = verify(siso_model)
        error_failures = [
            f
            for f in report.findings
            if not f.passed
            and f.severity.value == "error"
            and f.check_id != "G-002"  # BoundaryActions have no forward_in
        ]
        assert error_failures == [], [f.message for f in error_failures]

    def test_system_ir(self, siso_model):
        ir = compile_to_system(siso_model)
        assert len(ir.blocks) == 4
        temporal = [w for w in ir.wirings if w.is_temporal]
        assert len(temporal) == 1


class TestMIMOIntegration:
    def test_compile_and_canonical(self, mimo_model):
        spec = compile_model(mimo_model)
        canonical = project_canonical(spec)

        assert len(canonical.state_variables) == 2
        assert len(canonical.boundary_blocks) == 2
        assert len(canonical.mechanism_blocks) == 2
        assert len(canonical.policy_blocks) == 4  # 2 sensors + 2 controllers

    def test_verify_no_errors(self, mimo_model):
        report = verify(mimo_model)
        error_failures = [
            f
            for f in report.findings
            if not f.passed
            and f.severity.value == "error"
            and f.check_id != "G-002"  # BoundaryActions have no forward_in
        ]
        assert error_failures == [], [f.message for f in error_failures]


class TestOpenLoopIntegration:
    def test_compile_and_canonical(self, open_loop_model):
        spec = compile_model(open_loop_model)
        canonical = project_canonical(spec)

        assert len(canonical.state_variables) == 1
        assert len(canonical.boundary_blocks) == 1
        assert len(canonical.mechanism_blocks) == 1
        # controller reads input only (no sensor feedback in reads)
        assert len(canonical.policy_blocks) == 2  # sensor + controller
        assert len(canonical.control_blocks) == 0

    def test_verify_no_errors(self, open_loop_model):
        report = verify(open_loop_model)
        error_failures = [
            f
            for f in report.findings
            if not f.passed
            and f.severity.value == "error"
            and f.check_id != "G-002"  # BoundaryActions have no forward_in
        ]
        assert error_failures == [], [f.message for f in error_failures]
