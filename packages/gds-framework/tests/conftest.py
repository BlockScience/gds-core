"""Shared fixtures for GDS tests."""

import pytest

from gds.blocks.base import AtomicBlock
from gds.blocks.roles import Mechanism, Policy
from gds.ir.models import (
    BlockIR,
    FlowDirection,
    SystemIR,
    WiringIR,
)
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ── Composition algebra fixtures ────────────────────────────


@pytest.fixture
def block_a() -> AtomicBlock:
    return AtomicBlock(
        name="A",
        interface=Interface(forward_out=(port("Temperature"),)),
    )


@pytest.fixture
def block_b() -> AtomicBlock:
    return AtomicBlock(
        name="B",
        interface=Interface(
            forward_in=(port("Temperature"),),
            forward_out=(port("Command"),),
        ),
    )


@pytest.fixture
def block_c() -> AtomicBlock:
    return AtomicBlock(
        name="C",
        interface=Interface(
            forward_in=(port("Command"),),
            forward_out=(port("Output"),),
        ),
    )


@pytest.fixture
def block_unrelated() -> AtomicBlock:
    """Block whose tokens don't overlap with block_a's output."""
    return AtomicBlock(
        name="Unrelated",
        interface=Interface(forward_in=(port("Pressure"),)),
    )


@pytest.fixture
def block_sensor() -> AtomicBlock:
    return AtomicBlock(
        name="Temperature Sensor",
        interface=Interface(forward_out=(port("Temperature"),)),
    )


@pytest.fixture
def block_controller() -> AtomicBlock:
    return AtomicBlock(
        name="PID Controller",
        interface=Interface(
            forward_in=(port("Temperature"), port("Setpoint")),
            forward_out=(port("Heater Command"),),
            backward_in=(port("Energy Cost"),),
        ),
    )


@pytest.fixture
def block_plant() -> AtomicBlock:
    return AtomicBlock(
        name="Room",
        interface=Interface(
            forward_in=(port("Heater Command"),),
            forward_out=(port("Temperature"),),
            backward_out=(port("Energy Cost"),),
        ),
    )


@pytest.fixture
def sample_system_ir() -> SystemIR:
    return SystemIR(
        name="Sample",
        blocks=[
            BlockIR(name="A", signature=("", "Temperature", "", "")),
            BlockIR(name="B", signature=("Temperature", "Command", "", "")),
        ],
        wirings=[
            WiringIR(
                source="A",
                target="B",
                label="temperature",
                direction=FlowDirection.COVARIANT,
            )
        ],
    )


@pytest.fixture
def thermostat_system_ir() -> SystemIR:
    return SystemIR(
        name="Thermostat",
        blocks=[
            BlockIR(name="Sensor", signature=("", "Temperature", "", "")),
            BlockIR(
                name="Controller",
                signature=(
                    "Temperature + Setpoint",
                    "Heater Command",
                    "Energy Cost",
                    "",
                ),
            ),
            BlockIR(
                name="Room",
                signature=("Heater Command", "Temperature", "", "Energy Cost"),
            ),
        ],
        wirings=[
            WiringIR(
                source="Sensor",
                target="Controller",
                label="temperature",
                direction=FlowDirection.COVARIANT,
            ),
            WiringIR(
                source="Controller",
                target="Room",
                label="heater command",
                direction=FlowDirection.COVARIANT,
            ),
            WiringIR(
                source="Room",
                target="Controller",
                label="energy cost",
                direction=FlowDirection.CONTRAVARIANT,
                is_feedback=True,
            ),
        ],
    )


# ── Spec layer fixtures ────────────────────────────────────


@pytest.fixture
def typedef_population() -> TypeDef:
    return TypeDef(name="Population", python_type=int, constraint=lambda x: x >= 0)


@pytest.fixture
def typedef_rate() -> TypeDef:
    return TypeDef(name="Rate", python_type=float, constraint=lambda x: x > 0)


@pytest.fixture
def space_signal(typedef_population: TypeDef) -> Space:
    return Space(name="PreySignal", fields={"prey_count": typedef_population})


@pytest.fixture
def entity_prey(typedef_population: TypeDef) -> Entity:
    return Entity(
        name="Prey",
        variables={
            "population": StateVariable(
                name="population",
                typedef=typedef_population,
                symbol="N",
            )
        },
    )


@pytest.fixture
def sample_mechanism() -> Mechanism:
    return Mechanism(
        name="Update Prey",
        interface=Interface(forward_in=(port("Hunt Result"),)),
        updates=[("Prey", "population")],
        params_used=["birth_rate"],
    )


@pytest.fixture
def sample_spec(
    typedef_population: TypeDef,
    typedef_rate: TypeDef,
    space_signal: Space,
    entity_prey: Entity,
    sample_mechanism: Mechanism,
) -> GDSSpec:
    observe = Policy(
        name="Observe",
        interface=Interface(forward_out=(port("PreySignal"),)),
        params_used=["birth_rate"],
    )
    spec = GDSSpec(name="Predator-Prey")
    spec.register_type(typedef_population)
    spec.register_type(typedef_rate)
    spec.register_space(space_signal)
    spec.register_entity(entity_prey)
    spec.register_block(observe)
    spec.register_block(sample_mechanism)
    spec.register_parameter("birth_rate", typedef_rate)
    spec.register_wiring(
        SpecWiring(
            name="Hunt Cycle",
            block_names=["Observe", "Update Prey"],
            wires=[Wire(source="Observe", target="Update Prey")],
        )
    )
    return spec
