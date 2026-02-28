"""Tests for ERD element declarations."""

import pytest

from gds_software.erd.elements import Attribute, Cardinality, ERDEntity, ERDRelationship


class TestAttribute:
    def test_basic(self):
        a = Attribute(name="id", is_primary_key=True)
        assert a.name == "id"
        assert a.is_primary_key is True
        assert a.is_nullable is True

    def test_typed(self):
        a = Attribute(name="email", type="string", is_nullable=False)
        assert a.type == "string"
        assert a.is_nullable is False


class TestERDEntity:
    def test_basic(self):
        e = ERDEntity(name="User")
        assert e.name == "User"
        assert e.attributes == []

    def test_with_attributes(self):
        e = ERDEntity(
            name="User",
            attributes=[
                Attribute(name="id", is_primary_key=True),
                Attribute(name="email"),
            ],
        )
        assert len(e.attributes) == 2

    def test_frozen(self):
        e = ERDEntity(name="User")
        with pytest.raises(Exception):
            e.name = "Other"  # type: ignore[misc]


class TestERDRelationship:
    def test_basic(self):
        r = ERDRelationship(name="has", source="User", target="Order")
        assert r.cardinality == Cardinality.ONE_TO_MANY


class TestCardinality:
    def test_values(self):
        assert Cardinality.ONE_TO_ONE == "1:1"
        assert Cardinality.ONE_TO_MANY == "1:N"
        assert Cardinality.MANY_TO_MANY == "N:N"
