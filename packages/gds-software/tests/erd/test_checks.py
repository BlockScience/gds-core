"""Tests for ERD verification checks."""

import pytest

from gds_software.erd.checks import (
    check_er001_relationship_validity,
    check_er002_pk_existence,
    check_er003_attribute_uniqueness,
    check_er004_relationship_naming,
)
from gds_software.erd.elements import Attribute, ERDEntity, ERDRelationship
from gds_software.erd.model import ERDModel
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return ERDModel(
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


class TestER001RelationshipValidity:
    def test_valid(self, good_model):
        findings = check_er001_relationship_validity(good_model)
        assert all(f.passed for f in findings)


class TestER002PKExistence:
    def test_has_pk(self, good_model):
        findings = check_er002_pk_existence(good_model)
        assert all(f.passed for f in findings)

    def test_no_pk(self):
        model = ERDModel(
            name="NoPK",
            entities=[ERDEntity(name="User", attributes=[Attribute(name="email")])],
        )
        findings = check_er002_pk_existence(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestER003AttributeUniqueness:
    def test_unique(self, good_model):
        findings = check_er003_attribute_uniqueness(good_model)
        assert all(f.passed for f in findings)


class TestER004RelationshipNaming:
    def test_unique(self, good_model):
        findings = check_er004_relationship_naming(good_model)
        assert all(f.passed for f in findings)


class TestVerifyEngine:
    def test_verify_erd(self, good_model):
        report = verify(good_model)
        assert report.system_name == "Shop"
        er_findings = [f for f in report.findings if f.check_id.startswith("ER-")]
        assert len(er_findings) > 0
