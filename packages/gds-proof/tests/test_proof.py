"""Tests for gds_proof.analysis.proof."""

from __future__ import annotations

import pytest
import sympy

from gds_proof import (
    Invariant,
    Lemma,
    LemmaKind,
    ProofBuilder,
    ProofScript,
    ProofStatus,
    attach_proof,
    hash_proof,
    verify_lemma,
    verify_proof,
)
from tests.conftest import X

# ---------------------------------------------------------------------------
# REQ-PROOF-01: Three lemma kinds verify correctly
# ---------------------------------------------------------------------------


class TestVerifyLemma:
    @pytest.mark.requirement("REQ-PROOF-01")
    def test_equality_via_doit(self):
        """Sum(1/2^k, k=0..inf) = 2 — evaluable by .doit()."""
        k = sympy.Symbol("k", integer=True, nonneg=True)
        lemma = Lemma(
            name="geometric",
            kind=LemmaKind.EQUALITY,
            expr=sympy.Sum(sympy.Rational(1, 2) ** k, (k, 0, sympy.oo)),
            expected=sympy.Integer(2),
        )
        result = verify_lemma(lemma)
        assert result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_equality_via_simplify(self):
        """2 + 2 = 4 — resolved by simplify."""
        lemma = Lemma(
            name="arithmetic",
            kind=LemmaKind.EQUALITY,
            expr=sympy.Integer(2) + sympy.Integer(2),
            expected=sympy.Integer(4),
        )
        result = verify_lemma(lemma)
        assert result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_equality_fails_wrong_expected(self):
        lemma = Lemma(
            name="wrong",
            kind=LemmaKind.EQUALITY,
            expr=sympy.Integer(2) + sympy.Integer(2),
            expected=sympy.Integer(5),
        )
        result = verify_lemma(lemma)
        assert not result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_equality_missing_expected_fails(self):
        lemma = Lemma(
            name="no_expected",
            kind=LemmaKind.EQUALITY,
            expr=sympy.Integer(4),
        )
        result = verify_lemma(lemma)
        assert not result.passed
        assert result.error is not None

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_boolean_true(self):
        """sympy.true simplifies to sympy.true."""
        lemma = Lemma(
            name="tautology",
            kind=LemmaKind.BOOLEAN,
            expr=sympy.true,
        )
        result = verify_lemma(lemma)
        assert result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_boolean_false(self):
        lemma = Lemma(
            name="contradiction",
            kind=LemmaKind.BOOLEAN,
            expr=sympy.false,
        )
        result = verify_lemma(lemma)
        assert not result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_boolean_with_assumptions(self):
        """x > 0 with x positive — should pass."""
        x = sympy.Symbol("x")
        lemma = Lemma(
            name="pos_check",
            kind=LemmaKind.BOOLEAN,
            expr=x > 0,
            assumptions={"x": {"positive": True, "real": True}},
        )
        result = verify_lemma(lemma)
        assert result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_query_positive(self):
        x = sympy.Symbol("x")
        lemma = Lemma(
            name="pos_query",
            kind=LemmaKind.QUERY,
            expr=sympy.Q.positive(x),
            assumptions={"x": {"positive": True}},
        )
        result = verify_lemma(lemma)
        assert result.passed

    @pytest.mark.requirement("REQ-PROOF-01")
    def test_query_fails_without_assumptions(self):
        x = sympy.Symbol("x")
        lemma = Lemma(
            name="pos_query_no_asm",
            kind=LemmaKind.QUERY,
            expr=sympy.Q.positive(x),
            assumptions={},
        )
        result = verify_lemma(lemma)
        assert not result.passed


# ---------------------------------------------------------------------------
# REQ-PROOF-02: verify_proof model hash check
# ---------------------------------------------------------------------------


class TestVerifyProof:
    @pytest.mark.requirement("REQ-PROOF-02")
    def test_verified_on_correct_hash(self, geometric_series_script, model_hash):
        result = verify_proof(geometric_series_script, model_hash)
        assert result.status == ProofStatus.VERIFIED

    @pytest.mark.requirement("REQ-PROOF-02")
    def test_failed_on_wrong_model_hash(self, geometric_series_script, bad_model_hash):
        result = verify_proof(geometric_series_script, bad_model_hash)
        assert result.status == ProofStatus.FAILED
        assert "model_hash" in result.failure_summary.lower()

    @pytest.mark.requirement("REQ-PROOF-02")
    def test_proof_hash_returned_on_verified(self, geometric_series_script, model_hash):
        result = verify_proof(geometric_series_script, model_hash)
        assert result.proof_hash is not None
        assert len(result.proof_hash) == 64

    @pytest.mark.requirement("REQ-PROOF-02")
    def test_lemma_results_populated_on_verified(
        self, geometric_series_script, model_hash
    ):
        result = verify_proof(geometric_series_script, model_hash)
        assert len(result.lemma_results) == len(geometric_series_script.lemmas)
        assert all(lr.passed for lr in result.lemma_results)

    @pytest.mark.requirement("REQ-PROOF-02")
    def test_fails_on_failing_lemma(self, model_hash):
        script = (
            ProofBuilder(model_hash, "balance_nonneg", "bad", "bad proof")
            .lemma(
                "wrong_arithmetic",
                LemmaKind.EQUALITY,
                expr=sympy.Integer(2) + sympy.Integer(2),
                expected=sympy.Integer(5),
            )
            .build()
        )
        result = verify_proof(script, model_hash)
        assert result.status == ProofStatus.FAILED
        assert "wrong_arithmetic" in result.failure_summary


