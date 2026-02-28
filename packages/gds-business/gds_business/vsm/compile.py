"""Compiler: ValueStreamModel -> GDSSpec -> SystemIR.

Two public functions:
- compile_vsm(model) -> GDSSpec: registers types, spaces, entities, blocks, wirings
- compile_vsm_to_system(model) -> SystemIR: builds composition tree and compiles

Composition tree:
    (suppliers | customers) >> (steps |) >> (buffers |)
        .loop([buffer content -> steps]) if buffers exist
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

from gds_business.common.compile_utils import (
    build_inter_tier_wirings,
    parallel_tier,
    sequential_with_explicit_wiring,
)
from gds_business.vsm.elements import (
    Customer,
    InventoryBuffer,
    ProcessStep,
    Supplier,
)

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_business.vsm.model import ValueStreamModel


# ── Semantic type definitions ────────────────────────────────

MaterialType = TypeDef(
    name="VSM Material",
    python_type=dict,
    description="Material flow payload",
)

ProcessSignalType = TypeDef(
    name="VSM ProcessSignal",
    python_type=dict,
    description="Process step signal / kanban data",
)


# ── Semantic spaces ──────────────────────────────────────────

MaterialSpace = Space(
    name="VSM MaterialSpace",
    fields={"value": MaterialType},
    description="Space for material flow data",
)

ProcessSignalSpace = Space(
    name="VSM ProcessSignalSpace",
    fields={"value": ProcessSignalType},
    description="Space for process step signals",
)


# ── Port naming helpers ──────────────────────────────────────


def _material_port_name(name: str) -> str:
    return f"{name} Material"


def _content_port_name(name: str) -> str:
    return f"{name} Content"


def _supply_port_name(name: str) -> str:
    return f"{name} Supply"


def _demand_port_name(name: str) -> str:
    return f"{name} Demand"


def _buffer_block_name(name: str) -> str:
    return f"{name} Buffer"


# ── Block builders ───────────────────────────────────────────


def _build_supplier_block(supplier: Supplier) -> BoundaryAction:
    """Supplier -> BoundaryAction: emits supply signal."""
    return BoundaryAction(
        name=supplier.name,
        interface=Interface(
            forward_out=(port(_supply_port_name(supplier.name)),),
        ),
    )


def _build_customer_block(customer: Customer) -> BoundaryAction:
    """Customer -> BoundaryAction: emits demand signal."""
    return BoundaryAction(
        name=customer.name,
        interface=Interface(
            forward_out=(port(_demand_port_name(customer.name)),),
        ),
    )


def _build_step_block(step: ProcessStep, model: ValueStreamModel) -> Policy:
    """ProcessStep -> Policy: receives material/signals, emits material.

    Collects inbound flows as input ports, outbound flows as output ports.
    """
    in_ports = []

    # Inbound material flows
    for flow in model.material_flows:
        if flow.target == step.name:
            src = flow.source
            if src in model.supplier_names:
                in_ports.append(port(_supply_port_name(src)))
            elif src in model.buffer_names:
                in_ports.append(port(_content_port_name(src)))
            else:
                in_ports.append(port(_material_port_name(src)))

    # Inbound information flows
    for flow in model.information_flows:
        if flow.target == step.name:
            src = flow.source
            if src in model.customer_names:
                in_ports.append(port(_demand_port_name(src)))
            elif src in model.buffer_names:
                in_ports.append(port(_content_port_name(src)))
            else:
                in_ports.append(port(_material_port_name(src)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Policy(
        name=step.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_material_port_name(step.name)),),
        ),
    )


def _build_buffer_mechanism(buf: InventoryBuffer, model: ValueStreamModel) -> Mechanism:
    """InventoryBuffer -> Mechanism: receives material, emits content."""
    in_ports = []

    # Material from upstream step
    upstream, _ = buf.between
    in_ports.append(port(_material_port_name(upstream)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Mechanism(
        name=_buffer_block_name(buf.name),
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_content_port_name(buf.name)),),
        ),
        updates=[(buf.name, "quantity")],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_buffer_entity(buf: InventoryBuffer) -> Entity:
    """Create an Entity with a 'quantity' state variable for a buffer."""
    return Entity(
        name=buf.name,
        variables={
            "quantity": StateVariable(
                name="quantity",
                typedef=MaterialType,
                description=f"Buffer quantity at {buf.name}",
            ),
        },
        description=f"State entity for buffer {buf.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: ValueStreamModel) -> Block:
    """Build the tiered parallel-sequential composition.

    Structure:
        (suppliers | customers) >> (steps |) >> (buffers |)
            .loop([buffer content -> steps]) if buffers exist
    """
    boundary_blocks = [_build_supplier_block(s) for s in model.suppliers] + [
        _build_customer_block(c) for c in model.customers
    ]
    step_blocks = [_build_step_block(s, model) for s in model.steps]
    buffer_blocks = [_build_buffer_mechanism(b, model) for b in model.buffers]

    # Build tiers
    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [boundary_blocks, step_blocks, buffer_blocks]:
        if tier_blocks:
            tiers.append((parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        return parallel_tier(step_blocks)

    # Sequential across tiers with explicit inter-tier wirings
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: buffer content feeds back to downstream steps at t+1
    temporal_wirings: list[Wiring] = []
    for buf in model.buffers:
        buf_bname = _buffer_block_name(buf.name)
        content_port = _content_port_name(buf.name)
        _, downstream = buf.between

        # Check if downstream step has the content port as input
        for step in model.steps:
            if step.name == downstream:
                temporal_wirings.append(
                    Wiring(
                        source_block=buf_bname,
                        source_port=content_port,
                        target_block=step.name,
                        target_port=content_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_vsm(model: ValueStreamModel) -> GDSSpec:
    """Compile a ValueStreamModel into a GDSSpec.

    Registers: types, spaces, entities, blocks, wirings.
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(MaterialType, ProcessSignalType)

    # 2. Register spaces
    spec.collect(MaterialSpace, ProcessSignalSpace)

    # 3. Register entities (one per buffer)
    for buf in model.buffers:
        spec.register_entity(_build_buffer_entity(buf))

    # 4. Register blocks
    for s in model.suppliers:
        spec.register_block(_build_supplier_block(s))

    for c in model.customers:
        spec.register_block(_build_customer_block(c))

    for step in model.steps:
        spec.register_block(_build_step_block(step, model))

    for buf in model.buffers:
        spec.register_block(_build_buffer_mechanism(buf, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for flow in model.material_flows:
        source = flow.source
        target = flow.target
        if source in model.buffer_names:
            source = _buffer_block_name(source)
        if target in model.buffer_names:
            target = _buffer_block_name(target)
        wires.append(Wire(source=source, target=target, space="VSM MaterialSpace"))

    for flow in model.information_flows:
        source = flow.source
        target = flow.target
        if source in model.buffer_names:
            source = _buffer_block_name(source)
        if target in model.buffer_names:
            target = _buffer_block_name(target)
        wires.append(Wire(source=source, target=target, space="VSM ProcessSignalSpace"))

    if wires:
        spec.register_wiring(
            SpecWiring(
                name=f"{model.name} Wiring",
                block_names=all_block_names,
                wires=wires,
                description=f"Auto-generated wiring for VSM {model.name!r}",
            )
        )

    return spec


def compile_vsm_to_system(model: ValueStreamModel) -> SystemIR:
    """Compile a ValueStreamModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
