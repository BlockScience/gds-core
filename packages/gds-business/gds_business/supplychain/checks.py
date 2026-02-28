"""Supply chain network verification checks (SCN-001..SCN-004).

These operate on SupplyChainModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_business.supplychain.model import SupplyChainModel


def check_scn001_network_connectivity(model: SupplyChainModel) -> list[Finding]:
    """SCN-001: All nodes reachable via BFS from demand/supply paths."""
    findings: list[Finding] = []

    # Build undirected adjacency from shipments
    adj: dict[str, set[str]] = {n.name: set() for n in model.nodes}
    for s in model.shipments:
        if s.source_node in adj and s.target_node in adj:
            adj[s.source_node].add(s.target_node)
            adj[s.target_node].add(s.source_node)

    # Also connect demand source targets
    for d in model.demand_sources:
        if d.target_node in adj:
            adj[d.target_node].add(f"__demand_{d.name}")

    # BFS from each demand target
    reachable: set[str] = set()
    for d in model.demand_sources:
        if d.target_node not in adj:
            continue
        queue = [d.target_node]
        visited: set[str] = set()
        while queue:
            node = queue.pop(0)
            if node in visited or node not in adj:
                continue
            visited.add(node)
            reachable.add(node)
            queue.extend(adj[node] - visited)

    # If no demands, try from first node
    if not model.demand_sources and model.nodes:
        queue = [model.nodes[0].name]
        visited = set()
        while queue:
            node = queue.pop(0)
            if node in visited or node not in adj:
                continue
            visited.add(node)
            reachable.add(node)
            queue.extend(adj[node] - visited)

    for node in model.nodes:
        is_reachable = node.name in reachable
        findings.append(
            Finding(
                check_id="SCN-001",
                severity=Severity.WARNING,
                message=(
                    f"Node {node.name!r} "
                    f"{'is' if is_reachable else 'is NOT'} reachable "
                    f"in the supply network"
                ),
                source_elements=[node.name],
                passed=is_reachable,
            )
        )
    return findings


def check_scn002_shipment_node_validity(model: SupplyChainModel) -> list[Finding]:
    """SCN-002: Shipment source_node and target_node exist."""
    findings: list[Finding] = []
    for s in model.shipments:
        src_valid = s.source_node in model.node_names
        findings.append(
            Finding(
                check_id="SCN-002",
                severity=Severity.ERROR,
                message=(
                    f"Shipment {s.name!r} source_node {s.source_node!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared node"
                ),
                source_elements=[s.name, s.source_node],
                passed=src_valid,
            )
        )
        tgt_valid = s.target_node in model.node_names
        findings.append(
            Finding(
                check_id="SCN-002",
                severity=Severity.ERROR,
                message=(
                    f"Shipment {s.name!r} target_node {s.target_node!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared node"
                ),
                source_elements=[s.name, s.target_node],
                passed=tgt_valid,
            )
        )
    return findings


def check_scn003_demand_target_validity(model: SupplyChainModel) -> list[Finding]:
    """SCN-003: Demand target_node exists."""
    findings: list[Finding] = []
    for d in model.demand_sources:
        valid = d.target_node in model.node_names
        findings.append(
            Finding(
                check_id="SCN-003",
                severity=Severity.ERROR,
                message=(
                    f"DemandSource {d.name!r} target_node {d.target_node!r} "
                    f"{'is' if valid else 'is NOT'} a declared node"
                ),
                source_elements=[d.name, d.target_node],
                passed=valid,
            )
        )
    return findings


def check_scn004_no_orphan_nodes(model: SupplyChainModel) -> list[Finding]:
    """SCN-004: Every node appears in at least one shipment or demand."""
    findings: list[Finding] = []
    connected: set[str] = set()
    for s in model.shipments:
        connected.add(s.source_node)
        connected.add(s.target_node)
    for d in model.demand_sources:
        connected.add(d.target_node)

    for node in model.nodes:
        is_connected = node.name in connected
        findings.append(
            Finding(
                check_id="SCN-004",
                severity=Severity.WARNING,
                message=(
                    f"Node {node.name!r} {'is' if is_connected else 'is NOT'} connected"
                ),
                source_elements=[node.name],
                passed=is_connected,
            )
        )
    return findings


ALL_SCN_CHECKS = [
    check_scn001_network_connectivity,
    check_scn002_shipment_node_validity,
    check_scn003_demand_target_validity,
    check_scn004_no_orphan_nodes,
]
