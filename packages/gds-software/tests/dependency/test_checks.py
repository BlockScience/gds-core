"""Tests for dependency graph verification checks."""

import pytest

from gds_software.dependency.checks import (
    check_dg001_dep_validity,
    check_dg002_acyclicity,
    check_dg003_layer_ordering,
    check_dg004_module_connectivity,
)
from gds_software.dependency.elements import Dep, Module
from gds_software.dependency.model import DependencyModel
from gds_software.verification.engine import verify


@pytest.fixture
def good_model():
    return DependencyModel(
        name="Stack",
        modules=[
            Module(name="core", layer=0),
            Module(name="api", layer=1),
        ],
        deps=[Dep(source="api", target="core")],
    )


class TestDG001DepValidity:
    def test_valid(self, good_model):
        findings = check_dg001_dep_validity(good_model)
        assert all(f.passed for f in findings)


class TestDG002Acyclicity:
    def test_acyclic(self, good_model):
        findings = check_dg002_acyclicity(good_model)
        assert all(f.passed for f in findings)

    def test_cycle(self):
        model = DependencyModel(
            name="Cyclic",
            modules=[Module(name="A"), Module(name="B")],
            deps=[
                Dep(source="A", target="B"),
                Dep(source="B", target="A"),
            ],
        )
        findings = check_dg002_acyclicity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestDG003LayerOrdering:
    def test_valid_ordering(self, good_model):
        findings = check_dg003_layer_ordering(good_model)
        assert all(f.passed for f in findings)

    def test_upward_dep(self):
        model = DependencyModel(
            name="Upward",
            modules=[
                Module(name="low", layer=0),
                Module(name="high", layer=2),
            ],
            deps=[Dep(source="low", target="high")],
        )
        findings = check_dg003_layer_ordering(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestDG004ModuleConnectivity:
    def test_connected(self, good_model):
        findings = check_dg004_module_connectivity(good_model)
        assert all(f.passed for f in findings)

    def test_isolated_module(self):
        model = DependencyModel(
            name="Isolated",
            modules=[Module(name="A"), Module(name="Island")],
            deps=[Dep(source="A", target="A")],
        )
        findings = check_dg004_module_connectivity(model)
        failed = [f for f in findings if not f.passed]
        assert len(failed) == 1


class TestVerifyEngine:
    def test_verify_dep(self, good_model):
        report = verify(good_model)
        assert report.system_name == "Stack"
        dg_findings = [f for f in report.findings if f.check_id.startswith("DG-")]
        assert len(dg_findings) > 0
