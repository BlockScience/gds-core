"""Tests for the Double Integrator control model (gds-control DSL)."""

from double_integrator.model import (
    build_canonical,
    build_model,
    build_spec,
    build_system,
)
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
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
from gds_control.verification.engine import verify as cs_verify

# ── Model Declaration ──────────────────────────────────────────


class TestModel:
    def test_two_states(self):
        model = build_model()
        assert len(model.states) == 2
        assert {s.name for s in model.states} == {"position", "velocity"}

    def test_one_input(self):
        model = build_model()
        assert len(model.inputs) == 1
        assert model.inputs[0].name == "force"

    def test_two_sensors(self):
        model = build_model()
        assert len(model.sensors) == 2
        assert {s.name for s in model.sensors} == {"pos_sensor", "vel_sensor"}

    def test_one_controller(self):
        model = build_model()
        assert len(model.controllers) == 1
        assert model.controllers[0].name == "PD"

    def test_controller_reads_all_signals(self):
        model = build_model()
        pd = model.controllers[0]
        assert set(pd.reads) == {"pos_sensor", "vel_sensor", "force"}

    def test_controller_drives_both_states(self):
        model = build_model()
        pd = model.controllers[0]
        assert set(pd.drives) == {"position", "velocity"}

    def test_initial_values(self):
        model = build_model()
        for state in model.states:
            assert state.initial == 0.0


# ── DSL Verification (CS checks) ──────────────────────────────


class TestDSLVerification:
    def test_cs_checks_pass(self):
        model = build_model()
        report = cs_verify(model)
        errors = [
            f
            for f in report.findings
            if not f.passed
            and f.severity.value == "error"
            and f.check_id != "G-002"  # BoundaryActions have no forward_in
        ]
        assert errors == [], [f.message for f in errors]

    def test_no_undriven_states(self):
        model = build_model()
        report = cs_verify(model)
        undriven = [
            f for f in report.findings if f.check_id == "CS-001" and not f.passed
        ]
        assert undriven == []

    def test_no_unobserved_states(self):
        model = build_model()
        report = cs_verify(model)
        unobserved = [
            f for f in report.findings if f.check_id == "CS-002" and not f.passed
        ]
        assert unobserved == []


# ── GDSSpec (compiled from DSL) ────────────────────────────────


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert {"position", "velocity"} == set(spec.entities.keys())

    def test_six_blocks(self):
        """1 input + 2 sensors + 1 controller + 2 dynamics = 6 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 6

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 1  # force
        assert len(policies) == 3  # pos_sensor, vel_sensor, PD
        assert len(mechanisms) == 2  # position Dynamics, velocity Dynamics

    def test_input_is_boundary_action(self):
        spec = build_spec()
        force = spec.blocks["force"]
        assert isinstance(force, BoundaryAction)
        assert force.interface.forward_in == ()

    def test_sensors_are_policies(self):
        spec = build_spec()
        for name in ["pos_sensor", "vel_sensor"]:
            assert isinstance(spec.blocks[name], Policy)

    def test_controller_is_policy(self):
        spec = build_spec()
        assert isinstance(spec.blocks["PD"], Policy)

    def test_dynamics_are_mechanisms(self):
        spec = build_spec()
        for name in ["position Dynamics", "velocity Dynamics"]:
            block = spec.blocks[name]
            assert isinstance(block, Mechanism)
            assert len(block.updates) == 1


# ── Canonical Projection ───────────────────────────────────────


class TestCanonical:
    def test_state_dim_equals_two(self):
        """dim(x) = 2 → rows(A) = 2."""
        c = build_canonical()
        assert len(c.state_variables) == 2

    def test_input_dim_equals_one(self):
        """dim(u) = 1 → cols(B) = 1."""
        c = build_canonical()
        assert len(c.input_ports) == 1

    def test_two_mechanisms(self):
        """|f| = 2 dynamics mechanisms → state transition matrix A."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 2
        assert "position Dynamics" in c.mechanism_blocks
        assert "velocity Dynamics" in c.mechanism_blocks

    def test_three_policies(self):
        """|g| = 3 → 2 sensors (C) + 1 controller (K)."""
        c = build_canonical()
        assert len(c.policy_blocks) == 3
        assert "pos_sensor" in c.policy_blocks
        assert "vel_sensor" in c.policy_blocks
        assert "PD" in c.policy_blocks

    def test_no_control_blocks(self):
        """ControlAction unused in DSL — all blocks are BA/Policy/Mechanism."""
        c = build_canonical()
        assert len(c.control_blocks) == 0

    def test_one_boundary(self):
        c = build_canonical()
        assert len(c.boundary_blocks) == 1
        assert "force" in c.boundary_blocks

    def test_update_map(self):
        """Each mechanism updates exactly one state variable."""
        c = build_canonical()
        update_dict = {name: targets for name, targets in c.update_map}
        assert ("position", "value") in update_dict["position Dynamics"]
        assert ("velocity", "value") in update_dict["velocity Dynamics"]

    def test_decision_ports_cover_all_outputs(self):
        """Decision space D = sensor outputs + controller output."""
        c = build_canonical()
        port_names = {p_name for _, p_name in c.decision_ports}
        assert "pos_sensor Measurement" in port_names
        assert "vel_sensor Measurement" in port_names
        assert "PD Control" in port_names

    def test_role_partition_complete(self):
        """Every block appears in exactly one canonical role."""
        spec = build_spec()
        c = build_canonical()
        all_canonical = (
            set(c.boundary_blocks)
            | set(c.policy_blocks)
            | set(c.mechanism_blocks)
            | set(c.control_blocks)
        )
        assert all_canonical == set(spec.blocks.keys())

    def test_role_partition_disjoint(self):
        c = build_canonical()
        sets = [
            set(c.boundary_blocks),
            set(c.policy_blocks),
            set(c.mechanism_blocks),
            set(c.control_blocks),
        ]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                assert sets[i] & sets[j] == set()


# ── SystemIR and Composition ──────────────────────────────────


class TestSystem:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Double Integrator"

    def test_six_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 6

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "force",
            "pos_sensor",
            "vel_sensor",
            "PD",
            "position Dynamics",
            "velocity Dynamics",
        }
        assert names == expected

    def test_temporal_wirings(self):
        """Two temporal loops: dynamics → sensors across timesteps."""
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 2

    def test_temporal_pairs(self):
        system = build_system()
        temporal_pairs = {(w.source, w.target) for w in system.wirings if w.is_temporal}
        assert ("position Dynamics", "pos_sensor") in temporal_pairs
        assert ("velocity Dynamics", "vel_sensor") in temporal_pairs

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_feedback_wirings(self):
        """No within-timestep backward flow (unlike thermostat)."""
        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 0


# ── GDS Verification ──────────────────────────────────────────


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


# ── Query API ─────────────────────────────────────────────────


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "position Dynamics" in updates["position"]["value"]
        assert "velocity Dynamics" in updates["velocity"]["value"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 3
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_position(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("position", "value")
        assert "position Dynamics" in affecting

    def test_blocks_affecting_velocity(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("velocity", "value")
        assert "velocity Dynamics" in affecting