# ---------------------------------------------------------------------------
# REQ-PROOF-03: Evidence round-trip
# ---------------------------------------------------------------------------


class TestEvidenceRoundTrip:
    @pytest.mark.requirement("REQ-PROOF-03")
    def test_to_evidence_from_evidence_hash_stable(
        self, geometric_series_script, model_hash
    ):
        evidence = geometric_series_script.to_evidence()
        restored = ProofScript.from_evidence(evidence)
        assert hash_proof(restored, model_hash) == hash_proof(
            geometric_series_script, model_hash
        )

    @pytest.mark.requirement("REQ-PROOF-03")
    def test_evidence_is_json_compatible(self, geometric_series_script):
        import json

        evidence = geometric_series_script.to_evidence()
        # Should not raise
        serialized = json.dumps(evidence)
        assert isinstance(serialized, str)

    @pytest.mark.requirement("REQ-PROOF-03")
    def test_restored_script_verifies(self, geometric_series_script, model_hash):
        evidence = geometric_series_script.to_evidence()
        restored = ProofScript.from_evidence(evidence)
        result = verify_proof(restored, model_hash)
        assert result.status == ProofStatus.VERIFIED

    @pytest.mark.requirement("REQ-PROOF-03")
    def test_lemma_expressions_restored(self, geometric_series_script, model_hash):
        evidence = geometric_series_script.to_evidence()
        restored = ProofScript.from_evidence(evidence)
        orig_expr = geometric_series_script.lemmas[0].expr
        restored_expr = restored.lemmas[0].expr
        assert sympy.simplify(orig_expr - restored_expr) == 0


# ---------------------------------------------------------------------------
# REQ-ATTACH-01: attach_proof enforces preconditions
# ---------------------------------------------------------------------------


class TestAttachProof:
    @pytest.mark.requirement("REQ-ATTACH-01")
    def test_attach_sets_proof_hash(self, geometric_series_script, model_hash):
        inv = Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        result = attach_proof(inv, geometric_series_script, model_hash)
        expected = hash_proof(geometric_series_script, model_hash)
        assert result.proof_hash == expected

    @pytest.mark.requirement("REQ-ATTACH-01")
    def test_attach_returns_new_instance(self, geometric_series_script, model_hash):
        inv = Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        result = attach_proof(inv, geometric_series_script, model_hash)
        # Original is unchanged (Pydantic model copy)
        assert inv.proof_hash is None
        assert result.proof_hash is not None

    @pytest.mark.requirement("REQ-ATTACH-01")
    def test_attach_raises_wrong_invariant_name(
        self, geometric_series_script, model_hash
    ):
        inv = Invariant(name="different_invariant", expr=sympy.Ge(X, 0))
        with pytest.raises(ValueError, match="target_invariant"):
            attach_proof(inv, geometric_series_script, model_hash)

    @pytest.mark.requirement("REQ-ATTACH-01")
    def test_attach_raises_wrong_model_hash(self, geometric_series_script, model_hash):
        inv = Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        wrong_hash = "f" * 64
        # Script model_hash != wrong_hash → ValueError
        with pytest.raises(ValueError):
            attach_proof(inv, geometric_series_script, wrong_hash)

    @pytest.mark.requirement("REQ-ATTACH-01")
    def test_attach_raises_on_unverified_proof(self, model_hash):
        """A proof script with a failing lemma cannot be attached."""
        failing_script = (
            ProofBuilder(model_hash, "balance_nonneg", "bad", "bad proof")
            .lemma(
                "wrong",
                LemmaKind.EQUALITY,
                expr=sympy.Integer(2) + sympy.Integer(2),
                expected=sympy.Integer(5),
            )
            .build()
        )
        inv = Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        with pytest.raises(ValueError, match="VERIFIED"):
            attach_proof(inv, failing_script, model_hash)


# ---------------------------------------------------------------------------
# ProofBuilder
# ---------------------------------------------------------------------------


class TestProofBuilder:
    def test_chainable_api(self, model_hash):
        sympy.Symbol("k", integer=True, nonneg=True)
        script = (
            ProofBuilder(model_hash, "balance_nonneg", "test", "test claim")
            .lemma(
                "l1",
                LemmaKind.EQUALITY,
                expr=sympy.Integer(1) + sympy.Integer(1),
                expected=sympy.Integer(2),
            )
            .lemma("l2", LemmaKind.BOOLEAN, expr=sympy.true)
            .build()
        )
        assert len(script.lemmas) == 2

    def test_empty_builder_raises(self, model_hash):
        with pytest.raises(ValueError):
            ProofBuilder(model_hash, "inv", "name", "claim").build()

    def test_script_has_correct_metadata(self, model_hash):
        script = (
            ProofBuilder(model_hash, "balance_nonneg", "my_proof", "my claim")
            .lemma("l1", LemmaKind.BOOLEAN, expr=sympy.true)
            .build()
        )
        assert script.name == "my_proof"
        assert script.target_invariant == "balance_nonneg"
        assert script.model_hash == model_hash
        assert script.claim == "my claim"
