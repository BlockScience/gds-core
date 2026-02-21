"""Tests for ControlModel → GDSSpec and SystemIR compilation."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy

from gds_control.dsl.compile import (
    StateType,
    compile_model,
    compile_to_system,
)
from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.model import ControlModel


@pytest.fixture
def siso_model():
    return ControlModel(
        name="SISO",
        states=[State(name="x")],
        inputs=[Input(name="r")],
        sensors=[Sensor(name="y", observes=["x"])],
        controllers=[Controller(name="K", reads=["y", "r"], drives=["x"])],
    )


@pytest.fixture
def siso_spec(siso_model):
    return compile_model(siso_model)


@pytest.fixture
def siso_ir(siso_model):
    return compile_to_system(siso_model)


class TestSpecRegistration:
    def test_type_count(self, siso_spec):
        assert len(siso_spec.types) == 4

    def test_space_count(self, siso_spec):
        assert len(siso_spec.spaces) == 4

    def test_entity_count(self, siso_spec):
        assert len(siso_spec.entities) == 1
        assert "x" in siso_spec.entities

    def test_entity_variable(self, siso_spec):
        entity = siso_spec.entities["x"]
        assert "value" in entity.variables
        assert entity.variables["value"].typedef is StateType

    def test_block_count(self, siso_spec):
        # 1 input + 1 sensor + 1 controller + 1 dynamics = 4
        assert len(siso_spec.blocks) == 4

    def test_parameter_count(self, siso_spec):
        assert len(siso_spec.parameter_schema) == 1


class TestBlockRoles:
    def test_input_is_boundary(self, siso_spec):
        assert isinstance(siso_spec.blocks["r"], BoundaryAction)

    def test_sensor_is_policy(self, siso_spec):
        assert isinstance(siso_spec.blocks["y"], Policy)

    def test_controller_is_policy(self, siso_spec):
        assert isinstance(siso_spec.blocks["K"], Policy)

    def test_dynamics_is_mechanism(self, siso_spec):
        assert isinstance(siso_spec.blocks["x Dynamics"], Mechanism)


class TestPortNames:
    def test_input_port(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["r"].interface.forward_out}
        assert ports == {"r Reference"}

    def test_sensor_in_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["y"].interface.forward_in}
        assert ports == {"x State"}

    def test_sensor_out_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["y"].interface.forward_out}
        assert ports == {"y Measurement"}

    def test_controller_in_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["K"].interface.forward_in}
        assert ports == {"y Measurement", "r Reference"}

    def test_controller_out_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["K"].interface.forward_out}
        assert ports == {"K Control"}

    def test_dynamics_in_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["x Dynamics"].interface.forward_in}
        assert ports == {"K Control"}

    def test_dynamics_out_ports(self, siso_spec):
        ports = {p.name for p in siso_spec.blocks["x Dynamics"].interface.forward_out}
        assert ports == {"x State"}


class TestMechanismUpdates:
    def test_dynamics_updates(self, siso_spec):
        mech = siso_spec.blocks["x Dynamics"]
        assert isinstance(mech, Mechanism)
        assert set(map(tuple, mech.updates)) == {("x", "value")}


class TestSystemIR:
    def test_block_count(self, siso_ir):
        # 1 input + 1 sensor + 1 controller + 1 dynamics = 4
        assert len(siso_ir.blocks) == 4

    def test_block_names(self, siso_ir):
        names = {b.name for b in siso_ir.blocks}
        assert names == {"r", "y", "K", "x Dynamics"}

    def test_has_temporal_wirings(self, siso_ir):
        temporal = [w for w in siso_ir.wirings if w.is_temporal]
        assert len(temporal) == 1  # x Dynamics → y

    def test_temporal_wiring_pair(self, siso_ir):
        temporal = [w for w in siso_ir.wirings if w.is_temporal]
        pairs = {(w.source, w.target) for w in temporal}
        assert ("x Dynamics", "y") in pairs


class TestMIMOCompilation:
    @pytest.fixture
    def mimo_model(self):
        return ControlModel(
            name="MIMO",
            states=[State(name="x1"), State(name="x2")],
            inputs=[Input(name="r1"), Input(name="r2")],
            sensors=[
                Sensor(name="y1", observes=["x1"]),
                Sensor(name="y2", observes=["x2"]),
            ],
            controllers=[
                Controller(name="K1", reads=["y1", "r1"], drives=["x1"]),
                Controller(name="K2", reads=["y2", "r2"], drives=["x2"]),
            ],
        )

    def test_block_count(self, mimo_model):
        spec = compile_model(mimo_model)
        # 2 inputs + 2 sensors + 2 controllers + 2 dynamics = 8
        assert len(spec.blocks) == 8

    def test_entity_count(self, mimo_model):
        spec = compile_model(mimo_model)
        assert len(spec.entities) == 2

    def test_temporal_wirings(self, mimo_model):
        ir = compile_to_system(mimo_model)
        temporal = [w for w in ir.wirings if w.is_temporal]
        # x1 Dynamics → y1, x2 Dynamics → y2
        assert len(temporal) == 2
