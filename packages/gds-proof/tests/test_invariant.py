"""Tests for gds_proof.invariant."""

from __future__ import annotations

import pytest
import sympy

from gds_proof import Invariant
from tests.conftest import X


class TestInvariant:
    @pytest.mark.requirement("REQ-INV-01")
    def test_construction(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0))
        assert inv.name == "x_nonneg"
        assert inv.kind == "user_declared"
        assert inv.description is None
        assert inv.analytic_status is None
        assert inv.proof_hash is None

    @pytest.mark.requirement("REQ-INV-01")
    def test_free_symbols(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0))
        assert X in inv.free_symbols

    @pytest.mark.requirement("REQ-INV-01")
    def test_is_proved_false_by_default(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0))
        assert not inv.is_proved

    @pytest.mark.requirement("REQ-INV-01")
    def test_is_proved_true_when_set(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0), analytic_status="PROVED")
        assert inv.is_proved

    @pytest.mark.requirement("REQ-INV-01")
    def test_has_proof_script_false_by_default(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0))
        assert not inv.has_proof_script

    @pytest.mark.requirement("REQ-INV-01")
    def test_has_proof_script_true_when_set(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0), proof_hash="a" * 64)
        assert inv.has_proof_script

    @pytest.mark.requirement("REQ-INV-01")
    def test_prepopulated_kind(self):
        inv = Invariant(name="auto", expr=sympy.Ge(X, 0), kind="prepopulated")
        assert inv.kind == "prepopulated"

    @pytest.mark.requirement("REQ-INV-02")
    def test_analytic_status_and_proof_hash_are_orthogonal(self):
        """INCONCLUSIVE + proof_hash is valid; PROVED + no proof_hash is valid."""
        inc_with_proof = Invariant(
            name="i",
            expr=sympy.Ge(X, 0),
            analytic_status="INCONCLUSIVE",
            proof_hash="b" * 64,
        )
        proved_no_proof = Invariant(
            name="i",
            expr=sympy.Ge(X, 0),
            analytic_status="PROVED",
        )
        assert inc_with_proof.analytic_status == "INCONCLUSIVE"
        assert inc_with_proof.has_proof_script
        assert proved_no_proof.is_proved
        assert not proved_no_proof.has_proof_script
