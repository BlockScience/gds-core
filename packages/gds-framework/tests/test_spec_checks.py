"""Tests for semantic verification checks (spec_checks)."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_completeness,
    check_determinism,
    check_disturbance_routing,
    check_reachability,
    check_type_safety,
)


@pytest.fixture
def pop_type():
    return TypeDef(name="Population", python_type=int, constraint=lambda x: x >= 0)


@pytest.fixture
def entity_with_var(pop_type):
    return Entity(
        name="Prey",
        variables={
            "population": StateVariable(name="population", typedef=pop_type),
        },
    )


# ── SC-001: Completeness ────────────────────────────────────


class TestCompleteness:
    def test_orphan_variable_detected(self, entity_with_var):
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        # No mechanism updates Prey.population
        findings = check_completeness(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert "orphan" in failed[0].message.lower()

    def test_all_updated_passes(self, entity_with_var):
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        m = Mechanism(
            name="Update Prey",
            updates=[("Prey", "population")],
        )
        spec.register_block(m)
        findings = check_completeness(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_empty_spec_passes(self):
        spec = GDSSpec(name="Empty")
        findings = check_completeness(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# ── SC-002: Determinism ──────────────────────────────────────


class TestDeterminism:
    def test_write_conflict_detected(self, entity_with_var):
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        m1 = Mechanism(name="Mech1", updates=[("Prey", "population")])
        m2 = Mechanism(name="Mech2", updates=[("Prey", "population")])
        spec.register_block(m1)
        spec.register_block(m2)
        spec.register_wiring(
            SpecWiring(name="Conflict", block_names=["Mech1", "Mech2"])
        )
        findings = check_determinism(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert "write conflict" in failed[0].message.lower()

    def test_non_overlapping_passes(self, pop_type):
        e = Entity(
            name="Species",
            variables={
                "prey_pop": StateVariable(name="prey_pop", typedef=pop_type),
                "pred_pop": StateVariable(name="pred_pop", typedef=pop_type),
            },
        )
        spec = GDSSpec(name="Test")
        spec.register_entity(e)
        m1 = Mechanism(name="UpdatePrey", updates=[("Species", "prey_pop")])
        m2 = Mechanism(name="UpdatePred", updates=[("Species", "pred_pop")])
        spec.register_block(m1)
        spec.register_block(m2)
        spec.register_wiring(
            SpecWiring(name="NoConflict", block_names=["UpdatePrey", "UpdatePred"])
        )
        findings = check_determinism(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 0

    def test_empty_wirings_passes(self):
        spec = GDSSpec(name="Empty")
        findings = check_determinism(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# ── SC-003: Reachability ─────────────────────────────────────


class TestReachability:
    def test_reachable(self):
        spec = GDSSpec(name="Test")
        a = Policy(name="A", interface=Interface(forward_out=(port("X"),)))
        b = Mechanism(name="B", interface=Interface(forward_in=(port("X"),)))
        spec.register_block(a)
        spec.register_block(b)
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                block_names=["A", "B"],
                wires=[Wire(source="A", target="B")],
            )
        )
        findings = check_reachability(spec, "A", "B")
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_unreachable(self):
        spec = GDSSpec(name="Test")
        a = Policy(name="A")
        b = Mechanism(name="B")
        spec.register_block(a)
        spec.register_block(b)
        # No wiring connecting A to B
        findings = check_reachability(spec, "A", "B")
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert "cannot reach" in failed[0].message.lower()

    def test_transitive_reachability(self):
        spec = GDSSpec(name="Test")
        a = Policy(name="A")
        b = Policy(name="B")
        c = Mechanism(name="C")
        spec.register_block(a)
        spec.register_block(b)
        spec.register_block(c)
        spec.register_wiring(
            SpecWiring(
                name="Chain",
                block_names=["A", "B", "C"],
                wires=[
                    Wire(source="A", target="B"),
                    Wire(source="B", target="C"),
                ],
            )
        )
        findings = check_reachability(spec, "A", "C")
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# ── SC-004: Type safety ──────────────────────────────────────


class TestTypeSafety:
    def test_valid_space_reference(self):
        t = TypeDef(name="Prob", python_type=float)
        from gds.spaces import Space

        s = Space(name="Signal", fields={"x": t})
        spec = GDSSpec(name="Test")
        spec.register_type(t)
        spec.register_space(s)
        a = Policy(name="A")
        b = Mechanism(name="B")
        spec.register_block(a)
        spec.register_block(b)
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                block_names=["A", "B"],
                wires=[Wire(source="A", target="B", space="Signal")],
            )
        )
        findings = check_type_safety(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1

    def test_unregistered_space_detected(self):
        spec = GDSSpec(name="Test")
        a = Policy(name="A")
        b = Mechanism(name="B")
        spec.register_block(a)
        spec.register_block(b)
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                block_names=["A", "B"],
                wires=[Wire(source="A", target="B", space="NonExistentSpace")],
            )
        )
        findings = check_type_safety(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert failed[0].severity == Severity.ERROR

    def test_no_space_reference_passes(self):
        spec = GDSSpec(name="Test")
        a = Policy(name="A")
        b = Mechanism(name="B")
        spec.register_block(a)
        spec.register_block(b)
        spec.register_wiring(
            SpecWiring(
                name="Flow",
                block_names=["A", "B"],
                wires=[Wire(source="A", target="B")],
            )
        )
        findings = check_type_safety(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# -- DST-001: Disturbance routing ----------------------------------------


@pytest.mark.requirement("DST-001")
class TestDisturbanceRouting:
    def test_no_disturbance_returns_empty(self):
        """Specs without disturbance-tagged blocks produce no findings."""
        spec = GDSSpec(name="NoDist")
        ba = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Signal"),)),
        )
        p = Policy(
            name="Controller",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Command"),),
            ),
        )
        spec.register_block(ba)
        spec.register_block(p)
        findings = check_disturbance_routing(spec)
        assert len(findings) == 0

    def test_disturbance_wired_to_mechanism_passes(self):
        """Disturbance routed directly to Mechanism is valid."""
        spec = GDSSpec(name="ValidDist")
        w = BoundaryAction(
            name="Wind",
            interface=Interface(forward_out=(port("Force"),)),
            tags={"role": "disturbance"},
        )
        m = Mechanism(
            name="Plant",
            interface=Interface(forward_in=(port("Force"),)),
            updates=[("Body", "position")],
        )
        spec.register_block(w)
        spec.register_block(m)
        spec.register_wiring(
            SpecWiring(
                name="disturbance_wiring",
                block_names=["Wind", "Plant"],
                wires=[Wire(source="Wind", target="Plant", space="Force")],
            )
        )
        findings = check_disturbance_routing(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) == 1
        assert passed[0].check_id == "DST-001"

    def test_disturbance_wired_to_policy_fails(self):
        """Disturbance routed to Policy violates bypass invariant."""
        spec = GDSSpec(name="BadDist")
        w = BoundaryAction(
            name="Noise",
            interface=Interface(forward_out=(port("Signal"),)),
            tags={"role": "disturbance"},
        )
        p = Policy(
            name="Controller",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Command"),),
            ),
        )
        spec.register_block(w)
        spec.register_block(p)
        spec.register_wiring(
            SpecWiring(
                name="bad_wiring",
                block_names=["Noise", "Controller"],
                wires=[
                    Wire(source="Noise", target="Controller", space="Signal"),
                ],
            )
        )
        findings = check_disturbance_routing(spec)
        errors = [f for f in findings if not f.passed]
        assert len(errors) == 1
        assert errors[0].check_id == "DST-001"
        assert "Noise" in errors[0].message


# -- Canonical disturbance port partitioning ------------------------------


class TestCanonicalDisturbancePorts:
    def test_disturbance_ports_extracted(self):
        """project_canonical() separates disturbance from controlled ports."""
        spec = GDSSpec(name="WithDist")
        sensor = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Temp"),)),
        )
        wind = BoundaryAction(
            name="Wind",
            interface=Interface(forward_out=(port("Force"),)),
            tags={"role": "disturbance"},
        )
        spec.register_block(sensor)
        spec.register_block(wind)
        canonical = project_canonical(spec)
        assert ("Sensor", "Temp") in canonical.input_ports
        assert ("Wind", "Force") in canonical.disturbance_ports
        assert ("Wind", "Force") not in canonical.input_ports

    def test_no_disturbance_all_in_input_ports(self):
        """Without disturbance tags, all BoundaryAction ports are input_ports."""
        spec = GDSSpec(name="NoDist")
        ba = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Temp"),)),
        )
        spec.register_block(ba)
        canonical = project_canonical(spec)
        assert len(canonical.input_ports) == 1
        assert len(canonical.disturbance_ports) == 0
