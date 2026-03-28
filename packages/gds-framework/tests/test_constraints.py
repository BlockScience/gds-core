"""Tests for structural annotations: AdmissibleInputConstraint,
TransitionSignature, StateMetric, and SC-008/SC-009.
"""

import pytest
from pydantic import ValidationError

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.constraints import AdmissibleInputConstraint, StateMetric, TransitionSignature
from gds.spec import GDSSpec
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_admissibility_references,
    check_transition_reads,
)


@pytest.fixture
def temp_type():
    return TypeDef(name="Temperature", python_type=float)


@pytest.fixture
def room_entity(temp_type):
    return Entity(
        name="Room",
        variables={
            "temperature": StateVariable(name="temperature", typedef=temp_type),
        },
    )


@pytest.fixture
def sensor():
    return BoundaryAction(
        name="Sensor",
        interface=Interface(forward_out=(port("Temperature"),)),
    )


@pytest.fixture
def controller():
    return Policy(
        name="Controller",
        interface=Interface(
            forward_in=(port("Temperature"),),
            forward_out=(port("Heater Command"),),
        ),
    )


@pytest.fixture
def heater():
    return Mechanism(
        name="Heater",
        interface=Interface(forward_in=(port("Heater Command"),)),
        updates=[("Room", "temperature")],
    )


@pytest.fixture
def thermostat_spec(temp_type, room_entity, sensor, controller, heater):
    spec = GDSSpec(name="thermostat")
    spec.collect(temp_type, room_entity, sensor, controller, heater)
    return spec


# ── Model construction ───────────────────────────────────────


class TestAdmissibleInputConstraintModel:
    def test_creates_frozen(self):
        ac = AdmissibleInputConstraint(
            name="balance_limit",
            boundary_block="market_order",
            depends_on=[("Agent", "balance")],
            description="Cannot sell more than owned",
        )
        assert ac.name == "balance_limit"
        assert ac.boundary_block == "market_order"
        assert ac.depends_on == [("Agent", "balance")]
        assert ac.constraint is None

        with pytest.raises(ValidationError):
            ac.name = "changed"  # type: ignore[misc]

    def test_defaults(self):
        ac = AdmissibleInputConstraint(name="test", boundary_block="b")
        assert ac.depends_on == []
        assert ac.constraint is None
        assert ac.description == ""

    def test_with_constraint(self):
        fn = lambda state, u: u <= state["balance"]  # noqa: E731
        ac = AdmissibleInputConstraint(
            name="test",
            boundary_block="b",
            constraint=fn,
        )
        assert ac.constraint is fn


class TestTransitionSignatureModel:
    def test_creates_frozen(self):
        ts = TransitionSignature(
            mechanism="Heater",
            reads=[("Room", "temperature")],
            depends_on_blocks=["Controller"],
        )
        assert ts.mechanism == "Heater"
        assert ts.reads == [("Room", "temperature")]
        assert ts.depends_on_blocks == ["Controller"]

        with pytest.raises(ValidationError):
            ts.mechanism = "changed"  # type: ignore[misc]

    def test_defaults(self):
        ts = TransitionSignature(mechanism="M")
        assert ts.reads == []
        assert ts.depends_on_blocks == []
        assert ts.preserves_invariant == ""

    def test_with_invariant(self):
        ts = TransitionSignature(
            mechanism="M",
            preserves_invariant="temperature >= 0",
        )
        assert ts.preserves_invariant == "temperature >= 0"


# ── Registration ──────────────────────────────────────────────


class TestRegistration:
    def test_register_admissibility_chainable(self, thermostat_spec):
        ac = AdmissibleInputConstraint(
            name="sensor_dep",
            boundary_block="Sensor",
            depends_on=[("Room", "temperature")],
        )
        result = thermostat_spec.register_admissibility(ac)
        assert result is thermostat_spec
        assert "sensor_dep" in thermostat_spec.admissibility_constraints

    def test_register_admissibility_duplicate_raises(self, thermostat_spec):
        ac = AdmissibleInputConstraint(name="dup", boundary_block="Sensor")
        thermostat_spec.register_admissibility(ac)
        with pytest.raises(ValueError, match="already registered"):
            thermostat_spec.register_admissibility(ac)

    def test_multiple_constraints_per_boundary(self, thermostat_spec):
        ac1 = AdmissibleInputConstraint(name="limit_a", boundary_block="Sensor")
        ac2 = AdmissibleInputConstraint(name="limit_b", boundary_block="Sensor")
        thermostat_spec.register_admissibility(ac1)
        thermostat_spec.register_admissibility(ac2)
        assert len(thermostat_spec.admissibility_constraints) == 2

    def test_register_transition_signature_chainable(self, thermostat_spec):
        ts = TransitionSignature(
            mechanism="Heater",
            reads=[("Room", "temperature")],
        )
        result = thermostat_spec.register_transition_signature(ts)
        assert result is thermostat_spec
        assert "Heater" in thermostat_spec.transition_signatures

    def test_register_transition_signature_duplicate_raises(self, thermostat_spec):
        ts = TransitionSignature(mechanism="Heater")
        thermostat_spec.register_transition_signature(ts)
        with pytest.raises(ValueError, match="already registered"):
            thermostat_spec.register_transition_signature(ts)


