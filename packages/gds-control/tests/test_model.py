"""Tests for ControlModel construction-time validation."""

import pytest

from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.errors import CSValidationError
from gds_control.dsl.model import ControlModel


class TestControlModelValid:
    def test_minimal(self):
        m = ControlModel(name="test", states=[State(name="x")])
        assert m.name == "test"
        assert len(m.states) == 1

    def test_full_siso(self):
        m = ControlModel(
            name="SISO",
            states=[State(name="x")],
            inputs=[Input(name="r")],
            sensors=[Sensor(name="y", observes=["x"])],
            controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
        )
        assert m.state_names == {"x"}
        assert m.sensor_names == {"y"}
        assert m.input_names == {"r"}
        assert m.element_names == {"x", "r", "y", "K"}

    def test_mimo(self):
        m = ControlModel(
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
        assert len(m.states) == 2
        assert len(m.controllers) == 2


class TestControlModelInvalid:
    def test_no_states(self):
        with pytest.raises(CSValidationError, match="at least one state"):
            ControlModel(name="empty", states=[])

    def test_duplicate_names(self):
        with pytest.raises(CSValidationError, match="Duplicate element name"):
            ControlModel(
                name="dup",
                states=[State(name="x")],
                inputs=[Input(name="x")],
            )

    def test_sensor_observes_nonexistent_state(self):
        with pytest.raises(CSValidationError, match="not a declared state"):
            ControlModel(
                name="bad",
                states=[State(name="x")],
                sensors=[Sensor(name="y", observes=["z"])],
            )

    def test_controller_reads_nonexistent(self):
        with pytest.raises(CSValidationError, match="not a declared sensor or input"):
            ControlModel(
                name="bad",
                states=[State(name="x")],
                controllers=[Controller(name="K", reads=["ghost"], drives=["x"])],
            )

    def test_controller_drives_nonexistent_state(self):
        with pytest.raises(CSValidationError, match="not a declared state"):
            ControlModel(
                name="bad",
                states=[State(name="x")],
                controllers=[Controller(name="K", reads=[], drives=["z"])],
            )

    def test_multiple_errors(self):
        with pytest.raises(CSValidationError) as exc_info:
            ControlModel(
                name="bad",
                states=[State(name="x")],
                sensors=[Sensor(name="y", observes=["z"])],
                controllers=[Controller(name="K", reads=["ghost"], drives=["w"])],
            )
        msg = str(exc_info.value)
        assert "not a declared state" in msg
        assert "not a declared sensor or input" in msg
