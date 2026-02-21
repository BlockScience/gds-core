"""Verification engine — orchestrates CS checks + GDS checks.

Runs CS-001..CS-006 on the ControlModel, then optionally compiles to
SystemIR and runs GDS generic checks (G-001..G-006).
"""

from __future__ import annotations

from collections.abc import Callable

from gds.verification.findings import Finding, VerificationReport

from gds_control.dsl.model import ControlModel
from gds_control.verification.checks import ALL_CS_CHECKS


def verify(
    model: ControlModel,
    cs_checks: list[Callable[[ControlModel], list[Finding]]] | None = None,
    include_gds_checks: bool = True,
) -> VerificationReport:
    """Run verification checks on a ControlModel.

    1. CS-001..CS-006 on the model (pre-compilation)
    2. If include_gds_checks: compile to SystemIR and run G-001..G-006

    Args:
        model: The control system model to verify.
        cs_checks: Optional subset of CS checks. Defaults to all.
        include_gds_checks: Whether to compile and run GDS generic checks.
    """
    checks = cs_checks or ALL_CS_CHECKS
    findings: list[Finding] = []

    # Phase 1: CS checks on model
    for check_fn in checks:
        findings.extend(check_fn(model))

    # Phase 2: GDS generic checks on compiled SystemIR
    if include_gds_checks:
        from gds.verification.engine import ALL_CHECKS as GDS_ALL_CHECKS

        system_ir = model.compile_system()
        for gds_check in GDS_ALL_CHECKS:
            findings.extend(gds_check(system_ir))

    return VerificationReport(system_name=model.name, findings=findings)
