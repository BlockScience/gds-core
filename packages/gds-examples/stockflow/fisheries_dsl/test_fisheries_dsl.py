"""Tests for the Gordon-Schaefer Fishery model (gds-stockflow DSL)."""

from fisheries_dsl.model import (
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
from stockflow.verification.engine import verify as sf_verify

# -- Model Declaration -------------------------------------------------------


class TestModel:
    def test_two_stocks(self):
        model = build_model()
        assert len(model.stocks) == 2
        assert {s.name for s in model.stocks} == {"Fish Stock", "Fleet Effort"}

    def test_two_flows(self):
        model = build_model()
        assert len(model.flows) == 2
        assert {f.name for f in model.flows} == {
            "Net Fish Change",
            "Net Effort Change",
        }

    def test_net_fish_change_targets_fish_stock(self):
        model = build_model()
        flow = next(f for f in model.flows if f.name == "Net Fish Change")
        assert flow.target == "Fish Stock"

    def test_net_effort_change_targets_fleet(self):
        model = build_model()
        flow = next(f for f in model.flows if f.name == "Net Effort Change")
        assert flow.target == "Fleet Effort"

    def test_three_auxiliaries(self):
        model = build_model()
        assert len(model.auxiliaries) == 3
        assert {a.name for a in model.auxiliaries} == {
            "Growth Rate",
            "Harvest Rate",
            "Profit Signal",
        }

    def test_growth_rate_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Growth Rate")
        assert set(aux.inputs) == {
            "Fish Stock",
            "Intrinsic Growth Rate",
            "Carrying Capacity",
        }

    def test_harvest_rate_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Harvest Rate")
        assert set(aux.inputs) == {"Fish Stock", "Fleet Effort", "Catchability"}

    def test_profit_signal_inputs(self):
        model = build_model()
        aux = next(a for a in model.auxiliaries if a.name == "Profit Signal")
        assert set(aux.inputs) == {
            "Fish Stock",
            "Fleet Effort",
            "Market Price",
            "Cost Per Unit Effort",
            "Catchability",
            "Effort Adjustment Speed",
        }

    def test_six_converters(self):
        model = build_model()
        assert len(model.converters) == 6
        assert {c.name for c in model.converters} == {
            "Intrinsic Growth Rate",
            "Carrying Capacity",
            "Catchability",
            "Market Price",
            "Cost Per Unit Effort",
            "Effort Adjustment Speed",
        }

    def test_initial_values(self):
        model = build_model()
        initials = {s.name: s.initial for s in model.stocks}
        assert initials["Fish Stock"] == 1000.0
        assert initials["Fleet Effort"] == 50.0


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
        assert {"Fish Stock", "Fleet Effort"} == set(spec.entities.keys())

    def test_entities_have_level_variable(self):
        spec = build_spec()
        for entity in spec.entities.values():
            assert "level" in entity.variables

    def test_thirteen_blocks(self):
        """6 converters + 3 auxiliaries + 2 flows + 2 mechanisms = 13 blocks."""
        spec = build_spec()
        assert len(spec.blocks) == 13

    def test_block_roles(self):
        spec = build_spec()
        boundaries = [b for b in spec.blocks.values() if isinstance(b, BoundaryAction)]
        policies = [b for b in spec.blocks.values() if isinstance(b, Policy)]
        mechanisms = [b for b in spec.blocks.values() if isinstance(b, Mechanism)]
        assert len(boundaries) == 6  # six converters
        assert len(policies) == 5  # three auxiliaries + two flows
        assert len(mechanisms) == 2  # Fish Stock/Fleet Effort Accumulation

    def test_converters_are_boundary_actions(self):
        spec = build_spec()
        for name in [
            "Intrinsic Growth Rate",
            "Carrying Capacity",
            "Catchability",
            "Market Price",
            "Cost Per Unit Effort",
            "Effort Adjustment Speed",
        ]:
            block = spec.blocks[name]
            assert isinstance(block, BoundaryAction)
            assert block.interface.forward_in == ()

    def test_auxiliaries_are_policies(self):
        spec = build_spec()
        for name in ["Growth Rate", "Harvest Rate", "Profit Signal"]:
            assert isinstance(spec.blocks[name], Policy)

    def test_flows_are_policies(self):
        spec = build_spec()
        for name in ["Net Fish Change", "Net Effort Change"]:
            block = spec.blocks[name]
            assert isinstance(block, Policy)
            assert block.interface.forward_in == ()

    def test_stock_mechanisms(self):
        spec = build_spec()
        for stock_name in ["Fish Stock", "Fleet Effort"]:
            block = spec.blocks[f"{stock_name} Accumulation"]
            assert isinstance(block, Mechanism)
            assert (stock_name, "level") in block.updates

    def test_parameters_registered(self):
        spec = build_spec()
        param_names = spec.parameter_schema.names()
        assert "Intrinsic Growth Rate" in param_names
        assert "Carrying Capacity" in param_names
        assert "Catchability" in param_names
        assert "Market Price" in param_names
        assert "Cost Per Unit Effort" in param_names
        assert "Effort Adjustment Speed" in param_names


# -- Canonical Projection -----------------------------------------------------


class TestCanonical:
    def test_state_dim_equals_two(self):
        """dim(x) = 2: Fish Stock, Fleet Effort levels."""
        c = build_canonical()
        assert len(c.state_variables) == 2

    def test_input_dim_equals_six(self):
        """dim(u) = 6: six converter parameters."""
        c = build_canonical()
        assert len(c.boundary_blocks) == 6

    def test_two_mechanisms(self):
        """|f| = 2 accumulation mechanisms."""
        c = build_canonical()
        assert len(c.mechanism_blocks) == 2
        assert "Fish Stock Accumulation" in c.mechanism_blocks
        assert "Fleet Effort Accumulation" in c.mechanism_blocks

    def test_five_policies(self):
        """|g| = 5: 3 auxiliaries + 2 flows."""
        c = build_canonical()
        assert len(c.policy_blocks) == 5

    def test_no_control_blocks(self):
        """ControlAction unused in stockflow DSL."""
        c = build_canonical()
        assert len(c.control_blocks) == 0

    def test_role_partition_complete(self):
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
        assert system.name == "Fisheries Bioeconomic"

    def test_thirteen_blocks_in_ir(self):
        system = build_system()
        assert len(system.blocks) == 13

    def test_block_names(self):
        system = build_system()
        names = {b.name for b in system.blocks}
        expected = {
            "Intrinsic Growth Rate",
            "Carrying Capacity",
            "Catchability",
            "Market Price",
            "Cost Per Unit Effort",
            "Effort Adjustment Speed",
            "Growth Rate",
            "Harvest Rate",
            "Profit Signal",
            "Net Fish Change",
            "Net Effort Change",
            "Fish Stock Accumulation",
            "Fleet Effort Accumulation",
        }
        assert names == expected

    def test_temporal_wirings(self):
        """Five temporal loops: stock levels feed auxiliaries across timesteps."""
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        assert len(temporal) == 5

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal = [w for w in system.wirings if w.is_temporal]
        for w in temporal:
            assert w.direction == FlowDirection.COVARIANT

    def test_no_feedback_wirings(self):
        """No within-timestep backward flow (DSL doesn't support it)."""
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
        assert "Fish Stock Accumulation" in updates["Fish Stock"]["level"]
        assert "Fleet Effort Accumulation" in updates["Fleet Effort"]["level"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 6
        assert len(by_kind["policy"]) == 5
        assert len(by_kind["control"]) == 0
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_fish_stock(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Fish Stock", "level")
        assert "Fish Stock Accumulation" in affecting

    def test_blocks_affecting_fleet_effort(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Fleet Effort", "level")
        assert "Fleet Effort Accumulation" in affecting
