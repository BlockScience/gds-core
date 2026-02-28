"""Compiler: SupplyChainModel -> GDSSpec -> SystemIR.

Two public functions:
- compile_scn(model) -> GDSSpec: registers types, spaces, entities, blocks, wirings
- compile_scn_to_system(model) -> SystemIR: builds composition tree and compiles

Composition tree:
    (demands |) >> (policies |) >> (node_mechanisms |)
        .loop([inventory -> policies])
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
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    SupplyNode,
)

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_business.supplychain.model import SupplyChainModel


# ── Semantic type definitions ────────────────────────────────

InventoryType = TypeDef(
    name="SCN Inventory",
    python_type=float,
    description="Inventory level at a supply node",
)

ShipmentRateType = TypeDef(
    name="SCN ShipmentRate",
    python_type=float,
    description="Rate of material flow between nodes",
)

DemandType = TypeDef(
    name="SCN Demand",
    python_type=float,
    description="Exogenous demand signal",
)


# ── Semantic spaces ──────────────────────────────────────────

InventorySpace = Space(
    name="SCN InventorySpace",
    fields={"level": InventoryType},
    description="Space for node inventory levels",
)

ShipmentRateSpace = Space(
    name="SCN ShipmentRateSpace",
    fields={"rate": ShipmentRateType},
    description="Space for shipment flow rates",
)

DemandSpace = Space(
    name="SCN DemandSpace",
    fields={"demand": DemandType},
    description="Space for demand signals",
)


# ── Port naming helpers ──────────────────────────────────────


def _inventory_port_name(name: str) -> str:
    return f"{name} Inventory"


def _rate_port_name(name: str) -> str:
    return f"{name} Rate"


def _signal_port_name(name: str) -> str:
    return f"{name} Signal"


def _mechanism_block_name(name: str) -> str:
    return f"{name} Mechanism"


# ── Block builders ───────────────────────────────────────────


def _build_demand_block(demand: DemandSource) -> BoundaryAction:
    """DemandSource -> BoundaryAction: emits demand signal."""
    return BoundaryAction(
        name=demand.name,
        interface=Interface(
            forward_out=(port(_signal_port_name(demand.name)),),
        ),
    )


def _build_policy_block(policy: OrderPolicy, model: SupplyChainModel) -> Policy:
    """OrderPolicy -> Policy: receives demand + inventory signals, emits rate.

    Collects demand signals targeting this policy's node and inventory
    signals from observed nodes.
    """
    in_ports = []

    # Demand signals targeting this policy's node
    for d in model.demand_sources:
        if d.target_node == policy.node:
            in_ports.append(port(_signal_port_name(d.name)))

    # Inventory signals from observed nodes
    for inp in policy.inputs:
        in_ports.append(port(_inventory_port_name(inp)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Policy(
        name=policy.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_rate_port_name(policy.name)),),
        ),
    )


def _build_node_mechanism(node: SupplyNode, model: SupplyChainModel) -> Mechanism:
    """SupplyNode -> Mechanism: receives rates, updates inventory."""
    in_ports = []

    # Rates from order policies on this node
    for op in model.order_policies:
        if op.node == node.name:
            in_ports.append(port(_rate_port_name(op.name)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Mechanism(
        name=_mechanism_block_name(node.name),
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_inventory_port_name(node.name)),),
        ),
        updates=[(node.name, "inventory")],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_node_entity(node: SupplyNode) -> Entity:
    """Create an Entity with an 'inventory' state variable for a supply node."""
    return Entity(
        name=node.name,
        variables={
            "inventory": StateVariable(
                name="inventory",
                typedef=InventoryType,
                description=f"Inventory level at {node.name}",
            ),
        },
        description=f"State entity for supply node {node.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: SupplyChainModel) -> Block:
    """Build the tiered parallel-sequential composition with temporal loop.

    Structure:
        (demands |) >> (policies |) >> (node_mechanisms |)
            .loop([inventory -> policies])
    """
    demand_blocks = [_build_demand_block(d) for d in model.demand_sources]
    policy_blocks = [_build_policy_block(p, model) for p in model.order_policies]
    mechanism_blocks = [_build_node_mechanism(n, model) for n in model.nodes]

    # Build tiers
    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [demand_blocks, policy_blocks, mechanism_blocks]:
        if tier_blocks:
            tiers.append((parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        return parallel_tier(mechanism_blocks)

    # Sequential across tiers with explicit inter-tier wirings
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: inventory feeds back to policies at t+1
    temporal_wirings: list[Wiring] = []
    for node in model.nodes:
        mech_name = _mechanism_block_name(node.name)
        inv_port = _inventory_port_name(node.name)

        for policy in model.order_policies:
            # Check if this policy observes this node's inventory
            if node.name in policy.inputs:
                temporal_wirings.append(
                    Wiring(
                        source_block=mech_name,
                        source_port=inv_port,
                        target_block=policy.name,
                        target_port=inv_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_scn(model: SupplyChainModel) -> GDSSpec:
    """Compile a SupplyChainModel into a GDSSpec.

    Registers: types, spaces, entities, blocks, wirings.
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(InventoryType, ShipmentRateType, DemandType)

    # 2. Register spaces
    spec.collect(InventorySpace, ShipmentRateSpace, DemandSpace)

    # 3. Register entities (one per supply node)
    for node in model.nodes:
        spec.register_entity(_build_node_entity(node))

    # 4. Register blocks
    for d in model.demand_sources:
        spec.register_block(_build_demand_block(d))

    for p in model.order_policies:
        spec.register_block(_build_policy_block(p, model))

    for node in model.nodes:
        spec.register_block(_build_node_mechanism(node, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    # Demand -> Policy wires
    for d in model.demand_sources:
        for p in model.order_policies:
            if p.node == d.target_node:
                wires.append(
                    Wire(source=d.name, target=p.name, space="SCN DemandSpace")
                )

    # Policy -> Mechanism wires
    for p in model.order_policies:
        wires.append(
            Wire(
                source=p.name,
                target=_mechanism_block_name(p.node),
                space="SCN ShipmentRateSpace",
            )
        )

    # Mechanism -> Policy temporal wires (inventory feedback)
    for node in model.nodes:
        for p in model.order_policies:
            if node.name in p.inputs:
                wires.append(
                    Wire(
                        source=_mechanism_block_name(node.name),
                        target=p.name,
                        space="SCN InventorySpace",
                    )
                )

    if wires:
        spec.register_wiring(
            SpecWiring(
                name=f"{model.name} Wiring",
                block_names=all_block_names,
                wires=wires,
                description=f"Auto-generated wiring for SCN {model.name!r}",
            )
        )

    return spec


def compile_scn_to_system(model: SupplyChainModel) -> SystemIR:
    """Compile a SupplyChainModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
