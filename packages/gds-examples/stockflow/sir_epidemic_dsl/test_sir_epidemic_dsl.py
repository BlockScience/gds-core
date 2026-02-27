"""Tests for the SIR Epidemic model (gds-stockflow DSL)."""

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
from sir_epidemic_dsl.model import (
    build_canonical,
    build_model,
    build_spec,
    build_system,
)
from stockflow.verification.engine import verify as sf_verify

# ── Model Declaration ──────────────────────────────────────────


class TestModel:
    def test_three_stocks(self):
        model = build_model()
        assert len(model.stocks) == 3
        assert {s.name for s in model.stocks} == {
            "Susceptible",
            "Infected",
            "Recovered",
        }

    def test_two_flows(self):
        model = build_model()
        assert len(model.flows) == 2
        assert {f.name for f in model.flows} == {"Infection", "Recovery"}

    def test_infection_flow_endpoints(self):
        model = build_model()
        infection = next(f for f in model.flows if f.name == "Infection")
        assert infection.source == "Susceptible"
        assert infection.target == "Infected"

    def test_recovery_flow_endpoints(self):
        model = build_model()
        recovery = next(f for f in model.flows if f.name == "Recovery")
        assert recovery.source == "Infected"
        assert recovery.target == "Recovered"

    def test_two_auxiliaries(self):
        model = build_model()
        assert len(model.auxiliaries) == 2
        assert {a.name for a in model.auxiliaries} == {
            "Infection Rate",
            "Recovery Rate",
        }

    def test_infection_rate_inputs(self):
        model = build_model()
        inf_rate = next(a for a in model.auxiliaries if a.name == "Infection Rate")
        assert set(inf_rate.inputs) == {
            "Susceptible",
            "Infected",
            "Contact Rate",
        }

    def test_recovery_rate_inputs(self):
        model = build_model()
        rec_rate = next(a for a in model.auxiliaries if a.name == "Recovery Rate")
        assert set(rec_rate.inputs) == {"Infected", "Recovery Time"}

    def test_two_converters(self):
        model = build_model()
        assert len(model.converters) == 2
        assert {c.name for c in model.converters} == {
            "Contact Rate",
            "Recovery Time",
        }

    def test_initial_values(self):
        model = build_model()
        initials = {s.name: s.initial for s in model.stocks}
        assert initials["Susceptible"] == 999.0
        assert initials["Infected"] == 1.0
        assert initials["Recovered"] == 0.0


# ── DSL Verification (SF checks) ──────────────────────────────


class TestDSLVerification:
    def test_sf_checks_pass(self):
        model = build_model()
        report = sf_verify(model, include_gds_checks=False)
        errors = [
            f for f in report.findings if not f.passed and f.severity.value == "error"
        ]
        assert errors == [], [f.message for f in errors]

    def test_no_orphan_stocks(self):
        model = build_model()
        report = sf_verify(model, include_gds_checks=False)
        orphans = [
            f for f in report.findings if f.check_id == "SF-001" and not f.passed
        ]
        assert orphans == []

    def test_flow_stock_validity(self):
        model = build_model()
        report = sf_verify(model, include_gds_checks=False)
        invalid = [
            f for f in report.findings if f.check_id == "SF-002" and not f.passed
        ]
        assert invalid == []

    def test_auxiliary_acyclicity(self):
        model = build_model()
        report = sf_verify(model, include_gds_checks=False)
        cycles = [f for f in report.findings if f.check_id == "SF-003" and not f.passed]
        assert cycles == []

    def test_converter_connectivity(self):
        model = build_model()
        report = sf_verify(model, include_gds_checks=False)
        disconnected = [
            f for f in report.findings if f.check_id == "SF-004" and not f.passed
        ]
        assert disconnected == []


