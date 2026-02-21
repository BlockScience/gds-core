"""Stock-flow verification checks (SF-001..SF-005).

These operate on StockFlowModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from stockflow.dsl.model import StockFlowModel


def check_sf001_orphan_stocks(model: StockFlowModel) -> list[Finding]:
    """SF-001: Every stock has at least one flow with it as source or target."""
    findings: list[Finding] = []
    for stock in model.stocks:
        connected = any(
            f.source == stock.name or f.target == stock.name for f in model.flows
        )
        findings.append(
            Finding(
                check_id="SF-001",
                severity=Severity.WARNING,
                message=(
                    f"Stock {stock.name!r} has no connected flows"
                    if not connected
                    else f"Stock {stock.name!r} has connected flows"
                ),
                source_elements=[stock.name],
                passed=connected,
            )
        )
    return findings


def check_sf002_flow_stock_validity(model: StockFlowModel) -> list[Finding]:
    """SF-002: Flow source/target are declared stocks.

    This is also enforced at model construction time, but the check
    provides a formal Finding for verification reports.
    """
    findings: list[Finding] = []
    stock_names = model.stock_names
    for flow in model.flows:
        if flow.source:
            valid = flow.source in stock_names
            findings.append(
                Finding(
                    check_id="SF-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Flow {flow.name!r} source {flow.source!r} "
                        f"{'is' if valid else 'is NOT'} a declared stock"
                    ),
                    source_elements=[flow.name, flow.source],
                    passed=valid,
                )
            )
        if flow.target:
            valid = flow.target in stock_names
            findings.append(
                Finding(
                    check_id="SF-002",
                    severity=Severity.ERROR,
                    message=(
                        f"Flow {flow.name!r} target {flow.target!r} "
                        f"{'is' if valid else 'is NOT'} a declared stock"
                    ),
                    source_elements=[flow.name, flow.target],
                    passed=valid,
                )
            )
    return findings


def check_sf003_auxiliary_acyclicity(model: StockFlowModel) -> list[Finding]:
    """SF-003: No cycles in auxiliary dependency graph.

    Builds a directed graph of auxiliary → auxiliary dependencies and
    checks for cycles via DFS.
    """
    # Build adjacency list: aux name → list of aux names it depends on
    aux_names = {a.name for a in model.auxiliaries}
    adj: dict[str, list[str]] = {a.name: [] for a in model.auxiliaries}
    for aux in model.auxiliaries:
        for inp in aux.inputs:
            if inp in aux_names:
                adj[aux.name].append(inp)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {name: WHITE for name in aux_names}
    cycle_members: list[str] = []

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for neighbor in adj[node]:
            if color[neighbor] == GRAY:
                cycle_members.append(node)
                cycle_members.append(neighbor)
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    has_cycle = any(dfs(name) for name in aux_names if color[name] == WHITE)

    if has_cycle:
        return [
            Finding(
                check_id="SF-003",
                severity=Severity.ERROR,
                message=f"Cycle detected in auxiliary dependency graph: {cycle_members}",
                source_elements=list(set(cycle_members)),
                passed=False,
            )
        ]
    return [
        Finding(
            check_id="SF-003",
            severity=Severity.ERROR,
            message="Auxiliary dependency graph is acyclic",
            source_elements=list(aux_names),
            passed=True,
        )
    ]


def check_sf004_converter_connectivity(model: StockFlowModel) -> list[Finding]:
    """SF-004: Every converter is referenced by at least one auxiliary."""
    findings: list[Finding] = []
    # Collect all input references from auxiliaries
    referenced: set[str] = set()
    for aux in model.auxiliaries:
        referenced.update(aux.inputs)

    for conv in model.converters:
        connected = conv.name in referenced
        findings.append(
            Finding(
                check_id="SF-004",
                severity=Severity.WARNING,
                message=(
                    f"Converter {conv.name!r} "
                    f"{'is' if connected else 'is NOT'} referenced by any auxiliary"
                ),
                source_elements=[conv.name],
                passed=connected,
            )
        )
    return findings


def check_sf005_flow_completeness(model: StockFlowModel) -> list[Finding]:
    """SF-005: Every flow has at least one of source or target.

    This is enforced at model construction, but provides a formal Finding.
    """
    findings: list[Finding] = []
    for flow in model.flows:
        has_endpoint = bool(flow.source or flow.target)
        findings.append(
            Finding(
                check_id="SF-005",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.name!r} "
                    f"{'has' if has_endpoint else 'has neither'} source or target"
                ),
                source_elements=[flow.name],
                passed=has_endpoint,
            )
        )
    return findings


ALL_SF_CHECKS = [
    check_sf001_orphan_stocks,
    check_sf002_flow_stock_validity,
    check_sf003_auxiliary_acyclicity,
    check_sf004_converter_connectivity,
    check_sf005_flow_completeness,
]
