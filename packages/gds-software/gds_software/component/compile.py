"""Compiler: ComponentModel -> GDSSpec -> SystemIR.

Composition tree:
    (boundary_components |) >> (internal |) >> (stateful |)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
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
from gds_software.component.elements import Component

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.component.model import ComponentModel


# ── Semantic types ───────────────────────────────────────────

ComponentDataType = TypeDef(
    name="CP Data",
    python_type=dict,
    description="Component interface data",
)

ComponentStateType = TypeDef(
    name="CP State",
    python_type=dict,
    description="Stateful component internal state",
)

# ── Semantic spaces ──────────────────────────────────────────

ComponentDataSpace = Space(
    name="CP DataSpace",
    fields={"value": ComponentDataType},
    description="Space for component interface data",
)

ComponentStateSpace = Space(
    name="CP StateSpace",
    fields={"value": ComponentStateType},
    description="Space for stateful component state",
)


# ── Port naming helpers ──────────────────────────────────────


def _provides_port_name(iface: str) -> str:
    return f"{iface} + Provided"


def _requires_port_name(iface: str) -> str:
    return f"{iface} + Required"


# ── Block builders ───────────────────────────────────────────


def _is_boundary(comp: Component, model: ComponentModel) -> bool:
    """A component is boundary if it has no required interfaces."""
    return len(comp.requires) == 0 and not comp.stateful


def _build_component_block(
    comp: Component, model: ComponentModel
) -> BoundaryAction | Policy | Mechanism:
    """Component -> appropriate GDS role based on properties."""
    in_ports = tuple(port(_requires_port_name(r)) for r in comp.requires)
    out_ports = tuple(port(_provides_port_name(p)) for p in comp.provides)

    # Ensure at least one output port
    if not out_ports:
        out_ports = (port(f"{comp.name} Output"),)

    if _is_boundary(comp, model):
        return BoundaryAction(
            name=comp.name,
            interface=Interface(forward_out=out_ports),
        )
    elif comp.stateful:
        return Mechanism(
            name=comp.name,
            interface=Interface(forward_in=in_ports, forward_out=out_ports),
            updates=[(comp.name, "state")],
        )
    else:
        return Policy(
            name=comp.name,
            interface=Interface(forward_in=in_ports, forward_out=out_ports),
        )


def _build_component_entity(comp: Component) -> Entity:
    """Create Entity for a stateful component."""
    return Entity(
        name=comp.name,
        variables={
            "state": StateVariable(
                name="state",
                typedef=ComponentStateType,
                description=f"Internal state of {comp.name}",
            ),
        },
        description=f"State entity for component {comp.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: ComponentModel) -> Block:
    """Build tiered composition.

    Structure:
        (boundary |) >> (internal_stateless |) >> (stateful |)
    """
    boundary_blocks = []
    internal_blocks = []
    stateful_blocks = []

    for comp in model.components:
        block = _build_component_block(comp, model)
        if isinstance(block, BoundaryAction):
            boundary_blocks.append(block)
        elif isinstance(block, Mechanism):
            stateful_blocks.append(block)
        else:
            internal_blocks.append(block)

    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [boundary_blocks, internal_blocks, stateful_blocks]:
        if tier_blocks:
            tiers.append((parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        # Fallback: all components as one tier
        all_blocks = [_build_component_block(c, model) for c in model.components]
        return parallel_tier(all_blocks)

    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_component(model: ComponentModel) -> GDSSpec:
    """Compile a ComponentModel into a GDSSpec."""
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(ComponentDataType, ComponentStateType)

    # 2. Register spaces
    spec.collect(ComponentDataSpace, ComponentStateSpace)

    # 3. Register entities for stateful components
    for comp in model.components:
        if comp.stateful:
            spec.register_entity(_build_component_entity(comp))

    # 4. Register blocks
    for comp in model.components:
        spec.register_block(_build_component_block(comp, model))

    # 5. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for conn in model.connectors:
        wires.append(
            Wire(
                source=conn.source,
                target=conn.target,
                space="CP DataSpace",
            )
        )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for component diagram {model.name!r}",
        )
    )

    return spec


def compile_component_to_system(model: ComponentModel) -> SystemIR:
    """Compile a ComponentModel directly to SystemIR."""
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
