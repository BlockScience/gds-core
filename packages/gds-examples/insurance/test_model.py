"""Tests for the Insurance Contract model."""

from gds.blocks.composition import StackComposition
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
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
    check_reachability,
    check_type_safety,
)
from insurance.model import (
    Currency,
    RiskScore,
    build_spec,
    build_system,
    claim_arrival,
    claim_payout,
    insurer,
    policyholder,
    premium_calculation,
    reserve_update,
    risk_assessment,
)


class TestTypes:
    def test_currency_non_negative(self):
        assert Currency.check_value(0.0)
        assert Currency.check_value(1000.0)
        assert not Currency.check_value(-1.0)

    def test_risk_score_bounded(self):
        assert RiskScore.check_value(0.0)
        assert RiskScore.check_value(0.5)
        assert RiskScore.check_value(1.0)
        assert not RiskScore.check_value(-0.1)
        assert not RiskScore.check_value(1.1)


class TestEntities:
    def test_insurer_has_reserve_and_pool(self):
        assert "reserve" in insurer.variables
        assert "premium_pool" in insurer.variables

    def test_policyholder_has_coverage_and_history(self):
        assert "coverage" in policyholder.variables
        assert "claims_history" in policyholder.variables

    def test_entity_validation(self):
        assert insurer.validate_state({"reserve": 100.0, "premium_pool": 50.0}) == []
        assert len(insurer.validate_state({"reserve": -1.0, "premium_pool": 50.0})) > 0


class TestBlocks:
    def test_claim_arrival_is_boundary(self):
        assert isinstance(claim_arrival, BoundaryAction)
        assert claim_arrival.interface.forward_in == ()

    def test_risk_assessment_is_policy(self):
        assert isinstance(risk_assessment, Policy)

    def test_premium_is_control_action(self):
        assert isinstance(premium_calculation, ControlAction)
        assert premium_calculation.kind == "control"
        assert len(premium_calculation.params_used) == 3

    def test_claim_payout_is_mechanism_with_output(self):
        assert isinstance(claim_payout, Mechanism)
        assert len(claim_payout.interface.forward_out) == 1
        assert claim_payout.updates == [
            ("Policyholder", "claims_history"),
            ("Policyholder", "coverage"),
        ]

    def test_reserve_update_is_terminal_mechanism(self):
        assert isinstance(reserve_update, Mechanism)
        assert reserve_update.interface.forward_out == ()
        assert reserve_update.updates == [
            ("Insurer", "reserve"),
            ("Insurer", "premium_pool"),
        ]


class TestComposition:
    def test_sequential_pipeline_builds(self):
        pipeline = (
            claim_arrival
            >> risk_assessment
            >> premium_calculation
            >> claim_payout
            >> reserve_update
        )
        assert isinstance(pipeline, StackComposition)

    def test_flatten_yields_five_blocks(self):
        pipeline = (
            claim_arrival
            >> risk_assessment
            >> premium_calculation
            >> claim_payout
            >> reserve_update
        )
        flat = pipeline.flatten()
        assert len(flat) == 5

    def test_all_wirings_covariant(self):
        system = build_system()
        for w in system.wirings:
            assert w.direction == FlowDirection.COVARIANT
            assert not w.is_feedback
            assert not w.is_temporal


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert set(spec.entities.keys()) == {"Insurer", "Policyholder"}

    def test_spec_has_five_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 5

    def test_spec_has_three_params(self):
        spec = build_spec()
        assert set(spec.parameters.keys()) == {
            "base_premium_rate",
            "deductible",
            "coverage_limit",
        }


class TestVerification:
    def test_ir_compilation(self):
        system = build_system()
        assert system.name == "Insurance Contract"
        assert len(system.blocks) == 5

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

    def test_reachability_claim_to_reserve(self):
        spec = build_spec()
        findings = check_reachability(spec, "Claim Arrival", "Reserve Update")
        assert any(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


class TestQuery:
    def test_param_to_blocks(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Premium Calculation" in mapping["base_premium_rate"]
        assert "Premium Calculation" in mapping["deductible"]

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Reserve Update" in updates["Insurer"]["reserve"]
        assert "Claim Payout" in updates["Policyholder"]["claims_history"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 1
        assert len(by_kind["control"]) == 1
        assert len(by_kind["mechanism"]) == 2

    def test_dependency_graph(self):
        spec = build_spec()
        q = SpecQuery(spec)
        deps = q.dependency_graph()
        assert "Risk Assessment" in deps["Claim Arrival"]
        assert "Premium Calculation" in deps["Risk Assessment"]
        assert "Claim Payout" in deps["Premium Calculation"]
        assert "Reserve Update" in deps["Claim Payout"]
