"""gds-proof — deterministic model identity and SymPy invariant proof verification.

Part of the GDS ecosystem. Depends on ``gds-framework`` for structural types
(``AtomicBlock``, ``GDSSpec``, ``Mechanism``, ``Finding``, etc.) and provides
symbolic invariant analysis, inductive safety, and auxiliary proof scripts.

Core workflow::

    from gds_proof import (
        GDSSymbolicBlock, GDSSymbolicModel,
        Invariant, analyze_invariants, analyze_inductive_safety,
        hash_model, ProofBuilder, LemmaKind, verify_proof, attach_proof,
    )

    # 1. Enrich GDS blocks with symbolic expressions
    block = GDSSymbolicBlock(block=mechanism, spec=spec,
                             state_transition={...}, ...)
    model = GDSSymbolicModel(spec=spec, enrichments={...}, invariants_dict={...})

    # 2. Analyze
    symbolic = analyze_invariants(model)
    safety   = analyze_inductive_safety(model)

    # 3. Auxiliary proofs for INCONCLUSIVE results
    model_hash = hash_model(model)
    script = (ProofBuilder(model_hash, "inv_name", "proof_name", "claim")
              .lemma("step1", LemmaKind.EQUALITY, expr=..., expected=...)
              .build())
    result = verify_proof(script, model_hash)
    inv    = attach_proof(inv, script, model_hash)

    # 4. Convert to gds-framework VerificationReport
    from gds_proof.findings import (
        symbolic_analysis_to_findings, proof_findings_to_report,
    )
    findings = symbolic_analysis_to_findings(symbolic)
    report = proof_findings_to_report("my_spec", findings)
"""

__version__ = "0.2.0"

from gds_proof.adapter import (
    GDSSymbolicBlock,
    GDSSymbolicModel,
    derive_assumption_context,
    derive_state_symbols,
)
from gds_proof.analysis.inductive_safety import (
    InductiveSafetyResult,
    MultiStepResult,
    MultiStepVerdict,
    PredicateSufficiencyResult,
    PredicateSufficiencyVerdict,
    ReachabilityAnalysisResult,
    SingleStepResult,
    SingleStepVerdict,
    analyze_inductive_safety,
    analyze_reachability,
)
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
from gds_proof.analysis.symbolic import (
    InvariantMechanismResult,
    ProofMethod,
    SymbolicAnalysisResult,
    analyze_invariants,
)
from gds_proof.identity.hashing import hash_model, hash_proof
from gds_proof.invariant import Invariant
from gds_proof.predicate import Predicate, predicate_from_post_check
from gds_proof.protocols import SymbolicBlock, SymbolicModel
from gds_proof.serialization.canonical import (
    canonical_srepr,
    make_canonical_dict,
    restore_expr,
    validate_block_predicates,
)

__all__ = [
    "GDSSymbolicBlock",
    "GDSSymbolicModel",
    "InductiveSafetyResult",
    "Invariant",
    "InvariantMechanismResult",
    "Lemma",
    "LemmaKind",
    "LemmaResult",
    "MultiStepResult",
    "MultiStepVerdict",
    "Predicate",
    "PredicateSufficiencyResult",
    "PredicateSufficiencyVerdict",
    "ProofBuilder",
    "ProofMethod",
    "ProofResult",
    "ProofScript",
    "ProofStatus",
    "ReachabilityAnalysisResult",
    "SingleStepResult",
    "SingleStepVerdict",
    "SymbolicAnalysisResult",
    "SymbolicBlock",
    "SymbolicModel",
    "analyze_inductive_safety",
    "analyze_invariants",
    "analyze_reachability",
    "attach_proof",
    "canonical_srepr",
    "derive_assumption_context",
    "derive_state_symbols",
    "hash_model",
    "hash_proof",
    "make_canonical_dict",
    "predicate_from_post_check",
    "restore_expr",
    "validate_block_predicates",
    "verify_lemma",
    "verify_proof",
]
