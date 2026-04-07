"""Predicate-guarded inductive safety analysis.

Answers the question: starting from a state where all invariants hold,
can any sequence of predicate-admitted transitions reach a state that
violates an invariant?

This is distinct from ``gds_analysis.reachability`` which computes concrete
forward/backward reachable state sets via simulation.  This module proves
symbolic inductive safety via predicate implication.

Open-world model semantics
--------------------------
Port closure is NOT required.  Open inputs are universally quantified over
``U_{x_prev}`` — any signal that passes the predicate COULD arrive.  This
is the strongest possible assumption for safety analysis: we prove the
invariant holds for ALL admitted inputs, wired or not.

Three layers of analysis
------------------------

1. **Single-step** — for each (invariant I_j, block k) pair:

       [I_1(x) ∧ … ∧ I_n(x)] ∧ [P_1(x, u) ∧ … ∧ P_m(x, u)]
       →  I_j(f(x, u))

   The antecedent includes ALL invariants (not just the one being checked),
   reflecting the fact that the system starts from a fully valid state.

2. **Predicate sufficiency** — predicates alone, without invariants:

       [P_1(x, u) ∧ … ∧ P_m(x, u)]  →  I_j(f(x, u))

   Tests whether the block's local admissibility guards are sufficient
   on their own, regardless of starting state.

3. **Multi-step induction** — if ALL single-step results are PROVED, then
   by induction no reachable state violates any invariant.
"""

from __future__ import annotations

from enum import StrEnum

import sympy
from pydantic import BaseModel, ConfigDict

from gds_proof.invariant import Invariant  # noqa: TC001
from gds_proof.protocols import SymbolicBlock, SymbolicModel  # noqa: TC001
from gds_proof.types import SympyExpr  # noqa: TC001

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class SingleStepVerdict(StrEnum):
    """Verdict for single-step inductive safety of one (invariant, block) pair."""

    PROVED = "PROVED"
    DISPROVED = "DISPROVED"
    INCONCLUSIVE = "INCONCLUSIVE"


class SingleStepResult(BaseModel):
    """Single-step inductive safety for one (invariant, block) pair.

    Uses the conjunction of ALL model invariants in the antecedent,
    not just the one being checked.  This reflects starting from a fully
    valid state.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    invariant_name: str
    mechanism_name: str
    verdict: SingleStepVerdict
    antecedent_invariant_names: list[str] = []
    """Names of all invariants included in the antecedent conjunction."""

    predicate_count: int = 0
    """Number of predicates included from the block."""

    counterexample: dict | None = None
    residual: SympyExpr | None = None


class PredicateSufficiencyVerdict(StrEnum):
    """Whether a block's predicates alone prevent invariant violation."""

    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    INCONCLUSIVE = "INCONCLUSIVE"


class PredicateSufficiencyResult(BaseModel):
    """Predicate-only analysis for one (invariant, block) pair.

    Tests whether the block's local admissibility guards suffice without
    needing the full invariant conjunction in the antecedent.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    invariant_name: str
    mechanism_name: str
    verdict: PredicateSufficiencyVerdict
    predicate_count: int = 0
    residual: SympyExpr | None = None


class MultiStepVerdict(StrEnum):
    """Global inductive safety verdict."""

    PROVED = "PROVED"
    """All single-step pairs are PROVED.  By induction, no admitted
    transition sequence can reach an invariant-violating state."""

    INCONCLUSIVE = "INCONCLUSIVE"
    """At least one pair is INCONCLUSIVE.  Cannot establish global safety."""

    DISPROVED = "DISPROVED"
    """At least one pair is DISPROVED.  A counterexample transition exists."""


class MultiStepResult(BaseModel):
    """Global inductive safety result."""

    verdict: MultiStepVerdict
    failing_pairs: list[tuple[str, str]] = []
    """(invariant_name, block_name) pairs that prevented PROVED."""


class InductiveSafetyResult(BaseModel):
    """Complete three-layer inductive safety analysis for a model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    single_step: list[SingleStepResult] = []
    predicate_sufficiency: list[PredicateSufficiencyResult] = []
    multi_step: MultiStepResult = MultiStepResult(verdict=MultiStepVerdict.INCONCLUSIVE)

    def has_unsafe(self) -> bool:
        """True iff any single-step pair was DISPROVED."""
        return any(r.verdict == SingleStepVerdict.DISPROVED for r in self.single_step)

    def self_certifying_pairs(self) -> list[tuple[str, str]]:
        """(invariant, block) pairs where predicate sufficiency is SUFFICIENT."""
        return [
            (r.invariant_name, r.mechanism_name)
            for r in self.predicate_sufficiency
            if r.verdict == PredicateSufficiencyVerdict.SUFFICIENT
        ]

    def unresolved_invariants(self) -> list[str]:
        """Invariant names with at least one INCONCLUSIVE single-step result."""
        return sorted(
            {
                r.invariant_name
                for r in self.single_step
                if r.verdict == SingleStepVerdict.INCONCLUSIVE
            }
        )


