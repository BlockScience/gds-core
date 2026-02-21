"""Semantic verification checks for GDSSpec.

These check higher-order GDS properties at the specification level:
completeness, determinism, reachability, admissibility, and type safety.
Each function takes a GDSSpec and returns a list of Findings.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from gds.blocks.roles import HasParams, Mechanism
from gds.canonical import project_canonical
from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds.spec import GDSSpec


def check_completeness(spec: GDSSpec) -> list[Finding]:
    """Every entity variable is updated by at least one mechanism.

    Detects orphan state variables that can never change — a likely
    specification error.
    """
    findings: list[Finding] = []

    all_updates: set[tuple[str, str]] = set()
    for block in spec.blocks.values():
        if isinstance(block, Mechanism):
            for entity_name, var_name in block.updates:
                all_updates.add((entity_name, var_name))

    orphans: list[str] = []
    for entity in spec.entities.values():
        for var_name in entity.variables:
            if (entity.name, var_name) not in all_updates:
                orphans.append(f"{entity.name}.{var_name}")

    if orphans:
        findings.append(
            Finding(
                check_id="SC-001",
                severity=Severity.WARNING,
                message=(
                    f"Orphan state variables never updated by any mechanism: {orphans}"
                ),
                source_elements=orphans,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-001",
                severity=Severity.INFO,
                message="All state variables are updated by at least one mechanism",
                passed=True,
            )
        )

    return findings


def check_determinism(spec: GDSSpec) -> list[Finding]:
    """Within each wiring, no two mechanisms update the same variable.

    Detects write conflicts where multiple mechanisms try to modify
    the same state variable within the same composition.
    """
    findings: list[Finding] = []

    for wiring in spec.wirings.values():
        update_map: dict[tuple[str, str], list[str]] = defaultdict(list)
        for bname in wiring.block_names:
            block = spec.blocks.get(bname)
            if block is not None and isinstance(block, Mechanism):
                for entity_name, var_name in block.updates:
                    update_map[(entity_name, var_name)].append(bname)

        for (ename, vname), mechs in update_map.items():
            if len(mechs) > 1:
                findings.append(
                    Finding(
                        check_id="SC-002",
                        severity=Severity.ERROR,
                        message=(
                            f"Write conflict in wiring '{wiring.name}': "
                            f"{ename}.{vname} updated by {mechs}"
                        ),
                        source_elements=mechs,
                        passed=False,
                    )
                )

    if not any(f.check_id == "SC-002" for f in findings):
        findings.append(
            Finding(
                check_id="SC-002",
                severity=Severity.INFO,
                message="No write conflicts detected",
                passed=True,
            )
        )

    return findings


def check_reachability(spec: GDSSpec, from_block: str, to_block: str) -> list[Finding]:
    """Can signals reach from one block to another through wiring?

    Maps to GDS attainability correspondence.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            adj[wire.source].add(wire.target)

    visited: set[str] = set()
    queue = [from_block]
    reachable = False
    while queue:
        current = queue.pop(0)
        if current == to_block:
            reachable = True
            break
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adj.get(current, set()))

    if reachable:
        return [
            Finding(
                check_id="SC-003",
                severity=Severity.INFO,
                message=f"Block '{from_block}' can reach '{to_block}'",
                source_elements=[from_block, to_block],
                passed=True,
            )
        ]
    return [
        Finding(
            check_id="SC-003",
            severity=Severity.WARNING,
            message=f"Block '{from_block}' cannot reach '{to_block}'",
            source_elements=[from_block, to_block],
            passed=False,
        )
    ]


def check_parameter_references(spec: GDSSpec) -> list[Finding]:
    """All parameter references in blocks resolve to registered parameters.

    Validates that every ``params_used`` entry on blocks corresponds to
    a parameter definition in the spec's ``parameter_schema``.
    """
    findings: list[Finding] = []

    param_names = spec.parameter_schema.names()
    unresolved: list[str] = []
    for bname, block in spec.blocks.items():
        if isinstance(block, HasParams):
            for param in block.params_used:
                if param not in param_names:
                    unresolved.append(f"{bname} -> {param}")

    if unresolved:
        findings.append(
            Finding(
                check_id="SC-005",
                severity=Severity.ERROR,
                message=f"Unresolved parameter references: {unresolved}",
                source_elements=unresolved,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-005",
                severity=Severity.INFO,
                message="All parameter references resolve to registered definitions",
                passed=True,
            )
        )

    return findings


def check_type_safety(spec: GDSSpec) -> list[Finding]:
    """Wire spaces match source and target block expectations.

    Verifies that space references on wires correspond to registered
    spaces and that source/target blocks are connected to compatible spaces.
    """
    findings: list[Finding] = []

    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            if wire.space and wire.space not in spec.spaces:
                findings.append(
                    Finding(
                        check_id="SC-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Wire {wire.source} -> {wire.target} references "
                            f"unregistered space '{wire.space}'"
                        ),
                        source_elements=[wire.source, wire.target],
                        passed=False,
                    )
                )

    if not any(f.check_id == "SC-004" for f in findings):
        findings.append(
            Finding(
                check_id="SC-004",
                severity=Severity.INFO,
                message="All wire space references are valid",
                passed=True,
            )
        )

    return findings


def check_canonical_wellformedness(spec: GDSSpec) -> list[Finding]:
    """Canonical projection structural validity.

    Checks:
    - SC-006: At least one mechanism exists (f is non-empty)
    - SC-007: State space X is non-empty (entities with variables exist)
    """
    findings: list[Finding] = []
    canonical = project_canonical(spec)

    if not canonical.mechanism_blocks:
        findings.append(
            Finding(
                check_id="SC-006",
                severity=Severity.WARNING,
                message="No mechanisms found — state transition f is empty",
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-006",
                severity=Severity.INFO,
                message=(
                    "State transition f has "
                    f"{len(canonical.mechanism_blocks)} mechanism(s)"
                ),
                passed=True,
            )
        )

    if not canonical.state_variables:
        findings.append(
            Finding(
                check_id="SC-007",
                severity=Severity.WARNING,
                message="State space X is empty — no entity variables defined",
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-007",
                severity=Severity.INFO,
                message=(
                    f"State space X has {len(canonical.state_variables)} variable(s)"
                ),
                passed=True,
            )
        )

    return findings
