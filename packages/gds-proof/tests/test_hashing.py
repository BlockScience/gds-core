"""Tests for gds_proof.identity.hashing."""

from __future__ import annotations

import hashlib
import json

import pytest
import sympy

from gds_proof import hash_model, hash_proof
from gds_proof.identity.hashing import _serialize_for_hash

# ---------------------------------------------------------------------------
# REQ-HASH-01: Model hash determinism and stability
# ---------------------------------------------------------------------------


class TestHashModel:
    @pytest.mark.requirement("REQ-HASH-01")
    def test_returns_64_char_hex(self, withdrawal_model):
        h = hash_model(withdrawal_model)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.requirement("REQ-HASH-01")
    def test_deterministic_same_model(self, withdrawal_model):
        h1 = hash_model(withdrawal_model)
        h2 = hash_model(withdrawal_model)
        assert h1 == h2

    @pytest.mark.requirement("REQ-HASH-01")
    def test_different_models_different_hashes(self, withdrawal_model, deposit_model):
        assert hash_model(withdrawal_model) != hash_model(deposit_model)

    @pytest.mark.requirement("REQ-HASH-01")
    def test_is_sha256_of_canonical_dict(self, withdrawal_model):
        """Verify the hash is exactly SHA-256 of the serialized canonical dict."""
        data = withdrawal_model.canonical_dict()
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        expected = hashlib.sha256(serialized).hexdigest()
        assert hash_model(withdrawal_model) == expected

    @pytest.mark.requirement("REQ-HASH-01")
    def test_multi_block_model_hashes(self, multi_block_model, withdrawal_model):
        """Adding a block changes the hash."""
        assert hash_model(multi_block_model) != hash_model(withdrawal_model)


# ---------------------------------------------------------------------------
# REQ-HASH-02: Proof hash binds to model
# ---------------------------------------------------------------------------


class TestHashProof:
    @pytest.mark.requirement("REQ-HASH-02")
    def test_returns_64_char_hex(self, geometric_series_script, model_hash):
        h = hash_proof(geometric_series_script, model_hash)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.requirement("REQ-HASH-02")
    def test_deterministic(self, geometric_series_script, model_hash):
        h1 = hash_proof(geometric_series_script, model_hash)
        h2 = hash_proof(geometric_series_script, model_hash)
        assert h1 == h2

    @pytest.mark.requirement("REQ-HASH-02")
    def test_changes_with_different_model_hash(
        self, geometric_series_script, model_hash, bad_model_hash
    ):
        h1 = hash_proof(geometric_series_script, model_hash)
        h2 = hash_proof(geometric_series_script, bad_model_hash)
        assert h1 != h2

    @pytest.mark.requirement("REQ-HASH-02")
    def test_uses_srepr_for_expressions(self, geometric_series_script, model_hash):
        """Proof hash must use srepr — verify by reconstructing manually."""
        script = geometric_series_script
        lemma = script.lemmas[0]
        data = {
            "model_hash": model_hash,
            "target_invariant": script.target_invariant,
            "lemmas": [
                {
                    "name": lemma.name,
                    "kind": lemma.kind.value,
                    "expr": sympy.srepr(lemma.expr),
                    "expected": sympy.srepr(lemma.expected),
                    "assumptions": lemma.assumptions,
                    "depends_on": sorted(lemma.depends_on),
                }
            ],
        }
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        expected = hashlib.sha256(serialized).hexdigest()
        assert hash_proof(script, model_hash) == expected


# ---------------------------------------------------------------------------
# _serialize_for_hash
# ---------------------------------------------------------------------------


class TestSerializeForHash:
    def test_sort_keys(self):
        d = {"b": 1, "a": 2}
        s1 = _serialize_for_hash(d)
        d2 = {"a": 2, "b": 1}
        s2 = _serialize_for_hash(d2)
        assert s1 == s2

    def test_non_json_values_stringified(self):
        d = {"expr": sympy.Symbol("x") ** 2}
        # Should not raise
        s = _serialize_for_hash(d)
        assert isinstance(s, str)