# ── GDSSpec (compiled from DSL) ────────────────────────────────


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_three_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 3
        assert {"Susceptible", "Infected", "Recovered"} == set(spec.entities.keys())

    def test_entities_have_level_variable(self):
        spec = build_spec()
        for entity in spec.entities.values():
            assert "level" in entity.variables

    def test_nine_blocks(self):
        """2 converters + 2 auxiliaries + 2 flows + 3 mechanisms = 9 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 9

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 2  # Contact Rate, Recovery Time
        assert len(policies) == 4  # Infection Rate, Recovery Rate, Infection, Recovery
        assert len(mechanisms) == 3  # S/I/R Accumulation

    def test_converters_are_boundary_actions(self):
        spec = build_spec()
        for name in ["Contact Rate", "Recovery Time"]:
            block = spec.blocks[name]
            assert isinstance(block, BoundaryAction)
            assert block.interface.forward_in == ()

    def test_auxiliaries_are_policies(self):
        spec = build_spec()
        for name in ["Infection Rate", "Recovery Rate"]:
            assert isinstance(spec.blocks[name], Policy)

    def test_flows_are_policies(self):
        spec = build_spec()
        for name in ["Infection", "Recovery"]:
            block = spec.blocks[name]
            assert isinstance(block, Policy)
            # Flows have no forward_in in the DSL
            assert block.interface.forward_in == ()

    def test_stock_mechanisms(self):
        spec = build_spec()
        for stock_name in ["Susceptible", "Infected", "Recovered"]:
            block = spec.blocks[f"{stock_name} Accumulation"]
            assert isinstance(block, Mechanism)
            assert (stock_name, "level") in block.updates

    def test_parameters_registered(self):
        spec = build_spec()
        param_names = spec.parameter_schema.names()
        assert "Contact Rate" in param_names
        assert "Recovery Time" in param_names


# ── Canonical Projection ───────────────────────────────────────


class TestCanonical:
    def test_state_dim_equals_three(self):
        """dim(x) = 3: Susceptible, Infected, Recovered levels."""
        c = build_canonical()
        assert len(c.state_variables) == 3

    def test_input_dim_equals_two(self):
        """dim(u) = 2: Contact Rate, Recovery Time."""
        c = build_canonical()
        assert len(c.boundary_blocks) == 2
        assert "Contact Rate" in c.boundary_blocks
        assert "Recovery Time" in c.boundary_blocks

    def test_three_mechanisms(self):
        """|f| = 3 accumulation mechanisms."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 3
        assert "Susceptible Accumulation" in c.mechanism_blocks
        assert "Infected Accumulation" in c.mechanism_blocks
        assert "Recovered Accumulation" in c.mechanism_blocks

    def test_four_policies(self):
        """|g| = 4: 2 auxiliaries + 2 flows."""
        c = build_canonical()
        assert len(c.policy_blocks) == 4

    def test_no_control_blocks(self):
        """ControlAction unused in stockflow DSL."""
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


# ── SystemIR and Composition ──────────────────────────────────


class TestSystem:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "SIR Epidemic"

    def test_nine_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 9

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "Contact Rate",
            "Recovery Time",
            "Infection Rate",
            "Recovery Rate",
            "Infection",
            "Recovery",
            "Susceptible Accumulation",
            "Infected Accumulation",
            "Recovered Accumulation",
        }
        assert names == expected

    def test_temporal_wirings(self):
        """Three temporal loops: stock levels feed auxiliaries across timesteps.

        Susceptible -> Infection Rate, Infected -> Infection Rate,
        Infected -> Recovery Rate.
        """
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 3

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_feedback_wirings(self):
        """No within-timestep backward flow."""
        system = build_system()
        feedback = [w for w in system.wirings if w.is_feedback]
        assert len(feedback) == 0

    def test_conservation_structure(self):
        """Infection and Recovery are inter-stock flows (source AND target)."""
        system = build_system()
        block_names = {b.name for b in system.blocks}
        assert "Susceptible Accumulation" in block_names
        assert "Infected Accumulation" in block_names
        assert "Recovered Accumulation" in block_names


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

    def test_sf_and_gds_combined(self):
        """Full verification: SF + GDS checks together."""
        model = build_model()
        report = sf_verify(model, include_gds_checks=True)
        assert report.checks_total > 0
        sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(sf_findings) > 0
        assert len(gds_findings) > 0


# ── Query API ─────────────────────────────────────────────────


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Susceptible Accumulation" in updates["Susceptible"]["level"]
        assert "Infected Accumulation" in updates["Infected"]["level"]
        assert "Recovered Accumulation" in updates["Recovered"]["level"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 2
        assert len(by_kind["policy"]) == 4
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 3

    def test_blocks_affecting_susceptible(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Susceptible", "level")
        assert "Susceptible Accumulation" in affecting

    def test_blocks_affecting_infected(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Infected", "level")
        assert "Infected Accumulation" in affecting

    def test_blocks_affecting_recovered(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Recovered", "level")
        assert "Recovered Accumulation" in affecting
