"""ERD verification checks (ER-001..ER-004)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.erd.model import ERDModel


def check_er001_relationship_validity(model: ERDModel) -> list[Finding]:
    """ER-001: Relationship source/target are declared entities."""
    findings: list[Finding] = []
    for rel in model.relationships:
        src_valid = rel.source in model.entity_names
        findings.append(
            Finding(
                check_id="ER-001",
                severity=Severity.ERROR,
                message=(
                    f"Relationship {rel.name!r} source {rel.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared entity"
                ),
                source_elements=[rel.name, rel.source],
                passed=src_valid,
            )
        )
        tgt_valid = rel.target in model.entity_names
        findings.append(
            Finding(
                check_id="ER-001",
                severity=Severity.ERROR,
                message=(
                    f"Relationship {rel.name!r} target {rel.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared entity"
                ),
                source_elements=[rel.name, rel.target],
                passed=tgt_valid,
            )
        )
    return findings


def check_er002_pk_existence(model: ERDModel) -> list[Finding]:
    """ER-002: Every entity has at least one primary key attribute."""
    findings: list[Finding] = []
    for entity in model.entities:
        has_pk = any(a.is_primary_key for a in entity.attributes)
        findings.append(
            Finding(
                check_id="ER-002",
                severity=Severity.WARNING,
                message=(
                    f"Entity {entity.name!r} "
                    f"{'has' if has_pk else 'has NO'} primary key"
                ),
                source_elements=[entity.name],
                passed=has_pk,
            )
        )
    return findings


def check_er003_attribute_uniqueness(model: ERDModel) -> list[Finding]:
    """ER-003: No duplicate attribute names within an entity."""
    findings: list[Finding] = []
    for entity in model.entities:
        seen: set[str] = set()
        for attr in entity.attributes:
            is_unique = attr.name not in seen
            if not is_unique:
                findings.append(
                    Finding(
                        check_id="ER-003",
                        severity=Severity.ERROR,
                        message=(
                            f"Entity {entity.name!r} has duplicate "
                            f"attribute {attr.name!r}"
                        ),
                        source_elements=[entity.name, attr.name],
                        passed=False,
                    )
                )
            seen.add(attr.name)

    if not findings:
        findings.append(
            Finding(
                check_id="ER-003",
                severity=Severity.ERROR,
                message="All entity attributes are unique",
                source_elements=[],
                passed=True,
            )
        )
    return findings


def check_er004_relationship_naming(model: ERDModel) -> list[Finding]:
    """ER-004: No duplicate relationship names."""
    findings: list[Finding] = []
    seen: set[str] = set()
    for rel in model.relationships:
        is_unique = rel.name not in seen
        findings.append(
            Finding(
                check_id="ER-004",
                severity=Severity.ERROR,
                message=(
                    f"Relationship name {rel.name!r} "
                    f"{'is' if is_unique else 'is NOT'} unique"
                ),
                source_elements=[rel.name],
                passed=is_unique,
            )
        )
        seen.add(rel.name)
    return findings


ALL_ER_CHECKS = [
    check_er001_relationship_validity,
    check_er002_pk_existence,
    check_er003_attribute_uniqueness,
    check_er004_relationship_naming,
]
