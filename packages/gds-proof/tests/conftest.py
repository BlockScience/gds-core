"""Shared fixtures for the gds-proof test suite.

Concrete implementations of ProofableBlock and ProofableModel are defined
here for reuse across all test modules.

Symbol convention
-----------------
All symbols are PLAIN (no assumptions baked in).  Assumptions belong in
``assumption_context()``, not on the symbol.  Baking ``nonnegative=True``
into a symbol causes invariants like ``x >= 0`` to simplify to
``sympy.true`` before the proof engine sees them — vacuity fires spuriously.

Block catalogue
---------------
withdrawal  — x = x_prev - u,  pred: u < x_prev  (pullback of x > 0)
deposit     — x = x_prev + u,  no predicate
disjoint    — acts on z (different symbol space from x_prev invariants)
open_output — withdrawal + unwired output y = x_prev - u
"""

from __future__ import annotations

import pytest
import sympy

from gds_proof import (
    Invariant,
    make_canonical_dict,
    predicate_from_post_check,
)

# ---------------------------------------------------------------------------
# Canonical test symbols — plain, no assumptions
# ---------------------------------------------------------------------------

X = sympy.Symbol("x_prev")  # pre-state
U = sympy.Symbol("u")  # input
Y = sympy.Symbol("y")  # open output port
Z = sympy.Symbol("z")  # disjoint state (different block)


# ---------------------------------------------------------------------------
# Reusable concrete block
# ---------------------------------------------------------------------------


class SimpleBlock:
    """Configurable concrete block satisfying ProofableBlock."""

    def __init__(
        self,
        name: str,
        prev_state: frozenset,
        inputs: frozenset,
        predicates_list: list,
        transition: dict,
        outputs: dict,
        subs: dict,
    ) -> None:
        self._name = name
        self._prev_state = prev_state
        self._inputs = inputs
        self._predicates = predicates_list
        self._transition = transition
        self._outputs = outputs
        self._subs = subs

    @property
    def name(self) -> str:
        return self._name

    @property
    def prev_state_symbols(self) -> frozenset:
        return self._prev_state

    @property
    def input_symbols(self) -> frozenset:
        return self._inputs

    @property
    def predicates(self) -> list:
        return self._predicates

    @property
    def state_transition(self) -> dict:
        return self._transition

    @property
    def output_expressions(self) -> dict:
        return self._outputs

    def substitution(self) -> dict:
        return self._subs


# ---------------------------------------------------------------------------
# Reusable concrete model
# ---------------------------------------------------------------------------


class SimpleModel:
    """Configurable concrete model satisfying ProofableModel."""

    def __init__(
        self,
        blocks_dict: dict,
        invariants_dict: dict,
        assumptions: dict | None = None,
    ) -> None:
        self._blocks = blocks_dict
        self._invariants = invariants_dict
        self._assumptions = assumptions or {}

    def blocks(self) -> dict:
        return self._blocks

    def invariants(self) -> dict:
        return self._invariants

    def assumption_context(self) -> dict:
        return self._assumptions

    def canonical_dict(self) -> dict:
        return make_canonical_dict(
            {
                "blocks": {
                    name: {
                        "state_transition": {
                            k: str(v) for k, v in blk.state_transition.items()
                        }
                    }
                    for name, blk in self._blocks.items()
                },
                "invariants": {
                    name: inv.expr for name, inv in self._invariants.items()
                },
            }
        )


# ---------------------------------------------------------------------------
# Block fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def withdrawal_block() -> SimpleBlock:
    """x = x_prev - u,  predicate: u < x_prev (pullback of x > 0)."""
    pred = predicate_from_post_check(
        name="no_overdraft",
        post_state_check=sympy.Symbol("x") > 0,
        state_transition={"x": X - U},
        description="Balance remains positive after withdrawal",
    )
    return SimpleBlock(
        name="withdrawal",
        prev_state=frozenset({X}),
        inputs=frozenset({U}),
        predicates_list=[pred.expr],
        transition={"x_prev": X - U},
        outputs={"balance": X - U},
        subs={X: X - U},
    )


@pytest.fixture
def deposit_block() -> SimpleBlock:
    """x = x_prev + u,  no predicate (always admissible)."""
    return SimpleBlock(
        name="deposit",
        prev_state=frozenset({X}),
        inputs=frozenset({U}),
        predicates_list=[],
        transition={"x_prev": X + U},
        outputs={"balance": X + U},
        subs={X: X + U},
    )


