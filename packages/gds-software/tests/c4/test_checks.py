"""Tests for C4 verification checks."""

import pytest

from gds_software.c4.checks import (
    check_c4001_relationship_validity,
    check_c4002_container_hierarchy,
    check_c4003_external_connectivity,
    check_c4004_level_consistency,
)
from gds_software.c4.elements import (
    C4Component,
    C4Relationship,
    Container,
    Person,
)
from gds_software.c4.model import C4Model
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return C4Model(
        name="System",
        persons=[Person(name="User")],
        containers=[Container(name="API")],
        relationships=[
            C4Relationship(name="Uses", source="User", target="API"),
        ],
    )


class TestC4001RelationshipValidity:
    def test_valid(self, good_model):
        findings = check_c4001_relationship_validity(good_model)
        assert all(f.passed for f in findings)


class TestC4002ContainerHierarchy:
    def test_valid(self):
        model = C4Model(
            name="Test",
            containers=[Container(name="API")],
            components=[C4Component(name="Auth", container="API")],
        )
        findings = check_c4002_container_hierarchy(model)
        assert all(f.passed for f in findings)


class TestC4003ExternalConnectivity:
    def test_connected(self, good_model):
        findings = check_c4003_external_connectivity(good_model)
        assert all(f.passed for f in findings)

    def test_disconnected_person(self):
        model = C4Model(
            name="Test",
            persons=[Person(name="Ghost")],
            containers=[Container(name="API")],
        )
        findings = check_c4003_external_connectivity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestC4004LevelConsistency:
    def test_consistent(self, good_model):
        findings = check_c4004_level_consistency(good_model)
        assert all(f.passed for f in findings)


class TestVerifyEngine:
    def test_verify_c4(self, good_model):
        report = verify(good_model)
        assert report.system_name == "System"
        c4_findings = [f for f in report.findings if f.check_id.startswith("C4-")]
        assert len(c4_findings) > 0
