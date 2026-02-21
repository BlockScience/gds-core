"""View 5 — Parameter influence diagram.

Shows which parameters affect which blocks, and transitively which
entity variables — the full Θ → block → X causal map.

View 6 — Traceability diagram.

For each entity variable, traces the full causal chain: which blocks
can affect it, and which parameters feed those blocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.query import SpecQuery
from gds_viz._helpers import entity_id as _entity_id
from gds_viz._helpers import param_id as _param_id
from gds_viz._helpers import sanitize_id
from gds_viz._styles import MermaidTheme, classdefs_for_all, theme_directive

if TYPE_CHECKING:
    from gds.spec import GDSSpec


def params_to_mermaid(spec: GDSSpec, *, theme: MermaidTheme | None = None) -> str:
    """Generate a parameter influence diagram from a GDSSpec.

    Shows Θ parameters → blocks that use them → entities they update.
    Only includes blocks that reference at least one parameter, and
    entities reachable from those blocks via the update map.

    Args:
        spec: The GDS specification.
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.
    """
    lines = [theme_directive(theme), "flowchart LR"]
    query = SpecQuery(spec)

    # Class definitions
    lines.extend(classdefs_for_all(theme))

    param_to_blocks = query.param_to_blocks()
    entity_update_map = query.entity_update_map()

    # Collect which params and blocks are actually connected
    active_params = {p for p, blocks in param_to_blocks.items() if blocks}
    if not active_params:
        lines.append("    no_params[No parameters defined]:::empty")
        return "\n".join(lines)

    # Parameter nodes (hexagons)
    for pname in sorted(active_params):
        pid = _param_id(pname)
        lines.append(f'    {pid}{{{{"{pname}"}}}}:::param')

    # Block nodes — only those referenced by parameters
    param_blocks: set[str] = set()
    for blocks in param_to_blocks.values():
        param_blocks.update(blocks)

    for bname in sorted(param_blocks):
        bid = sanitize_id(bname)
        lines.append(f"    {bid}[{bname}]")

    # Entity nodes — only those updated by param-connected blocks
    # Build reverse map: mechanism -> [(entity, var)]
    mech_to_updates: dict[str, list[tuple[str, str]]] = {}
    for ename, var_map in entity_update_map.items():
        for vname, mechs in var_map.items():
            for mname in mechs:
                mech_to_updates.setdefault(mname, []).append((ename, vname))

    active_entities: set[str] = set()
    for bname in param_blocks:
        if bname in mech_to_updates:
            for ename, _ in mech_to_updates[bname]:
                active_entities.add(ename)

    # Also include entities reachable via dependency chain from param blocks
    dep_graph = query.dependency_graph()
    visited: set[str] = set()
    frontier = list(param_blocks)
    while frontier:
        current = frontier.pop()
        if current in visited:
            continue
        visited.add(current)
        if current in mech_to_updates:
            for ename, _ in mech_to_updates[current]:
                active_entities.add(ename)
        for target in dep_graph.get(current, set()):
            frontier.append(target)

    for ename in sorted(active_entities):
        entity = spec.entities[ename]
        var_parts = []
        for vname, var in entity.variables.items():
            var_parts.append(var.symbol if var.symbol else vname)
        var_str = ", ".join(var_parts)
        eid = _entity_id(ename)
        lines.append(f'    {eid}[("{ename}<br/>{var_str}")]:::entity')

    # Edges: param -> block
    for pname in sorted(active_params):
        pid = _param_id(pname)
        for bname in param_to_blocks[pname]:
            bid = sanitize_id(bname)
            lines.append(f"    {pid} -.-> {bid}")

    # Edges: block -> entity (for blocks in the param-reachable set)
    seen_edges: set[tuple[str, str]] = set()
    for bname in visited:
        if bname in mech_to_updates:
            bid = sanitize_id(bname)
            for ename, _vname in mech_to_updates[bname]:
                eid = _entity_id(ename)
                if (bid, eid) not in seen_edges:
                    seen_edges.add((bid, eid))
                    lines.append(f"    {bid} -.-> {eid}")

    # Edges: block -> block (dependency flow within param-reachable set)
    for source in sorted(visited):
        for target in sorted(dep_graph.get(source, set())):
            if target in visited:
                sid = sanitize_id(source)
                tid = sanitize_id(target)
                lines.append(f"    {sid} --> {tid}")

    return "\n".join(lines)


def trace_to_mermaid(
    spec: GDSSpec,
    entity: str,
    variable: str,
    *,
    theme: MermaidTheme | None = None,
) -> str:
    """Generate a traceability diagram for a single entity variable.

    Shows every block that can transitively affect the variable,
    the parameters feeding those blocks, and the causal chain.

    Args:
        spec: The GDS specification.
        entity: Entity name (e.g. "Susceptible").
        variable: Variable name (e.g. "count").
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.
    """
    lines = [theme_directive(theme), "flowchart RL"]
    query = SpecQuery(spec)

    # Class definitions
    lines.extend(classdefs_for_all(theme))

    affecting = query.blocks_affecting(entity, variable)
    if not affecting:
        lines.append(f"    target[{entity}.{variable}]:::target")
        lines.append("    none[No affecting blocks]:::empty")
        return "\n".join(lines)

    # Target node
    ent = spec.entities[entity]
    var = ent.variables[variable]
    symbol = var.symbol if var.symbol else variable
    lines.append(f'    target(["{entity}.{variable} ({symbol})"]):::target')

    # Block nodes
    for bname in affecting:
        bid = sanitize_id(bname)
        lines.append(f"    {bid}[{bname}]")

    # Parameter nodes for affecting blocks
    block_to_params = query.block_to_params()
    active_params: set[str] = set()
    for bname in affecting:
        for pname in block_to_params.get(bname, []):
            active_params.add(pname)

    for pname in sorted(active_params):
        pid = _param_id(pname)
        lines.append(f'    {pid}{{{{"{pname}"}}}}:::param')

    # Edges: mechanism -> target
    entity_update_map = query.entity_update_map()
    direct_mechs = entity_update_map.get(entity, {}).get(variable, [])
    for mname in direct_mechs:
        mid = sanitize_id(mname)
        lines.append(f"    {mid} ==> target")

    # Edges: block -> block (dependency within affecting set)
    dep_graph = query.dependency_graph()
    for source in affecting:
        sid = sanitize_id(source)
        for target in dep_graph.get(source, set()):
            if target in affecting:
                tid = sanitize_id(target)
                lines.append(f"    {sid} --> {tid}")

    # Edges: param -> block
    for bname in affecting:
        bid = sanitize_id(bname)
        for pname in block_to_params.get(bname, []):
            pid = _param_id(pname)
            lines.append(f"    {pid} -.-> {bid}")

    return "\n".join(lines)
