"""Tests for the Lotka-Volterra Predator-Prey model."""

import pytest

from gds.blocks.errors import GDSTypeError
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
from lotka_volterra.model import (
    GrowthRate,
    Population,
    build_spec,
    build_system,
    compute_rates,
    observe_populations,
    predator,
    prey,
    update_predator,
    update_prey,
)


class TestTypes:
    def test_population_non_negative(self):
        assert Population.check_value(0.0)
        assert Population.check_value(100.5)
        assert not Population.check_value(-1.0)

    def test_growth_rate_positive(self):
        assert GrowthRate.check_value(0.1)
        assert not GrowthRate.check_value(0.0)
        assert not GrowthRate.check_value(-0.5)


class TestEntities:
    def test_prey_has_population(self):
        assert "population" in prey.variables
        assert prey.variables["population"].symbol == "x"

    def test_predator_has_population(self):
        assert "population" in predator.variables
        assert predator.variables["population"].symbol == "y"

    def test_entity_validation(self):
        assert prey.validate_state({"population": 50.0}) == []
        assert len(prey.validate_state({"population": -1.0})) > 0


class TestBlocks:
    def test_observe_is_boundary(self):
        assert isinstance(observe_populations, BoundaryAction)
        assert observe_populations.interface.forward_in == ()

    def test_compute_is_policy_with_four_params(self):
        assert isinstance(compute_rates, Policy)
        assert len(compute_rates.params_used) == 4

    def test_update_prey_is_mechanism_with_forward_out(self):
        assert isinstance(update_prey, Mechanism)
        assert len(update_prey.interface.forward_out) == 1
        assert update_prey.updates == [("Prey", "population")]

    def test_update_predator_is_mechanism_with_forward_out(self):
        assert isinstance(update_predator, Mechanism)
        assert len(update_predator.interface.forward_out) == 1
        assert update_predator.updates == [("Predator", "population")]

    def test_mechanisms_have_parallel_structure(self):
        parallel = update_prey | update_predator
        flat = parallel.flatten()
        assert len(flat) == 2


class TestComposition:
    def test_temporal_loop_builds(self):
        system = build_system()
        assert system.name == "Lotka-Volterra"

    def test_flatten_yields_four_blocks(self):
        updates = update_prey | update_predator
        inner = observe_populations >> compute_rates >> updates
        flat = inner.flatten()
        assert len(flat) == 4

    def test_temporal_wirings_are_covariant(self):
        system = build_system()
        temporal_wirings = [w for w in system.wirings if w.is_temporal]
        assert len(temporal_wirings) == 2
        for w in temporal_wirings:
            assert w.direction == FlowDirection.COVARIANT

    def test_temporal_loop_rejects_contravariant(self):
        from gds.blocks.composition import Wiring

        updates = update_prey | update_predator
        inner = observe_populations >> compute_rates >> updates
        with pytest.raises(GDSTypeError, match="must be COVARIANT"):
            inner.loop(
                [
                    Wiring(
                        source_block="Update Prey",
                        source_port="Population Signal",
                        target_block="Compute Rates",
                        target_port="Population Signal",
                        direction=FlowDirection.CONTRAVARIANT,
                    )
                ]
            )

    def test_system_has_exit_condition(self):
        system = build_system()
        assert system.hierarchy is not None

        # The top-level hierarchy node should have exit_condition
        def find_temporal(node):
            if node.exit_condition:
                return node.exit_condition
            for child in node.children:
                result = find_temporal(child)
                if result:
                    return result
            return ""

        assert find_temporal(system.hierarchy) == "population_extinct"


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_two_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 2
        assert set(spec.entities.keys()) == {"Prey", "Predator"}

    def test_spec_has_four_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 4

    def test_spec_has_four_params(self):
        spec = build_spec()
        assert set(spec.parameters.keys()) == {
            "prey_birth_rate",
            "predation_rate",
            "predator_death_rate",
            "predator_efficiency",
        }


class TestVerification:
    def test_ir_compilation(self):
        system = build_system()
        assert len(system.blocks) == 4
        assert len(system.wirings) > 0

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


class TestQuery:
    def test_param_to_blocks(self):
        spec = build_spec()
        q = SpecQuery(spec)
        mapping = q.param_to_blocks()
        assert "Compute Rates" in mapping["prey_birth_rate"]
        assert "Compute Rates" in mapping["predation_rate"]

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Update Prey" in updates["Prey"]["population"]
        assert "Update Predator" in updates["Predator"]["population"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 1
        assert len(by_kind["mechanism"]) == 2

    def test_blocks_affecting_prey(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Prey", "population")
        assert "Update Prey" in affecting
