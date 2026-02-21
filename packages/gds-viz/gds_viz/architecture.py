"""View 3 — Architecture diagram.

Renders domain-grouped blocks with entities, wire labels, and
tag-based subgraphs from a GDSSpec.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from gds.query import SpecQuery
from gds_viz._helpers import entity_id as _entity_id
from gds_viz._helpers import sanitize_id
from gds_viz._styles import (
    MermaidTheme,
    classdefs_for_all,
    subgraph_style_lines,
    theme_directive,
)

if TYPE_CHECKING:
    from gds.spec import GDSSpec


_ROLE_LABELS: dict[str, str] = {
    "boundary": "Boundary (U)",
    "policy": "Policy (g)",
    "mechanism": "Mechanism (f)",
    "control": "Control",
    "generic": "Generic",
}

_ROLE_SHAPES: dict[str, tuple[str, str]] = {
    "boundary": ("([", "])"),
    "mechanism": ("[[", "]]"),
}

_DEFAULT_SHAPE: tuple[str, str] = ("[", "]")


def spec_to_mermaid(
    spec: GDSSpec,
    *,
    group_by: str | None = None,
    show_entities: bool = True,
    show_wires: bool = True,
    theme: MermaidTheme | None = None,
) -> str:
    """Generate a Mermaid flowchart from a GDSSpec.

    Renders an architecture-level view with blocks grouped by role or tag,
    entity cylinders, and dependency wires.

    Args:
        spec: The GDS specification to visualize.
        group_by: Tag key to group blocks by. None groups by GDS role.
        show_entities: If True, render entity cylinders with state variables.
        show_wires: If True, render dependency edges from wirings.
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.
    """
    lines = [theme_directive(theme), "flowchart TD"]
    query = SpecQuery(spec)

    # Class definitions
    lines.extend(classdefs_for_all(theme))

    # Render grouped blocks
    if group_by is not None:
        sg_styles = _render_tag_groups(lines, spec, group_by)
    else:
        sg_styles = _render_role_groups(lines, query, spec)

    # Entity cylinders
    if show_entities:
        _render_entities(lines, spec, query)

    # Dependency wires
    if show_wires:
        _render_wires(lines, spec, query)

    # Subgraph background styling
    lines.extend(subgraph_style_lines(sg_styles, theme))

    return "\n".join(lines)


def _render_role_groups(
    lines: list[str], query: SpecQuery, spec: GDSSpec
) -> dict[str, str]:
    """Group blocks by GDS role into subgraphs. Returns sg_id -> role map."""
    groups = query.blocks_by_kind()
    sg_styles: dict[str, str] = {}
    for role, label in _ROLE_LABELS.items():
        block_names = groups.get(role, [])
        if not block_names:
            continue
        sg_id = sanitize_id(role)
        sg_styles[sg_id] = role
        lines.append(f'    subgraph {sg_id} ["{label}"]')
        for bname in block_names:
            _render_block_node(lines, bname, spec, indent=2)
        lines.append("    end")
    return sg_styles


def _render_tag_groups(lines: list[str], spec: GDSSpec, tag_key: str) -> dict[str, str]:
    """Group blocks by a tag key into subgraphs.

    Returns empty sg map (no role styling).
    """
    groups: dict[str, list[str]] = defaultdict(list)
    for bname, block in spec.blocks.items():
        tag_val = block.get_tag(tag_key)
        if tag_val is not None:
            groups[tag_val].append(bname)
        else:
            groups["Ungrouped"].append(bname)

    for group_name, block_names in groups.items():
        sg_id = sanitize_id(group_name)
        lines.append(f'    subgraph {sg_id} ["{group_name}"]')
        for bname in block_names:
            _render_block_node(lines, bname, spec, indent=2)
        lines.append("    end")

    # Tag groups don't have role-based subgraph styling
    return {}


def _render_block_node(
    lines: list[str], bname: str, spec: GDSSpec, indent: int = 2
) -> None:
    """Render a single block node with role-appropriate shape and class."""
    prefix = "    " * indent
    block = spec.blocks[bname]
    kind = getattr(block, "kind", "generic")
    shape_open, shape_close = _ROLE_SHAPES.get(kind, _DEFAULT_SHAPE)
    bid = sanitize_id(bname)
    lines.append(f"{prefix}{bid}{shape_open}{bname}{shape_close}:::{kind}")


def _render_entities(lines: list[str], spec: GDSSpec, query: SpecQuery) -> None:
    """Render entity cylinders and mechanism->entity update edges."""
    update_map = query.entity_update_map()

    for ename, entity in spec.entities.items():
        var_parts: list[str] = []
        for vname, var in entity.variables.items():
            if var.symbol:
                var_parts.append(f"{vname}: {var.symbol}")
            else:
                var_parts.append(vname)
        var_str = ", ".join(var_parts)
        eid = _entity_id(ename)
        lines.append(f'    {eid}[("{ename}<br/>{var_str}")]:::entity')

    # Dotted edges from mechanisms to entities (deduplicated)
    seen_edges: set[tuple[str, str]] = set()
    for ename, var_map in update_map.items():
        eid = _entity_id(ename)
        for _vname, mechs in var_map.items():
            for mname in mechs:
                mid = sanitize_id(mname)
                if (mid, eid) not in seen_edges:
                    seen_edges.add((mid, eid))
                    lines.append(f"    {mid} -.-> {eid}")


def _render_wires(lines: list[str], spec: GDSSpec, query: SpecQuery) -> None:
    """Render dependency edges from spec wirings."""
    # Build a space label lookup: (source, target) -> space name
    wire_labels: dict[tuple[str, str], str] = {}
    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            if wire.space:
                wire_labels[(wire.source, wire.target)] = wire.space

    dep_graph = query.dependency_graph()
    for source, targets in dep_graph.items():
        sid = sanitize_id(source)
        for target in sorted(targets):
            tid = sanitize_id(target)
            label = wire_labels.get((source, target), "")
            if label:
                lines.append(f"    {sid} --{label}--> {tid}")
            else:
                lines.append(f"    {sid} --> {tid}")
