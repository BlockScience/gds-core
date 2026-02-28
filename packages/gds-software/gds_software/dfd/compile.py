"""Compiler: DFDModel -> GDSSpec -> SystemIR.

Two public functions:
- compile_dfd(model) -> GDSSpec: registers types, spaces, entities, blocks, wirings
- compile_dfd_to_system(model) -> SystemIR: builds composition tree and compiles to flat IR

Composition tree:
    (externals |) >> (processes |) >> (store_mechanisms |)
        .loop([store content -> process inputs])
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
from gds_software.dfd.elements import DataStore, ExternalEntity, Process

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.dfd.model import DFDModel


# ── Semantic type definitions ────────────────────────────────

SignalType = TypeDef(
    name="DFD Signal",
    python_type=dict,
    description="External entity signal data",
)

DataType = TypeDef(
    name="DFD Data",
    python_type=dict,
    description="Data flow payload between processes",
)

ContentType = TypeDef(
    name="DFD Content",
    python_type=dict,
    description="Data store content",
)


# ── Semantic spaces ──────────────────────────────────────────

SignalSpace = Space(
    name="DFD SignalSpace",
    fields={"value": SignalType},
    description="Space for external entity signals",
)

DataSpace = Space(
    name="DFD DataSpace",
    fields={"value": DataType},
    description="Space for data flow payloads",
)

ContentSpace = Space(
    name="DFD ContentSpace",
    fields={"value": ContentType},
    description="Space for data store content",
)


# ── Port naming helpers ──────────────────────────────────────


def _signal_port_name(name: str) -> str:
    return f"{name} Signal"


def _data_port_name(name: str) -> str:
    return f"{name} Data"


def _content_port_name(name: str) -> str:
    return f"{name} Content"


def _store_block_name(name: str) -> str:
    return f"{name} Store"


# ── Block builders ───────────────────────────────────────────


def _build_external_block(ext: ExternalEntity) -> BoundaryAction:
    """ExternalEntity -> BoundaryAction: no forward_in, emits Signal."""
    return BoundaryAction(
        name=ext.name,
        interface=Interface(
            forward_out=(port(_signal_port_name(ext.name)),),
        ),
    )


def _build_process_block(proc: Process, model: DFDModel) -> Policy:
    """Process -> Policy: receives data from flows, emits data.

    Collects all inbound flow data as forward_in ports, and all outbound
    flow names as forward_out ports.
    """
    # Inbound: flows where this process is the target
    in_ports = []
    for flow in model.data_flows:
        if flow.target == proc.name:
            source = flow.source
            if source in model.external_names:
                in_ports.append(port(_signal_port_name(source)))
            elif source in model.store_names:
                in_ports.append(port(_content_port_name(source)))
            else:
                in_ports.append(port(_data_port_name(source)))

    # Outbound: flows where this process is the source
    out_ports = []
    for flow in model.data_flows:
        if flow.source == proc.name:
            target = flow.target
            if target in model.store_names:
                out_ports.append(port(_data_port_name(proc.name)))
            else:
                out_ports.append(port(_data_port_name(proc.name)))

    # Deduplicate ports by name
    seen_in: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen_in:
            unique_in.append(p)
            seen_in.add(p.name)

    seen_out: set[str] = set()
    unique_out = []
    for p in out_ports:
        if p.name not in seen_out:
            unique_out.append(p)
            seen_out.add(p.name)

    # Ensure at least one output port
    if not unique_out:
        unique_out.append(port(_data_port_name(proc.name)))

    return Policy(
        name=proc.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=tuple(unique_out),
        ),
    )


def _build_store_mechanism(store: DataStore, model: DFDModel) -> Mechanism:
    """DataStore -> Mechanism: receives write data, emits content.

    The mechanism stores data written by processes and emits content
    for temporal loop feedback.
    """
    # Inbound: flows where this store is the target
    in_ports = []
    for flow in model.data_flows:
        if flow.target == store.name:
            source = flow.source
            if source in model.process_names:
                in_ports.append(port(_data_port_name(source)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Mechanism(
        name=_store_block_name(store.name),
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_content_port_name(store.name)),),
        ),
        updates=[(store.name, "content")],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_store_entity(store: DataStore) -> Entity:
    """Create an Entity with a 'content' state variable for a data store."""
    return Entity(
        name=store.name,
        variables={
            "content": StateVariable(
                name="content",
                typedef=ContentType,
                description=f"Stored content of {store.name}",
            ),
        },
        description=f"State entity for data store {store.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: DFDModel) -> Block:
    """Build the tiered parallel-sequential composition with temporal loop.

    Structure:
        (externals |) >> (processes |) >> (store_mechanisms |)
            .loop([store content -> process inputs])

    Empty tiers are skipped. Within each tier: parallel (|).
    Across tiers: sequential (>>) with explicit wirings.
    """
    external_blocks = [_build_external_block(e) for e in model.external_entities]
    process_blocks = [_build_process_block(p, model) for p in model.processes]
    store_blocks = [_build_store_mechanism(s, model) for s in model.data_stores]

    # Build tiers
    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [external_blocks, process_blocks, store_blocks]:
        if tier_blocks:
            tiers.append((parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        return parallel_tier(process_blocks)

    # Sequential across tiers with explicit inter-tier wirings
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: store content feeds back to processes at t+1
    temporal_wirings: list[Wiring] = []
    for store in model.data_stores:
        store_bname = _store_block_name(store.name)
        content_port = _content_port_name(store.name)

        for proc in model.processes:
            # Check if any flow goes from store to process
            has_flow = any(
                f.source == store.name and f.target == proc.name
                for f in model.data_flows
            )
            if has_flow:
                temporal_wirings.append(
                    Wiring(
                        source_block=store_bname,
                        source_port=content_port,
                        target_block=proc.name,
                        target_port=content_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_dfd(model: DFDModel) -> GDSSpec:
    """Compile a DFDModel into a GDSSpec.

    Registers: types, spaces, entities, blocks, wirings.
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(SignalType, DataType, ContentType)

    # 2. Register spaces
    spec.collect(SignalSpace, DataSpace, ContentSpace)

    # 3. Register entities (one per data store)
    for store in model.data_stores:
        spec.register_entity(_build_store_entity(store))

    # 4. Register blocks
    for ext in model.external_entities:
        spec.register_block(_build_external_block(ext))

    for proc in model.processes:
        spec.register_block(_build_process_block(proc, model))

    for store in model.data_stores:
        spec.register_block(_build_store_mechanism(store, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for flow in model.data_flows:
        source_block = flow.source
        target_block = flow.target
        # Determine the space based on source type
        if flow.source in model.external_names:
            space = "DFD SignalSpace"
        elif flow.source in model.store_names:
            space = "DFD ContentSpace"
            source_block = _store_block_name(flow.source)
        else:
            space = "DFD DataSpace"

        if flow.target in model.store_names:
            target_block = _store_block_name(flow.target)

        wires.append(Wire(source=source_block, target=target_block, space=space))

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for DFD {model.name!r}",
        )
    )

    return spec


def compile_dfd_to_system(model: DFDModel) -> SystemIR:
    """Compile a DFDModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
