"""Lightweight visualization utilities for GDS systems.

Generates Mermaid flowchart diagrams from SystemIR or Block compositions.
Mermaid diagrams can be rendered in:
- GitHub markdown
- GitLab markdown
- VS Code markdown preview
- mermaid.live
- Any tool with Mermaid support

The module provides two visualization strategies:

1. **Flat diagrams** (`system_to_mermaid()`) — show the compiled block structure
   with automatic shape/arrow styling based on block roles and wiring types.

2. **Architecture-aware diagrams** — domain-specific visualizations that encode
   semantic information (agent/environment boundaries, private/public data flow,
   stateful vs stateless components). See examples/prisoners_dilemma/visualize.py
   for a reference implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.ir.models import CompositionType, FlowDirection, HierarchyNodeIR
from gds_viz._helpers import sanitize_id
from gds_viz._styles import MermaidTheme, classdefs_for_roles, theme_directive

if TYPE_CHECKING:
    from gds.blocks.base import Block
    from gds.ir.models import SystemIR


def system_to_mermaid(
    system: SystemIR,
    show_hierarchy: bool = False,
    *,
    theme: MermaidTheme | None = None,
) -> str:
    """Generate a Mermaid flowchart from a SystemIR.

    Args:
        system: The compiled system to visualize.
        show_hierarchy: If True, uses the hierarchy tree to organize subgraphs.
                       If False, renders a flat graph of all blocks.
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.

    Example:
        ```python
        from examples.sir_epidemic.model import build_system
        from gds_viz import system_to_mermaid

        system = build_system()
        mermaid = system_to_mermaid(system)
        print(mermaid)
        ```
    """
    lines = [theme_directive(theme), "flowchart TD"]

    # Class definitions for role-based styling
    lines.extend(classdefs_for_roles(theme))

    if show_hierarchy and system.hierarchy:
        lines.append(_hierarchy_to_mermaid(system.hierarchy, indent=1))
    else:
        # Flat block diagram with role-based classes
        block_shapes = _get_block_shapes(system)
        block_roles = _get_block_roles(system)
        for block in system.blocks:
            shape_open, shape_close = block_shapes.get(block.name, ("[", "]"))
            safe_name = sanitize_id(block.name)
            role = block_roles.get(block.name, "generic")
            lines.append(
                f"    {safe_name}{shape_open}{block.name}{shape_close}:::{role}"
            )

    # Add wirings
    for wiring in system.wirings:
        src = sanitize_id(wiring.source)
        tgt = sanitize_id(wiring.target)
        label = wiring.label

        if wiring.is_temporal:
            # Temporal loop: dashed line with arrow back
            lines.append(f"    {src} -.{label}..-> {tgt}")
        elif wiring.is_feedback:
            # Feedback: thick arrow
            lines.append(f"    {src} =={label}==> {tgt}")
        elif wiring.direction == FlowDirection.CONTRAVARIANT:
            # Contravariant: backward arrow
            lines.append(f"    {tgt} <--{label}--- {src}")
        else:
            # Covariant forward: normal arrow
            lines.append(f"    {src} --{label}--> {tgt}")

    return "\n".join(lines)


def block_to_mermaid(block: Block, *, theme: MermaidTheme | None = None) -> str:
    """Generate a Mermaid flowchart from a Block composition tree.

    This is a convenience wrapper that flattens the block and creates
    a minimal diagram showing the composition structure.

    Args:
        block: The root block (atomic or composite).
        theme: Mermaid theme — one of 'default', 'neutral', 'dark', 'forest',
               'base'. None uses the default ('neutral').

    Returns:
        Mermaid flowchart diagram as a string.

    Example:
        ```python
        from gds.blocks.roles import BoundaryAction, Policy, Mechanism
        from gds.types.interface import Interface, port
        from gds_viz import block_to_mermaid

        observe = BoundaryAction(
            name="Observe",
            interface=Interface(forward_out=(port("Signal"),))
        )
        decide = Policy(
            name="Decide",
            interface=Interface(
                forward_in=(port("Signal"),),
                forward_out=(port("Action"),)
            )
        )
        update = Mechanism(
            name="Update",
            interface=Interface(forward_in=(port("Action"),)),
            updates=[("Entity", "state")]
        )

        pipeline = observe >> decide >> update
        print(block_to_mermaid(pipeline))
        ```
    """
    from gds.compiler.compile import compile_system

    # Compile with default settings
    system = compile_system(name=block.name, root=block)
    return system_to_mermaid(system, show_hierarchy=False, theme=theme)


def _hierarchy_to_mermaid(node: HierarchyNodeIR, indent: int = 1) -> str:
    """Recursively render hierarchy nodes as subgraphs."""
    prefix = "    " * indent
    lines = []

    if node.composition_type is None:
        # Leaf node - render as block
        safe_name = sanitize_id(node.name)
        lines.append(f"{prefix}{safe_name}[{node.name}]")
    else:
        # Composite node - render as subgraph
        subgraph_id = sanitize_id(node.id)
        comp_label = _composition_label(node.composition_type)
        lines.append(f"{prefix}subgraph {subgraph_id} [{comp_label}]")
        for child in node.children:
            lines.append(_hierarchy_to_mermaid(child, indent + 1))
        lines.append(f"{prefix}end")

    return "\n".join(lines)


def _get_block_shapes(system: SystemIR) -> dict[str, tuple[str, str]]:
    """Determine Mermaid shapes for blocks based on their signature.

    Returns dict mapping block name to (shape_open, shape_close) pair.
    - BoundaryAction (no inputs): stadium ([( ... )])
    - Terminal Mechanism (no outputs): double bracket ([[ ... ]])
    - Normal blocks: rectangle ([ ... ])
    """
    shapes = {}
    for block in system.blocks:
        fwd_in, fwd_out, bwd_in, bwd_out = block.signature
        has_input = bool(fwd_in) or bool(bwd_in)
        has_output = bool(fwd_out) or bool(bwd_out)

        if not has_input:
            # Boundary action
            shapes[block.name] = ("([", "])")
        elif not has_output:
            # Terminal mechanism
            shapes[block.name] = ("[[", "]]")
        else:
            # Normal block
            shapes[block.name] = ("[", "]")

    return shapes


def _get_block_roles(system: SystemIR) -> dict[str, str]:
    """Determine GDS role for blocks based on their signature.

    Maps block names to role keys: boundary, mechanism, or generic.
    """
    roles: dict[str, str] = {}
    for block in system.blocks:
        fwd_in, fwd_out, bwd_in, bwd_out = block.signature
        has_input = bool(fwd_in) or bool(bwd_in)
        has_output = bool(fwd_out) or bool(bwd_out)

        if not has_input:
            roles[block.name] = "boundary"
        elif not has_output:
            roles[block.name] = "mechanism"
        else:
            roles[block.name] = "generic"
    return roles


def _composition_label(comp_type: CompositionType) -> str:
    """Convert CompositionType to human-readable label."""
    return {
        CompositionType.SEQUENTIAL: "Sequential (>>)",
        CompositionType.PARALLEL: "Parallel (|)",
        CompositionType.FEEDBACK: "Feedback",
        CompositionType.TEMPORAL: "Temporal Loop",
    }.get(comp_type, comp_type.value)
