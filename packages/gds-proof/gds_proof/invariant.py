"""Invariant — a named formal requirement as a SymPy BooleanExpr.

Two orthogonal proof fields:

``analytic_status``
    Set by ``analyze_invariants()``.  Records the result of the automatic
    four-strategy SymPy implication prover across all (invariant, block)
    pairs.  Does not involve user-authored proofs.

``proof_hash``
    Set by ``attach_proof()`` after ``verify_proof()`` returns VERIFIED for
    a ``ProofScript`` targeting this invariant.  Records the SHA-256 hex
    digest that binds the proof script content to the model version.
    ``None`` means no verified proof script has been attached.

The two fields are independent: an invariant may have
``analytic_status="INCONCLUSIVE"`` and a non-None ``proof_hash`` (the
auxiliary proof upgrades an inconclusive automatic result), or
``analytic_status="PROVED"`` with ``proof_hash=None`` (automatic proof
succeeded, no manual script needed).
"""

from __future__ import annotations

from typing import Any, Literal

import sympy  # noqa: TC002
from pydantic import BaseModel, ConfigDict

from gds_proof.types import SympyBoolean, SympyExpr  # noqa: TC001


class Invariant(BaseModel):
    """Formal model-level requirement as a SymPy BooleanExpr."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    expr: SympyBoolean
    kind: Literal["prepopulated", "user_declared"] = "user_declared"
    description: str | None = None

    # ------------------------------------------------------------------
    # Automatic symbolic analysis — filled by analyze_invariants()
    # ------------------------------------------------------------------

    analytic_status: Literal["PROVED", "DISPROVED", "INCONCLUSIVE"] | None = None
    """Verdict of the automatic four-strategy implication prover.

    PROVED     — every (invariant, block) pair was proved symbolically.
    DISPROVED  — at least one pair was disproved (a counterexample exists).
    INCONCLUSIVE — at least one pair could not be resolved.
    """

    counterexample: dict[str, Any] | None = None
    """Symbol assignment that witnesses a DISPROVED verdict, if found."""

    inconclusive_residual: SympyExpr | None = None
    """Residual expression from the best-effort simplification attempt
    when the prover returned INCONCLUSIVE.  Useful for diagnosing why
    the prover could not resolve the pair."""

    # ------------------------------------------------------------------
    # Auxiliary proof attachment — filled by attach_proof()
    # ------------------------------------------------------------------

    proof_hash: str | None = None
    """SHA-256 hex digest of the ProofScript that has been verified for
    this invariant on the associated model version.

    Set exclusively via ``attach_proof(invariant, script, model_hash)``,
    which enforces that ``verify_proof`` returned VERIFIED before writing
    this field.  ``None`` means no proof script has been attached.
    """

    @property
    def free_symbols(self) -> frozenset[sympy.Symbol]:
        """Free symbols referenced by this invariant's expression."""
        return frozenset(self.expr.free_symbols)

    @property
    def is_proved(self) -> bool:
        """True iff automatic analysis proved the invariant."""
        return self.analytic_status == "PROVED"

    @property
    def has_proof_script(self) -> bool:
        """True iff a verified auxiliary proof script has been attached."""
        return self.proof_hash is not None
