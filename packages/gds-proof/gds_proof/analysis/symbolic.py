"""Symbolic invariant implication proofs.

For each (invariant, block) pair, attempts to prove that the block's state
transition preserves the invariant, using four ordered strategies.

Open-world model semantics
--------------------------
Port closure is NOT required.  Open inputs are universally quantified over
``U_{x_prev}`` — the predicate is the type system, not the wiring.  The
proof engine treats all input symbols as universally quantified regardless
of whether they are wired from an upstream block.

Invariants may be stated over output symbols of blocks with unwired
(open) output ports.  ``block.substitution()`` maps both state symbols
(``x_prev → f(x_prev, u)``) and output symbols (``y → c(f(x_prev, u), u)``)
so that ``invariant_expr.subs(block.substitution())`` handles both cases.

The composed model is itself a block: its open inputs form the input
Cartesian product and all outputs form the output Cartesian product.
Proofs on the composed model are proofs on this aggregate block.

Proof obligation
----------------
Given invariant ``I`` and block ``k`` with state transition ``x = f(x_prev, u)``
and predicate set ``{P_j}`` encoding ``U_{x_prev}``:

    ∀ x_prev, ∀ u ∈ U_{x_prev}:
        I(x_prev) ∧ P_1(x_prev, u) ∧ … ∧ P_m(x_prev, u)
        →  I(f(x_prev, u))

where ``I`` may be stated over state symbols, output symbols, or both.

Strategies (tried in order)
-----------------------------
1. ``VACUITY``              -- invariant symbols not in block's
                               combined domain; INCONCLUSIVE.
2. ``DIRECT_SIMPLIFICATION``— ``simplify(post_invariant)`` → True / False.
3. ``PREDICATE_IMPLICATION``— ``simplify(Implies(And(preds, pre), post))``.
4. ``Q_SYSTEM``             — ``sympy.ask()`` with parameter assumptions.
5. ``BARE_IMPLICATION``     — ``simplify(Implies(pre, post))`` no predicates.

Every ``InvariantMechanismResult`` carries a ``proof_method`` field recording
which strategy fired.  Auditors reproduce any result by re-running that
specific strategy against the same invariant, substitution, and assumptions.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

import sympy
from pydantic import BaseModel, ConfigDict, model_validator

from gds_proof.protocols import SymbolicBlock, SymbolicModel  # noqa: TC001
from gds_proof.types import SympyExpr  # noqa: TC001

# ---------------------------------------------------------------------------
# ProofMethod
# ---------------------------------------------------------------------------


class ProofMethod(StrEnum):
    """Which built-in strategy produced the verdict in ``_analyze_pair()``."""

    VACUITY = "vacuity"
    """Invariant and block symbol sets are disjoint.

    The block's transition cannot affect this invariant.
    Result is always INCONCLUSIVE — absence of effect is not a proof of
    preservation; it means the pair was not meaningfully tested.
    """

    DIRECT_SIMPLIFICATION = "direct_simplification"
    """``sympy.simplify(post_invariant)`` evaluates to True or False.

    No predicate conjunction or assumption context.  Catches trivially
    preserved invariants (e.g. the transition is identity on the invariant's
    symbols) and trivially violated ones.
    """

    PREDICATE_IMPLICATION = "predicate_implication"
    """``sympy.simplify(Implies(And(P_1, …, P_m, I_pre), I_post))``.

    Predicates encode ``U_{x_prev}`` — the state-dependent admissible input
    set.  They are typically pullbacks of post-state checks through ``f``, so
    including them in the antecedent directly exposes the local invariant each
    block guarantees, enabling SymPy to chain local → global.
    """

    Q_SYSTEM = "q_system"
    """``sympy.ask()`` with type assumptions from ``model.assumption_context()``.

    Uses parameter bounds (positive, real, finite, …) to load type information
    into the SymPy assumption engine.  Effective when Direct and Predicate
    strategies cannot simplify due to missing type knowledge.
    """

    BARE_IMPLICATION = "bare_implication"
    """``sympy.simplify(Implies(I_pre, I_post))`` without predicates.

    Last resort before INCONCLUSIVE.  Useful when the block has no predicates
    but the invariant is still provable from state structure alone.
    """

    EXCEPTION = "exception"
    """``TypeError``, ``ValueError``, ``RecursionError``, or
    ``sympy.SympifyError`` raised during analysis.  Result is always
    INCONCLUSIVE.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class InvariantMechanismResult(BaseModel):
    """Symbolic proof result for one (invariant, block) pair."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    invariant_name: str
    mechanism_name: str
    status: Literal["PROVED", "DISPROVED", "INCONCLUSIVE"]
    proof_method: ProofMethod
    counterexample: dict | None = None
    residual: SympyExpr | None = None
    """Residual expression when INCONCLUSIVE — useful for diagnosing why
    simplification did not resolve the pair."""

    @model_validator(mode="after")
    def _proof_method_set(self) -> InvariantMechanismResult:
        # proof_method is non-Optional; Pydantic already enforces this.
        # Validator documents the invariant explicitly.
        return self


class SymbolicAnalysisResult(BaseModel):
    """Matrix of all (invariant, block) proof results for a model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    results: list[InvariantMechanismResult] = []

    def has_disproved(self) -> bool:
        """True iff any pair was disproved."""
        return any(r.status == "DISPROVED" for r in self.results)

    def proved_invariants(self) -> list[str]:
        """Names of invariants where ALL paired blocks returned PROVED."""
        proved: set[str] = set()
        not_proved: set[str] = set()
        for r in self.results:
            if r.status == "PROVED":
                proved.add(r.invariant_name)
            else:
                not_proved.add(r.invariant_name)
        return sorted(proved - not_proved)

    def inconclusive_invariants(self) -> list[str]:
        """Names of invariants with at least one INCONCLUSIVE result."""
        return sorted(
            {r.invariant_name for r in self.results if r.status == "INCONCLUSIVE"}
        )

    def disproved_invariants(self) -> list[str]:
        """Names of invariants with at least one DISPROVED result."""
        return sorted(
            {r.invariant_name for r in self.results if r.status == "DISPROVED"}
        )


