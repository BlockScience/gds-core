"""Tests for C4 compilation."""

import pytest

from gds.blocks.roles import BoundaryAction, Mechanism, Policy
from gds.spec import GDSSpec

from gds_software.c4.compile import compile_c4, compile_c4_to_system
from gds_software.c4.elements import (
    C4Relationship,
    Container,
    Person,
)
from gds_software.c4.model import C4Model


@pytest.fixture
def web_model():
    return C4Model(
        name="WebSystem",
        persons=[Person(name="User")],
        containers=[
            Container(name="WebApp"),
            Container(name="Database", stateful=True),
        ],
        relationships=[
            C4Relationship(name="Uses", source="User", target="WebApp"),
            C4Relationship(name="Stores", source="WebApp", target="Database"),
        ],
    )


class TestCompileC4:
    def test_returns_gds_spec(self, web_model):
        spec = compile_c4(web_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "WebSystem"

    def test_types_registered(self, web_model):
        spec = compile_c4(web_model)
        assert "C4 Request" in spec.types

    def test_person_becomes_boundary_action(self, web_model):
        spec = compile_c4(web_model)
        assert "User" in spec.blocks
        assert isinstance(spec.blocks["User"], BoundaryAction)

    def test_stateful_becomes_mechanism(self, web_model):
        spec = compile_c4(web_model)
        assert "Database" in spec.blocks
        assert isinstance(spec.blocks["Database"], Mechanism)
        assert "Database" in spec.entities

    def test_stateless_becomes_policy(self, web_model):
        spec = compile_c4(web_model)
        assert "WebApp" in spec.blocks
        assert isinstance(spec.blocks["WebApp"], Policy)


class TestCompileC4ToSystem:
    def test_returns_system_ir(self, web_model):
        ir = compile_c4_to_system(web_model)
        assert ir.name == "WebSystem"
        # 1 person + 1 webapp + 1 database = 3
        assert len(ir.blocks) == 3

    def test_method_delegation(self, web_model):
        ir = web_model.compile_system()
        assert ir.name == "WebSystem"

    def test_containers_only(self):
        model = C4Model(
            name="Simple",
            containers=[Container(name="API"), Container(name="Worker")],
            relationships=[
                C4Relationship(name="R", source="API", target="Worker"),
            ],
        )
        ir = compile_c4_to_system(model)
        assert len(ir.blocks) == 2
