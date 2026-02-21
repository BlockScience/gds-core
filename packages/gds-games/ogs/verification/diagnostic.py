"""Generate Mermaid diagnostic diagrams from IR + verification findings."""

import re

from ogs.ir.models import PatternIR
from ogs.verification.findings import Severity, VerificationReport


def _sanitize_id(name: str) -> str:
    """Turn an arbitrary string into a safe Mermaid node ID."""
    return re.sub(r"[^a-zA-Z0-9]", "_", name)


def _is_hex_id(name: str) -> bool:
    """Check whether a name looks like a raw Obsidian hex node ID."""
    return bool(re.fullmatch(r"[0-9a-f]{12,}", name))


def _short_hex(hex_id: str) -> str:
    return hex_id[:8] + "..."


def generate_diagnostic_mermaid(
    pattern: PatternIR,
    report: VerificationReport,
) -> str:
    """Build a Mermaid flowchart highlighting verification issues.

    - Known games → solid boxes (blue border)
    - Inputs → stadium shapes (green border)
    - Orphaned / unknown nodes → dashed red boxes
    - Flows with errors → red arrows
    - Decision games with S-005 warnings → amber border
    """
    lines: list[str] = ["graph LR"]

    # Collect known entity names
    game_names = {g.name for g in pattern.games}
    input_names = {i.name for i in pattern.inputs}
    known_names = game_names | input_names

    # Collect nodes referenced by flows that aren't known
    orphan_ids: set[str] = set()
    for flow in pattern.flows:
        if flow.source not in known_names:
            orphan_ids.add(flow.source)
        if flow.target not in known_names:
            orphan_ids.add(flow.target)

    # Collect S-005 warning game names
    warn_games: set[str] = set()
    for f in report.findings:
        if not f.passed and f.check_id == "S-005" and f.severity == Severity.WARNING:
            for el in f.source_elements:
                if el in game_names:
                    warn_games.add(el)

    # Collect flow indices that have T-006 errors (unknown endpoints)
    error_flows: set[int] = set()
    for f in report.findings:
        if not f.passed and f.check_id == "T-006":
            # Match flows by checking source_elements against flow endpoints
            for idx, flow in enumerate(pattern.flows):
                if flow.source in f.source_elements or flow.target in f.source_elements:
                    error_flows.add(idx)

    # --- Emit game nodes (deduplicated) ---
    lines.append("")
    lines.append("    %% Games")
    seen_games: set[str] = set()
    for g in pattern.games:
        if g.name in seen_games:
            continue
        seen_games.add(g.name)
        sid = _sanitize_id(g.name)
        cls = "warnGame" if g.name in warn_games else "game"
        lines.append(f'    {sid}["{g.name}"]:::{cls}')

    # --- Emit input nodes (deduplicated) ---
    if pattern.inputs:
        lines.append("")
        lines.append("    %% Inputs")
        seen_inputs: set[str] = set()
        for inp in pattern.inputs:
            if inp.name in seen_inputs:
                continue
            seen_inputs.add(inp.name)
            sid = _sanitize_id(inp.name)
            lines.append(f'    {sid}(["{inp.name}"]):::input')

    # --- Emit orphaned nodes ---
    if orphan_ids:
        lines.append("")
        lines.append("    %% Orphaned nodes (not in any game group)")
        for oid in sorted(orphan_ids):
            sid = _sanitize_id(oid)
            label = _short_hex(oid) if _is_hex_id(oid) else oid
            lines.append(f'    {sid}["{label}"]:::orphan')

    # --- Emit flows ---
    lines.append("")
    lines.append("    %% Flows")
    error_link_indices: list[int] = []
    link_counter = 0
    for idx, flow in enumerate(pattern.flows):
        src = _sanitize_id(flow.source)
        tgt = _sanitize_id(flow.target)
        label = flow.label or ""
        arrow = "-->" if flow.direction.value == "covariant" else "-.->"

        line = (
            f'    {src} {arrow}|"{label}"| {tgt}'
            if label
            else f"    {src} {arrow} {tgt}"
        )
        lines.append(line)

        if idx in error_flows:
            error_link_indices.append(link_counter)
        link_counter += 1  # noqa: SIM113

    # --- Style classes ---
    lines.append("")
    lines.append("    %% Styles")
    lines.append("    classDef game fill:#2d4f67,stroke:#7e9cd8,color:#dcd7ba")
    lines.append("    classDef input fill:#363646,stroke:#98bb6c,color:#dcd7ba")
    lines.append(
        "    classDef orphan fill:#1f1f28,stroke:#e82424,color:#e82424,"
        "stroke-dasharray:5 5"
    )
    lines.append("    classDef warnGame fill:#2d4f67,stroke:#e6c384,color:#dcd7ba")

    # Color error links red
    if error_link_indices:
        indices = ",".join(str(i) for i in error_link_indices)
        lines.append(f"    linkStyle {indices} stroke:#e82424,stroke-width:2px")

    return "\n".join(lines)
