"""Compiler: StockFlowModel → GDSSpec → SystemIR.

Two public functions:
- compile_model(model) → GDSSpec: registers types, spaces, entities, blocks, wirings
- compile_to_system(model) → SystemIR: builds composition tree and compiles to flat IR

The composition tree is built once and reused — no divergence between spec
wirings and system wirings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.composition import StackComposition, Wiring
from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.parameters import ParameterDef
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from stockflow.dsl.model import StockFlowModel


# ── Semantic type definitions ────────────────────────────────

LevelType = TypeDef(
    name="Level",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Stock accumulation level (non-negative)",
    units="units",
)

UnconstrainedLevelType = TypeDef(
    name="UnconstrainedLevel",
    python_type=float,
    description="Stock accumulation level (may be negative)",
    units="units",
)

RateType = TypeDef(
    name="Rate",
    python_type=float,
    description="Flow rate of change",
    units="units/time",
)

SignalType = TypeDef(
    name="Signal",
    python_type=float,
    description="Auxiliary/converter signal value",
)


# ── Semantic spaces ──────────────────────────────────────────

LevelSpace = Space(
    name="LevelSpace",
    fields={"value": LevelType},
    description="Space for stock level values (non-negative)",
)

UnconstrainedLevelSpace = Space(
    name="UnconstrainedLevelSpace",
    fields={"value": UnconstrainedLevelType},
    description="Space for stock level values (may be negative)",
)

RateSpace = Space(
    name="RateSpace",
    fields={"value": RateType},
    description="Space for flow rate values",
)

SignalSpace = Space(
    name="SignalSpace",
    fields={"value": SignalType},
    description="Space for auxiliary/converter signal values",
)


# ── Port naming helpers ──────────────────────────────────────


def _stock_level_port_name(stock_name: str) -> str:
    return f"{stock_name} Level"


def _flow_rate_port_name(flow_name: str) -> str:
    return f"{flow_name} Rate"


def _signal_port_name(name: str) -> str:
    return f"{name} Signal"


def _accumulation_block_name(stock_name: str) -> str:
    return f"{stock_name} Accumulation"


# ── Block builders ───────────────────────────────────────────


def _build_converter_block(conv: Converter) -> BoundaryAction:
    """Converter → BoundaryAction: no forward_in, emits Signal."""
    return BoundaryAction(
        name=conv.name,
        interface=Interface(
            forward_out=(port(_signal_port_name(conv.name)),),
        ),
    )


def _build_auxiliary_block(aux: Auxiliary, model: StockFlowModel) -> Policy:
    """Auxiliary → Policy: receives Level/Signal ports, emits Signal."""
    forward_in_ports = []
    for inp_name in aux.inputs:
        if inp_name in model.stock_names:
            forward_in_ports.append(port(_stock_level_port_name(inp_name)))
        else:
            forward_in_ports.append(port(_signal_port_name(inp_name)))

    return Policy(
        name=aux.name,
        interface=Interface(
            forward_in=tuple(forward_in_ports),
            forward_out=(port(_signal_port_name(aux.name)),),
        ),
    )


def _build_flow_block(flow: Flow, model: StockFlowModel) -> Policy:
    """Flow → Policy: emits Rate.

    Flow blocks are pure rate producers in the sequential tier. Source stock
    levels arrive via temporal loop (.loop() wiring), NOT through the
    sequential tier — this avoids token overlap issues in the composition.
    """
    return Policy(
        name=flow.name,
        interface=Interface(
            forward_out=(port(_flow_rate_port_name(flow.name)),),
        ),
    )


def _build_stock_mechanism(stock: Stock, model: StockFlowModel) -> Mechanism:
    """Stock → Mechanism: receives Rate ports from flows, emits Level.

    The mechanism accumulates flow rates into the stock level.
    forward_out emits Level for temporal loop (feeds back to next timestep).
    """
    # Collect all flows that target or source this stock
    rate_ports = []
    for flow in model.flows:
        if flow.target == stock.name or flow.source == stock.name:
            rate_ports.append(port(_flow_rate_port_name(flow.name)))

    return Mechanism(
        name=_accumulation_block_name(stock.name),
        interface=Interface(
            forward_in=tuple(rate_ports),
            forward_out=(port(_stock_level_port_name(stock.name)),),
        ),
        updates=[(stock.name, "level")],
    )


# ── Entity builder ───────────────────────────────────────────


def _build_stock_entity(stock: Stock) -> Entity:
    """Create an Entity with a 'level' state variable for a stock."""
    level_td = LevelType if stock.non_negative else UnconstrainedLevelType
    return Entity(
        name=stock.name,
        variables={
            "level": StateVariable(
                name="level",
                typedef=level_td,
                description=f"Accumulated level of {stock.name}",
            ),
        },
        description=f"State entity for stock {stock.name!r}",
    )


# ── Composition tree builder ────────────────────────────────


def _parallel_tier(blocks: list[Block]) -> Block:
    """Compose a list of blocks in parallel."""
    tier: Block = blocks[0]
    for b in blocks[1:]:
        tier = tier | b
    return tier


def _build_inter_tier_wirings(
    first_tier_blocks: list[Block],
    second_tier_blocks: list[Block],
) -> list[Wiring]:
    """Build explicit wirings between two tiers based on port token overlap.

    For each output port in the first tier, find matching input ports in the
    second tier (by token intersection). This replaces auto-wiring so we can
    use explicit StackComposition and bypass the token overlap validator.
    """
    wirings: list[Wiring] = []
    for first_block in first_tier_blocks:
        for out_port in first_block.interface.forward_out:
            for second_block in second_tier_blocks:
                for in_port in second_block.interface.forward_in:
                    if out_port.type_tokens & in_port.type_tokens:
                        wirings.append(
                            Wiring(
                                source_block=first_block.name,
                                source_port=out_port.name,
                                target_block=second_block.name,
                                target_port=in_port.name,
                            )
                        )
    return wirings


def _sequential_with_explicit_wiring(
    first: Block,
    second: Block,
    wiring: list[Wiring],
) -> Block:
    """Compose two tiers sequentially with explicit wiring.

    Uses StackComposition directly to bypass the auto-wire token overlap check.
    If no wirings found, falls back to auto-wiring via >>.
    """
    if wiring:
        return StackComposition(
            name=f"{first.name} >> {second.name}",
            first=first,
            second=second,
            wiring=wiring,
        )
    # No wirings needed (e.g. second tier has no forward_in) — >> is safe
    return first >> second


def _build_composition_tree(model: StockFlowModel) -> Block:
    """Build the tiered parallel-sequential composition with temporal loop.

    Structure:
        (converters |) >> (auxiliaries |) >> (flows |) >> (stock_mechanisms |)
            .loop([stock level → aux/flow inputs])

    Empty tiers are skipped. Within each tier: parallel (|).
    Across tiers: sequential (>>) with explicit wirings to avoid false
    token overlap failures. Wrapped in .loop() for temporal recurrence.
    """
    converter_blocks = [_build_converter_block(c) for c in model.converters]
    auxiliary_blocks = [_build_auxiliary_block(a, model) for a in model.auxiliaries]
    flow_blocks = [_build_flow_block(f, model) for f in model.flows]
    stock_blocks = [_build_stock_mechanism(s, model) for s in model.stocks]

    # Build tiers as (parallel_block, atomic_blocks) pairs
    tiers: list[tuple[Block, list[Block]]] = []
    for tier_blocks in [converter_blocks, auxiliary_blocks, flow_blocks, stock_blocks]:
        if tier_blocks:
            tiers.append((_parallel_tier(tier_blocks), tier_blocks))

    if not tiers:
        return _parallel_tier(stock_blocks)

    # Sequential across tiers with explicit inter-tier wirings
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = _build_inter_tier_wirings(prev_blocks, next_blocks)
        root = _sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: stock levels feed back to auxiliaries/flows at t+1
    temporal_wirings: list[Wiring] = []
    for stock in model.stocks:
        stock_block_name = _accumulation_block_name(stock.name)
        level_port = _stock_level_port_name(stock.name)

        # Temporal wirings go to auxiliaries only — they have the matching
        # forward_in port. Flows are self-contained rate producers; source
        # stock level dependency is captured structurally via the flow
        # declaration, not as a port connection.
        for aux in model.auxiliaries:
            if stock.name in aux.inputs:
                temporal_wirings.append(
                    Wiring(
                        source_block=stock_block_name,
                        source_port=level_port,
                        target_block=aux.name,
                        target_port=level_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_model(model: StockFlowModel) -> GDSSpec:
    """Compile a StockFlowModel into a GDSSpec.

    Registers: types, spaces, entities, blocks, wirings, and parameters.
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(LevelType, UnconstrainedLevelType, RateType, SignalType)

    # 2. Register spaces
    spec.collect(LevelSpace, UnconstrainedLevelSpace, RateSpace, SignalSpace)

    # 3. Register entities (one per stock)
    for stock in model.stocks:
        spec.register_entity(_build_stock_entity(stock))

    # 4. Register blocks
    for conv in model.converters:
        spec.register_block(_build_converter_block(conv))

    for aux in model.auxiliaries:
        spec.register_block(_build_auxiliary_block(aux, model))

    for flow in model.flows:
        spec.register_block(_build_flow_block(flow, model))

    for stock in model.stocks:
        spec.register_block(_build_stock_mechanism(stock, model))

    # 5. Register spec wirings (document the composition structure)
    all_block_names = [b.name for b in spec.blocks.values()]
    wires: list[Wire] = []

    # Flow → Stock mechanism wirings
    for flow in model.flows:
        if flow.target:
            wires.append(
                Wire(
                    source=flow.name,
                    target=_accumulation_block_name(flow.target),
                    space="RateSpace",
                )
            )
        if flow.source:
            wires.append(
                Wire(
                    source=flow.name,
                    target=_accumulation_block_name(flow.source),
                    space="RateSpace",
                )
            )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=f"Auto-generated wiring for stock-flow model {model.name!r}",
        )
    )

    # 6. Register converters as parameters
    for conv in model.converters:
        spec.register_parameter(
            ParameterDef(
                name=conv.name,
                typedef=SignalType,
                description=f"Exogenous parameter: {conv.name}",
            )
        )

    return spec


def compile_to_system(model: StockFlowModel) -> SystemIR:
    """Compile a StockFlowModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
