"""Compile a Block composition tree into a flat SystemIR.

The compiler performs three transformations:

1. **Flatten** — walks the composition tree to extract all atomic blocks.
2. **Wire** — extracts explicit wirings and auto-wires stack compositions.
3. **Hierarchy** — captures the composition tree structure for visualization.

Each stage is exposed as a standalone generic function (``flatten_blocks``,
``extract_wirings``, ``extract_hierarchy``) so domain packages can reuse the
DFS traversal with custom callbacks instead of forking the compiler.

Domain packages provide a ``block_compiler`` callback to convert their
specific atomic block types into BlockIR, and optionally a
``wiring_emitter`` callback to transform structural wirings into domain IR.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
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
    InputIR,
    SystemIR,
    WiringIR,
    sanitize_id,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from gds.types.interface import Port


# ---------------------------------------------------------------------------
# Structural intermediates
# ---------------------------------------------------------------------------


class WiringOrigin(StrEnum):
    """How a structural wiring was discovered during DFS traversal."""

    AUTO = "auto"
    EXPLICIT = "explicit"
    FEEDBACK = "feedback"
    TEMPORAL = "temporal"


@dataclass(frozen=True)
class StructuralWiring:
    """Protocol-internal intermediate between DFS traversal and IR emission.

    The DFS walk produces these; the wiring emitter callback transforms them
    into domain-specific IR (e.g. ``WiringIR`` for GDS, flow edges for OGS).
    """

    source_block: str
    source_port: str
    target_block: str
    target_port: str
    direction: FlowDirection
    origin: WiringOrigin


# ---------------------------------------------------------------------------
# Stage 1: flatten_blocks
# ---------------------------------------------------------------------------


def flatten_blocks[B](
    root: Block,
    block_compiler: Callable[[AtomicBlock], B],
) -> list[B]:
    """Flatten the composition tree and map each leaf through *block_compiler*.

    Args:
        root: Root of the composition tree.
        block_compiler: Callback that converts an AtomicBlock into domain IR.
            For GDS, this produces ``BlockIR``; OGS can produce ``OpenGameIR``.

    Returns:
        Ordered list of compiled block IR objects.
    """
    return [block_compiler(b) for b in root.flatten()]


# ---------------------------------------------------------------------------
# Stage 2: extract_wirings
# ---------------------------------------------------------------------------


def extract_wirings[W](
    root: Block,
    wiring_emitter: Callable[[StructuralWiring], W] | None = None,
) -> list[W]:
    """Walk the composition tree and emit all wirings through *wiring_emitter*.

    The DFS traversal discovers explicit wirings, auto-wired connections,
    feedback wirings, and temporal wirings — each tagged with a
    ``WiringOrigin``. The emitter callback transforms each
    ``StructuralWiring`` into domain-specific IR.

    Args:
        root: Root of the composition tree.
        wiring_emitter: Callback that converts a ``StructuralWiring`` into
            domain IR. If None, uses the default GDS emitter that produces
            ``WiringIR``.

    Returns:
        Ordered list of emitted wiring IR objects.
    """
    if wiring_emitter is None:
        wiring_emitter = _default_wiring_emitter  # type: ignore[assignment]

    structural: list[StructuralWiring] = []
    _walk_structural_wirings(root, structural)
    return [wiring_emitter(sw) for sw in structural]


# ---------------------------------------------------------------------------
# Stage 3: extract_hierarchy
# ---------------------------------------------------------------------------


def extract_hierarchy(root: Block) -> HierarchyNodeIR:
    """Build a ``HierarchyNodeIR`` tree from the composition tree.

    Sequential and parallel chains are flattened from binary trees into
    n-ary groups for cleaner visualization.

    Args:
        root: Root of the composition tree.

    Returns:
        Root ``HierarchyNodeIR`` with flattened chains.
    """
    counter = [0]
    hierarchy = _extract_hierarchy(root, counter)
    return _flatten_sequential_chains(hierarchy)


# ---------------------------------------------------------------------------
# compile_system — thin wrapper over the three stages
# ---------------------------------------------------------------------------


def compile_system(
    name: str,
    root: Block,
    block_compiler: Callable[[AtomicBlock], BlockIR] | None = None,
    wiring_emitter: Callable[[StructuralWiring], WiringIR] | None = None,
    composition_type: CompositionType = CompositionType.SEQUENTIAL,
    source: str = "",
    inputs: list[InputIR] | None = None,
) -> SystemIR:
    """Compile a Block tree into a flat SystemIR.

    Args:
        name: System name.
        root: Root of the composition tree.
        block_compiler: Domain-specific function to convert AtomicBlock → BlockIR.
            If None, uses a default that extracts name + interface.
        wiring_emitter: Domain-specific function to convert StructuralWiring →
            WiringIR. If None, uses the default GDS emitter.
        composition_type: Top-level composition type.
        source: Source identifier.
        inputs: External inputs to include in the SystemIR. Layer 0 never
            infers inputs — domain packages supply them.
    """
    if block_compiler is None:
        block_compiler = _default_block_compiler

    blocks = flatten_blocks(root, block_compiler)
    wirings = extract_wirings(root, wiring_emitter)
    hierarchy = extract_hierarchy(root)

    return SystemIR(
        name=name,
        blocks=blocks,
        wirings=wirings,
        inputs=inputs or [],
        composition_type=composition_type,
        hierarchy=hierarchy,
        source=source,
    )


# ---------------------------------------------------------------------------
# Default callbacks
# ---------------------------------------------------------------------------


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


def _default_wiring_emitter(sw: StructuralWiring) -> WiringIR:
    """Default wiring emitter — converts StructuralWiring to WiringIR."""
    return WiringIR(
        source=sw.source_block,
        target=sw.target_block,
        label=sw.source_port,
        direction=sw.direction,
        is_feedback=sw.origin == WiringOrigin.FEEDBACK,
        is_temporal=sw.origin == WiringOrigin.TEMPORAL,
    )


def _ports_to_sig(ports: tuple[Port, ...]) -> str:
    """Convert a tuple of Ports to the IR signature string format."""
    if not ports:
        return ""
    return " + ".join(p.name for p in ports)


# ---------------------------------------------------------------------------
# DFS wiring traversal (produces StructuralWiring intermediates)
# ---------------------------------------------------------------------------


def _walk_structural_wirings(block: Block, out: list[StructuralWiring]) -> None:
    """Recursively walk the composition tree, collecting StructuralWirings."""
    if isinstance(block, AtomicBlock):
        return

    if isinstance(block, StackComposition):
        _walk_structural_wirings(block.first, out)
        _walk_structural_wirings(block.second, out)

        for w in block.wiring:
            out.append(_wiring_to_structural(w, WiringOrigin.EXPLICIT))

        if not block.wiring:
            _auto_wire_stack(block.first, block.second, out)

    elif isinstance(block, ParallelComposition):
        _walk_structural_wirings(block.left, out)
        _walk_structural_wirings(block.right, out)

    elif isinstance(block, FeedbackLoop):
        _walk_structural_wirings(block.inner, out)
        for fw in block.feedback_wiring:
            out.append(_wiring_to_structural(fw, WiringOrigin.FEEDBACK))

    elif isinstance(block, TemporalLoop):
        _walk_structural_wirings(block.inner, out)
        for w in block.temporal_wiring:
            out.append(_wiring_to_structural(w, WiringOrigin.TEMPORAL))


def _wiring_to_structural(wiring: Wiring, origin: WiringOrigin) -> StructuralWiring:
    """Convert a DSL Wiring to a StructuralWiring intermediate."""
    return StructuralWiring(
        source_block=wiring.source_block,
        source_port=wiring.source_port,
        target_block=wiring.target_block,
        target_port=wiring.target_port,
        direction=wiring.direction,
        origin=origin,
    )


def _auto_wire_stack(first: Block, second: Block, out: list[StructuralWiring]) -> None:
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
                out.append(
                    StructuralWiring(
                        source_block=source,
                        source_port=out_port.name,
                        target_block=target,
                        target_port=in_port.name,
                        direction=FlowDirection.COVARIANT,
                        origin=WiringOrigin.AUTO,
                    )
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


def _extract_hierarchy(block: Block, counter: list[int]) -> HierarchyNodeIR:
    """Recursively build a HierarchyNodeIR from the composition tree."""
    if isinstance(block, AtomicBlock):
        return HierarchyNodeIR(
            id=f"leaf_{sanitize_id(block.name)}",
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
