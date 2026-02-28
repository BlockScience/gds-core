"""Tests for DFD element declarations."""

import pytest

from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process


class TestExternalEntity:
    def test_basic(self):
        e = ExternalEntity(name="User")
        assert e.name == "User"
        assert e.description == ""

    def test_with_description(self):
        e = ExternalEntity(name="Admin", description="System administrator")
        assert e.description == "System administrator"

    def test_frozen(self):
        e = ExternalEntity(name="User")
        with pytest.raises(Exception):
            e.name = "Other"  # type: ignore[misc]


class TestProcess:
    def test_basic(self):
        p = Process(name="Validate Input")
        assert p.name == "Validate Input"

    def test_with_description(self):
        p = Process(name="Transform", description="Data transformation")
        assert p.description == "Data transformation"


class TestDataStore:
    def test_basic(self):
        d = DataStore(name="User DB")
        assert d.name == "User DB"

    def test_with_description(self):
        d = DataStore(name="Cache", description="In-memory cache")
        assert d.description == "In-memory cache"


class TestDataFlow:
    def test_basic(self):
        f = DataFlow(name="Login Request", source="User", target="Auth")
        assert f.name == "Login Request"
        assert f.source == "User"
        assert f.target == "Auth"
        assert f.data == ""

    def test_with_data(self):
        f = DataFlow(
            name="Query",
            source="Auth",
            target="User DB",
            data="credentials",
        )
        assert f.data == "credentials"
