"""Tests for dependency graph element declarations."""

import pytest

from gds_software.dependency.elements import Dep, Layer, Module


class TestModule:
    def test_basic(self):
        m = Module(name="core")
        assert m.name == "core"
        assert m.layer == 0

    def test_with_layer(self):
        m = Module(name="api", layer=2)
        assert m.layer == 2

    def test_frozen(self):
        m = Module(name="core")
        with pytest.raises(Exception):
            m.name = "other"  # type: ignore[misc]


class TestDep:
    def test_basic(self):
        d = Dep(source="api", target="core")
        assert d.source == "api"
        assert d.target == "core"


class TestLayer:
    def test_basic(self):
        layer = Layer(name="Foundation", depth=0)
        assert layer.name == "Foundation"
        assert layer.depth == 0
