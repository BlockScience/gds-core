"""Mermaid visualization generators for OGS patterns.

Inspired by gds-viz, but adapted for game-theory-specific PatternIR.

Views:
1. Structural - block topology with composition operators
2. Architecture by Role - games grouped by game_type
3. Architecture by Domain - games grouped by tags
4. Game Hierarchy - nested composition tree
5. Flow Topology - covariant flow graph
6. Terminal Conditions - state transitions
"""

from __future__ import annotations

from ogs.ir.models import FlowDirection, GameType, PatternIR


def structural_to_mermaid(pattern: PatternIR) -> str:
    """View 1: Structural - compiled game graph with composition topology.

    Shows all games as nodes with their types, and all flows as edges.
    Role-based styling: decision games are rectangles, functions are stadiums.
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 60}}}%%"]
    lines.append("flowchart TD")

    # Define nodes with shapes based on game type
    for game in pattern.games:
        node_id = _sanitize_id(game.name)
        if game.game_type == GameType.DECISION:
            # Rectangle for decision games
            lines.append(f'    {node_id}["{game.name}"]')
        elif game.game_type == GameType.FUNCTION_COVARIANT:
            # Stadium for covariant functions
            lines.append(f'    {node_id}(["{game.name}"])')
        elif game.game_type == GameType.FUNCTION_CONTRAVARIANT:
            # Cylinder for contravariant functions
            lines.append(f"    {node_id}[({game.name})]")
        else:
            # Default rectangle
            lines.append(f'    {node_id}["{game.name}"]')

    # Add flows as edges
    for flow in pattern.flows:
        source_id = _sanitize_id(flow.source)
        target_id = _sanitize_id(flow.target)

        # Style edges based on flow type
        if (
            flow.is_feedback
            or flow.is_corecursive
            or flow.direction == FlowDirection.CONTRAVARIANT
        ):
            lines.append(f'    {source_id} -.->|"{flow.label}"| {target_id}')
        else:
            lines.append(f'    {source_id} -->|"{flow.label}"| {target_id}')

    return "\n".join(lines)


def architecture_by_role_to_mermaid(pattern: PatternIR) -> str:
    """View 2: Architecture by Role - games grouped by game_type.

    Groups games by their GameType (decision, function_covariant, etc.).
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 80}}}%%"]
    lines.append("flowchart TD")

    # Group games by type
    by_type: dict[GameType, list] = {}
    for game in pattern.games:
        by_type.setdefault(game.game_type, []).append(game)

    # Create subgraphs for each type
    for game_type, games in sorted(by_type.items(), key=lambda x: x[0].value):
        type_name = game_type.value.replace("_", " ").title()
        lines.append(f"    subgraph {game_type.value} [{type_name}]")
        for game in games:
            node_id = _sanitize_id(game.name)
            lines.append(f'        {node_id}["{game.name}"]')
        lines.append("    end")

    # Add flows between subgraphs
    for flow in pattern.flows:
        source_id = _sanitize_id(flow.source)
        target_id = _sanitize_id(flow.target)
        lines.append(f'    {source_id} -->|"{flow.label}"| {target_id}')

    return "\n".join(lines)


