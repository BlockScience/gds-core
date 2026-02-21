"""View 2 — Canonical GDS diagram.

Renders the mathematical decomposition X_t -> U -> g -> f -> X_{t+1}
from a CanonicalGDS projection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_viz._helpers import sanitize_id
from gds_viz._styles import (
    MermaidTheme,
    classdefs_for_all,
    subgraph_style_lines,
    theme_directive,
)

if TYPE_CHECKING:
    from gds.canonical import CanonicalGDS


def canonical_to_mermaid(
    canonical: CanonicalGDS,
    *,
    show_updates: bool = True,
    show_parameters: bool = True,
    theme: MermaidTheme | None = None,
) -> str:
    """Generate a Mermaid flowchart from a CanonicalGDS projection.

    Renders the formal GDS decomposition: X_t -> U -> g -> f -> X_{t+1}
    with optional parameter space (Theta) and update map labels.

    Args:
        canonical: The canonical GDS projection to visualize.
        show_updates: If True, label mechanism->X edges with entity.variable.
        show_parameters: If True, show the Theta node when parameters exist.
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.
    """
    lines = [theme_directive(theme), "flowchart LR"]

    # Class definitions
    lines.extend(classdefs_for_all(theme))

    # State variable listing for X_t / X_{t+1}
    # Use entity.var format to disambiguate variables with the same name
    var_names = [v for _, v in canonical.state_variables]
    has_dupes = len(var_names) != len(set(var_names))
    if has_dupes:
        var_list = ", ".join(f"{e}.{v}" for e, v in canonical.state_variables)
    else:
        var_list = ", ".join(var_names)
    if var_list:
        x_label = f"X_t<br/>{var_list}"
        x_next_label = f"X_{{t+1}}<br/>{var_list}"
    else:
        x_label = "X_t"
        x_next_label = "X_{t+1}"

    lines.append(f'    X_t(["{x_label}"]):::state')
    lines.append(f'    X_next(["{x_next_label}"]):::state')

    # Parameter node (Theta)
    if show_parameters and canonical.has_parameters:
        param_names = ", ".join(canonical.parameter_schema.names())
        lines.append(f'    Theta{{{{"\u0398<br/>{param_names}"}}}}:::param')

    # Role subgraphs — only render non-empty ones
    rendered_sgs: dict[str, str] = {}
    for sg_id, label, blocks, role in [
        ("U", "Boundary (U)", canonical.boundary_blocks, "boundary"),
        ("g", "Policy (g)", canonical.policy_blocks, "policy"),
        ("f", "Mechanism (f)", canonical.mechanism_blocks, "mechanism"),
        ("ctrl", "Control", canonical.control_blocks, "control"),
    ]:
        if blocks:
            _render_subgraph(lines, sg_id, label, blocks, role)
            rendered_sgs[sg_id] = role

    # Edges between layers
    _render_flow_edges(lines, canonical)

    # Update edges: mechanism -> X_{t+1}
    _render_update_edges(lines, canonical, show_updates)

    # Control feedback edges
    if canonical.control_blocks:
        for cname in canonical.control_blocks:
            cid = sanitize_id(cname)
            # f -> ctrl (dashed)
            lines.append(f"    f -.-> {cid}")
            # ctrl -> g (dashed)
            lines.append(f"    {cid} -.-> g")

    # Parameter edges
    if show_parameters and canonical.has_parameters:
        if canonical.policy_blocks:
            lines.append("    Theta -.-> g")
        if canonical.mechanism_blocks:
            lines.append("    Theta -.-> f")

    # Subgraph background styling
    lines.extend(subgraph_style_lines(rendered_sgs, theme))

    return "\n".join(lines)


def _render_subgraph(
    lines: list[str],
    sg_id: str,
    label: str,
    block_names: tuple[str, ...],
    role: str = "generic",
) -> None:
    """Render a subgraph for a role layer if it has blocks."""
    if not block_names:
        return
    lines.append(f'    subgraph {sg_id} ["{label}"]')
    for name in block_names:
        sid = sanitize_id(name)
        lines.append(f"        {sid}[{name}]:::{role}")
    lines.append("    end")


def _render_flow_edges(lines: list[str], canonical: CanonicalGDS) -> None:
    """Render forward-flow edges between role layers.

    Uses subgraph-level edges between layers to avoid spurious
    cross-product connections (e.g. Alice Decision -> Bob World Model).
    Individual block edges are only used for X_t -> first layer.
    """
    layer_ids: list[str] = []
    if canonical.boundary_blocks:
        layer_ids.append("U")
    if canonical.policy_blocks:
        layer_ids.append("g")
    if canonical.mechanism_blocks:
        layer_ids.append("f")

    if not layer_ids:
        lines.append("    X_t --> X_next")
        return

    # X_t -> first subgraph
    lines.append(f"    X_t --> {layer_ids[0]}")

    # Inter-layer: subgraph -> subgraph
    for i in range(len(layer_ids) - 1):
        lines.append(f"    {layer_ids[i]} --> {layer_ids[i + 1]}")

    # Last layer -> X_{t+1} (only if update edges won't cover this)
    if layer_ids[-1] != "f":
        lines.append(f"    {layer_ids[-1]} --> X_next")


def _render_update_edges(
    lines: list[str], canonical: CanonicalGDS, show_updates: bool
) -> None:
    """Render edges from mechanisms to X_{t+1}."""
    if not canonical.mechanism_blocks:
        return

    if show_updates and canonical.update_map:
        for mech_name, updates in canonical.update_map:
            mid = sanitize_id(mech_name)
            for entity, var in updates:
                lines.append(f"    {mid} -.-> |{entity}.{var}| X_next")
    else:
        for mech_name in canonical.mechanism_blocks:
            mid = sanitize_id(mech_name)
            lines.append(f"    {mid} --> X_next")
