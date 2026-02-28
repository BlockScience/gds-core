"""Tests for component diagram verification checks."""

import pytest

from gds_software.component.checks import (
    check_cp001_interface_satisfaction,
    check_cp002_connector_validity,
    check_cp003_dangling_interfaces,
    check_cp004_component_naming,
)
from gds_software.component.elements import Component, Connector
from gds_software.component.model import ComponentModel
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return ComponentModel(
        name="System",
        components=[
            Component(name="A", provides=["IData"]),
            Component(name="B", requires=["IData"]),
        ],
        connectors=[
            Connector(
                name="C1",
                source="A",
                source_interface="IData",
                target="B",
                target_interface="IData",
            ),
        ],
    )


class TestCP001InterfaceSatisfaction:
    def test_satisfied(self, good_model):
        findings = check_cp001_interface_satisfaction(good_model)
        assert all(f.passed for f in findings)

    def test_unsatisfied(self):
        model = ComponentModel(
            name="Unsatisfied",
            components=[Component(name="A", requires=["IMissing"])],
        )
        findings = check_cp001_interface_satisfaction(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestCP002ConnectorValidity:
    def test_valid(self, good_model):
        findings = check_cp002_connector_validity(good_model)
        assert all(f.passed for f in findings)


class TestCP003DanglingInterfaces:
    def test_consumed(self, good_model):
        findings = check_cp003_dangling_interfaces(good_model)
        assert all(f.passed for f in findings)

    def test_dangling(self):
        model = ComponentModel(
            name="Dangling",
            components=[Component(name="A", provides=["IDangling"])],
        )
        findings = check_cp003_dangling_interfaces(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestCP004ComponentNaming:
    def test_unique(self, good_model):
        findings = check_cp004_component_naming(good_model)
        assert all(f.passed for f in findings)


class TestVerifyEngine:
    def test_verify_component(self, good_model):
        report = verify(good_model)
        assert report.system_name == "System"
        cp_findings = [f for f in report.findings if f.check_id.startswith("CP-")]
        assert len(cp_findings) > 0