# ---------------------------------------------------------------------------
# Assumption helpers
# ---------------------------------------------------------------------------


def _make_assumed_symbols(
    assumptions: dict[sympy.Symbol, dict],
) -> dict[sympy.Basic, sympy.Basic]:
    """Map each plain symbol to an assumption-enhanced copy.

    Used to substitute into invariant expressions before simplification,
    giving SymPy access to parameter type information (positive, real, …).
    """
    subs: dict[sympy.Basic, sympy.Basic] = {}
    for sym, asm in assumptions.items():
        if asm:
            enhanced = sympy.Symbol(str(sym), **asm)
            if enhanced != sym:
                subs[sym] = enhanced
    return subs


def _try_qsystem(
    post_invariant: sympy.Basic,
    assumptions: dict[sympy.Symbol, dict],
) -> bool | None:
    """Attempt Q-system proof via ``sympy.ask()``.

    Returns True (proved), False (disproved), or None (inconclusive).
    """
    try:
        facts = []
        for sym, asm in assumptions.items():
            for prop, val in asm.items():
                if val:
                    q_pred = getattr(sympy.Q, prop, None)
                    if q_pred is not None:
                        facts.append(q_pred(sym))

        context = sympy.And(*facts) if facts else sympy.true
        result = sympy.ask(post_invariant, context)

        if result is True:
            return True
        if result is False:
            return False
        return None
    except (TypeError, ValueError, RecursionError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Core pair analysis
# ---------------------------------------------------------------------------


def _analyze_pair(
    invariant_name: str,
    invariant_expr: sympy.Basic,
    block_name: str,
    block: SymbolicBlock,
    assumptions: dict[sympy.Symbol, dict],
) -> InvariantMechanismResult:
    """Attempt to prove I(x_prev) ∧ predicates(x_prev, u) → I(f(x_prev, u)).

    Tries strategies in order; returns on first definitive result.
    Always returns with a non-None ``proof_method``.
    """

    def _result(
        status: Literal["PROVED", "DISPROVED", "INCONCLUSIVE"],
        method: ProofMethod,
        *,
        counterexample: dict | None = None,
        residual: sympy.Basic | None = None,
    ) -> InvariantMechanismResult:
        return InvariantMechanismResult(
            invariant_name=invariant_name,
            mechanism_name=block_name,
            status=status,
            proof_method=method,
            counterexample=counterexample,
            residual=residual,
        )

    # ------------------------------------------------------------------
    # Step 0: Vacuity check.
    # The invariant's free symbols must intersect with the block's combined
    # domain: prev_state_symbols union input_symbols union substitution keys.
    # substitution() maps BOTH state symbols (x_prev) AND output symbols (y),
    # so this correctly handles invariants over unwired output ports.
    #
    # If there is no intersection, this block genuinely cannot affect the
    # invariant — returning INCONCLUSIVE (not PROVED: absence of effect is
    # not a proof of preservation, and the pair was not meaningfully tested).
    #
    # Port closure is NOT required: open inputs and unwired outputs are
    # valid. The vacuity check is purely about symbol reachability.
    # ------------------------------------------------------------------
    inv_syms = invariant_expr.free_symbols
    block_domain = block.prev_state_symbols | block.input_symbols

    try:
        # substitution() is called inside try — it can raise on bad blocks
        subs = block.substitution()
    except (TypeError, ValueError, AttributeError) as exc:
        return _result(
            "INCONCLUSIVE",
            ProofMethod.EXCEPTION,
            residual=sympy.Symbol(f"__error_{exc.__class__.__name__}__"),
        )

    # subs.keys() includes both x_prev symbols and output (y) symbols
    if not (inv_syms & (block_domain | set(subs.keys()))):
        return _result("INCONCLUSIVE", ProofMethod.VACUITY)

    try:
        # Build post-state invariant by substituting the state transition
        post_invariant = invariant_expr.subs(subs)

        # If substitution left the expression structurally unchanged,
        # the block does not affect these symbols — trivially preserved.
        if post_invariant == invariant_expr:
            return _result("PROVED", ProofMethod.DIRECT_SIMPLIFICATION)

        # Apply assumption-enhanced symbols for richer simplification
        assumed_subs = _make_assumed_symbols(assumptions)
        pre_inv = invariant_expr.subs(assumed_subs)
        post_inv = post_invariant.subs(assumed_subs)

        # ------------------------------------------------------------------
        # Strategy 1: Direct simplification of post-invariant
        # ------------------------------------------------------------------
        simplified = sympy.simplify(post_inv)
        if simplified is sympy.true:
            return _result("PROVED", ProofMethod.DIRECT_SIMPLIFICATION)
        if simplified is sympy.false:
            return _result("DISPROVED", ProofMethod.DIRECT_SIMPLIFICATION)

        # ------------------------------------------------------------------
        # Strategy 2: Predicate implication
        # Predicates encode U_{x_prev} — typically check(f(x_prev, u)).
        # Including them in the antecedent exposes the local invariant each
        # block guarantees, enabling SymPy to chain local → global.
        # ------------------------------------------------------------------
        predicates = block.predicates
        if predicates:
            pred_exprs = [p.subs(assumed_subs) for p in predicates]
            conjunction = (
                sympy.And(*pred_exprs) if len(pred_exprs) > 1 else pred_exprs[0]
            )
            impl = sympy.Implies(sympy.And(conjunction, pre_inv), post_inv)
            impl_result = sympy.simplify(impl)
            if impl_result is sympy.true:
                return _result("PROVED", ProofMethod.PREDICATE_IMPLICATION)
            if impl_result is sympy.false:
                return _result(
                    "DISPROVED",
                    ProofMethod.PREDICATE_IMPLICATION,
                    residual=impl_result,
                )

        # ------------------------------------------------------------------
        # Strategy 3: Q-system with parameter assumptions
        # ------------------------------------------------------------------
        q_result = _try_qsystem(post_inv, assumptions)
        if q_result is True:
            return _result("PROVED", ProofMethod.Q_SYSTEM)
        if q_result is False:
            return _result("DISPROVED", ProofMethod.Q_SYSTEM)

        # ------------------------------------------------------------------
        # Strategy 4: Bare implication — no predicates
        # ------------------------------------------------------------------
        bare = sympy.Implies(pre_inv, post_inv)
        bare_result = sympy.simplify(bare)
        if bare_result is sympy.true:
            return _result("PROVED", ProofMethod.BARE_IMPLICATION)
        if bare_result is sympy.false:
            return _result(
                "DISPROVED",
                ProofMethod.BARE_IMPLICATION,
                residual=bare_result,
            )

        # All strategies exhausted — INCONCLUSIVE
        return _result(
            "INCONCLUSIVE",
            ProofMethod.BARE_IMPLICATION,
            residual=bare_result if isinstance(bare_result, sympy.Basic) else None,
        )

    except (TypeError, ValueError, RecursionError, sympy.SympifyError) as exc:
        return _result(
            "INCONCLUSIVE",
            ProofMethod.EXCEPTION,
            residual=sympy.Symbol(f"__error_{exc.__class__.__name__}__"),
        )


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def analyze_invariants(model: SymbolicModel) -> SymbolicAnalysisResult:
    """Run symbolic implication analysis over all (invariant, block) pairs.

    For each pair, attempts to prove that the block's state transition
    preserves the invariant under the predicate-gated admissible input set.

    Parameters
    ----------
    model:
        Any object satisfying ``SymbolicModel``.  The proof engine calls
        ``model.blocks()``, ``model.invariants()``, and
        ``model.assumption_context()`` — nothing else.

    Returns
    -------
    SymbolicAnalysisResult
        One ``InvariantMechanismResult`` per (invariant, block) pair,
        each with a non-None ``proof_method`` recording which strategy fired.
    """
    assumptions = model.assumption_context()
    results: list[InvariantMechanismResult] = []

    for inv_name, inv in model.invariants().items():
        for block_name, block in model.blocks().items():
            result = _analyze_pair(
                inv_name,
                inv.expr,
                block_name,
                block,
                assumptions,
            )
            results.append(result)

    return SymbolicAnalysisResult(results=results)
