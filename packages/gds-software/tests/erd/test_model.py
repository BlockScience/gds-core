"""Tests for ERDModel validation."""

import pytest

from gds_software.common.errors import SWValidationError
from gds_software.erd.elements import Attribute, ERDEntity, ERDRelationship
from gds_software.erd.model import ERDModel


class TestModelConstruction:
    def test_minimal(self):
        m = ERDModel(name="Test", entities=[ERDEntity(name="User")])
        assert m.name == "Test"

    def test_full_model(self):
        m = ERDModel(
            name="Shop",
            entities=[
                ERDEntity(
                    name="User",
                    attributes=[Attribute(name="id", is_primary_key=True)],
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
        assert m.entity_names == {"User", "Order"}


class TestValidation:
    def test_no_entities_raises(self):
        with pytest.raises(SWValidationError, match="at least one entity"):
            ERDModel(name="Bad", entities=[])

    def test_duplicate_entity_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate entity name"):
            ERDModel(
                name="Bad",
                entities=[ERDEntity(name="A"), ERDEntity(name="A")],
            )

    def test_bad_relationship_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared entity"):
            ERDModel(
                name="Bad",
                entities=[ERDEntity(name="A")],
                relationships=[
                    ERDRelationship(name="R", source="Ghost", target="A"),
                ],
            )

    def test_duplicate_attribute_raises(self):
        with pytest.raises(SWValidationError, match="duplicate attribute"):
            ERDModel(
                name="Bad",
                entities=[
                    ERDEntity(
                        name="A",
                        attributes=[
                            Attribute(name="x"),
                            Attribute(name="x"),
                        ],
                    ),
                ],
            )
