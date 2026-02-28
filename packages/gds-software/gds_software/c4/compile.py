"""Compiler: C4Model -> GDSSpec -> SystemIR.

Composition tree:
    (persons | external_systems) >> (containers |) >> (databases |)
        .loop([db -> containers]) if stateful containers exist
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

from gds_software.c4.elements import C4Component, Container, ExternalSystem, Person
from gds_software.common.compile_utils import (
    build_inter_tier_wirings,
    parallel_tier,
    sequential_with_explicit_wiring,
)

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.c4.model import C4Model


# ── Semantic types ───────────────────────────────────────────

C4RequestType = TypeDef(
    name="C4 Request",
    python_type=dict,
    description="C4 request/response data",
)

C4StateType = TypeDef(
    name="C4 State",
    python_type=dict,
    description="C4 stateful container/component state",
)

C4RequestSpace = Space(
    name="C4 RequestSpace",
    fields={"value": C4RequestType},
    description="Space for C4 requests",
)

C4StateSpace = Space(
    name="C4 StateSpace",
    fields={"value": C4StateType},
    description="Space for C4 stateful data",
)


# ── Port naming helpers ──────────────────────────────────────


def _port_name(name: str) -> str:
    return f"{name} C4Port"


# ── Block builders ───────────────────────────────────────────


def _build_person_block(person: Person) -> BoundaryAction:
    return BoundaryAction(
        name=person.name,
        interface=Interface(
            forward_out=(port(_port_name(person.name)),),
        ),
    )


def _build_external_system_block(ext: ExternalSystem) -> BoundaryAction:
    return BoundaryAction(
        name=ext.name,
        interface=Interface(
            forward_out=(port(_port_name(ext.name)),),
        ),
    )


def _build_container_block(container: Container, model: C4Model) -> Policy | Mechanism:
    """Container -> Policy or Mechanism based on stateful flag."""
    # Inbound: relationships targeting this container
    in_ports = []
    for rel in model.relationships:
        if rel.target == container.name:
            in_ports.append(port(_port_name(rel.source)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    out_port = port(_port_name(container.name))

    if container.stateful:
        return Mechanism(
            name=container.name,
            interface=Interface(
                forward_in=tuple(unique_in),
                forward_out=(out_port,),
            ),
            updates=[(container.name, "data")],
        )
    return Policy(
        name=container.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(out_port,),
        ),
    )


def _build_component_block(comp: C4Component, model: C4Model) -> Policy | Mechanism:
    """C4Component -> Policy or Mechanism."""
    in_ports = []
    for rel in model.relationships:
        if rel.target == comp.name:
            in_ports.append(port(_port_name(rel.source)))

    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    out_port = port(_port_name(comp.name))

    if comp.stateful:
        return Mechanism(
            name=comp.name,
            interface=Interface(
                forward_in=tuple(unique_in),
                forward_out=(out_port,),
            ),
            updates=[(comp.name, "data")],
        )
    return Policy(
        name=comp.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(out_port,),
        ),
    )


def _build_entity(name: str) -> Entity:
    return Entity(
        name=name,
        variables={
            "data": StateVariable(
                name="data",
                typedef=C4StateType,
                description=f"State data of {name}",
            ),
        },
        description=f"State entity for {name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: C4Model) -> Block:
    """Build tiered composition.

    Structure:
        (persons | externals) >> (containers | components) >> (databases)
            .loop([db -> containers])
    """
    boundary_blocks: list[Block] = []
    for p in model.persons:
        boundary_blocks.append(_build_person_block(p))
    for e in model.external_systems:
        boundary_blocks.append(_build_external_system_block(e))

    stateless_blocks: list[Block] = []
    stateful_blocks: list[Block] = []

    for c in model.containers:
        block = _build_container_block(c, model)
        if isinstance(block, Mechanism):
            stateful_blocks.append(block)
        else:
            stateless_blocks.append(block)

    for comp in model.components:
        block = _build_component_block(comp, model)
        if isinstance(block, Mechanism):
            stateful_blocks.append(block)
        else:
            stateless_blocks.append(block)

    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [boundary_blocks, stateless_blocks, stateful_blocks]:
        if tier_blocks:
            tiers.append((parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        # Fallback
        all_blocks: list[Block] = []
        for c in model.containers:
            all_blocks.append(_build_container_block(c, model))
        return (
            parallel_tier(all_blocks)
            if all_blocks
            else Policy(
                name="empty",
                interface=Interface(forward_out=(port("empty"),)),
            )
        )

    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: stateful containers feed back to stateless ones
    temporal_wirings: list[Wiring] = []
    for rel in model.relationships:
        # Check if source is stateful and target is stateless
        stateful_names = {c.name for c in model.containers if c.stateful}
        stateful_names |= {c.name for c in model.components if c.stateful}
        if rel.source in stateful_names:
            for block in stateless_blocks:
                if block.name == rel.target:
                    temporal_wirings.append(
                        Wiring(
                            source_block=rel.source,
                            source_port=_port_name(rel.source),
                            target_block=rel.target,
                            target_port=_port_name(rel.source),
                            direction=FlowDirection.COVARIANT,
                        )
                    )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_c4(model: C4Model) -> GDSSpec:
    """Compile a C4Model into a GDSSpec."""
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(C4RequestType, C4StateType)

    # 2. Register spaces
    spec.collect(C4RequestSpace, C4StateSpace)

    # 3. Register entities for stateful containers/components
    for c in model.containers:
        if c.stateful:
            spec.register_entity(_build_entity(c.name))
    for c in model.components:
        if c.stateful:
            spec.register_entity(_build_entity(c.name))

    # 4. Register blocks
    for p in model.persons:
        spec.register_block(_build_person_block(p))
    for e in model.external_systems:
        spec.register_block(_build_external_system_block(e))
    for c in model.containers:
        spec.register_block(_build_container_block(c, model))
    for c in model.components:
        spec.register_block(_build_component_block(c, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for rel in model.relationships:
        wires.append(
            Wire(source=rel.source, target=rel.target, space="C4 RequestSpace")
        )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for C4 model {model.name!r}",
        )
    )

    return spec


def compile_c4_to_system(model: C4Model) -> SystemIR:
    """Compile a C4Model directly to SystemIR."""
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
