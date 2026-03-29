"""Tests for semantic verification checks (spec_checks)."""

import pytest

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_completeness,
    check_control_action_observes,
    check_control_action_routing,
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


# ══════════════════════════════════════════════════════════════
# SC-010: ControlAction Routing
# ══════════════════════════════════════════════════════════════


class TestControlActionRouting:
    """SC-010: ControlAction output must not wire to Policy/BoundaryAction."""

    def test_no_control_action_passes(self):
        """Specs without ControlAction get an INFO pass."""
        spec = GDSSpec(name="Test")
        p = Policy(
            name="P",
            interface=Interface(
                forward_in=(port("in"),),
                forward_out=(port("out"),),
            ),
        )
        spec.register_block(p)
        findings = check_control_action_routing(spec)
        assert all(f.passed for f in findings)
        assert findings[0].check_id == "SC-010"

    def test_valid_routing_ca_to_mechanism(self):
        """ControlAction -> Mechanism is valid."""
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="Observe",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        m = Mechanism(
            name="Update",
            interface=Interface(forward_in=(port("Signal"),)),
            updates=[],
        )
        spec.register_block(ca)
        spec.register_block(m)
        spec.register_wiring(
            SpecWiring(
                name="Forward",
                block_names=["Observe", "Update"],
                wires=[Wire(source="Observe", target="Update")],
            )
        )
        findings = check_control_action_routing(spec)
        assert all(f.passed for f in findings)

    def test_invalid_routing_ca_to_policy(self):
        """ControlAction -> Policy in forward path is a WARNING."""
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="Observe",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        p = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Action"),),
            ),
        )
        spec.register_block(ca)
        spec.register_block(p)
        spec.register_wiring(
            SpecWiring(
                name="BadRoute",
                block_names=["Observe", "Decide"],
                wires=[Wire(source="Observe", target="Decide")],
            )
        )
        findings = check_control_action_routing(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].check_id == "SC-010"
        assert failed[0].severity == Severity.WARNING

    def test_invalid_routing_ca_to_boundary(self):
        """ControlAction -> BoundaryAction in forward path is a WARNING."""
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="Observe",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        ba = BoundaryAction(
            name="Input",
            interface=Interface(forward_out=(port("Data"),)),
        )
        spec.register_block(ca)
        spec.register_block(ba)
        spec.register_wiring(
            SpecWiring(
                name="BadRoute",
                block_names=["Observe", "Input"],
                wires=[Wire(source="Observe", target="Input")],
            )
        )
        findings = check_control_action_routing(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1

    def test_feedback_path_not_in_spec_wiring(self):
        """Feedback routing (.feedback()) is NOT in SpecWiring, so SC-010 allows it.

        SpecWiring only contains forward-path wires. Feedback routing happens
        at the composition layer and never appears as a Wire in SpecWiring.
        This test verifies SC-010 correctly ignores feedback by showing that
        a spec with ControlAction -> Mechanism wiring (forward) passes even
        when a feedback composition exists at the composition layer.
        """
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="Observe",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Signal"),),
            ),
        )
        p = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Other"),),
                forward_out=(port("Command"),),
            ),
        )
        m = Mechanism(
            name="Update",
            interface=Interface(forward_in=(port("Signal"),)),
            updates=[],
        )
        spec.register_block(ca)
        spec.register_block(p)
        spec.register_block(m)
        # Forward-path wiring: CA -> Mechanism (valid)
        # No wire from CA -> Policy in SpecWiring
        # (feedback from CA -> Policy would be via .feedback() at composition layer)
        spec.register_wiring(
            SpecWiring(
                name="Forward",
                block_names=["Observe", "Decide", "Update"],
                wires=[Wire(source="Observe", target="Update")],
            )
        )
        findings = check_control_action_routing(spec)
        assert all(f.passed for f in findings)


# ══════════════════════════════════════════════════════════════
# SC-011: ControlAction Observes References
# ══════════════════════════════════════════════════════════════


class TestControlActionObserves:
    """SC-011: ControlAction.observes must reference valid entity vars."""

    def test_no_control_action_passes(self):
        spec = GDSSpec(name="Test")
        findings = check_control_action_observes(spec)
        assert all(f.passed for f in findings)
        assert findings[0].check_id == "SC-011"

    def test_valid_observes(self, pop_type):
        spec = GDSSpec(name="Test")
        entity = Entity(
            name="Room",
            variables={"temp": StateVariable(name="temp", typedef=pop_type)},
        )
        spec.register_entity(entity)
        ca = ControlAction(
            name="Sensor",
            interface=Interface(
                forward_in=(port("State"),),
                forward_out=(port("Reading"),),
            ),
            observes=[("Room", "temp")],
        )
        spec.register_block(ca)
        findings = check_control_action_observes(spec)
        assert all(f.passed for f in findings)

    def test_unknown_entity(self, pop_type):
        spec = GDSSpec(name="Test")
        ca = ControlAction(
            name="Bad",
            observes=[("Ghost", "x")],
        )
        spec.register_block(ca)
        findings = check_control_action_observes(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].check_id == "SC-011"
        assert failed[0].severity == Severity.ERROR
        assert "Ghost" in failed[0].message

    def test_unknown_variable(self, pop_type):
        spec = GDSSpec(name="Test")
        entity = Entity(
            name="Room",
            variables={"temp": StateVariable(name="temp", typedef=pop_type)},
        )
        spec.register_entity(entity)
        ca = ControlAction(
            name="Bad",
            observes=[("Room", "pressure")],
        )
        spec.register_block(ca)
        findings = check_control_action_observes(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert "Room.pressure" in failed[0].message

    def test_empty_observes_passes(self):
        """ControlAction with observes=[] is valid (no references to check)."""
        spec = GDSSpec(name="Test")
        ca = ControlAction(name="Empty")
        spec.register_block(ca)
        findings = check_control_action_observes(spec)
        assert all(f.passed for f in findings)
