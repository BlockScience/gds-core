"""CLD verification checks (CLD-001..CLD-003).

These operate on CausalLoopModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_business.cld.model import CausalLoopModel


def check_cld001_loop_polarity(model: CausalLoopModel) -> list[Finding]:
    """CLD-001: Loop polarity classification.

    Find all cycles in the CLD and classify them:
    - Even number of negative links = Reinforcing (R)
    - Odd number of negative links = Balancing (B)
    """
    findings: list[Finding] = []

    # Build adjacency list with polarity
    adj: dict[str, list[tuple[str, str]]] = {v.name: [] for v in model.variables}
    for link in model.links:
        if link.source in adj:
            adj[link.source].append((link.target, link.polarity))

    # Find all simple cycles using DFS
    cycles: list[list[tuple[str, str]]] = []
    visited: set[str] = set()

    def dfs(
        node: str,
        start: str,
        path: list[tuple[str, str]],
        in_path: set[str],
    ) -> None:
        for neighbor, polarity in adj[node]:
            if neighbor == start and len(path) > 1:
                cycles.append(path + [(neighbor, polarity)])
            elif neighbor not in in_path and neighbor not in visited:
                dfs(
                    neighbor, start, path + [(neighbor, polarity)], in_path | {neighbor}
                )

    for var in model.variables:
        dfs(var.name, var.name, [(var.name, "")], {var.name})
        visited.add(var.name)

    if not cycles:
        findings.append(
            Finding(
                check_id="CLD-001",
                severity=Severity.INFO,
                message="No feedback loops detected in the CLD",
                source_elements=[],
                passed=True,
            )
        )
    else:
        for cycle in cycles:
            nodes = [n for n, _ in cycle[:-1]]
            # Count negative links in the cycle (skip first tuple which has empty polarity)
            neg_count = sum(1 for _, p in cycle[1:] if p == "-")
            loop_type = "Balancing (B)" if neg_count % 2 == 1 else "Reinforcing (R)"
            findings.append(
                Finding(
                    check_id="CLD-001",
                    severity=Severity.INFO,
                    message=(
                        f"Loop {' -> '.join(nodes)} -> {nodes[0]}: "
                        f"{loop_type} ({neg_count} negative link(s))"
                    ),
                    source_elements=nodes,
                    passed=True,
                )
            )

    return findings


def check_cld002_variable_reachability(model: CausalLoopModel) -> list[Finding]:
    """CLD-002: Every variable appears in at least one link."""
    findings: list[Finding] = []
    linked_vars: set[str] = set()
    for link in model.links:
        linked_vars.add(link.source)
        linked_vars.add(link.target)

    for var in model.variables:
        reachable = var.name in linked_vars
        findings.append(
            Finding(
                check_id="CLD-002",
                severity=Severity.WARNING,
                message=(
                    f"Variable {var.name!r} "
                    f"{'appears' if reachable else 'does NOT appear'} in any link"
                ),
                source_elements=[var.name],
                passed=reachable,
            )
        )
    return findings


def check_cld003_no_self_loops(model: CausalLoopModel) -> list[Finding]:
    """CLD-003: No self-loops (source != target on all links)."""
    findings: list[Finding] = []
    for link in model.links:
        is_self_loop = link.source == link.target
        findings.append(
            Finding(
                check_id="CLD-003",
                severity=Severity.ERROR,
                message=(
                    f"Self-loop detected: {link.source!r} -> {link.target!r}"
                    if is_self_loop
                    else f"Link {link.source!r} -> {link.target!r} is not a self-loop"
                ),
                source_elements=[link.source, link.target],
                passed=not is_self_loop,
            )
        )
    return findings


ALL_CLD_CHECKS = [
    check_cld001_loop_polarity,
    check_cld002_variable_reachability,
    check_cld003_no_self_loops,
]
