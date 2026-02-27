"""Tests for the Thermostat PID model (gds-control DSL)."""

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
from thermostat_dsl.model import (
    build_canonical,
    build_model,
    build_spec,
    build_system,
)

# -- Model Declaration -------------------------------------------------------


class TestModel:
    def test_two_states(self):
        model = build_model()
        assert len(model.states) == 2
        assert {s.name for s in model.states} == {"temperature", "energy_consumed"}

    def test_one_input(self):
        model = build_model()
        assert len(model.inputs) == 1
        assert model.inputs[0].name == "setpoint"

    def test_one_sensor(self):
        model = build_model()
        assert len(model.sensors) == 1
        assert model.sensors[0].name == "temp_sensor"

    def test_sensor_observes_temperature(self):
        model = build_model()
        sensor = model.sensors[0]
        assert sensor.observes == ["temperature"]

    def test_one_controller(self):
        model = build_model()
        assert len(model.controllers) == 1
        assert model.controllers[0].name == "PID"

    def test_controller_reads_sensor_and_setpoint(self):
        model = build_model()
        pid = model.controllers[0]
        assert set(pid.reads) == {"temp_sensor", "setpoint"}

    def test_controller_drives_both_states(self):
        model = build_model()
        pid = model.controllers[0]
        assert set(pid.drives) == {"temperature", "energy_consumed"}

    def test_initial_values(self):
        model = build_model()
        initials = {s.name: s.initial for s in model.states}
        assert initials["temperature"] == 20.0
        assert initials["energy_consumed"] == 0.0


# -- DSL Verification (CS checks) --------------------------------------------


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

    def test_energy_consumed_unobserved(self):
        """energy_consumed is not observed by any sensor -- expected warning."""
        model = build_model()
        report = cs_verify(model)
        unobserved = [
            f for f in report.findings if f.check_id == "CS-002" and not f.passed
        ]
        # energy_consumed has no sensor observing it
        unobserved_states = [f.message for f in unobserved]
        assert any("energy_consumed" in msg for msg in unobserved_states)


# -- GDSSpec (compiled from DSL) ----------------------------------------------


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert {"temperature", "energy_consumed"} == set(spec.entities.keys())

    def test_entities_have_value_variable(self):
        spec = build_spec()
        for entity in spec.entities.values():
            assert "value" in entity.variables

    def test_five_blocks(self):
        """1 input + 1 sensor + 1 controller + 2 dynamics = 5 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 5

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 1  # setpoint
        assert len(policies) == 2  # temp_sensor, PID
        assert len(mechanisms) == 2  # temperature Dynamics, energy_consumed Dynamics

    def test_input_is_boundary_action(self):
        spec = build_spec()
        setpoint = spec.blocks["setpoint"]
        assert isinstance(setpoint, BoundaryAction)
        assert setpoint.interface.forward_in == ()

    def test_sensor_is_policy(self):
        spec = build_spec()
        assert isinstance(spec.blocks["temp_sensor"], Policy)

    def test_controller_is_policy(self):
        spec = build_spec()
        assert isinstance(spec.blocks["PID"], Policy)

    def test_dynamics_are_mechanisms(self):
        spec = build_spec()
        for name in ["temperature Dynamics", "energy_consumed Dynamics"]:
            block = spec.blocks[name]
            assert isinstance(block, Mechanism)
            assert len(block.updates) == 1


# -- Canonical Projection -----------------------------------------------------


class TestCanonical:
    def test_state_dim_equals_two(self):
        """dim(x) = 2: temperature, energy_consumed."""
        c = build_canonical()
        assert len(c.state_variables) == 2

    def test_input_dim_equals_one(self):
        """dim(u) = 1: setpoint."""
        c = build_canonical()
        assert len(c.boundary_blocks) == 1
        assert "setpoint" in c.boundary_blocks

    def test_two_mechanisms(self):
        """|f| = 2 dynamics mechanisms."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 2
        assert "temperature Dynamics" in c.mechanism_blocks
        assert "energy_consumed Dynamics" in c.mechanism_blocks

    def test_two_policies(self):
        """|g| = 2: 1 sensor + 1 controller."""
        c = build_canonical()
        assert len(c.policy_blocks) == 2
        assert "temp_sensor" in c.policy_blocks
        assert "PID" in c.policy_blocks

    def test_no_control_blocks(self):
        """ControlAction unused in control DSL -- all blocks are BA/Policy/Mechanism."""
        c = build_canonical()
        assert len(c.control_blocks) == 0

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


# -- SystemIR and Composition ------------------------------------------------


class TestSystem:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Thermostat PID"

    def test_five_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 5

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "setpoint",
            "temp_sensor",
            "PID",
            "temperature Dynamics",
            "energy_consumed Dynamics",
        }
        assert names == expected

    def test_one_temporal_wiring(self):
        """One temporal loop: temperature Dynamics -> temp_sensor."""
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 1

    def test_temporal_pair(self):
        system = build_system()
        temporal_pairs = {(w.source, w.target) for w in system.wirings if w.is_temporal}
        assert ("temperature Dynamics", "temp_sensor") in temporal_pairs

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_feedback_wirings(self):
        """No within-timestep backward flow -- unlike raw thermostat.

        The raw thermostat has .feedback() for energy cost, but the control
        DSL only generates .loop() (temporal COVARIANT).
        """
        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 0


# -- GDS Verification --------------------------------------------------------


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


# -- Query API ---------------------------------------------------------------


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "temperature Dynamics" in updates["temperature"]["value"]
        assert "energy_consumed Dynamics" in updates["energy_consumed"]["value"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 2
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_temperature(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("temperature", "value")
        assert "temperature Dynamics" in affecting

    def test_blocks_affecting_energy(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("energy_consumed", "value")
        assert "energy_consumed Dynamics" in affecting
