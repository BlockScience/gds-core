"""Canonical serialization for gds-proof models and proof scripts.

All SymPy expressions are serialized via ``sympy.srepr()``, which produces
a deterministic, round-trippable string representation.

``make_canonical_dict`` is the single normalization entry point: it
recursively sorts dict keys and srepr's all SymPy expressions.
Implementors of ``ProofableModel.canonical_dict()`` delegate here.
"""

from __future__ import annotations

from typing import Any

import sympy

from gds_proof.analysis.proof import ProofScript  # noqa: TC001
from gds_proof.invariant import Invariant  # noqa: TC001
from gds_proof.protocols import ProofableBlock  # noqa: TC001

# ---------------------------------------------------------------------------
# Core normalization
# ---------------------------------------------------------------------------


def make_canonical_dict(components: Any) -> Any:
    """Recursively sort dict keys and srepr all SymPy expressions.

    Implementors of ``ProofableModel.canonical_dict()`` delegate here
    rather than implementing sort logic themselves.

    Guarantees
    ----------
    Two calls with logically identical components produce identical output
    regardless of insertion order.  This guarantee is the foundation of
    ``hash_model()`` stability.

    Parameters
    ----------
    components:
        Any JSON-compatible structure, possibly containing ``sympy.Basic``
        values at any depth.

    Returns
    -------
    Any
        Same structure with all dict keys sorted and all ``sympy.Basic``
        values replaced by their ``srepr`` strings.
    """

    def _normalize(obj: Any) -> Any:
        if isinstance(obj, sympy.Basic):
            return sympy.srepr(obj)
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in sorted(obj.items())}
        if isinstance(obj, (list, tuple)):
            return [_normalize(v) for v in obj]
        return obj

    return _normalize(components)


# ---------------------------------------------------------------------------
# Expression round-trip
# ---------------------------------------------------------------------------


def canonical_srepr(expr: sympy.Basic) -> str:
    """Deterministic canonical string form of a SymPy expression.

    Uses ``sympy.srepr``, which is fully explicit and round-trippable.
    Prefer this over ``str(expr)`` whenever persistence or hashing is
    involved.
    """
    return sympy.srepr(expr)


def restore_expr(s: str) -> sympy.Basic:
    """Restore a SymPy expression from its ``canonical_srepr`` form."""
    return sympy.sympify(s)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Invariant canonical form
# ---------------------------------------------------------------------------


def canonical_invariant_dict(inv: Invariant) -> dict:
    """JSON-serializable canonical form of an Invariant.

    Includes only declared fields (name, expr, kind, description).
    Excludes analysis results (analytic_status, proof_hash, etc.) which
    are execution artifacts, not declarations.
    """
    return make_canonical_dict(
        {
            "name": inv.name,
            "expr": inv.expr,
            "kind": inv.kind,
            "description": inv.description,
        }
    )


# ---------------------------------------------------------------------------
# Proof canonical form
# ---------------------------------------------------------------------------


def canonical_proof_dict(script: ProofScript) -> dict:
    """JSON-serializable canonical form of a ProofScript.

    Delegates to ``ProofScript.to_evidence()``, which uses ``sympy.srepr``
    for all expressions.  Sufficient for independent re-verification via
    ``ProofScript.from_evidence()``.
    """
    return script.to_evidence()


# ---------------------------------------------------------------------------
# Predicate structural validation
# ---------------------------------------------------------------------------


def validate_block_predicates(block: ProofableBlock) -> list[str]:
    """Check predicate free symbols are in prev_state union input symbols.

    Predicates encode the state-dependent admissible input set ``U_{x_prev}``.
    They may reference both the pre-transition state (``x_prev``) and the
    input (``u``).  A predicate referencing any other symbol is a modelling
    error — the block cannot observe it at decision time.

    Parameters
    ----------
    block:
        The block whose predicates are to be validated.

    Returns
    -------
    list[str]
        Violation messages.  Empty list means all predicates are valid.
    """
    violations: list[str] = []
    admissible = block.prev_state_symbols | block.input_symbols
    for i, pred in enumerate(block.predicates):
        extra = frozenset(pred.free_symbols) - admissible
        if extra:
            violations.append(
                f"Block '{block.name}' predicate[{i}]: free symbols "
                f"{extra} are not in prev_state_symbols union input_symbols "
                f"({admissible}). Predicates may only reference x_prev and u."
            )
    return violations
