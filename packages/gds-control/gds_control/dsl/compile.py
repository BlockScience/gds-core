"""Compiler: ControlModel → GDSSpec → SystemIR.

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

from gds_control.dsl.elements import Controller, Input, Sensor, State

if TYPE_CHECKING:
    from gds.blocks.base import Block

    from gds_control.dsl.model import ControlModel


# ── Semantic type definitions ────────────────────────────────

StateType = TypeDef(
    name="State",
    python_type=float,
    description="Plant state variable",
)

ReferenceType = TypeDef(
    name="Reference",
    python_type=float,
    description="Exogenous reference/disturbance",
)

MeasurementType = TypeDef(
    name="Measurement",
    python_type=float,
    description="Sensor measurement",
)

ControlType = TypeDef(
    name="Control",
    python_type=float,
    description="Controller output",
)


# ── Semantic spaces ──────────────────────────────────────────

StateSpace = Space(
    name="StateSpace",
    fields={"value": StateType},
    description="Space for plant state values",
)

ReferenceSpace = Space(
    name="ReferenceSpace",
    fields={"value": ReferenceType},
    description="Space for exogenous reference/disturbance values",
)

MeasurementSpace = Space(
    name="MeasurementSpace",
    fields={"value": MeasurementType},
    description="Space for sensor measurement values",
)

ControlSpace = Space(
    name="ControlSpace",
    fields={"value": ControlType},
    description="Space for controller output values",
)


# ── Port naming helpers ──────────────────────────────────────


def _state_port_name(state_name: str) -> str:
    return f"{state_name} State"


def _reference_port_name(input_name: str) -> str:
    return f"{input_name} Reference"


def _measurement_port_name(sensor_name: str) -> str:
    return f"{sensor_name} Measurement"


def _control_port_name(controller_name: str) -> str:
    return f"{controller_name} Control"


def _dynamics_block_name(state_name: str) -> str:
    return f"{state_name} Dynamics"


# ── Block builders ───────────────────────────────────────────


def _build_input_block(inp: Input) -> BoundaryAction:
    """Input → BoundaryAction: no forward_in, emits Reference."""
    return BoundaryAction(
        name=inp.name,
        interface=Interface(
            forward_out=(port(_reference_port_name(inp.name)),),
        ),
        params_used=[inp.name],
    )


def _build_sensor_block(sensor: Sensor) -> Policy:
    """Sensor → Policy: receives State ports, emits Measurement."""
    forward_in_ports = []
    for obs_name in sensor.observes:
        forward_in_ports.append(port(_state_port_name(obs_name)))

    return Policy(
        name=sensor.name,
        interface=Interface(
            forward_in=tuple(forward_in_ports),
            forward_out=(port(_measurement_port_name(sensor.name)),),
        ),
    )


def _build_controller_block(ctrl: Controller, model: ControlModel) -> Policy:
    """Controller → Policy: receives Measurement/Reference ports, emits Control."""
    forward_in_ports = []
    params = []
    for read_name in ctrl.reads:
        if read_name in model.sensor_names:
            forward_in_ports.append(port(_measurement_port_name(read_name)))
        else:
            # Must be an input name
            forward_in_ports.append(port(_reference_port_name(read_name)))
            params.append(read_name)

    return Policy(
        name=ctrl.name,
        interface=Interface(
            forward_in=tuple(forward_in_ports),
            forward_out=(port(_control_port_name(ctrl.name)),),
        ),
        params_used=params if params else [],
    )


def _build_state_mechanism(state: State, model: ControlModel) -> Mechanism:
    """State → Mechanism: receives Control ports from driving controllers, emits State.

    forward_out emits State for temporal loop (feeds back to sensors at t+1).
    """
    control_ports = []
    for ctrl in model.controllers:
        if state.name in ctrl.drives:
            control_ports.append(port(_control_port_name(ctrl.name)))

    return Mechanism(
        name=_dynamics_block_name(state.name),
        interface=Interface(
            forward_in=tuple(control_ports),
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
                description=f"State variable for {state.name}",
            ),
        },
        description=f"State entity for {state.name!r}",
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
    """Build explicit wirings between two tiers based on port token overlap."""
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
    """Compose two tiers sequentially with explicit wiring."""
    if wiring:
        return StackComposition(
            name=f"{first.name} >> {second.name}",
            first=first,
            second=second,
            wiring=wiring,
        )
    return first >> second


def _build_composition_tree(model: ControlModel) -> Block:
    """Build the tiered parallel-sequential composition with temporal loop.

    Structure:
        (inputs | sensors) >> (controllers) >> (state_dynamics)
            .loop([state_dynamics forward_out → sensor forward_in])

    - Tier 1: Inputs + sensors in parallel. Sensor forward_in (state ports)
      are filled by temporal loop, not by sequential tier.
    - Tier 2: Controllers. forward_in receives measurement + reference from tier 1.
    - Tier 3: State dynamics mechanisms. forward_in receives control from tier 2.
    - Temporal loop: COVARIANT wirings from dynamics → sensors.
    """
    input_blocks = [_build_input_block(i) for i in model.inputs]
    sensor_blocks = [_build_sensor_block(s) for s in model.sensors]
    controller_blocks = [_build_controller_block(c, model) for c in model.controllers]
    state_blocks = [_build_state_mechanism(s, model) for s in model.states]

    # Build tiers as (parallel_block, atomic_blocks) pairs
    tiers: list[tuple[Block, list[Block]]] = []

    # Tier 1: inputs + sensors combined
    tier1_blocks = input_blocks + sensor_blocks
    if tier1_blocks:
        tiers.append((_parallel_tier(tier1_blocks), tier1_blocks))

    # Tier 2: controllers
    if controller_blocks:
        tiers.append((_parallel_tier(controller_blocks), controller_blocks))

    # Tier 3: state dynamics (always non-empty — model requires ≥1 state)
    tiers.append((_parallel_tier(state_blocks), state_blocks))

    # Sequential across tiers with explicit inter-tier wirings
    root, _ = tiers[0]
    for i in range(1, len(tiers)):
        next_tier, next_blocks = tiers[i]
        prev_blocks = tiers[i - 1][1]
        wirings = _build_inter_tier_wirings(prev_blocks, next_blocks)
        root = _sequential_with_explicit_wiring(root, next_tier, wirings)

    # Temporal loop: state outputs feed back to sensors at t+1
    temporal_wirings: list[Wiring] = []
    for state in model.states:
        dynamics_name = _dynamics_block_name(state.name)
        state_port = _state_port_name(state.name)

        for sensor in model.sensors:
            if state.name in sensor.observes:
                temporal_wirings.append(
                    Wiring(
                        source_block=dynamics_name,
                        source_port=state_port,
                        target_block=sensor.name,
                        target_port=state_port,
                        direction=FlowDirection.COVARIANT,
                    )
                )

    if temporal_wirings:
        root = root.loop(temporal_wirings)

    return root


# ── Public API ───────────────────────────────────────────────


def compile_model(model: ControlModel) -> GDSSpec:
    """Compile a ControlModel into a GDSSpec.

    Registers: types, spaces, entities, blocks, wirings, and parameters.
    """
    spec = GDSSpec(name=model.name, description=model.description)

    # 1. Register types
    spec.collect(StateType, ReferenceType, MeasurementType, ControlType)

    # 2. Register spaces
    spec.collect(StateSpace, ReferenceSpace, MeasurementSpace, ControlSpace)

    # 3. Register entities (one per state)
    for state in model.states:
        spec.register_entity(_build_state_entity(state))

    # 4. Register blocks
    for inp in model.inputs:
        spec.register_block(_build_input_block(inp))

    for sensor in model.sensors:
        spec.register_block(_build_sensor_block(sensor))

    for ctrl in model.controllers:
        spec.register_block(_build_controller_block(ctrl, model))

    for state in model.states:
        spec.register_block(_build_state_mechanism(state, model))

    # 5. Register spec wirings
    all_block_names = [b for b in spec.blocks]
    wires: list[Wire] = []

    # Controller → State dynamics wirings
    for ctrl in model.controllers:
        for drive in ctrl.drives:
            wires.append(
                Wire(
                    source=ctrl.name,
                    target=_dynamics_block_name(drive),
                    space="ControlSpace",
                )
            )

    spec.register_wiring(
        SpecWiring(
            name=f"{model.name} Wiring",
            block_names=all_block_names,
            wires=wires,
            description=(f"Auto-generated wiring for control model {model.name!r}"),
        )
    )

    # 6. Register inputs as parameters
    for inp in model.inputs:
        spec.register_parameter(
            ParameterDef(
                name=inp.name,
                typedef=ReferenceType,
                description=f"Exogenous input: {inp.name}",
            )
        )

    return spec


def compile_to_system(model: ControlModel) -> SystemIR:
    """Compile a ControlModel directly to SystemIR.

    Builds the composition tree and delegates to GDS compile_system().
    """
    root = _build_composition_tree(model)
    return compile_system(model.name, root)
