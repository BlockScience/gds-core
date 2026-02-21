"""Tests for the SIR Epidemic model."""

from gds.blocks.composition import StackComposition
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
    check_reachability,
    check_type_safety,
)
from sir_epidemic.model import (
    Count,
    Rate,
    build_spec,
    build_system,
    contact_process,
    infection_policy,
    susceptible,
    update_infected,
    update_recovered,
    update_susceptible,
)


class TestTypes:
    def test_count_validates_non_negative(self):
        assert Count.check_value(0)
        assert Count.check_value(100)
        assert not Count.check_value(-1)

    def test_count_rejects_float(self):
        assert not Count.check_value(1.5)

    def test_rate_validates_positive(self):
        assert Rate.check_value(0.1)
        assert not Rate.check_value(0.0)
        assert not Rate.check_value(-0.5)


class TestEntities:
    def test_susceptible_has_count(self):
        assert "count" in susceptible.variables
        assert susceptible.variables["count"].typedef is Count

    def test_entity_validates_state(self):
        assert susceptible.validate_state({"count": 100}) == []
        assert len(susceptible.validate_state({"count": -1})) > 0
        assert len(susceptible.validate_state({})) > 0


class TestBlocks:
    def test_contact_is_boundary(self):
        assert isinstance(contact_process, BoundaryAction)
        assert contact_process.interface.forward_in == ()
        assert len(contact_process.interface.forward_out) == 1

    def test_infection_is_policy(self):
        assert isinstance(infection_policy, Policy)
        assert len(infection_policy.interface.forward_in) == 1
        assert len(infection_policy.interface.forward_out) == 3

    def test_updates_are_mechanisms(self):
        for mech in [update_susceptible, update_infected, update_recovered]:
            assert isinstance(mech, Mechanism)
            assert mech.interface.backward_in == ()
            assert mech.interface.backward_out == ()

    def test_mechanism_update_targets(self):
        assert update_susceptible.updates == [("Susceptible", "count")]
        assert update_infected.updates == [("Infected", "count")]
        assert update_recovered.updates == [("Recovered", "count")]


class TestComposition:
    def test_sequential_pipeline_builds(self):
        mechanisms = update_susceptible | update_infected | update_recovered
        pipeline = contact_process >> infection_policy >> mechanisms
        assert isinstance(pipeline, StackComposition)

    def test_flatten_yields_five_blocks(self):
        mechanisms = update_susceptible | update_infected | update_recovered
        pipeline = contact_process >> infection_policy >> mechanisms
        flat = pipeline.flatten()
        assert len(flat) == 5
        names = [b.name for b in flat]
        assert "Contact Process" in names
        assert "Infection Policy" in names
        assert "Update Susceptible" in names

    def test_token_overlap_on_stack(self):
        _ = contact_process >> infection_policy  # validates token overlap
        out_tokens = set()
        for p in contact_process.interface.forward_out:
            out_tokens.update(p.type_tokens)
        in_tokens = set()
        for p in infection_policy.interface.forward_in:
            in_tokens.update(p.type_tokens)
        assert out_tokens & in_tokens


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_three_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 3
        assert set(spec.entities.keys()) == {"Susceptible", "Infected", "Recovered"}

    def test_spec_has_five_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 5

    def test_spec_has_three_params(self):
        spec = build_spec()
        assert set(spec.parameters.keys()) == {"beta", "gamma", "contact_rate"}


class TestVerification:
    def test_ir_compilation(self):
        system = build_system()
        assert system.name == "SIR Epidemic"
        assert len(system.blocks) == 5

    def test_generic_checks_pass(self):
        # G-002 excluded: BoundaryActions have no inputs, terminal Mechanisms no outputs
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

    def test_wirings_are_covariant(self):
        system = build_system()
        for w in system.wirings:
            assert w.direction == FlowDirection.COVARIANT

    def test_completeness(self):
        spec = build_spec()
        findings = check_completeness(spec)
        assert all(f.passed for f in findings)

    def test_determinism(self):
        spec = build_spec()
        findings = check_determinism(spec)
        assert all(f.passed for f in findings)

    def test_reachability(self):
        spec = build_spec()
        findings = check_reachability(spec, "Contact Process", "Update Susceptible")
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
        assert "Contact Process" in mapping["contact_rate"]
        assert "Infection Policy" in mapping["beta"]

    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Update Susceptible" in updates["Susceptible"]["count"]
        assert "Update Infected" in updates["Infected"]["count"]
        assert "Update Recovered" in updates["Recovered"]["count"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 1
        assert len(by_kind["mechanism"]) == 3

    def test_dependency_graph(self):
        spec = build_spec()
        q = SpecQuery(spec)
        deps = q.dependency_graph()
        assert "Infection Policy" in deps["Contact Process"]

    def test_blocks_affecting_susceptible(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Susceptible", "count")
        assert "Update Susceptible" in affecting
        assert "Infection Policy" in affecting
        assert "Contact Process" in affecting
