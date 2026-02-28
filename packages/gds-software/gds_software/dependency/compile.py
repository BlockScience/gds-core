"""Compiler: DependencyModel -> GDSSpec -> SystemIR.

Composition tree:
    (layer_0 |) >> (layer_1 |) >> (layer_2 |) ...
    Ordered by layer depth. Stateless — no temporal loops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.roles import Policy
from gds.compiler.compile import compile_system
from gds.ir.models import SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

from gds_software.common.compile_utils import (
    build_inter_tier_wirings,
    parallel_tier,
    sequential_with_explicit_wiring,
)
from gds_software.dependency.elements import Module

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_software.dependency.model import DependencyModel


# ── Semantic types ───────────────────────────────────────────

ModuleType = TypeDef(
    name="DG Module",
    python_type=dict,
    description="Module interface data in dependency graph",
)

ModuleSpace = Space(
    name="DG ModuleSpace",
    fields={"value": ModuleType},
    description="Space for module dependency data",
)


# ── Port naming helpers ──────────────────────────────────────


def _module_port_name(name: str) -> str:
    return f"{name} Module"


# ── Block builders ───────────────────────────────────────────


def _build_module_block(mod: Module, model: DependencyModel) -> Policy:
    """Module -> Policy: receives deps, emits module signal.

    Stateless — dependency graphs are purely structural.
    """
    # Inbound: modules that this module depends on
    in_ports = []
    for dep in model.deps:
        if dep.source == mod.name:
            in_ports.append(port(_module_port_name(dep.target)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Policy(
        name=mod.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_module_port_name(mod.name)),),
        ),
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: DependencyModel) -> Block:
    """Build layered composition ordered by module layer depth.

    Structure: (layer_0 |) >> (layer_1 |) >> ...
    """
    # Group modules by layer
    layer_map: dict[int, list[Module]] = {}
    for mod in model.modules:
        layer_map.setdefault(mod.layer, []).append(mod)

    sorted_depths = sorted(layer_map.keys())

    tiers: list[tuple[Block, list[Block]]] = []
    for depth in sorted_depths:
        mods = layer_map[depth]
        blocks = [_build_module_block(m, model) for m in mods]
        tiers.append((parallel_tier(blocks), blocks))

    if not tiers:
        all_blocks = [_build_module_block(m, model) for m in model.modules]
        return parallel_tier(all_blocks)

    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = build_inter_tier_wirings(prev_blocks, next_blocks)
        root = sequential_with_explicit_wiring(root, next_tier, wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_dep(model: DependencyModel) -> GDSSpec:
    """Compile a DependencyModel into a GDSSpec."""
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(ModuleType)

    # 2. Register spaces
    spec.collect(ModuleSpace)

    # 3. Register blocks
    for mod in model.modules:
        spec.register_block(_build_module_block(mod, model))

    # 4. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for dep in model.deps:
        wires.append(Wire(source=dep.target, target=dep.source, space="DG ModuleSpace"))

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for dependency graph {model.name!r}",
        )
    )

    return spec


def compile_dep_to_system(model: DependencyModel) -> SystemIR:
    """Compile a DependencyModel directly to SystemIR."""
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
