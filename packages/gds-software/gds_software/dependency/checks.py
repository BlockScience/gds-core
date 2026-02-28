"""Dependency graph verification checks (DG-001..DG-004).

These operate on DependencyModel (pre-compilation declarations), not IR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.dependency.model import DependencyModel


def check_dg001_dep_validity(model: DependencyModel) -> list[Finding]:
    """DG-001: Dependency source/target are declared modules."""
    findings: list[Finding] = []
    for dep in model.deps:
        src_valid = dep.source in model.module_names
        findings.append(
            Finding(
                check_id="DG-001",
                severity=Severity.ERROR,
                message=(
                    f"Dep source {dep.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared module"
                ),
                source_elements=[dep.source],
                passed=src_valid,
            )
        )
        tgt_valid = dep.target in model.module_names
        findings.append(
            Finding(
                check_id="DG-001",
                severity=Severity.ERROR,
                message=(
                    f"Dep target {dep.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared module"
                ),
                source_elements=[dep.target],
                passed=tgt_valid,
            )
        )
    return findings


def check_dg002_acyclicity(model: DependencyModel) -> list[Finding]:
    """DG-002: No cycles in the dependency graph."""
    adj: dict[str, list[str]] = {m.name: [] for m in model.modules}
    for dep in model.deps:
        if dep.source in adj:
            adj[dep.source].append(dep.target)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {name: WHITE for name in adj}
    cycle_members: list[str] = []

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for neighbor in adj[node]:
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle_members.append(node)
                cycle_members.append(neighbor)
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    has_cycle = any(dfs(name) for name in adj if color[name] == WHITE)

    if has_cycle:
        return [
            Finding(
                check_id="DG-002",
                severity=Severity.ERROR,
                message=f"Cycle detected in dependency graph: {cycle_members}",
                source_elements=list(set(cycle_members)),
                passed=False,
            )
        ]
    return [
        Finding(
            check_id="DG-002",
            severity=Severity.ERROR,
            message="Dependency graph is acyclic",
            source_elements=list(adj.keys()),
            passed=True,
        )
    ]


def check_dg003_layer_ordering(model: DependencyModel) -> list[Finding]:
    """DG-003: Dependencies only go from higher layers to lower layers."""
    findings: list[Finding] = []
    module_layer = {m.name: m.layer for m in model.modules}

    for dep in model.deps:
        if dep.source not in module_layer or dep.target not in module_layer:
            continue
        src_layer = module_layer[dep.source]
        tgt_layer = module_layer[dep.target]
        valid = src_layer > tgt_layer or src_layer == tgt_layer
        findings.append(
            Finding(
                check_id="DG-003",
                severity=Severity.WARNING,
                message=(
                    f"Dep {dep.source!r} (layer {src_layer}) -> "
                    f"{dep.target!r} (layer {tgt_layer}): "
                    f"{'valid' if valid else 'upward dependency'}"
                ),
                source_elements=[dep.source, dep.target],
                passed=valid,
            )
        )

    if not findings:
        findings.append(
            Finding(
                check_id="DG-003",
                severity=Severity.WARNING,
                message="No dependencies to check layer ordering",
                source_elements=[],
                passed=True,
            )
        )
    return findings


def check_dg004_module_connectivity(model: DependencyModel) -> list[Finding]:
    """DG-004: Every module is connected (has at least one dependency)."""
    findings: list[Finding] = []
    connected: set[str] = set()
    for dep in model.deps:
        connected.add(dep.source)
        connected.add(dep.target)

    for mod in model.modules:
        is_connected = mod.name in connected
        findings.append(
            Finding(
                check_id="DG-004",
                severity=Severity.WARNING,
                message=(
                    f"Module {mod.name!r} "
                    f"{'is' if is_connected else 'is NOT'} connected"
                ),
                source_elements=[mod.name],
                passed=is_connected,
            )
        )
    return findings


ALL_DG_CHECKS = [
    check_dg001_dep_validity,
    check_dg002_acyclicity,
    check_dg003_layer_ordering,
    check_dg004_module_connectivity,
]
