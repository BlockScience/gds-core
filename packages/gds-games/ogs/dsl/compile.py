"""Compile a DSL Pattern into the flat PatternIR representation.

The compiler performs three transformations:

1. **Flatten** — walks the composition tree to extract all atomic games.
2. **Wire** — extracts explicit flows and auto-wires sequential compositions.
3. **Map metadata** — converts DSL-level metadata into IR equivalents.
"""

from __future__ import annotations

from ogs.dsl.base import OpenGame
from ogs.dsl.composition import (
    CorecursiveLoop,
    FeedbackLoop,
    Flow,
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
    # 1. Flatten games
    atomic_games = pattern.game.flatten()
    game_irs = [_compile_game(g) for g in atomic_games]

    # 2. Walk composition tree to extract flows
    flows = _extract_flows(pattern.game)

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

    # 4. Extract composition hierarchy
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


def _extract_flows(game: OpenGame) -> list[FlowIR]:
    """Recursively walk the game tree and collect all flows."""
    flows: list[FlowIR] = []
    _walk_flows(game, flows)
    return flows


def _walk_flows(game: OpenGame, flows: list[FlowIR]) -> None:
    """Recursively walk the composition tree, collecting all flows."""
    if isinstance(game, AtomicGame):
        return

    if isinstance(game, SequentialComposition):
        _walk_flows(game.first, flows)
        _walk_flows(game.second, flows)

        for w in game.wiring:
            flows.append(_flow_to_ir(w))

        if not game.wiring:
            _auto_wire_sequential(game.first, game.second, flows)

    elif isinstance(game, ParallelComposition):
        _walk_flows(game.left, flows)
        _walk_flows(game.right, flows)

    elif isinstance(game, FeedbackLoop):
        _walk_flows(game.inner, flows)
        for fw in game.feedback_wiring:
            flows.append(_flow_to_ir(fw, is_feedback=True))

    elif isinstance(game, CorecursiveLoop):
        _walk_flows(game.inner, flows)
        for w in game.corecursive_wiring:
            flows.append(_flow_to_ir(w, is_corecursive=True))


def _auto_wire_sequential(
    first: OpenGame, second: OpenGame, flows: list[FlowIR]
) -> None:
    """Auto-wire matching Y→X ports between sequentially composed games."""
    first_leaves = _get_leaf_names(first)
    second_leaves = _get_leaf_names(second)

    for y_port in first.signature.y:
        for x_port in second.signature.x:
            if y_port.type_tokens & x_port.type_tokens:
                source = _find_port_owner(first, y_port, "y") or first_leaves[-1]
                target = _find_port_owner(second, x_port, "x") or second_leaves[0]
                flows.append(
                    FlowIR(
                        source=source,
                        target=target,
                        label=y_port.name,
                        flow_type=_infer_flow_type(y_port, FlowDirection.COVARIANT),
                        direction=FlowDirection.COVARIANT,
                    )
                )


def _flow_to_ir(
    flow: Flow,
    is_feedback: bool = False,
    is_corecursive: bool = False,
) -> FlowIR:
    """Convert a DSL Flow to an IR FlowIR."""
    flow_type = (
        FlowType.UTILITY_COUTILITY
        if flow.direction == FlowDirection.CONTRAVARIANT
        else FlowType.OBSERVATION
    )
    return FlowIR(
        source=flow.source_game,
        target=flow.target_game,
        label=flow.source_port,
        flow_type=flow_type,
        direction=flow.direction,
        is_feedback=is_feedback,
        is_corecursive=is_corecursive,
    )


def _infer_flow_type(port: Port, direction: FlowDirection) -> FlowType:
    """Infer the semantic flow type from port name and direction."""
    if direction == FlowDirection.CONTRAVARIANT:
        return FlowType.UTILITY_COUTILITY

    name_lower = port.name.lower()
    if "decision" in name_lower or "choice" in name_lower:
        return FlowType.CHOICE_OBSERVATION
    return FlowType.OBSERVATION


def _get_leaf_names(game: OpenGame) -> list[str]:
    """Get names of all leaf (atomic) games."""
    return [g.name for g in game.flatten()]


def _find_port_owner(game: OpenGame, target_port: Port, slot: str) -> str | None:
    """Find which leaf game owns a given port in the specified slot.

    Maps game-theory slot names (x, y, r, s) to interface field names.
    """
    slot_map = {
        "x": "forward_in",
        "y": "forward_out",
        "r": "backward_in",
        "s": "backward_out",
    }
    interface_slot = slot_map.get(slot, slot)
    for leaf in game.flatten():
        ports = getattr(leaf.interface, interface_slot)
        if target_port in ports:
            return leaf.name
    return None


# ---------------------------------------------------------------------------
# Hierarchy extraction
# ---------------------------------------------------------------------------


def _sanitize_id(name: str) -> str:
    """Convert a name to a valid ID."""
    import re

    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _extract_hierarchy(game: OpenGame, counter: list[int]) -> HierarchyNodeIR:
    """Recursively walk the composition tree and build a HierarchyNodeIR."""
    if isinstance(game, AtomicGame):
        return HierarchyNodeIR(
            id=f"leaf_{_sanitize_id(game.name)}",
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
