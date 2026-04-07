"""Tests for gds_proof.serialization.canonical."""

from __future__ import annotations

import pytest
import sympy

from gds_proof import (
    Invariant,
    canonical_srepr,
    make_canonical_dict,
    restore_expr,
    validate_block_predicates,
)
from gds_proof.serialization.canonical import canonical_invariant_dict
from tests.conftest import SimpleBlock, U, X, Y

# ---------------------------------------------------------------------------
# REQ-CANONICAL-01: make_canonical_dict is insertion-order-independent
# ---------------------------------------------------------------------------


class TestMakeCanonicalDict:
    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_order_independent(self):
        x, y = sympy.symbols("x y")
        d1 = make_canonical_dict({"b": x + y, "a": x**2})
        d2 = make_canonical_dict({"a": x**2, "b": x + y})
        assert d1 == d2

    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_nested_dict_order_independent(self):
        x = sympy.Symbol("x")
        d1 = make_canonical_dict({"outer": {"b": x, "a": x + 1}})
        d2 = make_canonical_dict({"outer": {"a": x + 1, "b": x}})
        assert d1 == d2

    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_sympy_expressions_become_strings(self):
        x = sympy.Symbol("x")
        d = make_canonical_dict({"expr": x**2 + 1})
        assert isinstance(d["expr"], str)

    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_sympy_expr_round_trips(self):
        x = sympy.Symbol("x")
        expr = x**2 + 2 * x + 1
        d = make_canonical_dict({"e": expr})
        restored = sympy.sympify(d["e"])
        assert sympy.simplify(restored - expr) == 0

    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_list_values_preserved_in_order(self):
        x, y = sympy.symbols("x y")
        d = make_canonical_dict({"items": [x, y]})
        # Lists are NOT sorted — only dict keys are sorted
        assert d["items"][0] == sympy.srepr(x)
        assert d["items"][1] == sympy.srepr(y)

    @pytest.mark.requirement("REQ-CANONICAL-01")
    def test_scalar_values_pass_through(self):
        d = make_canonical_dict({"n": 42, "s": "hello", "b": True})
        assert d["n"] == 42
        assert d["s"] == "hello"
        assert d["b"] is True


# ---------------------------------------------------------------------------
# REQ-SERIAL-01: canonical_srepr is deterministic and round-trips
# ---------------------------------------------------------------------------


class TestCanonicalSrepr:
    @pytest.mark.requirement("REQ-SERIAL-01")
    def test_deterministic(self):
        x, y = sympy.symbols("x y")
        expr = x**2 + 2 * x * y + y**2
        assert canonical_srepr(expr) == canonical_srepr(expr)

    @pytest.mark.requirement("REQ-SERIAL-01")
    def test_round_trip(self):
        x, y = sympy.symbols("x y")
        expr = x**2 + 2 * x * y + y**2
        s = canonical_srepr(expr)
        restored = restore_expr(s)
        assert sympy.simplify(restored - expr) == 0

    @pytest.mark.requirement("REQ-SERIAL-01")
    def test_different_expressions_different_reprs(self):
        x = sympy.Symbol("x")
        assert canonical_srepr(x) != canonical_srepr(x + 1)

    @pytest.mark.requirement("REQ-SERIAL-01")
    def test_sympy_true_round_trips(self):
        s = canonical_srepr(sympy.true)
        assert restore_expr(s) == sympy.true

    @pytest.mark.requirement("REQ-SERIAL-01")
    def test_boolean_expr_round_trips(self):
        x = sympy.Symbol("x")
        expr = sympy.Ge(x, 0)
        s = canonical_srepr(expr)
        restored = restore_expr(s)
        # BooleanExpr: compare via srepr equality (subtraction not defined)
        assert canonical_srepr(restored) == canonical_srepr(expr)


# ---------------------------------------------------------------------------
# canonical_invariant_dict
# ---------------------------------------------------------------------------


class TestCanonicalInvariantDict:
    def test_excludes_execution_artifacts(self):
        inv = Invariant(
            name="x_nonneg",
            expr=sympy.Ge(X, 0),
            analytic_status="PROVED",
            proof_hash="a" * 64,
        )
        d = canonical_invariant_dict(inv)
        assert "analytic_status" not in d
        assert "proof_hash" not in d
        assert "counterexample" not in d

    def test_includes_declaration_fields(self):
        inv = Invariant(
            name="x_nonneg",
            expr=sympy.Ge(X, 0),
            kind="user_declared",
            description="balance non-negative",
        )
        d = canonical_invariant_dict(inv)
        assert d["name"] == "x_nonneg"
        assert d["kind"] == "user_declared"
        assert d["description"] == "balance non-negative"
        assert "expr" in d

    def test_expr_is_srepr_string(self):
        inv = Invariant(name="x_nonneg", expr=sympy.Ge(X, 0))
        d = canonical_invariant_dict(inv)
        assert isinstance(d["expr"], str)


# ---------------------------------------------------------------------------
# validate_block_predicates
# ---------------------------------------------------------------------------


class TestValidateBlockPredicates:
    def test_valid_state_and_input(self):
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Lt(U, X)],
            transition={"x_prev": X - U},
            outputs={},
            subs={X: X - U},
        )
        assert validate_block_predicates(block) == []

    def test_invalid_outside_symbol(self):
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Lt(Y, X)],  # Y not in domain
            transition={},
            outputs={},
            subs={},
        )
        violations = validate_block_predicates(block)
        assert len(violations) == 1

    def test_state_only_predicate_is_valid(self):
        """x_prev > 0 — references only state, valid state-dependent guard."""
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Gt(X, 0)],
            transition={},
            outputs={},
            subs={},
        )
        assert validate_block_predicates(block) == []

    def test_empty_predicates_always_valid(self):
        block = SimpleBlock(
            name="d",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[],
            transition={},
            outputs={},
            subs={},
        )
        assert validate_block_predicates(block) == []