# ── Validation (validate_spec) ────────────────────────────────


class TestValidation:
    def test_valid_admissibility_no_errors(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="sensor_dep",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert not errors

    def test_admissibility_unknown_block(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(name="bad", boundary_block="NonExistent")
        )
        errors = thermostat_spec.validate_spec()
        assert any("unregistered block" in e for e in errors)

    def test_admissibility_wrong_role(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="bad",
                boundary_block="Controller",  # Policy, not BoundaryAction
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("not a BoundaryAction" in e for e in errors)

    def test_admissibility_unknown_entity(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="bad",
                boundary_block="Sensor",
                depends_on=[("NoSuchEntity", "var")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown entity" in e for e in errors)

    def test_admissibility_unknown_variable(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="bad",
                boundary_block="Sensor",
                depends_on=[("Room", "nonexistent")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown variable" in e for e in errors)

    def test_valid_transition_signature_no_errors(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
                depends_on_blocks=["Controller"],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert not errors

    def test_transition_unknown_block(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(mechanism="NonExistent")
        )
        errors = thermostat_spec.validate_spec()
        assert any("unregistered block" in e for e in errors)

    def test_transition_wrong_role(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(mechanism="Controller")
        )
        errors = thermostat_spec.validate_spec()
        assert any("not a Mechanism" in e for e in errors)

    def test_transition_unknown_read_entity(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("NoSuch", "var")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown entity" in e for e in errors)

    def test_transition_unknown_read_variable(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "nonexistent")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown variable" in e for e in errors)

    def test_transition_unknown_depends_on_block(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                depends_on_blocks=["GhostBlock"],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unregistered block" in e for e in errors)


# ── SC-008: check_admissibility_references ────────────────────


class TestSC008:
    def test_no_constraints_passes(self):
        spec = GDSSpec(name="empty")
        findings = check_admissibility_references(spec)
        assert all(f.passed for f in findings)
        assert findings[0].check_id == "SC-008"

    def test_valid_constraint_passes(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="sensor_dep",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
            )
        )
        findings = check_admissibility_references(thermostat_spec)
        assert all(f.passed for f in findings)

    def test_invalid_block_fails(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(name="bad", boundary_block="NonExistent")
        )
        findings = check_admissibility_references(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].severity == Severity.ERROR

    def test_wrong_role_fails(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(name="bad", boundary_block="Heater")
        )
        findings = check_admissibility_references(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1

    def test_invalid_depends_on_fails(self, thermostat_spec):
        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="bad",
                boundary_block="Sensor",
                depends_on=[("Room", "nonexistent")],
            )
        )
        findings = check_admissibility_references(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


# ── SC-009: check_transition_reads ─────────────────────────────


class TestSC009:
    def test_no_signatures_passes(self):
        spec = GDSSpec(name="empty")
        findings = check_transition_reads(spec)
        assert all(f.passed for f in findings)
        assert findings[0].check_id == "SC-009"

    def test_valid_signature_passes(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
                depends_on_blocks=["Controller"],
            )
        )
        findings = check_transition_reads(thermostat_spec)
        assert all(f.passed for f in findings)

    def test_invalid_mechanism_fails(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(mechanism="NonExistent")
        )
        findings = check_transition_reads(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].severity == Severity.ERROR

    def test_wrong_role_fails(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(mechanism="Controller")
        )
        findings = check_transition_reads(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1

    def test_invalid_reads_fails(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "nonexistent")],
            )
        )
        findings = check_transition_reads(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1

    def test_invalid_depends_on_block_fails(self, thermostat_spec):
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                depends_on_blocks=["GhostBlock"],
            )
        )
        findings = check_transition_reads(thermostat_spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


# ── Canonical projection ──────────────────────────────────────


class TestCanonicalProjection:
    def test_admissibility_map_populated(self, thermostat_spec):
        from gds.canonical import project_canonical

        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="sensor_dep",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
            )
        )
        canonical = project_canonical(thermostat_spec)
        assert len(canonical.admissibility_map) == 1
        name, deps = canonical.admissibility_map[0]
        assert name == "sensor_dep"
        assert ("Room", "temperature") in deps

    def test_read_map_populated(self, thermostat_spec):
        from gds.canonical import project_canonical

        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
            )
        )
        canonical = project_canonical(thermostat_spec)
        assert len(canonical.read_map) == 1
        mech, reads = canonical.read_map[0]
        assert mech == "Heater"
        assert ("Room", "temperature") in reads

    def test_empty_maps_by_default(self, thermostat_spec):
        from gds.canonical import project_canonical

        canonical = project_canonical(thermostat_spec)
        assert canonical.admissibility_map == ()
        assert canonical.read_map == ()


# ── Serialization ──────────────────────────────────────────────


class TestSerialization:
    def test_spec_to_dict_includes_constraints(self, thermostat_spec):
        from gds.serialize import spec_to_dict

        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="sensor_dep",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
                description="reads temp",
            )
        )
        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
                depends_on_blocks=["Controller"],
            )
        )
        d = spec_to_dict(thermostat_spec)
        assert "admissibility_constraints" in d
        assert "sensor_dep" in d["admissibility_constraints"]
        ac_d = d["admissibility_constraints"]["sensor_dep"]
        assert ac_d["boundary_block"] == "Sensor"
        assert ac_d["depends_on"] == [["Room", "temperature"]]
        assert ac_d["has_constraint"] is False

        assert "transition_signatures" in d
        assert "Heater" in d["transition_signatures"]
        ts_d = d["transition_signatures"]["Heater"]
        assert ts_d["reads"] == [["Room", "temperature"]]
        assert ts_d["depends_on_blocks"] == ["Controller"]


