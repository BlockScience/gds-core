"""Tests for the Crosswalk Problem model."""

from crosswalk.model import (
    BinaryChoice,
    StreetPosition,
    TrafficState,
    build_spec,
    build_system,
    observe_traffic,
    pedestrian_decision,
    safety_check,
    street,
    traffic_transition,
)
from gds.blocks.composition import StackComposition
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
    check_reachability,
    check_type_safety,
)


class TestTypes:
    def test_traffic_state_valid(self):
        assert TrafficState.check_value(-1)
        assert TrafficState.check_value(0)
        assert TrafficState.check_value(1)

    def test_traffic_state_invalid(self):
        assert not TrafficState.check_value(-2)
        assert not TrafficState.check_value(2)
        assert not TrafficState.check_value(0.5)

    def test_binary_choice(self):
        assert BinaryChoice.check_value(0)
        assert BinaryChoice.check_value(1)
        assert not BinaryChoice.check_value(2)
        assert not BinaryChoice.check_value(-1)

    def test_street_position_bounded(self):
        assert StreetPosition.check_value(0.0)
        assert StreetPosition.check_value(0.5)
        assert StreetPosition.check_value(1.0)
        assert not StreetPosition.check_value(-0.1)
        assert not StreetPosition.check_value(1.1)


class TestEntities:
    def test_street_has_traffic_state(self):
        assert "traffic_state" in street.variables

    def test_street_valid_state(self):
        assert street.validate_state({"traffic_state": 1}) == []
        assert street.validate_state({"traffic_state": 0}) == []
        assert street.validate_state({"traffic_state": -1}) == []

    def test_street_invalid_state(self):
        assert len(street.validate_state({"traffic_state": 2})) > 0
        assert len(street.validate_state({"traffic_state": -2})) > 0


class TestBlocks:
    def test_observe_traffic_is_boundary(self):
        assert isinstance(observe_traffic, BoundaryAction)
        assert observe_traffic.interface.forward_in == ()

    def test_pedestrian_decision_is_policy(self):
        assert isinstance(pedestrian_decision, Policy)
        assert len(pedestrian_decision.interface.forward_in) == 1
        assert len(pedestrian_decision.interface.forward_out) == 1

    def test_safety_check_is_control_action(self):
        assert isinstance(safety_check, ControlAction)
        assert safety_check.kind == "control"
        assert len(safety_check.params_used) == 1
        assert "crosswalk_location" in safety_check.params_used

    def test_traffic_transition_is_terminal_mechanism(self):
        assert isinstance(traffic_transition, Mechanism)
        assert traffic_transition.interface.forward_out == ()
        assert traffic_transition.updates == [("Street", "traffic_state")]


class TestComposition:
    def test_sequential_pipeline_builds(self):
        pipeline = (
            observe_traffic >> pedestrian_decision >> safety_check >> traffic_transition
        )
        assert isinstance(pipeline, StackComposition)

    def test_flatten_yields_four_blocks(self):
        pipeline = (
            observe_traffic >> pedestrian_decision >> safety_check >> traffic_transition
        )
        flat = pipeline.flatten()
        assert len(flat) == 4

    def test_all_wirings_covariant(self):
        system = build_system()
        for w in system.wirings:
            assert w.direction == FlowDirection.COVARIANT
            assert not w.is_feedback
            assert not w.is_temporal


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_one_entity(self):
        spec = build_spec()
        assert len(spec.entities) == 1
        assert "Street" in spec.entities

    def test_spec_has_four_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 4

    def test_spec_has_one_param(self):
        spec = build_spec()
        assert set(spec.parameters.keys()) == {"crosswalk_location"}


class TestVerification:
    def test_ir_compilation(self):
        system = build_system()
        assert system.name == "Crosswalk Problem"
        assert len(system.blocks) == 4

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

    def test_reachability_observe_to_transition(self):
        spec = build_spec()
        findings = check_reachability(spec, "Observe Traffic", "Traffic Transition")
        assert any(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


class TestQuery:
    def test_param_to_blocks(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Safety Check" in mapping["crosswalk_location"]

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Traffic Transition" in updates["Street"]["traffic_state"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 1
        assert len(by_kind["control"]) == 1
        assert len(by_kind["mechanism"]) == 1

    def test_dependency_graph(self):
        spec = build_spec()
        q = SpecQuery(spec)
        deps = q.dependency_graph()
        assert "Pedestrian Decision" in deps["Observe Traffic"]
        assert "Safety Check" in deps["Pedestrian Decision"]
        assert "Traffic Transition" in deps["Safety Check"]
