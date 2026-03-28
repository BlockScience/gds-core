"""Shared fixtures for gds-analysis tests."""

import math

import gds
import pytest
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    interface,
)
from gds.constraints import AdmissibleInputConstraint, StateMetric


@pytest.fixture()
def thermostat_spec() -> GDSSpec:
    """Thermostat spec with structural annotations."""
    temp_type = gds.typedef("Temperature", float, units="celsius")
    cmd_type = gds.typedef("HeaterCommand", float)

    temp_space = gds.space("TemperatureSpace", temperature=temp_type)
    entity = gds.entity("Room", temperature=gds.state_var(temp_type, symbol="T"))

    sensor = BoundaryAction(
        name="Sensor",
        interface=interface(forward_out=["Temperature"]),
    )
    controller = Policy(
        name="Controller",
        interface=interface(
            forward_in=["Temperature"],
            forward_out=["Heater Command"],
        ),
    )
    heater = Mechanism(
        name="Heater",
        interface=interface(forward_in=["Heater Command"]),
        updates=[("Room", "temperature")],
    )

    spec = GDSSpec(name="thermostat")
    spec.collect(
        temp_type,
        cmd_type,
        temp_space,
        entity,
        sensor,
        controller,
        heater,
    )
    spec.register_wiring(
        gds.SpecWiring(
            name="main",
            block_names=["Sensor", "Controller", "Heater"],
            wires=[
                gds.Wire(source="Sensor", target="Controller"),
                gds.Wire(source="Controller", target="Heater"),
            ],
        )
    )

    # Structural annotations
    spec.register_admissibility(
        AdmissibleInputConstraint(
            name="sensor_range",
            boundary_block="Sensor",
            depends_on=[("Room", "temperature")],
            constraint=lambda state, signal: (
                signal.get("temperature", 0) >= -50
                and signal.get("temperature", 0) <= 100
            ),
            description="Sensor reads must be in [-50, 100]",
        )
    )
    spec.register_state_metric(
        StateMetric(
            name="temp_distance",
            variables=[("Room", "temperature")],
            metric_type="euclidean",
            distance=lambda a, b: math.sqrt(
                sum((a.get(k, 0) - b.get(k, 0)) ** 2 for k in set(a) | set(b))
            ),
            description="Euclidean distance on temperature",
        )
    )

    return spec
