"""Tests for component diagram compilation."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec

from gds_software.component.compile import (
    compile_component,
    compile_component_to_system,
)
from gds_software.component.elements import Component, Connector
from gds_software.component.model import ComponentModel


@pytest.fixture
def system_model():
    return ComponentModel(
        name="System",
        components=[
            Component(name="Frontend", provides=["IUserAPI"]),
            Component(name="Backend", provides=["IData"], requires=["IUserAPI"]),
            Component(
                name="Database",
                provides=["IStore"],
                requires=["IData"],
                stateful=True,
            ),
        ],
        connectors=[
            Connector(
                name="C1",
                source="Frontend",
                source_interface="IUserAPI",
                target="Backend",
                target_interface="IUserAPI",
            ),
            Connector(
                name="C2",
                source="Backend",
                source_interface="IData",
                target="Database",
                target_interface="IData",
            ),
        ],
    )


class TestCompileComponent:
    def test_returns_gds_spec(self, system_model):
        spec = compile_component(system_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "System"

    def test_types_registered(self, system_model):
        spec = compile_component(system_model)
        assert "CP Data" in spec.types

    def test_boundary_component(self, system_model):
        spec = compile_component(system_model)
        assert "Frontend" in spec.blocks
        block = spec.blocks["Frontend"]
        assert isinstance(block, BoundaryAction)

    def test_internal_component(self, system_model):
        spec = compile_component(system_model)
        assert "Backend" in spec.blocks
        block = spec.blocks["Backend"]
        assert isinstance(block, Policy)

    def test_stateful_component(self, system_model):
        spec = compile_component(system_model)
        assert "Database" in spec.blocks
        block = spec.blocks["Database"]
        assert isinstance(block, Mechanism)
        assert "Database" in spec.entities

    def test_wirings_registered(self, system_model):
        spec = compile_component(system_model)
        assert len(spec.wirings) == 1


class TestCompileComponentToSystem:
    def test_returns_system_ir(self, system_model):
        ir = compile_component_to_system(system_model)
        assert ir.name == "System"
        assert len(ir.blocks) == 3

    def test_hierarchy_exists(self, system_model):
        ir = compile_component_to_system(system_model)
        assert ir.hierarchy is not None

    def test_method_delegation(self, system_model):
        ir = system_model.compile_system()
        assert ir.name == "System"
