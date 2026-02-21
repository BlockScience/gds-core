"""Verification engine — orchestrates OGS domain checks and GDS generic checks.

OGS owns 8 domain-specific checks (T-003..T-005, S-002, S-003, S-005..S-007)
that use game-theory semantics not expressible in GDS. For generic structural
verification (type matching, completeness, dangling wires, acyclicity, etc.),
the engine delegates to GDS via ``PatternIR.to_system_ir()`` — running GDS
checks G-001 through G-006 on the projected SystemIR.

This replaces 5 former OGS checks that were near-duplicates of GDS checks:

- T-001 (domain/codomain matching) → G-001
- T-002 (signature completeness) → G-002
- T-006 (dangling flows) → G-004
- S-001 (sequential type compatibility) → G-005
- S-004 (covariant acyclicity) → G-006

The individual check functions remain importable from ``type_checks`` and
``structural_checks`` for direct use, but are no longer run by ``verify()``.
"""

from collections.abc import Callable

from gds.verification.engine import ALL_CHECKS as GDS_ALL_CHECKS

from ogs.ir.models import PatternIR
from ogs.verification.findings import Finding, VerificationReport
from ogs.verification.structural_checks import (
    check_s002_parallel_independence,
    check_s003_feedback_type_compatibility,
    check_s005_decision_space_validation,
    check_s006_corecursive_wiring,
    check_s007_initialization_completeness,
)
from ogs.verification.type_checks import (
    check_t003_flow_type_consistency,
    check_t004_input_type_resolution,
    check_t005_unused_inputs,
)

#: OGS domain-specific checks — game-theory semantics not covered by GDS.
OGS_CHECKS: list[Callable[[PatternIR], list[Finding]]] = [
    check_t003_flow_type_consistency,
    check_t004_input_type_resolution,
    check_t005_unused_inputs,
    check_s002_parallel_independence,
    check_s003_feedback_type_compatibility,
    check_s005_decision_space_validation,
    check_s006_corecursive_wiring,
    check_s007_initialization_completeness,
]

#: Default check list — backwards-compatible alias for ``OGS_CHECKS``.
#: GDS generic checks are always run via projection (not in this list).
ALL_CHECKS: list[Callable[[PatternIR], list[Finding]]] = OGS_CHECKS


def verify(
    pattern: PatternIR,
    checks: list[Callable[[PatternIR], list[Finding]]] | None = None,
    include_gds_checks: bool = True,
) -> VerificationReport:
    """Run verification checks against a PatternIR.

    Args:
        pattern: The pattern to verify.
        checks: Optional subset of OGS domain checks to run. Defaults to
            ``ALL_CHECKS`` (8 OGS-specific checks).
        include_gds_checks: Run GDS generic checks (G-001..G-006) via
            ``to_system_ir()`` projection. Defaults to True.

    Returns:
        A VerificationReport with all findings.
    """
    checks = checks or ALL_CHECKS
    findings: list[Finding] = []
    for check_fn in checks:
        findings.extend(check_fn(pattern))

    if include_gds_checks:
        system_ir = pattern.to_system_ir()
        for check_fn_gds in GDS_ALL_CHECKS:
            findings.extend(check_fn_gds(system_ir))

    return VerificationReport(pattern_name=pattern.name, findings=findings)
