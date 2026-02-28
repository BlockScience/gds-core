"""Tests for C4 element declarations."""

import pytest

from gds_software.c4.elements import (
    C4Component,
    C4Relationship,
    Container,
    ExternalSystem,
    Person,
)


class TestPerson:
    def test_basic(self):
        p = Person(name="User")
        assert p.name == "User"

    def test_frozen(self):
        p = Person(name="User")
        with pytest.raises(Exception):
            p.name = "Other"  # type: ignore[misc]


class TestExternalSystem:
    def test_basic(self):
        e = ExternalSystem(name="Email Service")
        assert e.name == "Email Service"


class TestContainer:
    def test_basic(self):
        c = Container(name="API", technology="Python")
        assert c.name == "API"
        assert c.stateful is False

    def test_stateful(self):
        c = Container(name="DB", stateful=True)
        assert c.stateful is True


class TestC4Component:
    def test_basic(self):
        c = C4Component(name="Auth Module", container="API")
        assert c.name == "Auth Module"
        assert c.container == "API"


class TestC4Relationship:
    def test_basic(self):
        r = C4Relationship(name="Uses", source="User", target="API")
        assert r.source == "User"
        assert r.target == "API"
