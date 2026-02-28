"""Tests for component diagram element declarations."""

import pytest

from gds_software.component.elements import Component, Connector, InterfaceDef


class TestComponent:
    def test_basic(self):
        c = Component(name="Auth Service")
        assert c.name == "Auth Service"
        assert c.provides == []
        assert c.requires == []
        assert c.stateful is False

    def test_with_interfaces(self):
        c = Component(
            name="UserService",
            provides=["IUserAPI"],
            requires=["IDatabase"],
            stateful=True,
        )
        assert c.provides == ["IUserAPI"]
        assert c.requires == ["IDatabase"]
        assert c.stateful is True

    def test_frozen(self):
        c = Component(name="Svc")
        with pytest.raises(Exception):
            c.name = "Other"  # type: ignore[misc]


class TestConnector:
    def test_basic(self):
        c = Connector(
            name="C1",
            source="A",
            source_interface="IData",
            target="B",
            target_interface="IData",
        )
        assert c.source == "A"
        assert c.target == "B"


class TestInterfaceDef:
    def test_basic(self):
        i = InterfaceDef(name="IAuth")
        assert i.name == "IAuth"
