"""Tests for ComponentModel validation."""

import pytest

from gds_software.common.errors import SWValidationError
from gds_software.component.elements import Component, Connector
from gds_software.component.model import ComponentModel


class TestModelConstruction:
    def test_minimal(self):
        m = ComponentModel(
            name="Test",
            components=[Component(name="A")],
        )
        assert m.name == "Test"

    def test_full_model(self):
        m = ComponentModel(
            name="System",
            components=[
                Component(name="API", provides=["IData"]),
                Component(name="DB", provides=["IStore"], requires=["IData"]),
            ],
            connectors=[
                Connector(
                    name="C1",
                    source="API",
                    source_interface="IData",
                    target="DB",
                    target_interface="IData",
                ),
            ],
        )
        assert m.component_names == {"API", "DB"}


class TestValidation:
    def test_no_components_raises(self):
        with pytest.raises(SWValidationError, match="at least one component"):
            ComponentModel(name="Bad", components=[])

    def test_duplicate_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate component name"):
            ComponentModel(
                name="Bad",
                components=[Component(name="A"), Component(name="A")],
            )

    def test_bad_connector_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared component"):
            ComponentModel(
                name="Bad",
                components=[Component(name="A", requires=["I"])],
                connectors=[
                    Connector(
                        name="C",
                        source="Ghost",
                        source_interface="I",
                        target="A",
                        target_interface="I",
                    ),
                ],
            )

    def test_bad_connector_interface_raises(self):
        with pytest.raises(SWValidationError, match="not provided by"):
            ComponentModel(
                name="Bad",
                components=[
                    Component(name="A", provides=["IReal"]),
                    Component(name="B", requires=["IReal"]),
                ],
                connectors=[
                    Connector(
                        name="C",
                        source="A",
                        source_interface="IFake",
                        target="B",
                        target_interface="IReal",
                    ),
                ],
            )
