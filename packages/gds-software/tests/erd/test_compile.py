"""Tests for ERD compilation."""

import pytest

from gds.blocks.roles import Mechanism
from gds.spec import GDSSpec

from gds_software.erd.compile import compile_erd, compile_erd_to_system
from gds_software.erd.elements import Attribute, ERDEntity, ERDRelationship
from gds_software.erd.model import ERDModel


@pytest.fixture
def shop_model():
    return ERDModel(
        name="Shop",
        entities=[
            ERDEntity(
                name="User",
                attributes=[
                    Attribute(name="id", is_primary_key=True),
                    Attribute(name="email"),
                ],
            ),
            ERDEntity(
                name="Order",
                attributes=[Attribute(name="id", is_primary_key=True)],
            ),
        ],
        relationships=[
            ERDRelationship(name="places", source="User", target="Order"),
        ],
    )


class TestCompileERD:
    def test_returns_gds_spec(self, shop_model):
        spec = compile_erd(shop_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Shop"

    def test_types_registered(self, shop_model):
        spec = compile_erd(shop_model)
        assert "ERD Attribute" in spec.types

    def test_entities_registered(self, shop_model):
        spec = compile_erd(shop_model)
        assert "User" in spec.entities
        assert "Order" in spec.entities
        assert "id" in spec.entities["User"].variables
        assert "email" in spec.entities["User"].variables

    def test_relationship_becomes_mechanism(self, shop_model):
        spec = compile_erd(shop_model)
        assert "places Relationship" in spec.blocks
        block = spec.blocks["places Relationship"]
        assert isinstance(block, Mechanism)

    def test_wirings_registered(self, shop_model):
        spec = compile_erd(shop_model)
        assert len(spec.wirings) == 1


class TestCompileERDToSystem:
    def test_returns_system_ir(self, shop_model):
        ir = compile_erd_to_system(shop_model)
        assert ir.name == "Shop"
        assert len(ir.blocks) == 1  # 1 relationship mechanism

    def test_method_delegation(self, shop_model):
        ir = shop_model.compile_system()
        assert ir.name == "Shop"

    def test_no_relationships(self):
        model = ERDModel(
            name="Solo",
            entities=[ERDEntity(name="User")],
        )
        ir = compile_erd_to_system(model)
        assert len(ir.blocks) == 1  # identity mechanism
