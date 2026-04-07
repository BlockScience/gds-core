"""Auxiliary proof system for user-authored multi-lemma SymPy proofs.

Provides a builder for constructing proof scripts and a verifier that
re-executes each lemma independently.  Proofs target a specific invariant
on a specific model (identified by ``model_hash``) and can upgrade
INCONCLUSIVE symbolic analysis results to PROVED.

Builder and verifier are logically separate:

- ``ProofBuilder`` — client-side construction helper with a chainable API.
- ``verify_proof`` — re-executes the proof independently.  Requires only
  the serialized ``ProofScript`` and the ``model_hash``.  No trust in the
  original analyst is required.

Three lemma kinds correspond to what SymPy reliably verifies:

- ``EQUALITY``  — ``simplify(expr - expected) == 0`` or ``expr.doit() == expected``
- ``BOOLEAN``   — ``simplify(expr)`` evaluates to ``sympy.true``
- ``QUERY``     — ``sympy.ask(expr, context)`` returns ``True``

Attaching a verified proof to an invariant
------------------------------------------
Use ``attach_proof(invariant, script, model_hash)`` — the only sanctioned
write path for ``Invariant.proof_hash``.  It enforces three preconditions
before setting the field.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import sympy
from pydantic import BaseModel, ConfigDict

from gds_proof.invariant import Invariant  # noqa: TC001
from gds_proof.types import SympyExpr  # noqa: TC001

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LemmaKind(StrEnum):
    """The three verification strategies SymPy handles reliably."""

    EQUALITY = "equality"
    """``simplify(expr - expected) == 0`` or ``expr.doit() == expected``."""

    BOOLEAN = "boolean"
    """``simplify(expr)`` is ``sympy.true``."""

    QUERY = "query"
    """``sympy.ask(expr, assumption_context)`` is ``True``."""


class ProofStatus(StrEnum):
    """Overall proof verification status."""

    UNCHECKED = "UNCHECKED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Lemma(BaseModel):
    """A single verifiable SymPy claim within a proof script."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    kind: LemmaKind
    expr: SympyExpr
    expected: SympyExpr | None = None
    """Required for EQUALITY lemmas; the value ``expr`` must equal."""

    assumptions: dict[str, dict] = {}
    """symbol_name → SymPy assumption kwargs, e.g. ``{"x": {"positive": True}}``."""

    depends_on: list[str] = []
    """Names of prior lemmas whose results this lemma logically depends on."""

    description: str = ""


class LemmaResult(BaseModel):
    """Verification output for a single lemma."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    lemma_name: str
    passed: bool
    actual_value: SympyExpr | None = None
    """The SymPy value produced during verification (e.g. ``sympy.true``)."""

    error: str | None = None
    """Exception message if verification raised."""


class ProofResult(BaseModel):
    """Verification output for a complete proof script."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: ProofStatus
    proof_hash: str | None = None
    lemma_results: list[LemmaResult] = []
    failure_summary: str | None = None