@pytest.fixture
def disjoint_block() -> SimpleBlock:
    """Acts on Z — disjoint symbol space from X-based invariants."""
    return SimpleBlock(
        name="disjoint",
        prev_state=frozenset({Z}),
        inputs=frozenset(),
        predicates_list=[],
        transition={"z": Z + 1},
        outputs={"z_out": Z + 1},
        subs={Z: Z + 1},
    )


@pytest.fixture
def open_output_block() -> SimpleBlock:
    """Withdrawal block that also maps output symbol Y (unwired/open port)."""
    pred = predicate_from_post_check(
        name="no_overdraft",
        post_state_check=sympy.Symbol("x") > 0,
        state_transition={"x": X - U},
    )
    return SimpleBlock(
        name="withdrawal_open",
        prev_state=frozenset({X}),
        inputs=frozenset({U}),
        predicates_list=[pred.expr],
        transition={"x_prev": X - U},
        outputs={"y": X - U},
        # substitution includes BOTH state and output symbol mappings
        subs={X: X - U, Y: X - U},
    )


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------

STANDARD_ASSUMPTIONS = {
    X: {"nonnegative": True, "real": True},
    U: {"nonnegative": True, "real": True},
}


@pytest.fixture
def withdrawal_model(withdrawal_block) -> SimpleModel:
    """One block, one invariant: balance_nonneg (x_prev >= 0)."""
    return SimpleModel(
        blocks_dict={"withdrawal": withdrawal_block},
        invariants_dict={
            "balance_nonneg": Invariant(
                name="balance_nonneg",
                expr=sympy.Ge(X, 0),
            )
        },
        assumptions=STANDARD_ASSUMPTIONS,
    )


@pytest.fixture
def deposit_model(deposit_block) -> SimpleModel:
    """Deposit block only — x_prev + u >= 0 is trivially preserved for nonneg."""
    return SimpleModel(
        blocks_dict={"deposit": deposit_block},
        invariants_dict={
            "balance_nonneg": Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        },
        assumptions=STANDARD_ASSUMPTIONS,
    )


@pytest.fixture
def disjoint_model(disjoint_block) -> SimpleModel:
    """Block acts on Z, invariant is over X — vacuity should fire."""
    return SimpleModel(
        blocks_dict={"disjoint": disjoint_block},
        invariants_dict={
            "balance_nonneg": Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        },
        assumptions=STANDARD_ASSUMPTIONS,
    )


@pytest.fixture
def open_output_model(open_output_block) -> SimpleModel:
    """Block with open output Y — invariant over Y must not trigger vacuity."""
    return SimpleModel(
        blocks_dict={"withdrawal_open": open_output_block},
        invariants_dict={
            "balance_nonneg": Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0)),
            "output_nonneg": Invariant(name="output_nonneg", expr=sympy.Ge(Y, 0)),
        },
        assumptions=STANDARD_ASSUMPTIONS,
    )


@pytest.fixture
def multi_block_model(withdrawal_block, deposit_block) -> SimpleModel:
    """Both withdrawal and deposit blocks, one invariant."""
    return SimpleModel(
        blocks_dict={
            "withdrawal": withdrawal_block,
            "deposit": deposit_block,
        },
        invariants_dict={
            "balance_nonneg": Invariant(name="balance_nonneg", expr=sympy.Ge(X, 0))
        },
        assumptions=STANDARD_ASSUMPTIONS,
    )


# ---------------------------------------------------------------------------
# Proof script fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def model_hash(withdrawal_model) -> str:
    from gds_proof import hash_model

    return hash_model(withdrawal_model)


@pytest.fixture
def geometric_series_script(model_hash) -> object:
    """ProofScript: Sum(1/2^k, k=0..inf) = 2.  Guaranteed evaluable by SymPy."""
    from gds_proof import LemmaKind, ProofBuilder

    k = sympy.Symbol("k", integer=True, nonneg=True)
    return (
        ProofBuilder(
            model_hash,
            "balance_nonneg",
            "geometric_series_proof",
            "Geometric series convergence as example auxiliary lemma",
        )
        .lemma(
            "series_limit",
            LemmaKind.EQUALITY,
            expr=sympy.Sum(sympy.Rational(1, 2) ** k, (k, 0, sympy.oo)),
            expected=sympy.Integer(2),
            description="Sum of 1/2^k from 0 to infinity equals 2",
        )
        .build()
    )


@pytest.fixture
def bad_model_hash() -> str:
    return "0" * 64
