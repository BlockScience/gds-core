"""Tests for StateMachineModel validation."""

import pytest

from gds_software.common.errors import SWValidationError
from gds_software.statemachine.elements import Event, Region, State, Transition
from gds_software.statemachine.model import StateMachineModel


class TestModelConstruction:
    def test_minimal(self):
        m = StateMachineModel(
            name="Test",
            states=[State(name="Idle", is_initial=True)],
        )
        assert m.name == "Test"

    def test_full_model(self):
        m = StateMachineModel(
            name="Door",
            states=[
                State(name="Closed", is_initial=True),
                State(name="Open"),
                State(name="Locked"),
            ],
            events=[Event(name="Push"), Event(name="Lock")],
            transitions=[
                Transition(name="T1", source="Closed", target="Open", event="Push"),
                Transition(name="T2", source="Open", target="Closed", event="Push"),
                Transition(name="T3", source="Closed", target="Locked", event="Lock"),
            ],
        )
        assert len(m.states) == 3
        assert m.state_names == {"Closed", "Open", "Locked"}


class TestValidation:
    def test_no_states_raises(self):
        with pytest.raises(SWValidationError, match="at least one state"):
            StateMachineModel(name="Bad", states=[])

    def test_no_initial_state_raises(self):
        with pytest.raises(SWValidationError, match="exactly one initial"):
            StateMachineModel(
                name="Bad",
                states=[State(name="A"), State(name="B")],
            )

    def test_multiple_initial_raises(self):
        with pytest.raises(SWValidationError, match="multiple initial"):
            StateMachineModel(
                name="Bad",
                states=[
                    State(name="A", is_initial=True),
                    State(name="B", is_initial=True),
                ],
            )

    def test_duplicate_state_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate state name"):
            StateMachineModel(
                name="Bad",
                states=[
                    State(name="A", is_initial=True),
                    State(name="A"),
                ],
            )

    def test_bad_transition_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared state"):
            StateMachineModel(
                name="Bad",
                states=[State(name="A", is_initial=True)],
                events=[Event(name="E")],
                transitions=[
                    Transition(name="T", source="Ghost", target="A", event="E"),
                ],
            )

    def test_bad_transition_event_raises(self):
        with pytest.raises(SWValidationError, match="not a declared event"):
            StateMachineModel(
                name="Bad",
                states=[State(name="A", is_initial=True)],
                transitions=[
                    Transition(name="T", source="A", target="A", event="Ghost"),
                ],
            )

    def test_bad_region_state_raises(self):
        with pytest.raises(SWValidationError, match="undeclared state"):
            StateMachineModel(
                name="Bad",
                states=[State(name="A", is_initial=True)],
                regions=[Region(name="R", states=["Ghost"])],
            )


class TestProperties:
    def test_state_names(self):
        m = StateMachineModel(
            name="Test",
            states=[State(name="A", is_initial=True), State(name="B")],
        )
        assert m.state_names == {"A", "B"}

    def test_initial_state(self):
        m = StateMachineModel(
            name="Test",
            states=[State(name="A", is_initial=True), State(name="B")],
        )
        assert m.initial_state.name == "A"
