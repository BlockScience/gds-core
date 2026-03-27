"""Shared fixtures for gds-owl tests."""

import pytest

import gds
from gds import (
    BoundaryAction,
    CanonicalGDS,
    GDSSpec,
    Mechanism,
    Policy,
    SystemIR,
    VerificationReport,
    compile_system,
    interface,
    project_canonical,
    verify,
)
from gds.types.typedef import TypeDef


@pytest.fixture()
def temperature_type() -> TypeDef:
    return gds.typedef("Temperature", float, units="celsius")


@pytest.fixture()
def heater_command_type() -> TypeDef:
    return gds.typedef("HeaterCommand", float)


@pytest.fixture()
def temp_entity(temperature_type: TypeDef) -> gds.Entity:
    return gds.entity("Room", temperature=gds.state_var(temperature_type, symbol="T"))


@pytest.fixture()
def sensor() -> BoundaryAction:
    return BoundaryAction(
        name="Sensor",
        interface=interface(forward_out=["Temperature"]),
    )


@pytest.fixture()
def controller() -> Policy:
    return Policy(
        name="Controller",
        interface=interface(forward_in=["Temperature"], forward_out=["Heater Command"]),
        params_used=["gain"],
    )


@pytest.fixture()
def heater() -> Mechanism:
    return Mechanism(
        name="Heater",
        interface=interface(forward_in=["Heater Command"]),
        updates=[("Room", "temperature")],
    )


@pytest.fixture()
def thermostat_spec(
    temperature_type: TypeDef,
    heater_command_type: TypeDef,
    temp_entity: gds.Entity,
    sensor: BoundaryAction,
    controller: Policy,
    heater: Mechanism,
) -> GDSSpec:
    temp_space = gds.space("TemperatureSpace", temperature=temperature_type)
    cmd_space = gds.space("CommandSpace", command=heater_command_type)
    gain_param = gds.ParameterDef(
        name="gain",
        typedef=gds.typedef("GainType", float),
        description="Controller gain",
    )

    spec = GDSSpec(name="thermostat", description="Simple thermostat system")
    spec.collect(
        temperature_type,
        heater_command_type,
        temp_space,
        cmd_space,
        temp_entity,
        sensor,
        controller,
        heater,
        gain_param,
    )
    spec.register_wiring(
        gds.SpecWiring(
            name="main",
            block_names=["Sensor", "Controller", "Heater"],
            wires=[
                gds.Wire(
                    source="Sensor",
                    target="Controller",
                    space="TemperatureSpace",
                ),
                gds.Wire(source="Controller", target="Heater", space="CommandSpace"),
            ],
            description="Main thermostat wiring",
        )
    )
    return spec


@pytest.fixture()
def thermostat_ir(
    sensor: BoundaryAction,
    controller: Policy,
    heater: Mechanism,
) -> SystemIR:
    system = sensor >> controller >> heater
    return compile_system("thermostat", system)


@pytest.fixture()
def thermostat_canonical(thermostat_spec: GDSSpec) -> CanonicalGDS:
    return project_canonical(thermostat_spec)


@pytest.fixture()
def thermostat_report(thermostat_ir: SystemIR) -> VerificationReport:
    return verify(thermostat_ir)