# Deprecated alias — remove in v1.0.0
ReachabilityAnalysisResult = InductiveSafetyResult


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_invariant_conjunction(
    invariants: dict[str, Invariant],
    assumed_subs: dict[sympy.Basic, sympy.Basic],
) -> sympy.Basic:
    """Conjoin all invariant expressions with assumption-enhanced symbols."""
    exprs = [inv.expr.subs(assumed_subs) for inv in invariants.values()]
    if not exprs:
        return sympy.true
    return sympy.And(*exprs) if len(exprs) > 1 else exprs[0]


def _build_predicate_conjunction(
    block: SymbolicBlock,
    assumed_subs: dict[sympy.Basic, sympy.Basic],
) -> sympy.Basic | None:
    """Conjoin all block predicates with assumption-enhanced symbols.

    Returns None if the block has no predicates.
    """
    preds = block.predicates
    if not preds:
        return None
    enhanced = [p.subs(assumed_subs) for p in preds]
    return sympy.And(*enhanced) if len(enhanced) > 1 else enhanced[0]


def _try_prove_implication(
    antecedent: sympy.Basic,
    consequent: sympy.Basic,
) -> bool | None:
    """Attempt to prove or disprove ``antecedent → consequent`` via simplify.

    Returns True (proved), False (disproved), or None (inconclusive).
    """
    try:
        impl = sympy.Implies(antecedent, consequent)
        result = sympy.simplify(impl)
        if result is sympy.true:
            return True
        if result is sympy.false:
            return False
        return None
    except (TypeError, ValueError, RecursionError, sympy.SympifyError):
        return None


# ---------------------------------------------------------------------------
# Single-step analysis
# ---------------------------------------------------------------------------


def _analyze_single_step(
    inv_name: str,
    inv_expr: sympy.Basic,
    block_name: str,
    block: SymbolicBlock,
    all_invariants: dict[str, Invariant],
    assumed_subs: dict[sympy.Basic, sympy.Basic],
) -> SingleStepResult:
    """Single-step inductive safety for one (invariant, block) pair."""
    subs = block.substitution()
    post_inv = inv_expr.subs(subs).subs(assumed_subs)
    inv_conjunction = _build_invariant_conjunction(all_invariants, assumed_subs)
    pred_conjunction = _build_predicate_conjunction(block, assumed_subs)
    pred_count = len(block.predicates)

    if pred_conjunction is not None:
        antecedent = sympy.And(inv_conjunction, pred_conjunction)
    else:
        antecedent = inv_conjunction

    proved = _try_prove_implication(antecedent, post_inv)

    if proved is True:
        return SingleStepResult(
            invariant_name=inv_name,
            mechanism_name=block_name,
            verdict=SingleStepVerdict.PROVED,
            antecedent_invariant_names=list(all_invariants.keys()),
            predicate_count=pred_count,
        )
    if proved is False:
        return SingleStepResult(
            invariant_name=inv_name,
            mechanism_name=block_name,
            verdict=SingleStepVerdict.DISPROVED,
            antecedent_invariant_names=list(all_invariants.keys()),
            predicate_count=pred_count,
        )
    return SingleStepResult(
        invariant_name=inv_name,
        mechanism_name=block_name,
        verdict=SingleStepVerdict.INCONCLUSIVE,
        antecedent_invariant_names=list(all_invariants.keys()),
        predicate_count=pred_count,
        residual=post_inv,
    )


