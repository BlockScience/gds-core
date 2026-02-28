"""Compiler: StateMachineModel -> GDSSpec -> SystemIR.

Two public functions:
- compile_sm(model) -> GDSSpec: registers types, spaces, entities, blocks, wirings
- compile_sm_to_system(model) -> SystemIR: builds composition tree and compiles

Composition tree:
    (events |) >> (transition_policies |) >> (state_mechs |)
        .loop([state -> transition inputs])

With regions: regions -> ParallelComposition for orthogonal states.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.composition import Wiring
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

from gds_software.common.compile_utils import (
    build_inter_tier_wirings,
    parallel_tier,
    sequential_with_explicit_wiring,
)
from gds_software.statemachine.elements import Event, State, Transition

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.statemachine.model import StateMachineModel


# ── Semantic type definitions ────────────────────────────────

EventType = TypeDef(
    name="SM Event",
    python_type=str,
    description="State machine event signal",
)

StateType = TypeDef(
    name="SM State",
    python_type=str,
    description="State machine current state value",
)


# ── Semantic spaces ──────────────────────────────────────────

EventSpace = Space(
    name="SM EventSpace",
    fields={"value": EventType},
    description="Space for state machine events",
)

StateSpace = Space(
    name="SM StateSpace",
    fields={"value": StateType},
    description="Space for state machine state values",
)


# ── Port naming helpers ──────────────────────────────────────


def _event_port_name(name: str) -> str:
    return f"{name} Event"


def _state_port_name(name: str) -> str:
    return f"{name} State"


def _transition_block_name(name: str) -> str:
    return f"{name} Transition"


def _state_mech_name(name: str) -> str:
    return f"{name} Mechanism"


# ── Block builders ───────────────────────────────────────────


def _build_event_block(event: Event) -> BoundaryAction:
    """Event -> BoundaryAction: no forward_in, emits Event signal."""
    return BoundaryAction(
        name=event.name,
        interface=Interface(
            forward_out=(port(_event_port_name(event.name)),),
        ),
    )


def _build_transition_block(transition: Transition, model: StateMachineModel) -> Policy:
    """Transition -> Policy: receives event + source state, emits target state.

    The transition policy evaluates the guard (if any) and produces
    a state update signal.
    """
    in_ports = [
        port(_event_port_name(transition.event)),
        port(_state_port_name(transition.source)),
    ]

    return Policy(
        name=_transition_block_name(transition.name),
        interface=Interface(
            forward_in=tuple(in_ports),
            forward_out=(port(_state_port_name(transition.target)),),
        ),
    )


def _build_state_mechanism(state: State, model: StateMachineModel) -> Mechanism:
    """State -> Mechanism: receives transition outputs, emits state value.

    Collects all transitions that target this state as inputs.
    """
    in_ports = []
    for t in model.transitions:
        if t.target == state.name:
            in_ports.append(port(_state_port_name(state.name)))
            break  # One port per target state is sufficient

    # Also collect transitions that source from this state (for guard eval)
    # But these go via temporal loop, not forward_in

    return Mechanism(
        name=_state_mech_name(state.name),
        interface=Interface(
            forward_in=tuple(in_ports),
            forward_out=(port(_state_port_name(state.name)),),
        ),
        updates=[(state.name, "value")],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_state_entity(state: State) -> Entity:
    """Create an Entity with a 'value' state variable for a state."""
    return Entity(
        name=state.name,
        variables={
            "value": StateVariable(
                name="value",
                typedef=StateType,
                description=f"Current value of state {state.name}",
            ),
        },
        description=f"State entity for {state.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: StateMachineModel) -> Block:
    """Build the tiered composition with temporal loop.

    Structure:
        (events |) >> (transitions |) >> (state_mechs |)
            .loop([state -> transition inputs])
    """
    event_blocks = [_build_event_block(e) for e in model.events]
    transition_blocks = [_build_transition_block(t, model) for t in model.transitions]
    state_blocks = [_build_state_mechanism(s, model) for s in model.states]

    # If regions exist, group state mechanisms by region using parallel comp
    if model.regions:
        region_groups: list[Block] = []
        assigned_states: set[str] = set()
        for region in model.regions:
            region_mechs = [
                _build_state_mechanism(s, model)
                for s in model.states
                if s.name in region.states
            ]
            if region_mechs:
                region_groups.append(parallel_tier(region_mechs))
                assigned_states.update(region.states)

        # Unassigned states
        unassigned = [
            _build_state_mechanism(s, model)
            for s in model.states
            if s.name not in assigned_states
        ]
        if unassigned:
            region_groups.extend(unassigned)

        if region_groups:
            state_blocks_for_tier = region_groups
        else:
            state_blocks_for_tier = state_blocks
    else:
        state_blocks_for_tier = state_blocks  # type: ignore[assignment]

    # Build tiers
    tiers: list[tuple[Block, list[Block]]] = []
    if event_blocks:
        tiers.append((parallel_tier(event_blocks), event_blocks))
    if transition_blocks:
        tiers.append((parallel_tier(transition_blocks), transition_blocks))
    if state_blocks_for_tier:
        state_tier = (
            parallel_tier(state_blocks_for_tier)
            if len(state_blocks_for_tier) > 1
            else state_blocks_for_tier[0]
        )
        tiers.append((state_tier, state_blocks))

    if not tiers:
        return parallel_tier(state_blocks)

    # Sequential across tiers
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: state values feed back to transitions at t+1
    temporal_wirings: list[Wiring] = []
    for state in model.states:
        state_bname = _state_mech_name(state.name)
        state_port = _state_port_name(state.name)

        for t in model.transitions:
            if t.source == state.name:
                temporal_wirings.append(
                    Wiring(
                        source_block=state_bname,
                        source_port=state_port,
                        target_block=_transition_block_name(t.name),
                        target_port=state_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_sm(model: StateMachineModel) -> GDSSpec:
    """Compile a StateMachineModel into a GDSSpec."""
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(EventType, StateType)

    # 2. Register spaces
    spec.collect(EventSpace, StateSpace)

    # 3. Register entities (one per state)
    for state in model.states:
        spec.register_entity(_build_state_entity(state))

    # 4. Register blocks
    for event in model.events:
        spec.register_block(_build_event_block(event))

    for t in model.transitions:
        spec.register_block(_build_transition_block(t, model))

    for state in model.states:
        spec.register_block(_build_state_mechanism(state, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for t in model.transitions:
        wires.append(
            Wire(
                source=t.event,
                target=_transition_block_name(t.name),
                space="SM EventSpace",
            )
        )
        wires.append(
            Wire(
                source=_transition_block_name(t.name),
                target=_state_mech_name(t.target),
                space="SM StateSpace",
            )
        )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for state machine {model.name!r}",
        )
    )

    return spec


def compile_sm_to_system(model: StateMachineModel) -> SystemIR:
    """Compile a StateMachineModel directly to SystemIR."""
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
