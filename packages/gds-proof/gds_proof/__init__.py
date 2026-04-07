"""gds-proof — deterministic model identity and SymPy invariant proof verification.

Core workflow::

    from gds_proof.identity.hashing import hash_model, hash_proof
    from gds_proof.analysis.symbolic import analyze_invariants
    from gds_proof.analysis.reachability import analyze_reachability
    from gds_proof.analysis.proof import (
        ProofBuilder, LemmaKind, verify_proof, attach_proof
    )

    model_hash = hash_model(model)
    symbolic    = analyze_invariants(model)
    reachable   = analyze_reachability(model)

    script = (
        ProofBuilder(model_hash, "my_invariant", "proof_name", "claim text")
        .lemma("step1", LemmaKind.EQUALITY, expr=..., expected=...)
        .build()
    )
    result = verify_proof(script, model_hash)
    inv    = attach_proof(inv, script, model_hash)
"""

__version__ = "0.1.0"

from gds_proof.analysis.proof import (
    Lemma,
    LemmaKind,
    LemmaResult,
    ProofBuilder,
    ProofResult,
    ProofScript,
    ProofStatus,
    attach_proof,
    verify_lemma,
    verify_proof,
)
from gds_proof.analysis.reachability import (
    MultiStepResult,
    MultiStepVerdict,
    PredicateSufficiencyResult,
    PredicateSufficiencyVerdict,
    ReachabilityAnalysisResult,
    SingleStepResult,
    SingleStepVerdict,
    analyze_reachability,
)
from gds_proof.analysis.symbolic import (
    InvariantMechanismResult,
    ProofMethod,
    SymbolicAnalysisResult,
    analyze_invariants,
)
from gds_proof.identity.hashing import hash_model, hash_proof
from gds_proof.invariant import Invariant
from gds_proof.predicate import Predicate, predicate_from_post_check
from gds_proof.protocols import ProofableBlock, ProofableModel
from gds_proof.serialization.canonical import (
    canonical_srepr,
    make_canonical_dict,
    restore_expr,
    validate_block_predicates,
)

__all__ = [
    # Core types
    "Invariant",
    "InvariantMechanismResult",
    "Lemma",
    # Proof scripts
    "LemmaKind",
    "LemmaResult",
    "MultiStepResult",
    "MultiStepVerdict",
    "Predicate",
    "PredicateSufficiencyResult",
    "PredicateSufficiencyVerdict",
    "ProofBuilder",
    # Symbolic analysis
    "ProofMethod",
    "ProofResult",
    "ProofScript",
    "ProofStatus",
    # Protocols
    "ProofableBlock",
    "ProofableModel",
    "ReachabilityAnalysisResult",
    "SingleStepResult",
    # Reachability
    "SingleStepVerdict",
    "SymbolicAnalysisResult",
    "analyze_invariants",
    "analyze_reachability",
    "attach_proof",
    # Serialization
    "canonical_srepr",
    # Identity
    "hash_model",
    "hash_proof",
    "make_canonical_dict",
    "predicate_from_post_check",
    "restore_expr",
    "validate_block_predicates",
    "verify_lemma",
    "verify_proof",
]
