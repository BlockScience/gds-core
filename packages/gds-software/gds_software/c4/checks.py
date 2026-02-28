"""C4 model verification checks (C4-001..C4-004)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.c4.model import C4Model


def check_c4001_relationship_validity(model: C4Model) -> list[Finding]:
    """C4-001: Relationship source/target are declared elements."""
    findings: list[Finding] = []
    for rel in model.relationships:
        src_valid = rel.source in model.element_names
        findings.append(
            Finding(
                check_id="C4-001",
                severity=Severity.ERROR,
                message=(
                    f"Relationship {rel.name!r} source {rel.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared element"
                ),
                source_elements=[rel.name, rel.source],
                passed=src_valid,
            )
        )
        tgt_valid = rel.target in model.element_names
        findings.append(
            Finding(
                check_id="C4-001",
                severity=Severity.ERROR,
                message=(
                    f"Relationship {rel.name!r} target {rel.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared element"
                ),
                source_elements=[rel.name, rel.target],
                passed=tgt_valid,
            )
        )
    return findings


def check_c4002_container_hierarchy(model: C4Model) -> list[Finding]:
    """C4-002: Component containers reference declared containers."""
    findings: list[Finding] = []
    for comp in model.components:
        valid = comp.container in model.container_names
        findings.append(
            Finding(
                check_id="C4-002",
                severity=Severity.ERROR,
                message=(
                    f"Component {comp.name!r} container {comp.container!r} "
                    f"{'is' if valid else 'is NOT'} a declared container"
                ),
                source_elements=[comp.name, comp.container],
                passed=valid,
            )
        )
    return findings


def check_c4003_external_connectivity(model: C4Model) -> list[Finding]:
    """C4-003: External actors have at least one relationship."""
    findings: list[Finding] = []
    for p in model.persons:
        connected = any(
            r.source == p.name or r.target == p.name for r in model.relationships
        )
        findings.append(
            Finding(
                check_id="C4-003",
                severity=Severity.WARNING,
                message=(
                    f"Person {p.name!r} {'is' if connected else 'is NOT'} connected"
                ),
                source_elements=[p.name],
                passed=connected,
            )
        )
    for e in model.external_systems:
        connected = any(
            r.source == e.name or r.target == e.name for r in model.relationships
        )
        findings.append(
            Finding(
                check_id="C4-003",
                severity=Severity.WARNING,
                message=(
                    f"External system {e.name!r} "
                    f"{'is' if connected else 'is NOT'} connected"
                ),
                source_elements=[e.name],
                passed=connected,
            )
        )
    return findings


def check_c4004_level_consistency(model: C4Model) -> list[Finding]:
    """C4-004: Relationships between elements at appropriate levels."""
    findings: list[Finding] = []
    comp_names = {c.name for c in model.components}

    for rel in model.relationships:
        # Components should primarily relate to their parent container
        # or to other components, not directly to persons
        if rel.source in comp_names and rel.target in model.person_names:
            findings.append(
                Finding(
                    check_id="C4-004",
                    severity=Severity.WARNING,
                    message=(
                        f"Component {rel.source!r} directly relates to "
                        f"Person {rel.target!r} — consider routing through container"
                    ),
                    source_elements=[rel.name],
                    passed=False,
                )
            )

    if not findings:
        findings.append(
            Finding(
                check_id="C4-004",
                severity=Severity.WARNING,
                message="Level consistency is satisfied",
                source_elements=[],
                passed=True,
            )
        )
    return findings


ALL_C4_CHECKS = [
    check_c4001_relationship_validity,
    check_c4002_container_hierarchy,
    check_c4003_external_connectivity,
    check_c4004_level_consistency,
]
