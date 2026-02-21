"""Tests for control system DSL element declarations."""

import pytest
from pydantic import ValidationError

from gds_control.dsl.elements import Controller, Input, Sensor, State


class TestState:
    def test_construction(self):
        s = State(name="position")
        assert s.name == "position"
        assert s.initial is None

    def test_with_initial(self):
        s = State(name="velocity", initial=0.0)
        assert s.initial == 0.0

    def test_frozen(self):
        s = State(name="x")
        with pytest.raises(ValidationError):
            s.name = "y"  # type: ignore[misc]


class TestInput:
    def test_construction(self):
        i = Input(name="reference")
        assert i.name == "reference"

    def test_frozen(self):
        i = Input(name="r")
        with pytest.raises(ValidationError):
            i.name = "s"  # type: ignore[misc]


class TestSensor:
    def test_construction(self):
        s = Sensor(name="encoder", observes=["position"])
        assert s.name == "encoder"
        assert s.observes == ["position"]

    def test_default_observes(self):
        s = Sensor(name="encoder")
        assert s.observes == []

    def test_frozen(self):
        s = Sensor(name="enc", observes=["x"])
        with pytest.raises(ValidationError):
            s.name = "other"  # type: ignore[misc]


class TestController:
    def test_construction(self):
        c = Controller(name="pid", reads=["encoder"], drives=["position"])
        assert c.name == "pid"
        assert c.reads == ["encoder"]
        assert c.drives == ["position"]

    def test_default_lists(self):
        c = Controller(name="pid")
        assert c.reads == []
        assert c.drives == []

    def test_frozen(self):
        c = Controller(name="pid", reads=["enc"], drives=["x"])
        with pytest.raises(ValidationError):
            c.name = "other"  # type: ignore[misc]
