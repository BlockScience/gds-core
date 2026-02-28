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
    """Run verification checks on any software architecture model.

    Dispatches to the appropriate domain checks based on model type,
    then optionally compiles to SystemIR and runs GDS generic checks.
    """
    from gds_software.c4.checks import ALL_C4_CHECKS
    from gds_software.c4.model import C4Model
    from gds_software.component.checks import ALL_CP_CHECKS
    from gds_software.component.model import ComponentModel
    from gds_software.dependency.checks import ALL_DG_CHECKS
    from gds_software.dependency.model import DependencyModel
    from gds_software.dfd.checks import ALL_DFD_CHECKS
    from gds_software.dfd.model import DFDModel
    from gds_software.erd.checks import ALL_ER_CHECKS
    from gds_software.erd.model import ERDModel
    from gds_software.statemachine.checks import ALL_SM_CHECKS
    from gds_software.statemachine.model import StateMachineModel

    # Dispatch to appropriate checks
    if domain_checks is not None:
        checks = domain_checks
    elif isinstance(model, DFDModel):
        checks = ALL_DFD_CHECKS
    elif isinstance(model, StateMachineModel):
        checks = ALL_SM_CHECKS
    elif isinstance(model, ComponentModel):
        checks = ALL_CP_CHECKS
    elif isinstance(model, C4Model):
        checks = ALL_C4_CHECKS
    elif isinstance(model, ERDModel):
        checks = ALL_ER_CHECKS
    elif isinstance(model, DependencyModel):
        checks = ALL_DG_CHECKS
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
