"""Compiler: CausalLoopModel -> GDSSpec -> SystemIR.

Two public functions:
- compile_cld(model) -> GDSSpec: registers types, spaces, blocks, wirings
- compile_cld_to_system(model) -> SystemIR: builds composition tree and compiles

Composition tree:
    (all_variables |) — single parallel tier, stateless
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

from gds_business.cld.elements import Variable
from gds_business.common.compile_utils import parallel_tier

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_business.cld.model import CausalLoopModel


# ── Semantic type definitions ────────────────────────────────

SignalType = TypeDef(
    name="CLD Signal",
    python_type=dict,
    description="Causal loop variable signal",
)


# ── Semantic spaces ──────────────────────────────────────────

SignalSpace = Space(
    name="CLD SignalSpace",
    fields={"value": SignalType},
    description="Space for causal loop variable signals",
)


# ── Port naming helpers ──────────────────────────────────────


def _signal_port_name(name: str) -> str:
    return f"{name} Signal"


# ── Block builders ───────────────────────────────────────────


def _build_variable_block(var: Variable, model: CausalLoopModel) -> Policy:
    """Variable -> Policy: receives inbound signals, emits outbound signal.

    All variables are pure signal relays — no state.
    """
    # Inbound: links where this variable is the target
    in_ports = []
    for link in model.links:
        if link.target == var.name:
            in_ports.append(port(_signal_port_name(link.source)))

    # Deduplicate
    seen: set[str] = set()
    unique_in = []
    for p in in_ports:
        if p.name not in seen:
            unique_in.append(p)
            seen.add(p.name)

    return Policy(
        name=var.name,
        interface=Interface(
            forward_in=tuple(unique_in),
            forward_out=(port(_signal_port_name(var.name)),),
        ),
    )


# ── Composition tree builder ────────────────────────────────


def _build_composition_tree(model: CausalLoopModel) -> Block:
    """Build single parallel tier of all variables.

    Structure: (all_variables |) — stateless, no sequential chaining.
    """
    blocks = [_build_variable_block(v, model) for v in model.variables]
    return parallel_tier(blocks)


# ── Public API ───────────────────────────────────────────────


def compile_cld(model: CausalLoopModel) -> GDSSpec:
    """Compile a CausalLoopModel into a GDSSpec.

    Registers: types, spaces, blocks, wirings. No entities (stateless).
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(SignalType)

    # 2. Register spaces
    spec.collect(SignalSpace)

    # 3. Register blocks (all Policy)
    for var in model.variables:
        spec.register_block(_build_variable_block(var, model))

    # 4. Register spec wirings
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    for link in model.links:
        wires.append(
            Wire(source=link.source, target=link.target, space="CLD SignalSpace")
        )

    if wires:
        spec.register_wiring(
            SpecWiring(
                name=f"{model.name} Wiring",
                block_names=all_block_names,
                wires=wires,
                description=f"Auto-generated wiring for CLD {model.name!r}",
            )
        )

    return spec


def compile_cld_to_system(model: CausalLoopModel) -> SystemIR:
    """Compile a CausalLoopModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
