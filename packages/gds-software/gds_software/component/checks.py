"""Component diagram verification checks (CP-001..CP-004).

These operate on ComponentModel (pre-compilation declarations), not IR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.component.model import ComponentModel


def check_cp001_interface_satisfaction(model: ComponentModel) -> list[Finding]:
    """CP-001: Every required interface is satisfied by a connector."""
    findings: list[Finding] = []
    # Collect all satisfied required interfaces
    satisfied: set[tuple[str, str]] = set()
    for conn in model.connectors:
        satisfied.add((conn.target, conn.target_interface))

    for comp in model.components:
        for req in comp.requires:
            is_satisfied = (comp.name, req) in satisfied
            findings.append(
                Finding(
                    check_id="CP-001",
                    severity=Severity.ERROR,
                    message=(
                        f"Component {comp.name!r} required interface {req!r} "
                        f"{'is' if is_satisfied else 'is NOT'} satisfied"
                    ),
                    source_elements=[comp.name, req],
                    passed=is_satisfied,
                )
            )
    return findings


def check_cp002_connector_validity(model: ComponentModel) -> list[Finding]:
    """CP-002: Connector source/target reference declared components and interfaces."""
    findings: list[Finding] = []
    comp_map = {c.name: c for c in model.components}

    for conn in model.connectors:
        src_valid = (
            conn.source in comp_map
            and conn.source_interface in comp_map[conn.source].provides
        )
        findings.append(
            Finding(
                check_id="CP-002",
                severity=Severity.ERROR,
                message=(
                    f"Connector {conn.name!r} source {conn.source!r}."
                    f"{conn.source_interface!r} "
                    f"{'is' if src_valid else 'is NOT'} valid"
                ),
                source_elements=[conn.name, conn.source],
                passed=src_valid,
            )
        )

        tgt_valid = (
            conn.target in comp_map
            and conn.target_interface in comp_map[conn.target].requires
        )
        findings.append(
            Finding(
                check_id="CP-002",
                severity=Severity.ERROR,
                message=(
                    f"Connector {conn.name!r} target {conn.target!r}."
                    f"{conn.target_interface!r} "
                    f"{'is' if tgt_valid else 'is NOT'} valid"
                ),
                source_elements=[conn.name, conn.target],
                passed=tgt_valid,
            )
        )
    return findings


def check_cp003_dangling_interfaces(model: ComponentModel) -> list[Finding]:
    """CP-003: Every provided interface is consumed by a connector or is external."""
    findings: list[Finding] = []
    consumed: set[tuple[str, str]] = set()
    for conn in model.connectors:
        consumed.add((conn.source, conn.source_interface))

    for comp in model.components:
        for prov in comp.provides:
            is_consumed = (comp.name, prov) in consumed
            findings.append(
                Finding(
                    check_id="CP-003",
                    severity=Severity.WARNING,
                    message=(
                        f"Component {comp.name!r} provided interface {prov!r} "
                        f"{'is' if is_consumed else 'is NOT'} consumed by a connector"
                    ),
                    source_elements=[comp.name, prov],
                    passed=is_consumed,
                )
            )
    return findings


def check_cp004_component_naming(model: ComponentModel) -> list[Finding]:
    """CP-004: No duplicate component names."""
    findings: list[Finding] = []
    seen: set[str] = set()
    for comp in model.components:
        is_unique = comp.name not in seen
        findings.append(
            Finding(
                check_id="CP-004",
                severity=Severity.ERROR,
                message=(
                    f"Component name {comp.name!r} "
                    f"{'is' if is_unique else 'is NOT'} unique"
                ),
                source_elements=[comp.name],
                passed=is_unique,
            )
        )
        seen.add(comp.name)
    return findings


ALL_CP_CHECKS = [
    check_cp001_interface_satisfaction,
    check_cp002_connector_validity,
    check_cp003_dangling_interfaces,
    check_cp004_component_naming,
]
