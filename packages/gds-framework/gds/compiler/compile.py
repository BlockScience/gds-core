"""Compile a Block composition tree into a flat SystemIR.

The compiler performs three transformations:

1. **Flatten** — walks the composition tree to extract all atomic blocks.
2. **Wire** — extracts explicit wirings and auto-wires stack compositions.
3. **Hierarchy** — captures the composition tree structure for visualization.

Domain packages provide a ``block_compiler`` callback to convert their
specific atomic block types into BlockIR.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from gds.blocks.base import AtomicBlock, Block
from gds.blocks.composition import (
    FeedbackLoop,
    ParallelComposition,
    StackComposition,
    TemporalLoop,
    Wiring,
)
from gds.ir.models import (
    BlockIR,
    CompositionType,
    FlowDirection,
    HierarchyNodeIR,
    SystemIR,
    WiringIR,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from gds.types.interface import Port


def compile_system(
    name: str,
    root: Block,
    block_compiler: Callable[[AtomicBlock], BlockIR] | None = None,
    composition_type: CompositionType = CompositionType.SEQUENTIAL,
    source: str = "",
) -> SystemIR:
    """Compile a Block tree into a flat SystemIR.

    Args:
        name: System name.
        root: Root of the composition tree.
        block_compiler: Domain-specific function to convert AtomicBlock → BlockIR.
            If None, uses a default that extracts name + interface.
        composition_type: Top-level composition type.
        source: Source identifier.
    """
    if block_compiler is None:
        block_compiler = _default_block_compiler

    # 1. Flatten
    atomic_blocks = root.flatten()
    block_irs = [block_compiler(b) for b in atomic_blocks]

    # 2. Wire
    wirings = _extract_wirings(root)

    # 3. Hierarchy
    counter = [0]
    hierarchy = _extract_hierarchy(root, counter)
    hierarchy = _flatten_sequential_chains(hierarchy)

    return SystemIR(
        name=name,
        blocks=block_irs,
        wirings=wirings,
        composition_type=composition_type,
        hierarchy=hierarchy,
        source=source,
    )


def _default_block_compiler(block: AtomicBlock) -> BlockIR:
    """Default block compiler — extracts name and interface slots."""
    return BlockIR(
        name=block.name,
        signature=(
            _ports_to_sig(block.interface.forward_in),
            _ports_to_sig(block.interface.forward_out),
            _ports_to_sig(block.interface.backward_in),
            _ports_to_sig(block.interface.backward_out),
        ),
    )


def _ports_to_sig(ports: tuple[Port, ...]) -> str:
    """Convert a tuple of Ports to the IR signature string format."""
    if not ports:
        return ""
    return " + ".join(p.name for p in ports)


# ---------------------------------------------------------------------------
# Wiring extraction
# ---------------------------------------------------------------------------


def _extract_wirings(block: Block) -> list[WiringIR]:
    """Recursively walk the block tree and collect all wirings."""
    wirings: list[WiringIR] = []
    _walk_wirings(block, wirings)
    return wirings


def _walk_wirings(block: Block, wirings: list[WiringIR]) -> None:
    """Recursively walk the composition tree, collecting all wirings."""
    if isinstance(block, AtomicBlock):
        return

    if isinstance(block, StackComposition):
        _walk_wirings(block.first, wirings)
        _walk_wirings(block.second, wirings)

        for w in block.wiring:
            wirings.append(_wiring_to_ir(w))

        if not block.wiring:
            _auto_wire_stack(block.first, block.second, wirings)

    elif isinstance(block, ParallelComposition):
        _walk_wirings(block.left, wirings)
        _walk_wirings(block.right, wirings)

    elif isinstance(block, FeedbackLoop):
        _walk_wirings(block.inner, wirings)
        for fw in block.feedback_wiring:
            wirings.append(_wiring_to_ir(fw, is_feedback=True))

    elif isinstance(block, TemporalLoop):
        _walk_wirings(block.inner, wirings)
        for w in block.temporal_wiring:
            wirings.append(_wiring_to_ir(w, is_temporal=True))


def _auto_wire_stack(first: Block, second: Block, wirings: list[WiringIR]) -> None:
    """Auto-wire matching forward_out→forward_in ports in stack compositions."""
    first_leaves = _get_leaf_names(first)
    second_leaves = _get_leaf_names(second)

    for out_port in first.interface.forward_out:
        for in_port in second.interface.forward_in:
            if out_port.type_tokens & in_port.type_tokens:
                source = (
                    _find_port_owner(first, out_port, "forward_out") or first_leaves[-1]
                )
                target = (
                    _find_port_owner(second, in_port, "forward_in") or second_leaves[0]
                )
                wirings.append(
                    WiringIR(
                        source=source,
                        target=target,
                        label=out_port.name,
                        direction=FlowDirection.COVARIANT,
                    )
                )


def _wiring_to_ir(
    wiring: Wiring,
    is_feedback: bool = False,
    is_temporal: bool = False,
) -> WiringIR:
    """Convert a DSL Wiring to an IR WiringIR."""
    return WiringIR(
        source=wiring.source_block,
        target=wiring.target_block,
        label=wiring.source_port,
        direction=wiring.direction,
        is_feedback=is_feedback,
        is_temporal=is_temporal,
    )


def _get_leaf_names(block: Block) -> list[str]:
    """Get names of all leaf (atomic) blocks."""
    return [b.name for b in block.flatten()]


def _find_port_owner(block: Block, target_port: Port, slot: str) -> str | None:
    """Find which leaf block owns a given port in the specified slot."""
    for leaf in block.flatten():
        ports = getattr(leaf.interface, slot)
        if target_port in ports:
            return leaf.name
    return None


# ---------------------------------------------------------------------------
# Hierarchy extraction
# ---------------------------------------------------------------------------


def _sanitize_id(name: str) -> str:
    """Convert a name to a valid ID (alphanumeric + underscore only)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _extract_hierarchy(block: Block, counter: list[int]) -> HierarchyNodeIR:
    """Recursively build a HierarchyNodeIR from the composition tree."""
    if isinstance(block, AtomicBlock):
        return HierarchyNodeIR(
            id=f"leaf_{_sanitize_id(block.name)}",
            name=block.name,
            composition_type=None,
            block_name=block.name,
        )

    counter[0] += 1
    node_id = f"group_{counter[0]}"

    if isinstance(block, StackComposition):
        return HierarchyNodeIR(
            id=node_id,
            name=block.name,
            composition_type=CompositionType.SEQUENTIAL,
            children=[
                _extract_hierarchy(block.first, counter),
                _extract_hierarchy(block.second, counter),
            ],
        )
    elif isinstance(block, ParallelComposition):
        return HierarchyNodeIR(
            id=node_id,
            name=block.name,
            composition_type=CompositionType.PARALLEL,
            children=[
                _extract_hierarchy(block.left, counter),
                _extract_hierarchy(block.right, counter),
            ],
        )
    elif isinstance(block, FeedbackLoop):
        return HierarchyNodeIR(
            id=node_id,
            name=block.name,
            composition_type=CompositionType.FEEDBACK,
            children=[_extract_hierarchy(block.inner, counter)],
        )
    elif isinstance(block, TemporalLoop):
        return HierarchyNodeIR(
            id=node_id,
            name=block.name,
            composition_type=CompositionType.TEMPORAL,
            children=[_extract_hierarchy(block.inner, counter)],
            exit_condition=block.exit_condition,
        )

    return HierarchyNodeIR(id=node_id, name=block.name)


def _flatten_sequential_chains(node: HierarchyNodeIR) -> HierarchyNodeIR:
    """Collapse deeply nested binary sequential trees into n-ary groups."""
    new_children = [_flatten_sequential_chains(c) for c in node.children]

    if node.composition_type not in (
        CompositionType.SEQUENTIAL,
        CompositionType.PARALLEL,
    ):
        return node.model_copy(update={"children": new_children})

    flattened: list[HierarchyNodeIR] = []
    for child in new_children:
        if child.composition_type == node.composition_type:
            flattened.extend(child.children)
        else:
            flattened.append(child)

    return node.model_copy(update={"children": flattened})
