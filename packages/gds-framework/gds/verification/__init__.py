"""Verification engine, generic checks, and semantic spec checks."""

from gds.verification.engine import verify
from gds.verification.findings import Finding, Severity, VerificationReport
from gds.verification.spec_checks import (
    check_canonical_wellformedness,
    check_completeness,
    check_determinism,
    check_parameter_references,
    check_reachability,
    check_type_safety,
)

__all__ = [
    "Finding",
    "Severity",
    "VerificationReport",
    "check_canonical_wellformedness",
    "check_completeness",
    "check_determinism",
    "check_parameter_references",
    "check_reachability",
    "check_type_safety",
    "verify",
]
