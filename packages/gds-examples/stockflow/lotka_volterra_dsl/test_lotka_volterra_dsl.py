"""Tests for the Lotka-Volterra model (gds-stockflow DSL)."""

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
from lotka_volterra_dsl.model import (
    build_canonical,
    build_model,
    build_spec,
    build_system,
)
from stockflow.verification.engine import verify as sf_verify

# -- Model Declaration -------------------------------------------------------


class TestModel:
    def test_two_stocks(self):
        model = build_model()
        assert len(model.stocks) == 2
        assert {s.name for s in model.stocks} == {"Prey", "Predator"}

    def test_two_flows(self):
        model = build_model()
        assert len(model.flows) == 2
        assert {f.name for f in model.flows} == {
            "Prey Net Change",
            "Predator Net Change",
        }

    def test_prey_net_change_flow(self):
        model = build_model()
        prey_flow = next(f for f in model.flows if f.name == "Prey Net Change")
        assert prey_flow.target == "Prey"

    def test_predator_net_change_flow(self):
        model = build_model()
        pred_flow = next(f for f in model.flows if f.name == "Predator Net Change")
        assert pred_flow.target == "Predator"

    def test_four_auxiliaries(self):
        model = build_model()
        assert len(model.auxiliaries) == 4
        assert {a.name for a in model.auxiliaries} == {
            "Prey Growth",
            "Predation Loss",
            "Predator Growth",
            "Predator Death",
        }

    def test_prey_growth_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Prey Growth")
        assert set(aux.inputs) == {"Prey", "Prey Birth Rate"}

    def test_predation_loss_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Predation Loss")
        assert set(aux.inputs) == {"Prey", "Predator", "Predation Rate"}

    def test_predator_growth_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Predator Growth")
        assert set(aux.inputs) == {"Prey", "Predator", "Predator Efficiency"}

    def test_predator_death_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Predator Death")
        assert set(aux.inputs) == {"Predator", "Predator Death Rate"}

    def test_four_converters(self):
        model = build_model()
        assert len(model.converters) == 4
        assert {c.name for c in model.converters} == {
            "Prey Birth Rate",
            "Predation Rate",
            "Predator Death Rate",
            "Predator Efficiency",
        }

    def test_initial_values(self):
        model = build_model()
        initials = {s.name: s.initial for s in model.stocks}
        assert initials["Prey"] == 100.0
        assert initials["Predator"] == 20.0


# -- DSL Verification (SF checks) --------------------------------------------


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


# -- GDSSpec (compiled from DSL) ----------------------------------------------


class TestSpec:
    def test_spec_validates(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert {"Prey", "Predator"} == set(spec.entities.keys())

    def test_entities_have_level_variable(self):
        spec = build_spec()
        for entity in spec.entities.values():
            assert "level" in entity.variables

    def test_twelve_blocks(self):
        """4 converters + 4 auxiliaries + 2 flows + 2 mechanisms = 12 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 12

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 4  # four converters
        assert len(policies) == 6  # four auxiliaries + two flows
        assert len(mechanisms) == 2  # Prey/Predator Accumulation

    def test_converters_are_boundary_actions(self):
        spec = build_spec()
        for name in [
            "Prey Birth Rate",
            "Predation Rate",
            "Predator Death Rate",
            "Predator Efficiency",
        ]:
            block = spec.blocks[name]
            assert isinstance(block, BoundaryAction)
            assert block.interface.forward_in == ()

    def test_auxiliaries_are_policies(self):
        spec = build_spec()
        for name in [
            "Prey Growth",
            "Predation Loss",
            "Predator Growth",
            "Predator Death",
        ]:
            assert isinstance(spec.blocks[name], Policy)

    def test_flows_are_policies(self):
        spec = build_spec()
        for name in ["Prey Net Change", "Predator Net Change"]:
            block = spec.blocks[name]
            assert isinstance(block, Policy)
            assert block.interface.forward_in == ()

    def test_stock_mechanisms(self):
        spec = build_spec()
        for stock_name in ["Prey", "Predator"]:
            block = spec.blocks[f"{stock_name} Accumulation"]
            assert isinstance(block, Mechanism)
            assert (stock_name, "level") in block.updates

    def test_parameters_registered(self):
        spec = build_spec()
        param_names = spec.parameter_schema.names()
        assert "Prey Birth Rate" in param_names
        assert "Predation Rate" in param_names
        assert "Predator Death Rate" in param_names
        assert "Predator Efficiency" in param_names


# -- Canonical Projection -----------------------------------------------------


class TestCanonical:
    def test_state_dim_equals_two(self):
        """dim(x) = 2: Prey, Predator levels."""
        c = build_canonical()
        assert len(c.state_variables) == 2

    def test_input_dim_equals_four(self):
        """dim(u) = 4: four rate parameter converters."""
        c = build_canonical()
        assert len(c.boundary_blocks) == 4

    def test_two_mechanisms(self):
        """|f| = 2 accumulation mechanisms."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 2
        assert "Prey Accumulation" in c.mechanism_blocks
        assert "Predator Accumulation" in c.mechanism_blocks

    def test_six_policies(self):
        """|g| = 6: 4 auxiliaries + 2 flows."""
        c = build_canonical()
        assert len(c.policy_blocks) == 6

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


# -- SystemIR and Composition ------------------------------------------------


class TestSystem:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Lotka-Volterra"

    def test_twelve_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 12

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "Prey Birth Rate",
            "Predation Rate",
            "Predator Death Rate",
            "Predator Efficiency",
            "Prey Growth",
            "Predation Loss",
            "Predator Growth",
            "Predator Death",
            "Prey Net Change",
            "Predator Net Change",
            "Prey Accumulation",
            "Predator Accumulation",
        }
        assert names == expected

    def test_temporal_wirings(self):
        """Six temporal loops: stock levels feed auxiliaries across timesteps.

        Prey -> Prey Growth, Prey -> Predation Loss, Prey -> Predator Growth,
        Predator -> Predation Loss, Predator -> Predator Growth,
        Predator -> Predator Death.
        """
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 6

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

    def test_sf_and_gds_combined(self):
        """Full verification: SF + GDS checks together."""
        model = build_model()
        report = sf_verify(model, include_gds_checks=True)
        assert report.checks_total > 0
        sf_findings = [f for f in report.findings if f.check_id.startswith("SF-")]
        gds_findings = [f for f in report.findings if f.check_id.startswith("G-")]
        assert len(sf_findings) > 0
        assert len(gds_findings) > 0


# -- Query API ---------------------------------------------------------------


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Prey Accumulation" in updates["Prey"]["level"]
        assert "Predator Accumulation" in updates["Predator"]["level"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 4
        assert len(by_kind["policy"]) == 6
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_prey(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Prey", "level")
        assert "Prey Accumulation" in affecting

    def test_blocks_affecting_predator(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Predator", "level")
        assert "Predator Accumulation" in affecting
