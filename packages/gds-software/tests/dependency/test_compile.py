"""Tests for dependency graph compilation."""

import pytest

from gds.blocks.roles import Policy
from gds.spec import GDSSpec

from gds_software.dependency.compile import compile_dep, compile_dep_to_system
from gds_software.dependency.elements import Dep, Module
from gds_software.dependency.model import DependencyModel


@pytest.fixture
def stack_model():
    return DependencyModel(
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


class TestCompileDep:
    def test_returns_gds_spec(self, stack_model):
        spec = compile_dep(stack_model)
        assert isinstance(spec, GDSSpec)
        assert spec.name == "Stack"

    def test_types_registered(self, stack_model):
        spec = compile_dep(stack_model)
        assert "DG Module" in spec.types

    def test_modules_become_policies(self, stack_model):
        spec = compile_dep(stack_model)
        for name in ["core", "api", "web"]:
            assert name in spec.blocks
            assert isinstance(spec.blocks[name], Policy)

    def test_wirings_registered(self, stack_model):
        spec = compile_dep(stack_model)
        assert len(spec.wirings) == 1


class TestCompileDepToSystem:
    def test_returns_system_ir(self, stack_model):
        ir = compile_dep_to_system(stack_model)
        assert ir.name == "Stack"
        assert len(ir.blocks) == 3

    def test_hierarchy_exists(self, stack_model):
        ir = compile_dep_to_system(stack_model)
        assert ir.hierarchy is not None

    def test_method_delegation(self, stack_model):
        ir = stack_model.compile_system()
        assert ir.name == "Stack"

    def test_single_module(self):
        model = DependencyModel(name="Solo", modules=[Module(name="A")])
        ir = compile_dep_to_system(model)
        assert len(ir.blocks) == 1
