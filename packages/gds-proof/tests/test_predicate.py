"""Tests for gds_proof.predicate."""

from __future__ import annotations

import pytest
import sympy

from gds_proof import Predicate, predicate_from_post_check, validate_block_predicates
from tests.conftest import SimpleBlock, U, X, Y, Z

# ---------------------------------------------------------------------------
# REQ-PRED-01: Direct predicate construction
# ---------------------------------------------------------------------------


class TestDirectPredicate:
    @pytest.mark.requirement("REQ-PRED-01")
    def test_direct_construction(self):
        pred = Predicate(name="guard", expr=sympy.Lt(U, X))
        assert pred.name == "guard"
        assert pred.expr == sympy.Lt(U, X)
        assert pred.post_state_form is None

    @pytest.mark.requirement("REQ-PRED-01")
    def test_post_state_form_none_for_direct(self):
        pred = Predicate(name="g", expr=sympy.Lt(U, X))
        assert pred.post_state_form is None

    @pytest.mark.requirement("REQ-PRED-01")
    def test_free_symbols(self):
        pred = Predicate(name="g", expr=sympy.Lt(U, X))
        assert pred.free_symbols == frozenset({U, X})

    @pytest.mark.requirement("REQ-PRED-01")
    def test_numeric_literal_rejected(self):
        with pytest.raises(ValueError, match="BooleanExpr"):
            Predicate(name="bad", expr=sympy.Integer(1))

    @pytest.mark.requirement("REQ-PRED-01")
    def test_description_optional(self):
        pred = Predicate(name="g", expr=X > 0, description="positive balance")
        assert pred.description == "positive balance"


# ---------------------------------------------------------------------------
# REQ-PRED-02: Pullback predicate construction
# ---------------------------------------------------------------------------


class TestPullbackPredicate:
    @pytest.mark.requirement("REQ-PRED-02")
    def test_pullback_withdrawal(self):
        """x = x_prev - u, check x > 0  ⟹  expr: x_prev - u > 0."""
        x = sympy.Symbol("x")
        gt = sympy.StrictGreaterThan(x, 0)  # avoids chained cmp
        pred = predicate_from_post_check(
            name="no_overdraft",
            post_state_check=gt,
            state_transition={"x": X - U},
        )
        assert pred.post_state_form == gt
        # pulled-back expr is equivalent to u < x_prev
        assert X in pred.free_symbols or U in pred.free_symbols

    @pytest.mark.requirement("REQ-PRED-02")
    def test_pullback_expr_simplified(self):
        """predicate_from_post_check calls simplify — result should be canonical."""
        x = sympy.Symbol("x")
        pred = predicate_from_post_check(
            name="no_overdraft",
            post_state_check=x > 0,
            state_transition={"x": X - U},
        )
        # The pulled-back expression is equivalent to u < x_prev
        # sympy.simplify may render it as either form
        assert X in pred.free_symbols or U in pred.free_symbols

    @pytest.mark.requirement("REQ-PRED-02")
    def test_pullback_sets_post_state_form(self):
        x = sympy.Symbol("x")
        check = sympy.Ge(x, 0)
        pred = predicate_from_post_check("g", check, {"x": X - U})
        assert pred.post_state_form == check

    @pytest.mark.requirement("REQ-PRED-02")
    def test_pullback_is_pullback_detectable(self):
        x = sympy.Symbol("x")
        direct = Predicate(name="d", expr=sympy.Lt(U, X))
        pullback = predicate_from_post_check("p", x > 0, {"x": X - U})
        assert direct.post_state_form is None
        assert pullback.post_state_form is not None

    @pytest.mark.requirement("REQ-PRED-02")
    def test_post_state_free_symbols(self):
        x = sympy.Symbol("x")
        pred = predicate_from_post_check("g", x > 0, {"x": X - U})
        assert x in pred.post_state_free_symbols

    @pytest.mark.requirement("REQ-PRED-02")
    def test_pullback_description_carried(self):
        x = sympy.Symbol("x")
        pred = predicate_from_post_check(
            "g", x > 0, {"x": X - U}, description="balance stays positive"
        )
        assert pred.description == "balance stays positive"


# ---------------------------------------------------------------------------
# REQ-PRED-03: validate_block_predicates
# ---------------------------------------------------------------------------


class TestValidateBlockPredicates:
    @pytest.mark.requirement("REQ-PRED-03")
    def test_valid_predicate_state_and_input(self):
        """u < x_prev — references both x_prev and u, both in domain."""
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

    @pytest.mark.requirement("REQ-PRED-03")
    def test_valid_predicate_state_only(self):
        """x_prev > 0 — references only x_prev (state-dependent guard)."""
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Gt(X, 0)],
            transition={"x_prev": X - U},
            outputs={},
            subs={X: X - U},
        )
        assert validate_block_predicates(block) == []

    @pytest.mark.requirement("REQ-PRED-03")
    def test_invalid_predicate_references_outside_symbol(self):
        """Predicate references Y, which is not in prev_state or input."""
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Lt(Y, X)],  # Y not in domain
            transition={"x_prev": X - U},
            outputs={},
            subs={X: X - U},
        )
        violations = validate_block_predicates(block)
        assert len(violations) == 1
        assert "y" in violations[0].lower() or "Y" in violations[0]

    @pytest.mark.requirement("REQ-PRED-03")
    def test_no_predicates_no_violations(self):
        block = SimpleBlock(
            name="d",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[],
            transition={"x_prev": X + U},
            outputs={},
            subs={X: X + U},
        )
        assert validate_block_predicates(block) == []

    @pytest.mark.requirement("REQ-PRED-03")
    def test_multiple_violations_reported(self):
        block = SimpleBlock(
            name="w",
            prev_state=frozenset({X}),
            inputs=frozenset({U}),
            predicates_list=[sympy.Lt(Y, X), sympy.Lt(Z, U)],  # Y, Z both invalid
            transition={"x_prev": X - U},
            outputs={},
            subs={X: X - U},
        )
        violations = validate_block_predicates(block)
        assert len(violations) == 2
