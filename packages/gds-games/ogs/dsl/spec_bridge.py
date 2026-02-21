"""Bridge from OGS Pattern to GDS GDSSpec for canonical projection.

Maps game-theoretic structure to GDS roles:
- All atomic games → Policy (games compute equilibria, not state updates)
- PatternInput → BoundaryAction (exogenous inputs crossing the boundary)
- No Mechanism blocks (games don't update persistent state)

This means canonical projection yields: g = all games, f = ∅, X = ∅.
The system is pure policy — h = g — which is semantically correct for
compositional game theory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.roles import BoundaryAction, Policy
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.types.interface import Interface, port

if TYPE_CHECKING:
    from ogs.dsl.pattern import Pattern


def compile_pattern_to_spec(pattern: Pattern) -> GDSSpec:
    """Compile an OGS Pattern into a GDSSpec for canonical projection.

    Maps each atomic game to a Policy block and each PatternInput to a
    BoundaryAction. Registers flows as SpecWirings. No entities or
    Mechanisms — games have no persistent state.
    """
    from ogs.dsl.games import AtomicGame

    spec = GDSSpec(
        name=pattern.name, description=f"GDS projection of OGS pattern {pattern.name!r}"
    )

    # 1. Flatten games and register as Policy blocks
    atomic_games: list[AtomicGame] = pattern.game.flatten()
    for game in atomic_games:
        policy = Policy(
            name=game.name,
            interface=game.interface,
        )
        spec.register_block(policy)

    # 2. Register PatternInputs as BoundaryAction blocks
    for inp in pattern.inputs:
        if inp.target_game and inp.flow_label:
            out_port_name = inp.flow_label
        else:
            out_port_name = inp.name

        boundary = BoundaryAction(
            name=inp.name,
            interface=Interface(
                forward_out=(port(out_port_name),),
            ),
        )
        spec.register_block(boundary)

    # 3. Register wirings from flows
    #    We compile the pattern to IR first to get the resolved flows
    #    (including auto-wired sequential flows).
    from ogs.dsl.compile import compile_to_ir

    ir = compile_to_ir(pattern)

    block_names = list(spec.blocks.keys())
    wires: list[Wire] = []
    for flow in ir.flows:
        # Only register wires between blocks we actually registered
        if flow.source in spec.blocks and flow.target in spec.blocks:
            wires.append(
                Wire(
                    source=flow.source,
                    target=flow.target,
                    space=f"{flow.label} Flow",
                )
            )

    if wires:
        spec.register_wiring(
            SpecWiring(
                name=f"{pattern.name} Wiring",
                block_names=block_names,
                wires=wires,
                description=f"Auto-generated wiring for pattern {pattern.name!r}",
            )
        )

    return spec