# ── Query engine ───────────────────────────────────────────────


class TestQueryEngine:
    def test_admissibility_dependency_map(self, thermostat_spec):
        from gds.query import SpecQuery

        thermostat_spec.register_admissibility(
            AdmissibleInputConstraint(
                name="a",
                boundary_block="Sensor",
                depends_on=[("Room", "temperature")],
            )
        )
        q = SpecQuery(thermostat_spec)
        dep_map = q.admissibility_dependency_map()
        assert "Sensor" in dep_map
        assert ("Room", "temperature") in dep_map["Sensor"]

    def test_mechanism_read_map(self, thermostat_spec):
        from gds.query import SpecQuery

        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
            )
        )
        q = SpecQuery(thermostat_spec)
        read_map = q.mechanism_read_map()
        assert "Heater" in read_map
        assert ("Room", "temperature") in read_map["Heater"]

    def test_variable_readers(self, thermostat_spec):
        from gds.query import SpecQuery

        thermostat_spec.register_transition_signature(
            TransitionSignature(
                mechanism="Heater",
                reads=[("Room", "temperature")],
            )
        )
        q = SpecQuery(thermostat_spec)
        readers = q.variable_readers("Room", "temperature")
        assert "Heater" in readers

    def test_variable_readers_empty(self, thermostat_spec):
        from gds.query import SpecQuery

        q = SpecQuery(thermostat_spec)
        readers = q.variable_readers("Room", "temperature")
        assert readers == []


# ── StateMetric ────────────────────────────────────────────────


class TestStateMetricModel:
    def test_creates_frozen(self):
        sm = StateMetric(
            name="spatial_distance",
            variables=[("Room", "temperature")],
            metric_type="euclidean",
            description="Temperature distance",
        )
        assert sm.name == "spatial_distance"
        assert sm.variables == [("Room", "temperature")]
        assert sm.metric_type == "euclidean"
        assert sm.distance is None

        with pytest.raises(ValidationError):
            sm.name = "changed"  # type: ignore[misc]

    def test_with_callable(self):
        sm = StateMetric(
            name="custom",
            variables=[("Room", "temperature")],
            distance=lambda a, b: abs(a - b),
        )
        assert sm.distance is not None
        assert sm.distance(3.0, 1.0) == 2.0

    def test_defaults(self):
        sm = StateMetric(name="empty")
        assert sm.variables == []
        assert sm.metric_type == ""
        assert sm.distance is None
        assert sm.description == ""


class TestStateMetricRegistration:
    def test_register_chainable(self, thermostat_spec):
        sm = StateMetric(
            name="temp_dist",
            variables=[("Room", "temperature")],
            metric_type="euclidean",
        )
        result = thermostat_spec.register_state_metric(sm)
        assert result is thermostat_spec
        assert "temp_dist" in thermostat_spec.state_metrics

    def test_duplicate_raises(self, thermostat_spec):
        sm = StateMetric(name="dup", variables=[("Room", "temperature")])
        thermostat_spec.register_state_metric(sm)
        with pytest.raises(ValueError, match="already registered"):
            thermostat_spec.register_state_metric(sm)


class TestStateMetricValidation:
    def test_valid_metric_no_errors(self, thermostat_spec):
        thermostat_spec.register_state_metric(
            StateMetric(
                name="temp_dist",
                variables=[("Room", "temperature")],
                metric_type="euclidean",
            )
        )
        errors = thermostat_spec.validate_spec()
        assert not errors

    def test_unknown_entity(self, thermostat_spec):
        thermostat_spec.register_state_metric(
            StateMetric(
                name="bad",
                variables=[("NonExistent", "x")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown entity" in e for e in errors)

    def test_unknown_variable(self, thermostat_spec):
        thermostat_spec.register_state_metric(
            StateMetric(
                name="bad",
                variables=[("Room", "nonexistent_var")],
            )
        )
        errors = thermostat_spec.validate_spec()
        assert any("unknown variable" in e for e in errors)

    def test_empty_variables(self, thermostat_spec):
        thermostat_spec.register_state_metric(StateMetric(name="empty_metric"))
        errors = thermostat_spec.validate_spec()
        assert any("no variables" in e for e in errors)
