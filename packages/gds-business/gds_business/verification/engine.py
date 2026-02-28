"""Verification engine — orchestrates domain checks + GDS checks.

Dispatches by model type to the appropriate domain checks, then optionally
compiles to SystemIR and runs GDS generic checks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gds.verification.findings import Finding, VerificationReport


def verify(
    model: Any,
    domain_checks: list[Callable[..., list[Finding]]] | None = None,
    include_gds_checks: bool = True,
) -> VerificationReport:
    """Run verification checks on any business dynamics model.

    Dispatches to the appropriate domain checks based on model type,
    then optionally compiles to SystemIR and runs GDS generic checks.
    """
    from gds_business.cld.checks import ALL_CLD_CHECKS
    from gds_business.cld.model import CausalLoopModel
    from gds_business.supplychain.checks import ALL_SCN_CHECKS
    from gds_business.supplychain.model import SupplyChainModel
    from gds_business.vsm.checks import ALL_VSM_CHECKS
    from gds_business.vsm.model import ValueStreamModel

    # Dispatch to appropriate checks
    if domain_checks is not None:
        checks = domain_checks
    elif isinstance(model, CausalLoopModel):
        checks = ALL_CLD_CHECKS
    elif isinstance(model, SupplyChainModel):
        checks = ALL_SCN_CHECKS
    elif isinstance(model, ValueStreamModel):
        checks = ALL_VSM_CHECKS
    else:
        raise TypeError(f"Unknown model type: {type(model).__name__}")

    findings: list[Finding] = []

    # Phase 1: Domain checks on model
    for check_fn in checks:
        findings.extend(check_fn(model))

    # Phase 2: GDS generic checks on compiled SystemIR
    if include_gds_checks:
        from gds.verification.engine import ALL_CHECKS as GDS_ALL_CHECKS

        system_ir = model.compile_system()
        for gds_check in GDS_ALL_CHECKS:
            findings.extend(gds_check(system_ir))

    return VerificationReport(system_name=model.name, findings=findings)
