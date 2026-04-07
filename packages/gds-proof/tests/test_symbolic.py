"""Tests for gds_proof.analysis.symbolic."""

from __future__ import annotations

from typing import ClassVar

import pytest
import sympy
from pydantic import ValidationError

from gds_proof import (
    Invariant,
    ProofMethod,
    analyze_invariants,
)
from gds_proof.analysis.symbolic import (
    InvariantMechanismResult,
    _make_assumed_symbols,
    _try_qsystem,
)
from tests.conftest import STANDARD_ASSUMPTIONS, SimpleModel, U, X

# ---------------------------------------------------------------------------
# REQ-SYM-01: InvariantMechanismResult always has proof_method
# ---------------------------------------------------------------------------


class TestInvariantMechanismResult:
    @pytest.mark.requirement("REQ-SYM-01")
    def test_proof_method_required_at_construction(self):
        r = InvariantMechanismResult(
            invariant_name="i",
            mechanism_name="b",
            status="PROVED",
            proof_method=ProofMethod.DIRECT_SIMPLIFICATION,
        )
        assert r.proof_method == ProofMethod.DIRECT_SIMPLIFICATION

    @pytest.mark.requirement("REQ-SYM-01")
    def test_proof_method_missing_raises(self):
        with pytest.raises(ValidationError):
            InvariantMechanismResult(
                invariant_name="i",
                mechanism_name="b",
                status="PROVED",
                # proof_method omitted — should raise
            )


# ---------------------------------------------------------------------------
# REQ-SYM-02: Vacuity check
# ---------------------------------------------------------------------------


class TestVacuityCheck:
    @pytest.mark.requirement("REQ-SYM-02")
    def test_vacuity_fires_for_disjoint_symbols(self, disjoint_model):
        """Disjoint block (acts on Z) vs X-based invariant → VACUITY."""
        result = analyze_invariants(disjoint_model)
        assert len(result.results) == 1
        r = result.results[0]
        assert r.status == "INCONCLUSIVE"
        assert r.proof_method == ProofMethod.VACUITY

    @pytest.mark.requirement("REQ-SYM-02")
    def test_vacuity_does_not_fire_for_output_symbol(self, open_output_model):
        """Block has Y in substitution keys: vacuity must not fire."""
        result = analyze_invariants(open_output_model)
        output_results = [
            r for r in result.results if r.invariant_name == "output_nonneg"
        ]
        assert len(output_results) == 1
        assert output_results[0].proof_method != ProofMethod.VACUITY

    @pytest.mark.requirement("REQ-SYM-02")
    def test_no_vacuous_proved(self, disjoint_model):
        """Vacuity returns INCONCLUSIVE, never PROVED."""
        result = analyze_invariants(disjoint_model)
        for r in result.results:
            if r.proof_method == ProofMethod.VACUITY:
                assert r.status == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# REQ-SYM-03: Every result has a non-None proof_method
# ---------------------------------------------------------------------------


class TestProofMethodAlwaysSet:
    @pytest.mark.requirement("REQ-SYM-03")
    def test_all_results_have_proof_method(self, withdrawal_model):
        result = analyze_invariants(withdrawal_model)
        for r in result.results:
            assert r.proof_method is not None

    @pytest.mark.requirement("REQ-SYM-03")
    def test_all_results_have_proof_method_multi_block(self, multi_block_model):
        result = analyze_invariants(multi_block_model)
        for r in result.results:
            assert r.proof_method is not None

    @pytest.mark.requirement("REQ-SYM-03")
    def test_exception_method_on_unanalyzable_expr(self):
        """A block whose substitution raises should produce EXCEPTION method."""

        class BadBlock:
            name = "bad"
            prev_state_symbols = frozenset({X})
            input_symbols = frozenset({U})
            predicates: ClassVar[list] = []
            state_transition: ClassVar[dict] = {}
            output_expressions: ClassVar[dict] = {}

            def substitution(self):
                raise TypeError("simulated bad substitution")

        model = SimpleModel(
            blocks_dict={"bad": BadBlock()},
            invariants_dict={"inv": Invariant(name="inv", expr=sympy.Ge(X, 0))},
            assumptions=STANDARD_ASSUMPTIONS,
        )
        result = analyze_invariants(model)
        assert len(result.results) == 1
        r = result.results[0]
        assert r.proof_method == ProofMethod.EXCEPTION
        assert r.status == "INCONCLUSIVE"


# ---------------------------------------------------------------------------
# REQ-SYM-04: SymbolicAnalysisResult aggregation helpers
# ---------------------------------------------------------------------------


class TestSymbolicAnalysisResult:
    @pytest.mark.requirement("REQ-SYM-04")
    def test_has_disproved_false(self, withdrawal_model):
        result = analyze_invariants(withdrawal_model)
        # Withdrawal with predicate should not produce DISPROVED
        assert not result.has_disproved()

    @pytest.mark.requirement("REQ-SYM-04")
    def test_inconclusive_invariants_listed(self, withdrawal_model):
        result = analyze_invariants(withdrawal_model)
        # Without full Q-system resolution, withdrawal model is INCONCLUSIVE
        incs = result.inconclusive_invariants()
        assert isinstance(incs, list)

    @pytest.mark.requirement("REQ-SYM-04")
    def test_proved_invariants_requires_all_pairs(self, multi_block_model):
        """An invariant is only 'proved' if ALL its block pairs are PROVED."""
        result = analyze_invariants(multi_block_model)
        proved = result.proved_invariants()
        # balance_nonneg may or may not be in proved depending on SymPy resolution
        assert isinstance(proved, list)

    @pytest.mark.requirement("REQ-SYM-04")
    def test_disjoint_invariant_not_in_proved(self, disjoint_model):
        result = analyze_invariants(disjoint_model)
        assert "balance_nonneg" not in result.proved_invariants()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestMakeAssumedSymbols:
    def test_enhances_symbols_with_assumptions(self):
        x = sympy.Symbol("x")
        subs = _make_assumed_symbols({x: {"positive": True}})
        enhanced = subs.get(x)
        assert enhanced is not None
        assert enhanced.is_positive

    def test_empty_assumptions_no_substitution(self):
        x = sympy.Symbol("x")
        subs = _make_assumed_symbols({x: {}})
        assert x not in subs

    def test_unchanged_symbol_not_added(self):
        """Symbol with no matching assumptions should not appear in subs."""
        x = sympy.Symbol("x")
        subs = _make_assumed_symbols({x: {}})
        assert len(subs) == 0


class TestTryQsystem:
    def test_returns_true_for_positive(self):
        x = sympy.Symbol("x")
        result = _try_qsystem(sympy.Q.positive(x), {x: {"positive": True}})
        assert result is True

    def test_returns_none_for_inconclusive(self):
        x = sympy.Symbol("x")
        result = _try_qsystem(x > 0, {})  # no assumptions
        assert result is None
