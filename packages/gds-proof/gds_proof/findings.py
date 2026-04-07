"""Convert gds-proof results to gds-framework Finding/VerificationReport objects.

Integrates the proof engine output with the existing verification pipeline
so that proof results appear alongside structural (G-001..G-006) and semantic
(SC-001..SC-011) checks in a unified ``VerificationReport``.

Check ID scheme
---------------
- ``PROOF-001``: Invariant preservation (symbolic analysis)
- ``PROOF-002``: Single-step inductive safety
- ``PROOF-003``: Predicate sufficiency
- ``PROOF-004``: Multi-step inductive safety
- ``PROOF-005``: Auxiliary proof verification

``exportable_predicate`` is populated with the invariant's ``canonical_srepr``
form, making the formal predicate available to downstream consumers (the
OWL/RDF exporter in gds-interchange already reads this field).
"""

from __future__ import annotations

from gds.verification.findings import Finding, Severity, VerificationReport

from gds_proof.analysis.symbolic import (  # noqa: TC001
    InvariantMechanismResult,
    SymbolicAnalysisResult,
)
from gds_proof.serialization.canonical import canonical_srepr


def invariant_result_to_finding(
    result: InvariantMechanismResult,
    invariant_expr: object | None = None,
) -> Finding:
    """Convert a single symbolic analysis result to a ``Finding``.

    Parameters
    ----------
    result:
        One (invariant, block) pair result from ``analyze_invariants()``.
    invariant_expr:
        Optional SymPy expression for the invariant.  If provided, its
        ``canonical_srepr`` is stored in ``exportable_predicate``.

    Returns
    -------
    Finding
        With ``check_id="PROOF-001"`` and appropriate severity/pass status.
    """
    if result.status == "PROVED":
        return Finding(
            check_id="PROOF-001",
            severity=Severity.INFO,
            message=(
                f"Invariant '{result.invariant_name}' preserved by "
                f"block '{result.mechanism_name}' "
                f"(method: {result.proof_method.value})"
            ),
            source_elements=[result.invariant_name, result.mechanism_name],
            passed=True,
            exportable_predicate=(
                canonical_srepr(invariant_expr) if invariant_expr is not None else ""
            ),
        )
    elif result.status == "DISPROVED":
        return Finding(
            check_id="PROOF-001",
            severity=Severity.ERROR,
            message=(
                f"Invariant '{result.invariant_name}' VIOLATED by "
                f"block '{result.mechanism_name}' "
                f"(method: {result.proof_method.value})"
            ),
            source_elements=[result.invariant_name, result.mechanism_name],
            passed=False,
            exportable_predicate=(
                canonical_srepr(invariant_expr) if invariant_expr is not None else ""
            ),
        )
    else:
        return Finding(
            check_id="PROOF-001",
            severity=Severity.WARNING,
            message=(
                f"Invariant '{result.invariant_name}' INCONCLUSIVE for "
                f"block '{result.mechanism_name}' "
                f"(method: {result.proof_method.value})"
            ),
            source_elements=[result.invariant_name, result.mechanism_name],
            passed=False,
            exportable_predicate=(
                canonical_srepr(invariant_expr) if invariant_expr is not None else ""
            ),
        )


def symbolic_analysis_to_findings(
    analysis: SymbolicAnalysisResult,
    invariant_exprs: dict[str, object] | None = None,
) -> list[Finding]:
    """Convert all symbolic analysis results to a list of ``Finding`` objects.

    Parameters
    ----------
    analysis:
        Complete symbolic analysis result from ``analyze_invariants()``.
    invariant_exprs:
        Optional mapping of invariant names to their SymPy expressions.

    Returns
    -------
    list[Finding]
        One finding per (invariant, block) pair.
    """
    exprs = invariant_exprs or {}
    return [
        invariant_result_to_finding(r, exprs.get(r.invariant_name))
        for r in analysis.results
    ]


def proof_findings_to_report(
    system_name: str,
    findings: list[Finding],
) -> VerificationReport:
    """Wrap proof findings in a ``VerificationReport``.

    Parameters
    ----------
    system_name:
        Name for the report (typically the spec or model name).
    findings:
        List of findings from ``symbolic_analysis_to_findings()`` or
        manually constructed.

    Returns
    -------
    VerificationReport
        Ready for display, export, or merging with structural/semantic reports.
    """
    return VerificationReport(
        system_name=system_name,
        findings=findings,
    )
