"""Tests for semantic verification checks (spec_checks)."""

import pytest

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.canonical import project_canonical
from gds.constraints import AdmissibleInputConstraint, TransitionSignature
from gds.execution import ExecutionContract
from gds.parameters import ParameterDef
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef
from gds.verification.findings import Severity
from gds.verification.spec_checks import (
    check_admissibility_references,
    check_canonical_wellformedness,
    check_completeness,
    check_controlaction_pathway,
    check_determinism,
    check_disturbance_routing,
    check_execution_contract_compatibility,
    check_parameter_references,
    check_reachability,
    check_transition_reads,
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


@pytest.mark.requirement("SC-001")
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


@pytest.mark.requirement("SC-002")
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


@pytest.mark.requirement("SC-003")
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


@pytest.mark.requirement("SC-004")
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


# ── SC-010: ControlAction pathway ───���─────────────────��────


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


# -- SC-005: Parameter References ------------------------------------


@pytest.mark.requirement("SC-005")
class TestParameterReferences:
    def test_unresolved_param_detected(self):
        """Block uses a parameter not registered in the spec."""
        spec = GDSSpec(name="Test")
        m = Mechanism(
            name="Mech",
            interface=Interface(forward_in=(port("X"),)),
            updates=[("E", "v")],
            params_used=["alpha"],
        )
        spec.register_block(m)
        findings = check_parameter_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert failed[0].check_id == "SC-005"
        assert failed[0].severity == Severity.ERROR

    def test_resolved_params_pass(self):
        """All params_used entries resolve to registered parameters."""
        rate_type = TypeDef(name="Rate", python_type=float)
        spec = GDSSpec(name="Test")
        spec.register_type(rate_type)
        spec.register_parameter(ParameterDef(name="alpha", typedef=rate_type))
        m = Mechanism(
            name="Mech",
            interface=Interface(forward_in=(port("X"),)),
            updates=[("E", "v")],
            params_used=["alpha"],
        )
        spec.register_block(m)
        findings = check_parameter_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 0

    def test_no_params_passes(self):
        """Spec with no parameter usage passes trivially."""
        spec = GDSSpec(name="Empty")
        findings = check_parameter_references(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# -- SC-006/SC-007: Canonical Wellformedness --------------------------


@pytest.mark.requirement("SC-006")
@pytest.mark.requirement("SC-007")
class TestCanonicalWellformedness:
    def test_no_mechanisms_warns(self):
        """Spec with no mechanisms should warn that f is empty (SC-006)."""
        spec = GDSSpec(name="Test")
        # Add a policy but no mechanism
        p = Policy(name="P")
        spec.register_block(p)
        findings = check_canonical_wellformedness(spec)
        sc006 = [f for f in findings if f.check_id == "SC-006"]
        assert len(sc006) == 1
        assert not sc006[0].passed
        assert sc006[0].severity == Severity.WARNING

    def test_no_entities_warns(self):
        """Spec with no entities should warn that X is empty (SC-007)."""
        spec = GDSSpec(name="Test")
        m = Mechanism(name="M", updates=[])
        spec.register_block(m)
        findings = check_canonical_wellformedness(spec)
        sc007 = [f for f in findings if f.check_id == "SC-007"]
        assert len(sc007) == 1
        assert not sc007[0].passed
        assert sc007[0].severity == Severity.WARNING

    def test_wellformed_passes(self, entity_with_var):
        """Spec with both mechanisms and entities passes both checks."""
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        m = Mechanism(name="M", updates=[("Prey", "population")])
        spec.register_block(m)
        findings = check_canonical_wellformedness(spec)
        sc006 = [f for f in findings if f.check_id == "SC-006"]
        sc007 = [f for f in findings if f.check_id == "SC-007"]
        assert all(f.passed for f in sc006)
        assert all(f.passed for f in sc007)


# -- SC-008: Admissibility References ---------------------------------


@pytest.mark.requirement("SC-008")
class TestAdmissibilityReferences:
    def test_nonexistent_boundary_detected(self):
        """Constraint referencing a missing BoundaryAction raises ERROR."""
        spec = GDSSpec(name="Test")
        ac = AdmissibleInputConstraint(
            name="limit",
            boundary_block="Ghost",
            depends_on=[],
        )
        spec.register_admissibility(ac)
        findings = check_admissibility_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert failed[0].check_id == "SC-008"
        assert failed[0].severity == Severity.ERROR

    def test_valid_constraint_passes(self, entity_with_var):
        """Constraint referencing a registered BoundaryAction passes."""
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        ba = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Signal"),)),
        )
        spec.register_block(ba)
        ac = AdmissibleInputConstraint(
            name="limit",
            boundary_block="Sensor",
            depends_on=[("Prey", "population")],
        )
        spec.register_admissibility(ac)
        findings = check_admissibility_references(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 0

    def test_no_constraints_passes(self):
        """Spec with no admissibility constraints passes trivially."""
        spec = GDSSpec(name="Empty")
        findings = check_admissibility_references(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# -- SC-009: Transition Reads ------------------------------------------


@pytest.mark.requirement("SC-009")
class TestTransitionReads:
    def test_nonexistent_mechanism_detected(self):
        """Signature referencing a missing Mechanism raises ERROR."""
        spec = GDSSpec(name="Test")
        ts = TransitionSignature(
            mechanism="Ghost",
            reads=[],
        )
        spec.register_transition_signature(ts)
        findings = check_transition_reads(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) >= 1
        assert failed[0].check_id == "SC-009"
        assert failed[0].severity == Severity.ERROR

    def test_valid_signature_passes(self, entity_with_var):
        """Signature referencing a registered Mechanism passes."""
        spec = GDSSpec(name="Test")
        spec.register_entity(entity_with_var)
        m = Mechanism(name="Update", updates=[("Prey", "population")])
        spec.register_block(m)
        ts = TransitionSignature(
            mechanism="Update",
            reads=[("Prey", "population")],
        )
        spec.register_transition_signature(ts)
        findings = check_transition_reads(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 0

    def test_no_signatures_passes(self):
        """Spec with no transition signatures passes trivially."""
        spec = GDSSpec(name="Empty")
        findings = check_transition_reads(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) >= 1


# -- SC-011: ExecutionContract Compatibility ----------------------------


@pytest.mark.requirement("SC-011")
class TestExecutionContractCompatibility:
    def test_no_contract_info(self):
        """Spec with no ExecutionContract produces INFO finding."""
        spec = GDSSpec(name="NoContract")
        findings = check_execution_contract_compatibility(spec)
        assert len(findings) == 1
        assert findings[0].check_id == "SC-011"
        assert findings[0].passed
        assert findings[0].severity == Severity.INFO
        assert "no executioncontract" in findings[0].message.lower()

    def test_discrete_contract_info(self):
        """Spec with valid discrete contract produces INFO with details."""
        spec = GDSSpec(name="Discrete")
        spec.execution_contract = ExecutionContract(time_domain="discrete")
        findings = check_execution_contract_compatibility(spec)
        assert len(findings) == 1
        assert findings[0].check_id == "SC-011"
        assert findings[0].passed
        assert "discrete" in findings[0].message

    def test_atemporal_contract_info(self):
        """Spec with atemporal contract produces INFO."""
        spec = GDSSpec(name="Atemporal")
        spec.execution_contract = ExecutionContract(time_domain="atemporal")
        findings = check_execution_contract_compatibility(spec)
        assert len(findings) == 1
        assert findings[0].passed
        assert "atemporal" in findings[0].message


# -- DST-001: Disturbance Routing ----------------------------------------


class TestDisturbanceRouting:
    def test_no_disturbance_returns_empty(self):
        """Specs without disturbance-tagged blocks produce no findings."""
        spec = GDSSpec(name="NoDist")
        ba = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Signal"),)),
        )
        spec.register_block(ba)
        findings = check_disturbance_routing(spec)
        assert len(findings) == 0

    def test_valid_routing_to_mechanism_passes(self):
        """Disturbance wired to Mechanism passes DST-001."""
        spec = GDSSpec(name="ValidDist")
        dist = BoundaryAction(
            name="Wind",
            interface=Interface(forward_out=(port("Force"),)),
            tags={"role": "disturbance"},
        )
        m = Mechanism(
            name="Plant",
            interface=Interface(forward_in=(port("Force"),)),
            updates=[("Room", "temperature")],
        )
        spec.register_block(dist)
        spec.register_block(m)
        spec.register_wiring(
            SpecWiring(
                name="DistToMech",
                block_names=["Wind", "Plant"],
                wires=[Wire(source="Wind", target="Plant")],
            )
        )
        findings = check_disturbance_routing(spec)
        passed = [f for f in findings if f.passed]
        assert len(passed) == 1
        assert passed[0].check_id == "DST-001"

    def test_routing_to_policy_fails(self):
        """Disturbance wired to Policy produces ERROR."""
        spec = GDSSpec(name="BadDist")
        dist = BoundaryAction(
            name="Wind",
            interface=Interface(forward_out=(port("Force"),)),
            tags={"role": "disturbance"},
        )
        p = Policy(
            name="Controller",
            interface=Interface(
                forward_in=(port("Force"),),
                forward_out=(port("Command"),),
            ),
        )
        spec.register_block(dist)
        spec.register_block(p)
        spec.register_wiring(
            SpecWiring(
                name="DistToPolicy",
                block_names=["Wind", "Controller"],
                wires=[Wire(source="Wind", target="Controller")],
            )
        )
        findings = check_disturbance_routing(spec)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1
        assert failed[0].check_id == "DST-001"
        assert failed[0].severity == Severity.ERROR
        assert "Wind" in failed[0].message
        assert "Controller" in failed[0].message


# -- Canonical disturbance_ports ─────────────────────────────────


class TestCanonicalDisturbancePorts:
    def test_disturbance_ports_partitioned(self):
        """Disturbance-tagged BoundaryAction ports go to disturbance_ports."""
        spec = GDSSpec(name="WithDist")
        sensor = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Temperature"),)),
        )
        wind = BoundaryAction(
            name="Wind",
            interface=Interface(forward_out=(port("Force"),)),
            tags={"role": "disturbance"},
        )
        spec.register_block(sensor)
        spec.register_block(wind)
        canonical = project_canonical(spec)
        assert canonical.input_ports == (("Sensor", "Temperature"),)
        assert canonical.disturbance_ports == (("Wind", "Force"),)
        assert canonical.has_disturbances is True

    def test_no_disturbance_all_in_input_ports(self):
        """Without disturbance tags, all BoundaryAction ports are input_ports."""
        spec = GDSSpec(name="NoDist")
        sensor = BoundaryAction(
            name="Sensor",
            interface=Interface(forward_out=(port("Temperature"),)),
        )
        env = BoundaryAction(
            name="Environment",
            interface=Interface(forward_out=(port("Humidity"),)),
        )
        spec.register_block(sensor)
        spec.register_block(env)
        canonical = project_canonical(spec)
        assert len(canonical.input_ports) == 2
        assert canonical.disturbance_ports == ()
        assert canonical.has_disturbances is False
