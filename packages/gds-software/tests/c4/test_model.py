"""Tests for C4Model validation."""

import pytest

from gds_software.c4.elements import (
    C4Component,
    C4Relationship,
    Container,
    ExternalSystem,
    Person,
)
from gds_software.c4.model import C4Model
from gds_software.common.errors import SWValidationError


class TestModelConstruction:
    def test_minimal(self):
        m = C4Model(
            name="Test",
            containers=[Container(name="API")],
        )
        assert m.name == "Test"

    def test_full_model(self):
        m = C4Model(
            name="System",
            persons=[Person(name="User")],
            external_systems=[ExternalSystem(name="Email")],
            containers=[
                Container(name="WebApp"),
                Container(name="Database", stateful=True),
            ],
            components=[
                C4Component(name="Auth", container="WebApp"),
            ],
            relationships=[
                C4Relationship(name="Uses", source="User", target="WebApp"),
                C4Relationship(name="Stores", source="WebApp", target="Database"),
            ],
        )
        assert len(m.element_names) == 5


class TestValidation:
    def test_duplicate_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate element name"):
            C4Model(
                name="Bad",
                persons=[Person(name="X")],
                containers=[Container(name="X")],
            )

    def test_bad_relationship_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared element"):
            C4Model(
                name="Bad",
                containers=[Container(name="API")],
                relationships=[
                    C4Relationship(name="R", source="Ghost", target="API"),
                ],
            )

    def test_bad_component_container_raises(self):
        with pytest.raises(SWValidationError, match="not a declared container"):
            C4Model(
                name="Bad",
                containers=[Container(name="API")],
                components=[C4Component(name="C", container="Ghost")],
            )


class TestProperties:
    def test_element_names(self):
        m = C4Model(
            name="Test",
            persons=[Person(name="U")],
            containers=[Container(name="A")],
        )
        assert m.element_names == {"U", "A"}

    def test_container_names(self):
        m = C4Model(
            name="Test",
            containers=[Container(name="A"), Container(name="B")],
        )
        assert m.container_names == {"A", "B"}
