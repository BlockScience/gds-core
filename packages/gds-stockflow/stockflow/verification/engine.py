"""Verification engine — orchestrates SF checks + GDS checks.

Runs SF-001..SF-005 on the StockFlowModel, then optionally compiles to
GDSSpec/SystemIR and runs GDS semantic + generic checks.
"""

from __future__ import annotations

from collections.abc import Callable

from gds.verification.findings import Finding, VerificationReport

from stockflow.dsl.model import StockFlowModel
from stockflow.verification.checks import ALL_SF_CHECKS


def verify(
    model: StockFlowModel,
    sf_checks: list[Callable[[StockFlowModel], list[Finding]]] | None = None,
    include_gds_checks: bool = True,
) -> VerificationReport:
    """Run verification checks on a StockFlowModel.

    1. SF-001..SF-005 on the model (pre-compilation)
    2. If include_gds_checks: compile to SystemIR and run G-001..G-006

    Args:
        model: The stock-flow model to verify.
        sf_checks: Optional subset of SF checks. Defaults to all.
        include_gds_checks: Whether to compile and run GDS generic checks.
    """
    checks = sf_checks or ALL_SF_CHECKS
    findings: list[Finding] = []

    # Phase 1: SF checks on model
    for check_fn in checks:
        findings.extend(check_fn(model))

    # Phase 2: GDS generic checks on compiled SystemIR
    if include_gds_checks:
        from gds.verification.engine import ALL_CHECKS as GDS_ALL_CHECKS

        system_ir = model.compile_system()
        for gds_check in GDS_ALL_CHECKS:
            findings.extend(gds_check(system_ir))

    return VerificationReport(system_name=model.name, findings=findings)
