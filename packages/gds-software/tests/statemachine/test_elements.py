"""Tests for state machine element declarations."""

import pytest

from gds_software.statemachine.elements import Event, Guard, Region, State, Transition


class TestState:
    def test_basic(self):
        s = State(name="Idle")
        assert s.name == "Idle"
        assert s.is_initial is False
        assert s.is_final is False

    def test_initial(self):
        s = State(name="Start", is_initial=True)
        assert s.is_initial is True

    def test_frozen(self):
        s = State(name="Idle")
        with pytest.raises(Exception):
            s.name = "Other"  # type: ignore[misc]


class TestEvent:
    def test_basic(self):
        e = Event(name="ButtonPress")
        assert e.name == "ButtonPress"


class TestTransition:
    def test_basic(self):
        t = Transition(name="T1", source="Idle", target="Active", event="Start")
        assert t.source == "Idle"
        assert t.target == "Active"
        assert t.event == "Start"
        assert t.guard is None

    def test_with_guard(self):
        g = Guard(condition="x > 0")
        t = Transition(name="T1", source="A", target="B", event="E", guard=g)
        assert t.guard is not None
        assert t.guard.condition == "x > 0"


class TestRegion:
    def test_basic(self):
        r = Region(name="R1", states=["A", "B"])
        assert r.name == "R1"
        assert r.states == ["A", "B"]
