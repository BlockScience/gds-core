"""Tests for the Thermostat PID Control model."""

import pytest

from gds.blocks.composition import FeedbackLoop
from gds.blocks.errors import GDSCompositionError
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.ir.models import FlowDirection
from gds.query import SpecQuery
from gds.verification.engine import verify
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import (
    check_completeness,
    check_determinism,
    check_type_safety,
)
from thermostat.model import (
    EnergyCost,
    Temperature,
    build_spec,
    build_system,
    pid_controller,
    room,
    room_plant,
    temperature_sensor,
    update_room,
)


class TestTypes:
    def test_temperature_accepts_any_float(self):
        assert Temperature.check_value(-10.0)
        assert Temperature.check_value(25.5)
        assert Temperature.check_value(100.0)

    def test_temperature_rejects_non_float(self):
        assert not Temperature.check_value(25)

    def test_energy_cost_non_negative(self):
        assert EnergyCost.check_value(0.0)
        assert EnergyCost.check_value(42.5)
        assert not EnergyCost.check_value(-1.0)


class TestEntities:
    def test_room_has_two_variables(self):
        assert len(room.variables) == 2
        assert "temperature" in room.variables
        assert "energy_consumed" in room.variables

    def test_room_validates_state(self):
        assert room.validate_state({"temperature": 22.0, "energy_consumed": 5.0}) == []


class TestBlocks:
    def test_sensor_is_boundary(self):
        assert isinstance(temperature_sensor, BoundaryAction)
        assert temperature_sensor.interface.forward_in == ()

    def test_controller_is_policy_with_backward_in(self):
        assert isinstance(pid_controller, Policy)
        assert len(pid_controller.interface.backward_in) == 1
        assert pid_controller.interface.backward_in[0].name == "Energy Cost"

    def test_plant_is_control_action_with_backward_out(self):
        assert isinstance(room_plant, ControlAction)
        assert len(room_plant.interface.backward_out) == 1
        assert room_plant.interface.backward_out[0].name == "Energy Cost"

    def test_update_is_mechanism(self):
        assert isinstance(update_room, Mechanism)
        assert update_room.updates == [
            ("Room", "temperature"),
            ("Room", "energy_consumed"),
        ]

    def test_mechanism_cannot_have_backward_ports(self):
        from gds.types.interface import Interface, port

        with pytest.raises(GDSCompositionError, match="backward ports must be empty"):
            Mechanism(
                name="Bad",
                interface=Interface(backward_out=(port("Signal"),)),
            )


class TestComposition:
    def test_feedback_loop_builds(self):
        system = build_system()
        assert system.name == "Thermostat PID"

    def test_flatten_yields_four_blocks(self):
        from gds.blocks.composition import Wiring

        pipeline = temperature_sensor >> pid_controller >> room_plant >> update_room
        feedback = pipeline.feedback(
            [
                Wiring(
                    source_block="Room Plant",
                    source_port="Energy Cost",
                    target_block="PID Controller",
                    target_port="Energy Cost",
                    direction=FlowDirection.CONTRAVARIANT,
                )
            ]
        )
        assert isinstance(feedback, FeedbackLoop)
        flat = feedback.flatten()
        assert len(flat) == 4

    def test_feedback_wiring_is_contravariant(self):
        system = build_system()
        feedback_wirings = [w for w in system.wirings if w.is_feedback]
        assert len(feedback_wirings) == 1
        assert feedback_wirings[0].direction == FlowDirection.CONTRAVARIANT

    def test_forward_wirings_are_covariant(self):
        system = build_system()
        forward_wirings = [w for w in system.wirings if not w.is_feedback]
        for w in forward_wirings:
            assert w.direction == FlowDirection.COVARIANT


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_one_entity(self):
        spec = build_spec()
        assert len(spec.entities) == 1
        assert "Room" in spec.entities

    def test_spec_has_four_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 4

    def test_spec_has_four_params(self):
        spec = build_spec()
        assert set(spec.parameters.keys()) == {"setpoint", "Kp", "Ki", "Kd"}


class TestVerification:
    def test_generic_checks_pass(self):
        checks = [
            check_g001_domain_codomain_matching,
            check_g003_direction_consistency,
            check_g004_dangling_wirings,
            check_g005_sequential_type_compatibility,
            check_g006_covariant_acyclicity,
        ]
        system = build_system()
        report = verify(system, checks=checks)
        assert report.errors == 0, [f.message for f in report.findings if not f.passed]

    def test_completeness(self):
        spec = build_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_determinism(self):
        spec = build_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


class TestQuery:
    def test_param_to_blocks(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "PID Controller" in mapping["Kp"]
        assert "PID Controller" in mapping["setpoint"]

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Update Room" in updates["Room"]["temperature"]
        assert "Update Room" in updates["Room"]["energy_consumed"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 1
        assert len(by_kind["control"]) == 1
        assert len(by_kind["mechanism"]) == 1

    def test_blocks_affecting_temperature(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Room", "temperature")
        assert "Update Room" in affecting
