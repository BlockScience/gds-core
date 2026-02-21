"""Tests for the Iterated Prisoner's Dilemma model."""

from gds.blocks.composition import ParallelComposition
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
from prisoners_dilemma.model import (
    RoundNumber,
    Score,
    Strategy,
    alice,
    alice_decision,
    alice_world_model,
    bob,
    bob_decision,
    bob_world_model,
    build_spec,
    build_system,
    game,
    payoff_realization,
    payoff_setting,
)


class TestTypes:
    def test_score_accepts_any_float(self):
        assert Score.check_value(-5.0)
        assert Score.check_value(0.0)
        assert Score.check_value(100.0)

    def test_strategy_bounded_unit_interval(self):
        assert Strategy.check_value(0.0)
        assert Strategy.check_value(0.5)
        assert Strategy.check_value(1.0)
        assert not Strategy.check_value(-0.1)
        assert not Strategy.check_value(1.1)

    def test_round_number_positive_int(self):
        assert RoundNumber.check_value(1)
        assert RoundNumber.check_value(100)
        assert not RoundNumber.check_value(0)
        assert not RoundNumber.check_value(-1)


class TestEntities:
    def test_alice_has_strategy_and_score(self):
        assert "strategy_state" in alice.variables
        assert "score" in alice.variables
        assert alice.variables["strategy_state"].symbol == "s_A"

    def test_bob_has_strategy_and_score(self):
        assert "strategy_state" in bob.variables
        assert "score" in bob.variables
        assert bob.variables["strategy_state"].symbol == "s_B"

    def test_game_has_round_number(self):
        assert "round_number" in game.variables
        assert game.variables["round_number"].symbol == "t"

    def test_entity_validation(self):
        assert alice.validate_state({"strategy_state": 0.5, "score": 10.0}) == []
        assert len(alice.validate_state({"strategy_state": 1.5, "score": 0.0})) > 0
        assert game.validate_state({"round_number": 1}) == []
        assert len(game.validate_state({"round_number": 0})) > 0


class TestBlocks:
    def test_payoff_setting_is_boundary(self):
        assert isinstance(payoff_setting, BoundaryAction)
        assert payoff_setting.interface.forward_in == ()

    def test_decisions_are_policies(self):
        assert isinstance(alice_decision, Policy)
        assert isinstance(bob_decision, Policy)

    def test_payoff_realization_is_mechanism(self):
        assert isinstance(payoff_realization, Mechanism)
        assert len(payoff_realization.interface.forward_in) == 3
        assert len(payoff_realization.interface.forward_out) == 2
        assert ("Alice", "score") in payoff_realization.updates
        assert ("Bob", "score") in payoff_realization.updates
        assert ("Game", "round_number") in payoff_realization.updates

    def test_world_model_updates_are_mechanisms(self):
        assert isinstance(alice_world_model, Mechanism)
        assert isinstance(bob_world_model, Mechanism)
        assert alice_world_model.updates == [("Alice", "strategy_state")]
        assert bob_world_model.updates == [("Bob", "strategy_state")]


class TestComposition:
    def test_parallel_decisions(self):
        decisions = alice_decision | bob_decision
        assert isinstance(decisions, ParallelComposition)
        flat = decisions.flatten()
        assert len(flat) == 2

    def test_input_phase_parallel(self):
        decisions = alice_decision | bob_decision
        input_phase = payoff_setting | decisions
        flat = input_phase.flatten()
        assert len(flat) == 3

    def test_full_pipeline_builds(self):
        system = build_system()
        assert system.name == "Iterated Prisoners Dilemma"

    def test_flatten_yields_six_blocks(self):
        decisions = alice_decision | bob_decision
        input_phase = payoff_setting | decisions
        world_updates = alice_world_model | bob_world_model
        pipeline = input_phase >> payoff_realization >> world_updates
        flat = pipeline.flatten()
        assert len(flat) == 6

    def test_temporal_wirings(self):
        system = build_system()
        temporal_wirings = [w for w in system.wirings if w.is_temporal]
        assert len(temporal_wirings) == 2
        for w in temporal_wirings:
            assert w.direction == FlowDirection.COVARIANT

    def test_system_has_exit_condition(self):
        system = build_system()
        assert system.hierarchy is not None

        def find_temporal(node):
            if node.exit_condition:
                return node.exit_condition
            for child in node.children:
                result = find_temporal(child)
                if result:
                    return result
            return ""

        assert find_temporal(system.hierarchy) == "max_rounds_reached"


class TestSpec:
    def test_build_spec_no_validation_errors(self):
        spec = build_spec()
        errors = spec.validate_spec()
        assert errors == [], f"Validation errors: {errors}"

    def test_spec_has_three_entities(self):
        spec = build_spec()
        assert len(spec.entities) == 3
        assert set(spec.entities.keys()) == {"Alice", "Bob", "Game"}

    def test_spec_has_six_blocks(self):
        spec = build_spec()
        assert len(spec.blocks) == 6

    def test_spec_has_no_params(self):
        spec = build_spec()
        assert len(spec.parameters) == 0


class TestVerification:
    def test_ir_compilation(self):
        system = build_system()
        assert len(system.blocks) == 6
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

    def test_reachability_payoff_to_world_model(self):
        spec = build_spec()
        findings = check_reachability(
            spec, "Payoff Realization", "Alice World Model Update"
        )
        assert any(f.passed for f in findings)

    def test_type_safety(self):
        spec = build_spec()
        findings = check_type_safety(spec)
        assert all(f.passed for f in findings)


class TestQuery:
    def test_entity_update_map(self):
        spec = build_spec()
        q = SpecQuery(spec)
        updates = q.entity_update_map()
        assert "Payoff Realization" in updates["Alice"]["score"]
        assert "Payoff Realization" in updates["Bob"]["score"]
        assert "Payoff Realization" in updates["Game"]["round_number"]
        assert "Alice World Model Update" in updates["Alice"]["strategy_state"]
        assert "Bob World Model Update" in updates["Bob"]["strategy_state"]

    def test_blocks_by_kind(self):
        spec = build_spec()
        q = SpecQuery(spec)
        by_kind = q.blocks_by_kind()
        assert len(by_kind["boundary"]) == 1
        assert len(by_kind["policy"]) == 2
        assert len(by_kind["mechanism"]) == 3

    def test_dependency_graph(self):
        spec = build_spec()
        q = SpecQuery(spec)
        deps = q.dependency_graph()
        assert "Payoff Realization" in deps.get("Alice Decision", set())
        assert "Alice World Model Update" in deps.get("Payoff Realization", set())

    def test_blocks_affecting_alice_score(self):
        spec = build_spec()
        q = SpecQuery(spec)
        affecting = q.blocks_affecting("Alice", "score")
        assert "Payoff Realization" in affecting