class ProofScript(BaseModel):
    """An ordered chain of lemmas targeting one invariant on one model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    target_invariant: str
    model_hash: str
    """SHA-256 hex digest of the model this proof is bound to."""

    claim: str
    """Human-readable statement of what the proof chain establishes."""

    lemmas: list[Lemma]

    def to_evidence(self) -> dict[str, Any]:
        """Serialize proof script as a JSON-compatible evidence record.

        Each lemma expression is serialized with ``sympy.srepr`` for
        deterministic round-trip.  The returned dict is sufficient for
        independent re-verification via ``ProofScript.from_evidence()``.
        """
        return {
            "name": self.name,
            "target_invariant": self.target_invariant,
            "model_hash": self.model_hash,
            "claim": self.claim,
            "lemmas": [
                {
                    "name": lem.name,
                    "kind": lem.kind.value,
                    "expr": sympy.srepr(lem.expr),
                    "expected": (
                        sympy.srepr(lem.expected) if lem.expected is not None else None
                    ),
                    "assumptions": lem.assumptions,
                    "depends_on": lem.depends_on,
                    "description": lem.description,
                }
                for lem in self.lemmas
            ],
        }

    @classmethod
    def from_evidence(cls, data: dict[str, Any]) -> ProofScript:
        """Restore a ``ProofScript`` from an evidence dict.

        Inverse of ``to_evidence()``.  Uses ``sympy.sympify`` to restore
        expressions from their ``srepr`` strings.
        """
        lemmas = []
        for ld in data["lemmas"]:
            lemmas.append(
                Lemma(
                    name=ld["name"],
                    kind=LemmaKind(ld["kind"]),
                    expr=sympy.sympify(ld["expr"]),
                    expected=(
                        sympy.sympify(ld["expected"])
                        if ld.get("expected") is not None
                        else None
                    ),
                    assumptions=ld.get("assumptions", {}),
                    depends_on=ld.get("depends_on", []),
                    description=ld.get("description", ""),
                )
            )
        return cls(
            name=data["name"],
            target_invariant=data["target_invariant"],
            model_hash=data["model_hash"],
            claim=data["claim"],
            lemmas=lemmas,
        )


# ---------------------------------------------------------------------------
# Lemma verification helpers
# ---------------------------------------------------------------------------


def _make_assumed_symbol(name: str, assumptions: dict) -> sympy.Symbol:
    """Create a SymPy Symbol with the given assumption kwargs."""
    return sympy.Symbol(name, **assumptions)


def _build_assumption_subs(
    assumptions: dict[str, dict],
) -> dict[sympy.Symbol, sympy.Symbol]:
    """Map plain symbols to assumption-enhanced symbols for simplification."""
    return {
        sympy.Symbol(name): _make_assumed_symbol(name, asm)
        for name, asm in assumptions.items()
    }


def _build_q_context(assumptions: dict[str, dict]) -> sympy.Basic:
    """Build a SymPy Q assumption context from the assumptions dict."""
    facts = []
    for name, asm in assumptions.items():
        sym = sympy.Symbol(name)
        for prop, val in asm.items():
            if val:
                q_pred = getattr(sympy.Q, prop, None)
                if q_pred is not None:
                    facts.append(q_pred(sym))
    if not facts:
        return sympy.Q.is_true(sympy.true)  # type: ignore[attr-defined]
    return sympy.And(*facts)


# ---------------------------------------------------------------------------
# Lemma verification
# ---------------------------------------------------------------------------


def verify_lemma(lemma: Lemma) -> LemmaResult:
    """Verify a single lemma independently.

    Dispatches on ``lemma.kind``:

    EQUALITY
        ``sympy.simplify(expr - expected) == 0``, falling back to
        ``expr.doit() == expected`` for sum/product expressions.
    BOOLEAN
        ``sympy.simplify(expr) is sympy.true``.
    QUERY
        ``sympy.ask(expr, context)`` is ``True`` under stated assumptions.

    Returns
    -------
    LemmaResult
        ``passed=True`` iff the lemma is verified.
    """
    try:
        assumption_subs = _build_assumption_subs(lemma.assumptions)
        expr_with_assumptions = lemma.expr.subs(assumption_subs)

        if lemma.kind == LemmaKind.EQUALITY:
            if lemma.expected is None:
                return LemmaResult(
                    lemma_name=lemma.name,
                    passed=False,
                    error="EQUALITY lemma requires 'expected' to be set",
                )
            expected_with_assumptions = lemma.expected.subs(assumption_subs)
            diff = sympy.simplify(expr_with_assumptions - expected_with_assumptions)
            if diff == sympy.Integer(0):
                return LemmaResult(
                    lemma_name=lemma.name, passed=True, actual_value=sympy.Integer(0)
                )
            # Fallback: try .doit() for Sum/Product expressions
            evaluated = expr_with_assumptions.doit()
            diff = evaluated - expected_with_assumptions
            if sympy.simplify(diff) == sympy.Integer(0):
                return LemmaResult(
                    lemma_name=lemma.name, passed=True, actual_value=evaluated
                )
            return LemmaResult(
                lemma_name=lemma.name,
                passed=False,
                actual_value=diff,
                error=f"simplify(expr - expected) = {diff}, not 0",
            )

        if lemma.kind == LemmaKind.BOOLEAN:
            result = sympy.simplify(expr_with_assumptions)
            passed = result is sympy.true
            return LemmaResult(
                lemma_name=lemma.name, passed=passed, actual_value=result
            )

        if lemma.kind == LemmaKind.QUERY:
            context = _build_q_context(lemma.assumptions)
            ask_result = sympy.ask(expr_with_assumptions, context)
            passed = ask_result is True
            return LemmaResult(
                lemma_name=lemma.name,
                passed=passed,
                actual_value=sympy.true if passed else sympy.false,
            )

        # Should never reach here — enum exhaustion
        return LemmaResult(  # pragma: no cover
            lemma_name=lemma.name,
            passed=False,
            error=f"Unknown LemmaKind: {lemma.kind}",
        )

    except (TypeError, ValueError, RecursionError, AttributeError) as exc:
        return LemmaResult(lemma_name=lemma.name, passed=False, error=str(exc))


# ---------------------------------------------------------------------------
# Proof script verification
# ---------------------------------------------------------------------------


def verify_proof(script: ProofScript, model_hash: str) -> ProofResult:
    """Verify a complete proof script against a model hash.

    Precondition: ``script.model_hash == model_hash``.  If this does not
    hold, returns FAILED immediately — the proof was authored for a
    different model version.

    Each lemma is verified independently via ``verify_lemma()``.  A single
    failing lemma fails the entire proof.

    Parameters
    ----------
    script:
        The proof script to verify.
    model_hash:
        SHA-256 hex digest of the model the caller is working with.

    Returns
    -------
    ProofResult
        ``status=VERIFIED`` iff all lemmas pass and the model hash matches.
    """
    from gds_proof.identity.hashing import hash_proof

    if script.model_hash != model_hash:
        return ProofResult(
            status=ProofStatus.FAILED,
            failure_summary=(
                f"model_hash mismatch: proof was authored for "
                f"{script.model_hash!r}, caller provided {model_hash!r}"
            ),
        )

    lemma_results: list[LemmaResult] = []
    for lemma in script.lemmas:
        result = verify_lemma(lemma)
        lemma_results.append(result)
        if not result.passed:
            return ProofResult(
                status=ProofStatus.FAILED,
                proof_hash=hash_proof(script, model_hash),
                lemma_results=lemma_results,
                failure_summary=f"Lemma '{lemma.name}' failed: {result.error}",
            )

    return ProofResult(
        status=ProofStatus.VERIFIED,
        proof_hash=hash_proof(script, model_hash),
        lemma_results=lemma_results,
    )


# ---------------------------------------------------------------------------
# Proof attachment
# ---------------------------------------------------------------------------


def attach_proof(
    invariant: Invariant,
    script: ProofScript,
    model_hash: str,
) -> Invariant:
    """Attach a verified proof script to an invariant.

    The only sanctioned write path for ``Invariant.proof_hash``.

    Preconditions (all enforced, raise ``ValueError`` on failure):

    1. ``verify_proof(script, model_hash)`` returns ``ProofStatus.VERIFIED``.
    2. ``script.target_invariant == invariant.name``.
    3. ``script.model_hash == model_hash``.

    Parameters
    ----------
    invariant:
        The invariant to attach the proof to.
    script:
        The proof script to attach.
    model_hash:
        SHA-256 hex digest of the model both ``invariant`` and ``script``
        belong to.

    Returns
    -------
    Invariant
        A new ``Invariant`` instance (Pydantic model copy) with
        ``proof_hash`` set.  The original is not mutated.

    Raises
    ------
    ValueError
        If any precondition is not satisfied.
    """
    from gds_proof.identity.hashing import hash_proof

    if script.target_invariant != invariant.name:
        raise ValueError(
            f"script.target_invariant={script.target_invariant!r} does not "
            f"match invariant.name={invariant.name!r}"
        )
    if script.model_hash != model_hash:
        raise ValueError(
            f"script.model_hash={script.model_hash!r} does not match "
            f"model_hash={model_hash!r}"
        )

    result = verify_proof(script, model_hash)
    if result.status != ProofStatus.VERIFIED:
        raise ValueError(
            f"verify_proof returned {result.status.value}, not VERIFIED. "
            f"Cannot attach an unverified proof. Summary: {result.failure_summary}"
        )

    computed_hash = hash_proof(script, model_hash)
    return invariant.model_copy(update={"proof_hash": computed_hash})


# ---------------------------------------------------------------------------
# Builder (client-side construction helper)
# ---------------------------------------------------------------------------


class ProofBuilder:
    """Chainable builder for constructing auxiliary proof scripts.

    Usage::

        k = sympy.Symbol("k", integer=True, nonneg=True)
        script = (
            ProofBuilder(
                model_hash="125c837a...",
                target_invariant="total_supply_cap",
                name="supply_cap_convergence",
                claim="Geometric series of halving rewards converges to 21M BTC",
            )
            .lemma(
                "geometric_series_limit",
                LemmaKind.EQUALITY,
                expr=sympy.Sum(210000 * 50 / 2**k, (k, 0, sympy.oo)),
                expected=sympy.Integer(21_000_000),
                description="Sum of all block rewards across all eras equals 21M",
            )
            .build()
        )
    """

    def __init__(
        self,
        model_hash: str,
        target_invariant: str,
        name: str,
        claim: str,
    ) -> None:
        self._model_hash = model_hash
        self._target_invariant = target_invariant
        self._name = name
        self._claim = claim
        self._lemmas: list[Lemma] = []

    def lemma(
        self,
        name: str,
        kind: LemmaKind,
        expr: sympy.Basic,
        expected: sympy.Basic | None = None,
        assumptions: dict[str, dict] | None = None,
        depends_on: list[str] | None = None,
        description: str = "",
    ) -> ProofBuilder:
        """Add a lemma to the proof chain and return self for chaining."""
        self._lemmas.append(
            Lemma(
                name=name,
                kind=kind,
                expr=expr,
                expected=expected,
                assumptions=assumptions or {},
                depends_on=depends_on or [],
                description=description,
            )
        )
        return self

    def build(self) -> ProofScript:
        """Finalise and return the ``ProofScript``.

        Does not verify the proof — call ``verify_proof()`` separately.
        """
        if not self._lemmas:
            raise ValueError("A ProofScript must contain at least one lemma.")
        return ProofScript(
            name=self._name,
            target_invariant=self._target_invariant,
            model_hash=self._model_hash,
            claim=self._claim,
            lemmas=list(self._lemmas),
        )
