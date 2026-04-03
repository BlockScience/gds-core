"""Tests for semantic verification checks (spec_checks)."""

import pytest

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_completeness,
    check_controlaction_pathway,
    check_determinism,
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


# ── SC-010: ControlAction pathway ──────────────────────────


class TestControlActionPathway:
    def test_no_controlaction_returns_empty(self):
        """Specs without ControlAction blocks produce no findings."""
        spec = GDSSpec(name="NoCA")
        p = Policy(name="P")
        m = Mechanism(name="M")
        spec.register_block(p)
        spec.register_block(m)
        findings = check_controlaction_pathway(spec)
        assert len(findings) == 0

    def test_controlaction_not_wired_to_g_passes(self):
        """ControlAction wired to Mechanism (f pathway) passes SC-010."""
        spec = GDSSpec(name="ValidCA")
        ca = ControlAction(
            name="Output",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Observation"),),
            ),
        )
        m = Mechanism(
            name="Plant",
            interface=Interface(forward_in=(port("Observation"),)),
            updates=[("Room", "temperature")],
        )
        spec.register_block(ca)
        spec.register_block(m)
        spec.register_wiring(
            SpecWiring(
                name="CAtoMech",
                block_names=["Output", "Plant"],
                wires=[Wire(source="Output", target="Plant")],
            )
        )
        findings = check_controlaction_pathway(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) == 1
        assert passed[0].check_id == "SC-010"

    def test_controlaction_wired_to_policy_warns(self):
        """ControlAction wired to Policy (g pathway) produces WARNING."""
        spec = GDSSpec(name="BadCA")
        ca = ControlAction(
            name="Output",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        p = Policy(
            name="Controller",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Command"),),
            ),
        )
        spec.register_block(ca)
        spec.register_block(p)
        spec.register_wiring(
            SpecWiring(
                name="CAtoPolicy",
                block_names=["Output", "Controller"],
                wires=[Wire(source="Output", target="Controller")],
            )
        )
        findings = check_controlaction_pathway(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].check_id == "SC-010"
        assert failed[0].severity == Severity.WARNING
        assert "g-pathway" in failed[0].message

    def test_controlaction_wired_to_boundary_warns(self):
        """ControlAction wired to BoundaryAction (g pathway) produces WARNING."""
        spec = GDSSpec(name="BadCA2")
        ca = ControlAction(
            name="Output",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        ba = BoundaryAction(
            name="Boundary",
            interface=Interface(forward_out=(port("Env"),)),
        )
        spec.register_block(ca)
        spec.register_block(ba)
        spec.register_wiring(
            SpecWiring(
                name="CAtoBoundary",
                block_names=["Output", "Boundary"],
                wires=[Wire(source="Output", target="Boundary")],
            )
        )
        findings = check_controlaction_pathway(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].check_id == "SC-010"


# ── Canonical output_ports extraction ──────────────────────


class TestCanonicalOutputPorts:
    def test_output_ports_extracted_from_controlaction(self):
        """project_canonical extracts output_ports from ControlAction forward_out."""
        spec = GDSSpec(name="WithCA")
        ca = ControlAction(
            name="Sensor Output",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Temperature"), port("Humidity")),
            ),
        )
        spec.register_block(ca)
        canonical = project_canonical(spec)
        assert canonical.output_ports == (
            ("Sensor Output", "Temperature"),
            ("Sensor Output", "Humidity"),
        )
        assert canonical.control_blocks == ("Sensor Output",)

    def test_output_ports_empty_without_controlaction(self):
        """project_canonical has empty output_ports when no ControlAction exists."""
        spec = GDSSpec(name="NoCA")
        p = Policy(name="P", interface=Interface(forward_out=(port("X"),)))
        spec.register_block(p)
        canonical = project_canonical(spec)
        assert canonical.output_ports == ()

    def test_formula_includes_output_map_when_controlaction(self):
        """formula() includes y = C(x, d) when ControlAction blocks exist."""
        spec = GDSSpec(name="WithCA")
        ca = ControlAction(
            name="Output",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Y"),),
            ),
        )
        p = Policy(
            name="Controller",
            interface=Interface(forward_in=(port("Z"),), forward_out=(port("D"),)),
        )
        m = Mechanism(name="Plant", updates=[("E", "x")])
        spec.register_block(ca)
        spec.register_block(p)
        spec.register_block(m)
        formula = project_canonical(spec).formula()
        assert "y = C(x, d)" in formula
        assert "f" in formula

    def test_formula_no_output_map_without_controlaction(self):
        """formula() omits C when no ControlAction blocks exist."""
        spec = GDSSpec(name="NoCA")
        p = Policy(name="P")
        m = Mechanism(name="M", updates=[("E", "x")])
        spec.register_block(p)
        spec.register_block(m)
        formula = project_canonical(spec).formula()
        assert "C(x, d)" not in formula
