"""Tests for state machine compilation."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec

from gds_software.statemachine.compile import compile_sm, compile_sm_to_system
from gds_software.statemachine.elements import Event, Region, State, Transition
from gds_software.statemachine.model import StateMachineModel


@pytest.fixture
def door_model():
    return StateMachineModel(
        name="Door",
        states=[
            State(name="Closed", is_initial=True),
            State(name="Open"),
        ],
        events=[Event(name="Push")],
        transitions=[
            Transition(name="Open Door", source="Closed", target="Open", event="Push"),
            Transition(name="Close Door", source="Open", target="Closed", event="Push"),
        ],
    )


@pytest.fixture
def turnstile_model():
    return StateMachineModel(
        name="Turnstile",
        states=[
            State(name="Locked", is_initial=True),
            State(name="Unlocked"),
        ],
        events=[Event(name="Coin"), Event(name="Push")],
        transitions=[
            Transition(name="Insert", source="Locked", target="Unlocked", event="Coin"),
            Transition(name="Pass", source="Unlocked", target="Locked", event="Push"),
        ],
    )


class TestCompileSM:
    def test_returns_gds_spec(self, door_model):
        spec = compile_sm(door_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Door"

    def test_types_registered(self, door_model):
        spec = compile_sm(door_model)
        assert "SM Event" in spec.types
        assert "SM State" in spec.types

    def test_spaces_registered(self, door_model):
        spec = compile_sm(door_model)
        assert "SM EventSpace" in spec.spaces
        assert "SM StateSpace" in spec.spaces

    def test_entities_for_states(self, door_model):
        spec = compile_sm(door_model)
        assert "Closed" in spec.entities
        assert "Open" in spec.entities
        assert "value" in spec.entities["Closed"].variables

    def test_event_becomes_boundary_action(self, door_model):
        spec = compile_sm(door_model)
        assert "Push" in spec.blocks
        block = spec.blocks["Push"]
        assert isinstance(block, BoundaryAction)
        assert block.interface.forward_out[0].name == "Push Event"

    def test_transition_becomes_policy(self, door_model):
        spec = compile_sm(door_model)
        assert "Open Door Transition" in spec.blocks
        block = spec.blocks["Open Door Transition"]
        assert isinstance(block, Policy)

    def test_state_becomes_mechanism(self, door_model):
        spec = compile_sm(door_model)
        assert "Open Mechanism" in spec.blocks
        block = spec.blocks["Open Mechanism"]
        assert isinstance(block, Mechanism)
        assert ("Open", "value") in block.updates

    def test_wirings_registered(self, door_model):
        spec = compile_sm(door_model)
        assert len(spec.wirings) == 1


class TestCompileSMToSystem:
    def test_returns_system_ir(self, door_model):
        ir = compile_sm_to_system(door_model)
        assert ir.name == "Door"
        assert len(ir.blocks) > 0

    def test_block_count(self, door_model):
        ir = compile_sm_to_system(door_model)
        # 1 event + 2 transitions + 2 state mechanisms = 5
        assert len(ir.blocks) == 5

    def test_temporal_wirings(self, door_model):
        ir = compile_sm_to_system(door_model)
        temporal = [w for w in ir.wirings if w.is_temporal]
        # Closed -> Open Door, Open -> Close Door
        assert len(temporal) == 2

    def test_hierarchy_exists(self, door_model):
        ir = compile_sm_to_system(door_model)
        assert ir.hierarchy is not None

    def test_method_delegation(self, door_model):
        ir = door_model.compile_system()
        assert ir.name == "Door"

    def test_turnstile(self, turnstile_model):
        ir = compile_sm_to_system(turnstile_model)
        # 2 events + 2 transitions + 2 state mechanisms = 6
        assert len(ir.blocks) == 6

    def test_with_regions(self):
        model = StateMachineModel(
            name="Composite",
            states=[
                State(name="A", is_initial=True),
                State(name="B"),
                State(name="C"),
                State(name="D"),
            ],
            events=[Event(name="E")],
            transitions=[
                Transition(name="T1", source="A", target="B", event="E"),
                Transition(name="T2", source="C", target="D", event="E"),
            ],
            regions=[
                Region(name="R1", states=["A", "B"]),
                Region(name="R2", states=["C", "D"]),
            ],
        )
        ir = compile_sm_to_system(model)
        assert len(ir.blocks) == 7  # 1 event + 2 transitions + 4 states
