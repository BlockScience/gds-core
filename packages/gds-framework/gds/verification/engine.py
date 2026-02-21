"""Verification engine — orchestrates checks against a SystemIR."""

from collections.abc import Callable

from gds.ir.models import SystemIR
from gds.verification.findings import Finding, VerificationReport
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g002_signature_completeness,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)

ALL_CHECKS: list[Callable[[SystemIR], list[Finding]]] = [
    check_g001_domain_codomain_matching,
    check_g002_signature_completeness,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
]


def verify(
    system: SystemIR,
    checks: list[Callable[[SystemIR], list[Finding]]] | None = None,
) -> VerificationReport:
    """Run verification checks against a SystemIR.

    Args:
        system: The system to verify.
        checks: Optional subset of checks. Defaults to all generic checks.
    """
    checks = checks or ALL_CHECKS
    findings: list[Finding] = []
    for check_fn in checks:
        findings.extend(check_fn(system))
    return VerificationReport(system_name=system.name, findings=findings)
