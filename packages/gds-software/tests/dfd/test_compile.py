"""Tests for DFD compilation: DFDModel -> GDSSpec -> SystemIR."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec

from gds_software.dfd.compile import compile_dfd, compile_dfd_to_system
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process
from gds_software.dfd.model import DFDModel


@pytest.fixture
def auth_model():
    return DFDModel(
        name="Auth System",
        external_entities=[ExternalEntity(name="User")],
        processes=[
            Process(name="Authenticate"),
            Process(name="Authorize"),
        ],
        data_stores=[DataStore(name="User DB")],
        data_flows=[
            DataFlow(name="Login", source="User", target="Authenticate"),
            DataFlow(name="Lookup", source="Authenticate", target="User DB"),
            DataFlow(name="Read", source="User DB", target="Authorize"),
            DataFlow(name="Grant", source="Authorize", target="User"),
        ],
    )


@pytest.fixture
def simple_model():
    return DFDModel(
        name="Simple",
        processes=[Process(name="Transform")],
        external_entities=[ExternalEntity(name="Source")],
        data_flows=[
            DataFlow(name="Input", source="Source", target="Transform"),
        ],
    )


class TestCompileDFD:
    def test_returns_gds_spec(self, auth_model):
        spec = compile_dfd(auth_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Auth System"

    def test_types_registered(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "DFD Signal" in spec.types
        assert "DFD Data" in spec.types
        assert "DFD Content" in spec.types

    def test_spaces_registered(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "DFD SignalSpace" in spec.spaces
        assert "DFD DataSpace" in spec.spaces
        assert "DFD ContentSpace" in spec.spaces

    def test_entities_for_stores(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "User DB" in spec.entities
        assert "content" in spec.entities["User DB"].variables

    def test_external_becomes_boundary_action(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "User" in spec.blocks
        block = spec.blocks["User"]
        assert isinstance(block, BoundaryAction)
        assert block.interface.forward_in == ()
        assert len(block.interface.forward_out) == 1
        assert block.interface.forward_out[0].name == "User Signal"

    def test_process_becomes_policy(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "Authenticate" in spec.blocks
        block = spec.blocks["Authenticate"]
        assert isinstance(block, Policy)
        # Has input from User Signal
        port_names = {p.name for p in block.interface.forward_in}
        assert "User Signal" in port_names

    def test_store_becomes_mechanism(self, auth_model):
        spec = compile_dfd(auth_model)
        assert "User DB Store" in spec.blocks
        block = spec.blocks["User DB Store"]
        assert isinstance(block, Mechanism)
        assert block.interface.forward_out[0].name == "User DB Content"
        assert ("User DB", "content") in block.updates

    def test_wirings_registered(self, auth_model):
        spec = compile_dfd(auth_model)
        assert len(spec.wirings) == 1
        wiring = list(spec.wirings.values())[0]
        assert len(wiring.wires) > 0


class TestCompileDFDToSystem:
    def test_returns_system_ir(self, auth_model):
        ir = compile_dfd_to_system(auth_model)
        assert ir.name == "Auth System"
        assert len(ir.blocks) > 0

    def test_block_count(self, auth_model):
        ir = compile_dfd_to_system(auth_model)
        # 1 external + 2 processes + 1 store mechanism = 4
        assert len(ir.blocks) == 4

    def test_block_names(self, auth_model):
        ir = compile_dfd_to_system(auth_model)
        names = {b.name for b in ir.blocks}
        assert "User" in names
        assert "Authenticate" in names
        assert "Authorize" in names
        assert "User DB Store" in names

    def test_hierarchy_exists(self, auth_model):
        ir = compile_dfd_to_system(auth_model)
        assert ir.hierarchy is not None

    def test_simple_model(self, simple_model):
        ir = compile_dfd_to_system(simple_model)
        assert len(ir.blocks) == 2
        names = {b.name for b in ir.blocks}
        assert "Source" in names
        assert "Transform" in names

    def test_temporal_wirings(self, auth_model):
        ir = compile_dfd_to_system(auth_model)
        temporal = [w for w in ir.wirings if w.is_temporal]
        # User DB -> Authorize via temporal loop
        assert len(temporal) == 1

    def test_method_delegation(self, auth_model):
        """model.compile_system() delegates to compile_dfd_to_system()."""
        ir = auth_model.compile_system()
        assert ir.name == "Auth System"
        assert len(ir.blocks) == 4

    def test_processes_only_model(self):
        model = DFDModel(
            name="Minimal",
            processes=[Process(name="P1"), Process(name="P2")],
            data_flows=[DataFlow(name="F", source="P1", target="P2")],
        )
        ir = compile_dfd_to_system(model)
        assert len(ir.blocks) == 2
