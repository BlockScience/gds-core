"""Predicate — a named local admissibility guard on a block.

Canonical construction
----------------------
The admissible input set ``U_{x_prev}`` for a block is typically defined by
choosing a desired post-state property and pulling it back through the state
transition:

    U_{x_prev} = {u ∈ U : check(f(x_prev, u)) = True}

So every predicate has two equivalent forms:

``post_state_form``
    The check as stated over post-state symbols: ``check(x)``.
    This is the design intent — the local invariant the block guarantees
    for every admitted transition.  Example: ``x > 0``.

``expr``
    The same check after substituting ``x = f(x_prev, u)``: expressed over
    ``prev_state_symbols union input_symbols``.  This is what the proof engine
    uses.  Example: ``x_prev - u > 0`` (with ``f(x_prev, u) = x_prev - u``).

The two are related by:

    expr = post_state_form.subs(state_transition)

When ``post_state_form`` is provided alongside the block's ``state_transition``,
``predicate_from_post_check()`` constructs the ``expr`` automatically.

Local invariants and emergent properties
-----------------------------------------
The ``post_state_form`` is the local invariant the block enforces: for every
admitted transition, the post-state satisfies ``check(x)``.  These local
guarantees are the building blocks of emergent global invariants — properties
no single block owns but the composed system produces.

The proof engine uses ``expr`` (the pulled-back form) as an antecedent in the
implication proof:

    I(x_prev) ∧ check(f(x_prev, u)) → I(f(x_prev, u))

Having ``check(f(x_prev, u))`` in the antecedent is precisely what allows
SymPy to exploit the local guarantee when proving the global invariant.

This is a named container for use in domain models implementing
``ProofableBlock``.  The proof engine receives predicates as plain
``list[sympy.Basic]`` via ``ProofableBlock.predicates``.
"""

from __future__ import annotations

import sympy
from pydantic import BaseModel, ConfigDict, model_validator

from gds_proof.types import SympyBoolean  # noqa: TC001


class Predicate(BaseModel):
    """A named SymPy BooleanExpr gating a block's transition.

    Carries both the post-state form (design intent) and the pulled-back
    expr (proof engine input) when available.

    Parameters
    ----------
    name:
        Human-readable identifier, unique within a block.
    expr:
        The predicate as a function of ``prev_state_symbols union input_symbols``.
        This is ``check(f(x_prev, u))`` — the post-state check pulled back
        through the state transition.  Used directly by the proof engine.
    post_state_form:
        Optional.  The check as stated over post-state symbols: ``check(x)``.
        Preserves the design intent for auditors.  When provided,
        ``expr = post_state_form.subs(state_transition)`` must hold.
    description:
        Optional prose explanation of what local invariant this predicate
        enforces and why it was chosen.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    expr: SympyBoolean
    post_state_form: SympyBoolean | None = None
    description: str | None = None

    @model_validator(mode="after")
    def expr_is_boolean(self) -> Predicate:
        """Reject numeric literals masquerading as boolean expressions."""
        if isinstance(self.expr, (sympy.Integer, sympy.Float, sympy.Rational)):
            raise ValueError(
                f"Predicate '{self.name}': expr must be a BooleanExpr, "
                f"got numeric literal {self.expr!r}"
            )
        return self

    @property
    def free_symbols(self) -> frozenset[sympy.Symbol]:
        """Free symbols of the pulled-back predicate expression."""
        return frozenset(self.expr.free_symbols)

    @property
    def post_state_free_symbols(self) -> frozenset[sympy.Symbol]:
        """Free symbols of the post-state form, if provided."""
        if self.post_state_form is None:
            return frozenset()
        return frozenset(self.post_state_form.free_symbols)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def predicate_from_post_check(
    name: str,
    post_state_check: SympyBoolean,
    state_transition: dict[str, sympy.Basic],
    *,
    description: str | None = None,
) -> Predicate:
    """Construct a Predicate from a post-state check and state transition.

    The canonical construction of a predicate:

        U_{x_prev} = {u ∈ U : post_state_check(f(x_prev, u)) = True}

    This function performs the substitution ``x → f(x_prev, u)`` and
    simplifies the result to produce the ``expr`` field.

    Parameters
    ----------
    name:
        Predicate name.
    post_state_check:
        A BooleanExpr over post-state symbols ``x``.
        Example: ``x > 0`` where ``x`` is a SymPy Symbol.
    state_transition:
        Map from post-state symbol name (str) to its transition expression
        ``f_k(x_prev, u)`` — the same as ``ProofableBlock.state_transition``.
        Example: ``{"x": x_prev - u}`` for ``x = x_prev - u``.
    description:
        Optional prose description.

    Returns
    -------
    Predicate
        With ``post_state_form = post_state_check`` and
        ``expr = simplify(post_state_check.subs({Symbol(k): v ...}))``.

    Example
    -------
    ::

        x_prev = sympy.Symbol("x_prev", nonnegative=True)
        u      = sympy.Symbol("u",      nonnegative=True)
        x      = sympy.Symbol("x")

        pred = predicate_from_post_check(
            name="no_overdraft",
            post_state_check=x > 0,
            state_transition={"x": x_prev - u},
            description="Balance remains positive after withdrawal",
        )
        # pred.post_state_form = x > 0
        # pred.expr            = x_prev - u > 0   (i.e. u < x_prev)
    """
    # Build substitution: post-state symbol names → transition expressions
    subs: dict[sympy.Basic, sympy.Basic] = {
        sympy.Symbol(key): val for key, val in state_transition.items()
    }
    expr = sympy.simplify(post_state_check.subs(subs))
    return Predicate(
        name=name,
        expr=expr,
        post_state_form=post_state_check,
        description=description,
    )
