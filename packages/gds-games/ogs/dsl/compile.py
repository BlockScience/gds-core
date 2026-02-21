"""Compile a DSL Pattern into the flat PatternIR representation.

The compiler performs three transformations:

1. **Flatten** — walks the composition tree to extract all atomic games.
2. **Wire** — extracts explicit flows and auto-wires sequential compositions.
3. **Map metadata** — converts DSL-level metadata into IR equivalents.

Stages 1 and 2 delegate to the reusable GDS pipeline functions
(``flatten_blocks``, ``extract_wirings``), with OGS-specific callbacks
to produce ``OpenGameIR`` and ``FlowIR`` respectively.  Hierarchy
extraction remains OGS-specific to handle ``CORECURSIVE`` composition.
"""

from __future__ import annotations

from gds.blocks.base import Block
from gds.compiler.compile import (
    StructuralWiring,
    WiringOrigin,
    extract_wirings,
    flatten_blocks,
)
from gds.ir.models import sanitize_id

from ogs.dsl.composition import (
    CorecursiveLoop,
    FeedbackLoop,
    ParallelComposition,
    SequentialComposition,
)
from ogs.dsl.games import AtomicGame
from ogs.dsl.pattern import Pattern
from ogs.dsl.types import Port
from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    FlowIR,
    FlowType,
    HierarchyNodeIR,
    InputIR,
    OpenGameIR,
    PatternIR,
)


def compile_to_ir(pattern: Pattern) -> PatternIR:
    """Compile a DSL Pattern into PatternIR."""
    # 1. Flatten games (GDS stage 1)
    game_irs = flatten_blocks(pattern.game, _compile_game)

    # 2. Extract flows (GDS stage 2 with OGS emitter)
    flows: list[FlowIR] = extract_wirings(pattern.game, _ogs_wiring_emitter)

    # 3. Map inputs and generate input flows
    input_irs = []
    for inp in pattern.inputs:
        input_irs.append(
            InputIR(
                name=inp.name,
                input_type=inp.input_type,
                schema_hint=inp.schema_hint,
            )
        )
        if inp.target_game:
            flows.append(
                FlowIR(
                    source=inp.name,
                    target=inp.target_game,
                    label=inp.flow_label or inp.name,
                    flow_type=FlowType.OBSERVATION,
                    direction=FlowDirection.COVARIANT,
                )
            )

    # 4. Extract composition hierarchy (OGS-specific for CORECURSIVE)
    counter = [0]
    hierarchy = _extract_hierarchy(pattern.game, counter)
    hierarchy = _flatten_sequential_chains(hierarchy)

    return PatternIR(
        name=pattern.name,
        games=game_irs,
        flows=flows,
        inputs=input_irs,
        composition_type=pattern.composition_type,
        terminal_conditions=pattern.terminal_conditions,
        action_spaces=pattern.action_spaces,
        initialization=pattern.initializations,
        hierarchy=hierarchy,
        source_canvas=pattern.source,
    )


def _compile_game(game: AtomicGame) -> OpenGameIR:
    """Convert a DSL AtomicGame to an IR OpenGameIR."""
    return OpenGameIR(
        name=game.name,
        game_type=game.game_type,
        signature=(
            _ports_to_sig(game.signature.x),
            _ports_to_sig(game.signature.y),
            _ports_to_sig(game.signature.r),
            _ports_to_sig(game.signature.s),
        ),
        logic=game.logic,
        color_code=game.color_code,
        tags=game.tags,
    )


def _ports_to_sig(ports: tuple[Port, ...]) -> str:
    """Convert a tuple of Ports to the IR signature string format."""
    if not ports:
        return ""
    return " + ".join(p.name for p in ports)


def _ogs_wiring_emitter(sw: StructuralWiring) -> FlowIR:
    """Convert a GDS StructuralWiring into an OGS FlowIR."""
    if sw.direction == FlowDirection.CONTRAVARIANT:
        flow_type = FlowType.UTILITY_COUTILITY
    elif sw.origin == WiringOrigin.AUTO and _is_choice_port(sw.source_port):
        flow_type = FlowType.CHOICE_OBSERVATION
    else:
        flow_type = FlowType.OBSERVATION

    return FlowIR(
        source=sw.source_block,
        target=sw.target_block,
        label=sw.source_port,
        flow_type=flow_type,
        direction=sw.direction,
        is_feedback=(sw.origin == WiringOrigin.FEEDBACK),
        is_corecursive=(sw.origin == WiringOrigin.TEMPORAL),
    )


def _is_choice_port(port_name: str) -> bool:
    """Check whether a port name indicates a choice/decision flow."""
    name_lower = port_name.lower()
    return "decision" in name_lower or "choice" in name_lower


# ---------------------------------------------------------------------------
# Hierarchy extraction (OGS-specific for CORECURSIVE composition type)
# ---------------------------------------------------------------------------


def _extract_hierarchy(game: Block, counter: list[int]) -> HierarchyNodeIR:
    """Recursively walk the composition tree and build a HierarchyNodeIR."""
    if isinstance(game, AtomicGame):
        return HierarchyNodeIR(
            id=f"leaf_{sanitize_id(game.name)}",
            name=game.name,
            composition_type=None,
            block_name=game.name,
        )

    counter[0] += 1
    node_id = f"group_{counter[0]}"

    if isinstance(game, SequentialComposition):
        return HierarchyNodeIR(
            id=node_id,
            name=game.name,
            composition_type=CompositionType.SEQUENTIAL,
            children=[
                _extract_hierarchy(game.first, counter),
                _extract_hierarchy(game.second, counter),
            ],
        )
    elif isinstance(game, ParallelComposition):
        return HierarchyNodeIR(
            id=node_id,
            name=game.name,
            composition_type=CompositionType.PARALLEL,
            children=[
                _extract_hierarchy(game.left, counter),
                _extract_hierarchy(game.right, counter),
            ],
        )
    elif isinstance(game, FeedbackLoop):
        return HierarchyNodeIR(
            id=node_id,
            name=game.name,
            composition_type=CompositionType.FEEDBACK,
            children=[_extract_hierarchy(game.inner, counter)],
        )
    elif isinstance(game, CorecursiveLoop):
        return HierarchyNodeIR(
            id=node_id,
            name=game.name,
            composition_type=CompositionType.CORECURSIVE,
            children=[_extract_hierarchy(game.inner, counter)],
            exit_condition=game.exit_condition,
        )

    return HierarchyNodeIR(id=node_id, name=game.name)


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
