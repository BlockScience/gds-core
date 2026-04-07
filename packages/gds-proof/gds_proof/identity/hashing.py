"""Deterministic SHA-256 hashing for model identity and proof binding.

Pure functions — no state.

Hash scope
----------
``hash_model``
    Hashes the model's declared components via ``canonical_dict()``.
    Excludes execution artifacts (analysis results, provenance, approval).
    Two models with identical declarations produce identical hashes
    regardless of construction order.

``hash_proof``
    Hashes the lemma chain content (names, kinds, srepr'd expressions,
    expected values, assumptions) together with the ``model_hash``.
    Binds the proof to a specific model version: if the model changes,
    the proof hash changes, alerting auditors to re-verify.

The evidence chain
------------------

    model.canonical_dict()
        └─ hash_model(model) → model_hash          (64-char SHA-256 hex)
              └─ hash_proof(script, model_hash) → proof_hash
                    └─ verify_proof(script, model_hash) → ProofResult
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import sympy

from gds_proof.analysis.proof import ProofScript  # noqa: TC001
from gds_proof.protocols import ProofableModel  # noqa: TC001


def _serialize_for_hash(data: dict) -> str:
    """JSON-serialize a dict deterministically for hashing.

    Uses ``sort_keys=True`` and ``default=str`` to handle any non-JSON
    values (e.g. SymPy expressions that slipped through un-srepr'd).
    """
    return json.dumps(data, sort_keys=True, default=str)


def hash_model(model: ProofableModel) -> str:
    """Deterministic SHA-256 hash of a model's declared components.

    Delegates to ``model.canonical_dict()``, which implementors build
    via ``make_canonical_dict()`` from ``gds_proof.serialization.canonical``.

    Parameters
    ----------
    model:
        Any object satisfying the ``ProofableModel`` protocol.

    Returns
    -------
    str
        64-character SHA-256 hex digest.
    """
    data = model.canonical_dict()
    serialized = _serialize_for_hash(data)
    return hashlib.sha256(serialized.encode()).hexdigest()


def hash_proof(script: ProofScript, model_hash: str) -> str:
    """Deterministic SHA-256 hash binding a proof script to a model version.

    Hashes the lemma chain content (names, kinds, srepr'd expressions,
    expected values, assumptions) together with ``model_hash``.  Excludes
    verification results (those are execution artifacts, not proof content).

    If the model changes (model_hash changes) the proof hash changes, even
    if the lemma content is identical.  This surfaces the need to re-verify
    the proof against the updated model.

    Parameters
    ----------
    script:
        The ``ProofScript`` to hash.
    model_hash:
        64-char SHA-256 hex digest of the model this proof targets.

    Returns
    -------
    str
        64-character SHA-256 hex digest.
    """
    lemma_records: list[dict[str, Any]] = []
    for lemma in script.lemmas:
        lemma_records.append(
            {
                "name": lemma.name,
                "kind": lemma.kind.value,
                "expr": sympy.srepr(lemma.expr),
                "expected": (
                    sympy.srepr(lemma.expected) if lemma.expected is not None else None
                ),
                "assumptions": lemma.assumptions,
                "depends_on": sorted(lemma.depends_on),
            }
        )
    data: dict[str, Any] = {
        "model_hash": model_hash,
        "target_invariant": script.target_invariant,
        "lemmas": lemma_records,
    }
    serialized = _serialize_for_hash(data)
    return hashlib.sha256(serialized.encode()).hexdigest()