def architecture_by_domain_to_mermaid(
    pattern: PatternIR, tag_key: str = "domain"
) -> str:
    """View 3: Architecture by Domain - games grouped by tag.

    Groups games by a tag key (default: "domain"). Games without
    the tag go to "ungrouped".
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 80}}}%%"]
    lines.append("flowchart TD")

    # Group games by tag value
    by_domain: dict[str, list] = {}
    ungrouped = []

    for game in pattern.games:
        tag_value = game.tags.get(tag_key) if game.tags else None
        if tag_value:
            by_domain.setdefault(tag_value, []).append(game)
        else:
            ungrouped.append(game)

    # Create subgraphs for each domain
    # (prefix with "dom_" to avoid ID collisions with game nodes)
    for domain, games in sorted(by_domain.items()):
        safe_domain = "dom_" + _sanitize_id(domain)
        lines.append(f'    subgraph {safe_domain} ["{domain}"]')
        for game in games:
            node_id = _sanitize_id(game.name)
            lines.append(f'        {node_id}["{game.name}"]')
        lines.append("    end")

    # Ungrouped games
    if ungrouped:
        lines.append('    subgraph ungrouped ["Ungrouped"]')
        for game in ungrouped:
            node_id = _sanitize_id(game.name)
            lines.append(f'        {node_id}["{game.name}"]')
        lines.append("    end")

    # Add flows
    for flow in pattern.flows:
        source_id = _sanitize_id(flow.source)
        target_id = _sanitize_id(flow.target)
        lines.append(f'    {source_id} -->|"{flow.label}"| {target_id}')

    return "\n".join(lines)


def hierarchy_to_mermaid(pattern: PatternIR) -> str:
    """View 4: Game Hierarchy - nested composition tree.

    Shows the hierarchical composition structure
    (sequential, parallel, feedback, corecursive).
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 40, 'rankSpacing': 50}}}%%"]
    lines.append("flowchart TD")

    if not pattern.hierarchy:
        return "\n".join([*lines, "    No hierarchy information available"])

    def render_node(node, parent_id: str | None = None, depth: int = 0) -> list[str]:
        node_lines = []
        node_id = _sanitize_id(node.id)

        if node.composition_type:
            # Composite node
            type_label = (
                node.composition_type.value if node.composition_type else "group"
            )
            label = f"{node.name} ({type_label})"
            if node.exit_condition:
                label += f"<br/>exit: {node.exit_condition[:30]}..."

            node_lines.append(f'    {node_id}["{label}"]')

            if parent_id:
                node_lines.append(f"    {parent_id} --> {node_id}")

            for child in node.children:
                node_lines.extend(render_node(child, node_id, depth + 1))
        else:
            # Leaf node (atomic game)
            game_name = node.block_name or node.name
            node_lines.append(f'    {node_id}["{game_name}"]')
            if parent_id:
                node_lines.append(f"    {parent_id} --> {node_id}")

        return node_lines

    lines.extend(render_node(pattern.hierarchy))
    return "\n".join(lines)


def flow_topology_to_mermaid(pattern: PatternIR) -> str:
    """View 5: Flow Topology - covariant flow graph.

    Shows only covariant (forward) flows, useful for understanding data flow.
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 60}}}%%"]
    lines.append("flowchart LR")

    # Only covariant flows
    covariant_flows = [
        f for f in pattern.flows if f.direction == FlowDirection.COVARIANT
    ]

    # Collect all nodes that appear in covariant flows
    node_names = set()
    for flow in covariant_flows:
        node_names.add(flow.source)
        node_names.add(flow.target)

    # Define nodes
    for name in sorted(node_names):
        node_id = _sanitize_id(name)
        lines.append(f'    {node_id}["{name}"]')

    # Add covariant flows only
    for flow in covariant_flows:
        source_id = _sanitize_id(flow.source)
        target_id = _sanitize_id(flow.target)
        style = "-.->" if flow.is_corecursive else "-->"
        lines.append(f'    {source_id} {style}|"{flow.label}"| {target_id}')

    return "\n".join(lines)


def terminal_conditions_to_mermaid(pattern: PatternIR) -> str:
    """View 6: Terminal Conditions - state transitions.

    Shows terminal conditions as state transitions.
    """
    lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 60}}}%%"]
    lines.append("stateDiagram-v2")
    lines.append("    [*] --> Running")

    if not pattern.terminal_conditions:
        lines.append("    Running --> [*]")
        return "\n".join(lines)

    # Add terminal condition states
    for tc in pattern.terminal_conditions:
        tc_id = _sanitize_id(tc.name)
        lines.append(f"    Running --> {tc_id} : {tc.outcome}")
        lines.append(f"    {tc_id} : {tc.name}")
        if tc.description:
            lines.append(f"    note right of {tc_id}")
            lines.append(f"        {tc.description[:60]}")
            lines.append("    end note")

    return "\n".join(lines)


def generate_all_views(pattern: PatternIR) -> dict[str, str]:
    """Generate all 6 views and return as a dictionary."""
    return {
        "structural": structural_to_mermaid(pattern),
        "architecture_by_role": architecture_by_role_to_mermaid(pattern),
        "architecture_by_domain": architecture_by_domain_to_mermaid(pattern),
        "hierarchy": hierarchy_to_mermaid(pattern),
        "flow_topology": flow_topology_to_mermaid(pattern),
        "terminal_conditions": terminal_conditions_to_mermaid(pattern),
    }


def _sanitize_id(name: str) -> str:
    """Convert a name to a valid Mermaid ID."""
    import re

    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name)
    # Ensure it doesn't start with a number
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized
