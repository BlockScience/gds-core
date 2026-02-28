"""Tests for DependencyModel validation."""

import pytest

from gds_software.common.errors import SWValidationError
from gds_software.dependency.elements import Dep, Module
from gds_software.dependency.model import DependencyModel


class TestModelConstruction:
    def test_minimal(self):
        m = DependencyModel(name="Test", modules=[Module(name="A")])
        assert m.name == "Test"

    def test_full_model(self):
        m = DependencyModel(
            name="Stack",
            modules=[
                Module(name="core", layer=0),
                Module(name="api", layer=1),
                Module(name="web", layer=2),
            ],
            deps=[
                Dep(source="api", target="core"),
                Dep(source="web", target="api"),
            ],
        )
        assert m.module_names == {"core", "api", "web"}


class TestValidation:
    def test_no_modules_raises(self):
        with pytest.raises(SWValidationError, match="at least one module"):
            DependencyModel(name="Bad", modules=[])

    def test_duplicate_names_raises(self):
        with pytest.raises(SWValidationError, match="Duplicate module name"):
            DependencyModel(
                name="Bad",
                modules=[Module(name="A"), Module(name="A")],
            )

    def test_bad_dep_source_raises(self):
        with pytest.raises(SWValidationError, match="not a declared module"):
            DependencyModel(
                name="Bad",
                modules=[Module(name="A")],
                deps=[Dep(source="Ghost", target="A")],
            )

    def test_bad_dep_target_raises(self):
        with pytest.raises(SWValidationError, match="not a declared module"):
            DependencyModel(
                name="Bad",
                modules=[Module(name="A")],
                deps=[Dep(source="A", target="Ghost")],
            )
