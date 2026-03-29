"""Tests for the Gordon-Schaefer fishery (StockFlow DSL variant)."""

from gds.verification.engine import verify
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)
from gds.verification.spec_checks import check_completeness, check_determinism

from fishery_dsl.model import build_canonical, build_model, build_spec, build_system


class TestModel:
    def test_one_stock(self):
        model = build_model()
        assert len(model.stocks) == 1
        assert model.stocks[0].name == "Fish Population"

    def test_two_flows(self):
        model = build_model()
        assert {f.name for f in model.flows} == {"Natural Growth", "Harvest"}

    def test_two_auxiliaries(self):
        model = build_model()
        assert {a.name for a in model.auxiliaries} == {
            "Growth Rate Calc",
            "Harvest Rate Calc",
        }

    def test_five_converters(self):
        model = build_model()
        assert len(model.converters) == 5


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == []

    def test_one_entity(self):
        spec = build_spec()
        assert "Fish Population" in spec.entities

    def test_parameters_registered(self):
        spec = build_spec()
        names = spec.parameter_schema.names()
        assert "Intrinsic Growth Rate" in names
        assert "Carrying Capacity" in names
        assert "Catchability" in names
        assert "Total Effort" in names


class TestCompilation:
    def test_system_compiles(self):
        system = build_system()
        assert system.name == "Gordon-Schaefer Fishery"

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
        assert report.errors == 0

    def test_completeness(self):
        findings = check_completeness(build_spec())
        assert all(f.passed for f in findings)

    def test_determinism(self):
        findings = check_determinism(build_spec())
        assert all(f.passed for f in findings)


class TestCanonical:
    def test_projects(self):
        canonical = build_canonical()
        assert canonical is not None

    def test_has_state(self):
        canonical = build_canonical()
        assert len(canonical.state_variables) >= 1

    def test_has_mechanisms(self):
        canonical = build_canonical()
        assert len(canonical.mechanism_blocks) >= 1

    def test_formula_renders(self):
        canonical = build_canonical()
        formula = canonical.formula()
        assert "h" in formula
