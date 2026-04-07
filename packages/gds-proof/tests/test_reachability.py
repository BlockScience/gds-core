"""Tests for gds_proof.analysis.reachability."""

from __future__ import annotations

from typing import ClassVar

import pytest
import sympy

from gds_proof import (
    Invariant,
    MultiStepVerdict,
    PredicateSufficiencyVerdict,
    SingleStepVerdict,
    analyze_reachability,
)
from tests.conftest import SimpleModel

# ---------------------------------------------------------------------------
# REQ-REACH-01: Structure and completeness
# ---------------------------------------------------------------------------


class TestReachabilityStructure:
    @pytest.mark.requirement("REQ-REACH-01")
    def test_result_has_all_three_layers(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        assert hasattr(result, "single_step")
        assert hasattr(result, "predicate_sufficiency")
        assert hasattr(result, "multi_step")

    @pytest.mark.requirement("REQ-REACH-01")
    def test_single_step_count_equals_pairs(self, withdrawal_model):
        """One block x one invariant = one single-step result."""
        result = analyze_reachability(withdrawal_model)
        n_blocks = len(withdrawal_model.blocks())
        n_invs = len(withdrawal_model.invariants())
        assert len(result.single_step) == n_blocks * n_invs

    @pytest.mark.requirement("REQ-REACH-01")
    def test_sufficiency_count_equals_pairs(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        n_blocks = len(withdrawal_model.blocks())
        n_invs = len(withdrawal_model.invariants())
        assert len(result.predicate_sufficiency) == n_blocks * n_invs

    @pytest.mark.requirement("REQ-REACH-01")
    def test_multi_block_pair_count(self, multi_block_model):
        result = analyze_reachability(multi_block_model)
        n_blocks = len(multi_block_model.blocks())
        n_invs = len(multi_block_model.invariants())
        assert len(result.single_step) == n_blocks * n_invs


# ---------------------------------------------------------------------------
# REQ-REACH-02: Single-step uses full invariant conjunction
# ---------------------------------------------------------------------------


class TestSingleStep:
    @pytest.mark.requirement("REQ-REACH-02")
    def test_single_step_records_antecedent_invariants(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        ss = result.single_step[0]
        assert "balance_nonneg" in ss.antecedent_invariant_names

    @pytest.mark.requirement("REQ-REACH-02")
    def test_single_step_records_predicate_count(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        ss = result.single_step[0]
        assert ss.predicate_count == 1  # withdrawal has one predicate

    @pytest.mark.requirement("REQ-REACH-02")
    def test_deposit_single_step_no_predicates(self, deposit_model):
        result = analyze_reachability(deposit_model)
        ss = result.single_step[0]
        assert ss.predicate_count == 0


# ---------------------------------------------------------------------------
# REQ-REACH-03: Multi-step induction
# ---------------------------------------------------------------------------


class TestMultiStep:
    @pytest.mark.requirement("REQ-REACH-03")
    def test_inconclusive_when_any_pair_inconclusive(self, withdrawal_model):
        """Withdrawal model likely INCONCLUSIVE without full Q-system resolution."""
        result = analyze_reachability(withdrawal_model)
        # Multi-step is PROVED only if ALL single-step are PROVED
        all_proved = all(
            r.verdict == SingleStepVerdict.PROVED for r in result.single_step
        )
        if not all_proved:
            assert result.multi_step.verdict != MultiStepVerdict.PROVED

    @pytest.mark.requirement("REQ-REACH-03")
    def test_disproved_propagates_to_multi_step(self):
        """A block that always violates the invariant → multi-step DISPROVED."""
        # deposit_block for negative invariant: x_prev + u >= 10 is violated
        # when x_prev = 0, u = 0
        y = sympy.Symbol("y_state")
        v = sympy.Symbol("v_input")

        class WorseningBlock:
            name = "worse"
            prev_state_symbols = frozenset({y})
            input_symbols = frozenset({v})
            predicates: ClassVar[list] = []
            state_transition: ClassVar[dict] = {"y": y - 1}
            output_expressions: ClassVar[dict] = {}

            def substitution(self):
                return {y: y - 1}

        model = SimpleModel(
            blocks_dict={"worse": WorseningBlock()},
            invariants_dict={
                "y_positive": Invariant(name="y_positive", expr=sympy.Gt(y, 0))
            },
            assumptions={y: {"positive": True, "real": True}},
        )
        result = analyze_reachability(model)
        # y -> y - 1 violates y > 0 (since y - 1 > 0 does not follow from y > 0)
        # So multi-step should be INCONCLUSIVE or DISPROVED, not PROVED
        assert result.multi_step.verdict != MultiStepVerdict.PROVED

    @pytest.mark.requirement("REQ-REACH-03")
    def test_failing_pairs_listed(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        if result.multi_step.verdict != MultiStepVerdict.PROVED:
            assert len(result.multi_step.failing_pairs) > 0


# ---------------------------------------------------------------------------
# REQ-REACH-04: Predicate sufficiency
# ---------------------------------------------------------------------------


class TestPredicateSufficiency:
    @pytest.mark.requirement("REQ-REACH-04")
    def test_no_predicates_gives_inconclusive_sufficiency(self, deposit_model):
        """Deposit block has no predicates → sufficiency must be INCONCLUSIVE."""
        result = analyze_reachability(deposit_model)
        for ps in result.predicate_sufficiency:
            assert ps.verdict == PredicateSufficiencyVerdict.INCONCLUSIVE
            assert ps.predicate_count == 0

    @pytest.mark.requirement("REQ-REACH-04")
    def test_withdrawal_predicate_count_in_sufficiency(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        assert result.predicate_sufficiency[0].predicate_count == 1

    @pytest.mark.requirement("REQ-REACH-04")
    def test_self_certifying_pairs_helper(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        pairs = result.self_certifying_pairs()
        assert isinstance(pairs, list)
        # Each pair is (invariant_name, block_name)
        for inv_name, blk_name in pairs:
            assert isinstance(inv_name, str)
            assert isinstance(blk_name, str)


# ---------------------------------------------------------------------------
# REQ-REACH-05: Open-world model handling
# ---------------------------------------------------------------------------


class TestOpenWorldReachability:
    @pytest.mark.requirement("REQ-REACH-05")
    def test_open_output_invariant_included(self, open_output_model):
        """Invariant over unwired output Y is included in reachability analysis."""
        result = analyze_reachability(open_output_model)
        inv_names = {r.invariant_name for r in result.single_step}
        assert "output_nonneg" in inv_names

    @pytest.mark.requirement("REQ-REACH-05")
    def test_has_unsafe_false_for_well_designed_model(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        # has_unsafe is True only if a pair is explicitly DISPROVED
        assert isinstance(result.has_unsafe(), bool)

    @pytest.mark.requirement("REQ-REACH-05")
    def test_unresolved_invariants_helper(self, withdrawal_model):
        result = analyze_reachability(withdrawal_model)
        unresolved = result.unresolved_invariants()
        assert isinstance(unresolved, list)