# ---------------------------------------------------------------------------
# Predicate sufficiency
# ---------------------------------------------------------------------------


def _analyze_predicate_sufficiency(
    inv_name: str,
    inv_expr: sympy.Basic,
    block_name: str,
    block: SymbolicBlock,
    assumed_subs: dict[sympy.Basic, sympy.Basic],
) -> PredicateSufficiencyResult:
    """Test whether block predicates alone prevent invariant violation."""
    subs = block.substitution()
    post_inv = inv_expr.subs(subs).subs(assumed_subs)
    pred_conjunction = _build_predicate_conjunction(block, assumed_subs)
    pred_count = len(block.predicates)

    if pred_conjunction is None:
        return PredicateSufficiencyResult(
            invariant_name=inv_name,
            mechanism_name=block_name,
            verdict=PredicateSufficiencyVerdict.INCONCLUSIVE,
            predicate_count=0,
        )

    proved = _try_prove_implication(pred_conjunction, post_inv)

    if proved is True:
        return PredicateSufficiencyResult(
            invariant_name=inv_name,
            mechanism_name=block_name,
            verdict=PredicateSufficiencyVerdict.SUFFICIENT,
            predicate_count=pred_count,
        )
    if proved is False:
        return PredicateSufficiencyResult(
            invariant_name=inv_name,
            mechanism_name=block_name,
            verdict=PredicateSufficiencyVerdict.INSUFFICIENT,
            predicate_count=pred_count,
            residual=post_inv,
        )
    return PredicateSufficiencyResult(
        invariant_name=inv_name,
        mechanism_name=block_name,
        verdict=PredicateSufficiencyVerdict.INCONCLUSIVE,
        predicate_count=pred_count,
        residual=post_inv,
    )


# ---------------------------------------------------------------------------
# Multi-step induction
# ---------------------------------------------------------------------------


def _derive_multi_step(single_step_results: list[SingleStepResult]) -> MultiStepResult:
    """Derive global inductive safety from single-step results."""
    failing: list[tuple[str, str]] = []
    has_disproved = False

    for r in single_step_results:
        if r.verdict != SingleStepVerdict.PROVED:
            failing.append((r.invariant_name, r.mechanism_name))
            if r.verdict == SingleStepVerdict.DISPROVED:
                has_disproved = True

    if not failing:
        return MultiStepResult(verdict=MultiStepVerdict.PROVED, failing_pairs=[])

    if has_disproved:
        verdict = MultiStepVerdict.DISPROVED
    else:
        verdict = MultiStepVerdict.INCONCLUSIVE
    return MultiStepResult(verdict=verdict, failing_pairs=failing)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def analyze_inductive_safety(model: SymbolicModel) -> InductiveSafetyResult:
    """Run three-layer predicate-guarded inductive safety analysis.

    Parameters
    ----------
    model:
        Any object satisfying ``SymbolicModel``.

    Returns
    -------
    InductiveSafetyResult
        Single-step results, predicate sufficiency results, and the
        multi-step inductive safety verdict.
    """
    from gds_proof.analysis.symbolic import _make_assumed_symbols

    assumptions = model.assumption_context()
    assumed_subs = _make_assumed_symbols(assumptions)
    all_invariants = model.invariants()
    all_blocks = model.blocks()

    single_step_results: list[SingleStepResult] = []
    sufficiency_results: list[PredicateSufficiencyResult] = []

    for inv_name, inv in all_invariants.items():
        for block_name, block in all_blocks.items():
            single_step_results.append(
                _analyze_single_step(
                    inv_name,
                    inv.expr,
                    block_name,
                    block,
                    all_invariants,
                    assumed_subs,
                )
            )
            sufficiency_results.append(
                _analyze_predicate_sufficiency(
                    inv_name,
                    inv.expr,
                    block_name,
                    block,
                    assumed_subs,
                )
            )

    multi_step = _derive_multi_step(single_step_results)

    return InductiveSafetyResult(
        single_step=single_step_results,
        predicate_sufficiency=sufficiency_results,
        multi_step=multi_step,
    )


# Deprecated alias — remove in v1.0.0
analyze_reachability = analyze_inductive_safety
