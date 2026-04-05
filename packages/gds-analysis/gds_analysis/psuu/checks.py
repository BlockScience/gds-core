"""PSUU verification checks following the GDS Finding pattern.

Requires ``gds-framework`` to be installed.  All gds-framework imports
are deferred to function bodies so that importing this module never
fails when gds-framework is absent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gds.parameters import ParameterSchema
    from gds.verification.findings import Finding

    from gds_analysis.psuu.space import ParameterSpace


def check_parameter_space_compatibility(
    space: ParameterSpace, schema: ParameterSchema
) -> list[Finding]:
    """PSUU-001: Swept parameter space is compatible with declared theta.

    Verifies that all swept parameters exist in the schema and that
    sweep bounds respect declared TypeDef constraints and ParameterDef
    bounds.

    Returns a list of :class:`~gds.verification.findings.Finding`.
    """
    from gds.verification.findings import Finding, Severity

    violations = space.validate_against_schema(schema)
    findings: list[Finding] = []

    for v in violations:
        severity = (
            Severity.WARNING
            if v.violation_type == "missing_from_schema"
            else Severity.ERROR
        )
        findings.append(
            Finding(
                check_id="PSUU-001",
                severity=severity,
                message=v.message,
                source_elements=[v.param],
                passed=False,
            )
        )

    if not findings:
        findings.append(
            Finding(
                check_id="PSUU-001",
                severity=Severity.INFO,
                message="Parameter space is compatible with declared schema.",
                source_elements=list(space.params.keys()),
                passed=True,
            )
        )

    return findings
