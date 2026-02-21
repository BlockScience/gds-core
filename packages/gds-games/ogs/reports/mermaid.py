"""Mermaid diagram generators for PatternIR.

Generates two diagram types embedded in Markdown reports:

1. **Flowchart (LR)** — shows game composition with solid lines for covariant
   flows and dashed lines for contravariant (feedback) flows.
2. **Sequence Diagram** — shows temporal execution order with participants
   ordered by topological sort of covariant flows.

Both diagrams render correctly in GitHub-flavored Markdown and any Mermaid-
compatible viewer.
"""

import re

from ogs.ir.models import FlowDirection, FlowIR, PatternIR


def _topological_sort(games: list[str], flows: list[FlowIR]) -> list[str]:
    """Topological sort of games using covariant flows (Kahn's algorithm).

    Determines the execution order: games with no incoming covariant flows
    execute first, then their downstream consumers, etc. Falls back to the
    original list order for games not reached by any flow. Games involved
    in cycles (which S-004 should catch) are appended at the end.
    """
    adj: dict[str, list[str]] = {g: [] for g in games}
    in_degree: dict[str, int] = {g: 0 for g in games}

    for flow in flows:
        if flow.direction != FlowDirection.COVARIANT:
            continue
        if flow.source in adj and flow.target in adj:
            adj[flow.source].append(flow.target)
            in_degree[flow.target] += 1

    # Kahn's algorithm
    queue = [g for g in games if in_degree[g] == 0]
    result: list[str] = []
    while queue:
        # Stable sort: pick first by original order
        queue.sort(key=lambda g: games.index(g))
        node = queue.pop(0)
        result.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any remaining (cycles — shouldn't happen in valid DAGs)
    for g in games:
        if g not in result:
            result.append(g)

    return result


def _sanitize_id(name: str) -> str:
    """Convert a name to a valid Mermaid node ID (alphanumeric + underscore only)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _escape_label(text: str) -> str:
    """Escape a label for use inside Mermaid quoted strings."""
    return text.replace('"', "#quot;")


def generate_flowchart(pattern: PatternIR) -> str:
    """Generate a Mermaid flowchart LR showing game composition.

    Solid lines = covariant flows, dashed lines = contravariant flows.
    Input nodes shown as stadium-shaped (rounded) rectangles.
    """
    lines = [
        "%%{init: {'flowchart': {'nodeSpacing': 40, 'rankSpacing': 60, 'padding': 15}, 'themeVariables': {'fontSize': '16px'}}}%%",
        "flowchart LR",
    ]

    # Declare game nodes
    for game in pattern.games:
        sid = _sanitize_id(game.name)
        label = _escape_label(game.name)
        lines.append(f'    {sid}["{label}"]')

    # Declare input nodes (stadium-shaped)
    for inp in pattern.inputs:
        sid = _sanitize_id(inp.name)
        label = _escape_label(inp.name)
        lines.append(f'    {sid}(["{label}"])')

    # Draw flows
    for flow in pattern.flows:
        src = _sanitize_id(flow.source)
        tgt = _sanitize_id(flow.target)
        label = _escape_label(flow.label or flow.flow_type.value)
        if flow.direction == FlowDirection.CONTRAVARIANT:
            lines.append(f'    {src} -.->|"{label}"| {tgt}')
        else:
            lines.append(f'    {src} -->|"{label}"| {tgt}')

    return "\n".join(lines)


def generate_sequence_diagram(pattern: PatternIR) -> str:
    """Generate a Mermaid sequence diagram showing temporal flow order.

    Games are ordered by topological sort of covariant flows.
    Contravariant flows shown as dashed return arrows.
    """
    game_names = [g.name for g in pattern.games]
    sorted_names = _topological_sort(game_names, pattern.flows)

    lines = [
        "%%{init: {'sequence': {'actorFontSize': 16, 'messageFontSize': 14, 'width': 250, 'height': 55, 'actorMargin': 80, 'mirrorActors': false, 'boxMargin': 20}}}%%",
        "sequenceDiagram",
    ]

    # Declare participants in topological order
    for name in sorted_names:
        lines.append(f"    participant {_sanitize_id(name)} as {name}")

    # Add input participants
    for inp in pattern.inputs:
        lines.append(f"    participant {_sanitize_id(inp.name)} as {inp.name}")

    # Draw flows in order: covariant first, then contravariant
    covariant = [f for f in pattern.flows if f.direction == FlowDirection.COVARIANT]
    contravariant = [
        f for f in pattern.flows if f.direction == FlowDirection.CONTRAVARIANT
    ]

    for flow in covariant:
        src = _sanitize_id(flow.source)
        tgt = _sanitize_id(flow.target)
        label = flow.label or flow.flow_type.value
        lines.append(f"    {src}->>{tgt}: {label}")

    for flow in contravariant:
        src = _sanitize_id(flow.source)
        tgt = _sanitize_id(flow.target)
        label = flow.label or flow.flow_type.value
        lines.append(f"    {src}-->>{tgt}: {label}")

    return "\n".join(lines)
