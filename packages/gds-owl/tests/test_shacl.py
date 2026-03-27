"""Tests for SHACL shape library."""

import importlib.util

import pytest
from rdflib import RDF, SH, BNode, Graph, Literal

from gds import GDSSpec, SystemIR
from gds_owl._namespace import GDS_CORE
from gds_owl.export import report_to_graph, spec_to_graph, system_ir_to_graph
from gds_owl.shacl import (
    build_all_shapes,
    build_generic_shapes,
    build_semantic_shapes,
    build_structural_shapes,
)

HAS_PYSHACL = importlib.util.find_spec("pyshacl") is not None


class TestStructuralShapes:
    def test_returns_graph(self) -> None:
        g = build_structural_shapes()
        assert isinstance(g, Graph)
        assert len(g) > 0

    def test_has_node_shapes(self) -> None:
        g = build_structural_shapes()
        shapes = list(g.subjects(RDF.type, SH.NodeShape))
        # GDSSpec, BA, Mech, Policy, Entity, TypeDef, Space, etc.
        assert len(shapes) >= 8

    def test_spec_shape_targets_gds_spec(self) -> None:
        g = build_structural_shapes()
        from gds_owl.shacl import GDS_SHAPE

        spec_shape = GDS_SHAPE["GDSSpecShape"]
        targets = list(g.objects(spec_shape, SH.targetClass))
        assert GDS_CORE["GDSSpec"] in targets

    def test_mechanism_shape_requires_updates(self) -> None:
        g = build_structural_shapes()
        from gds_owl.shacl import GDS_SHAPE

        mech_shape = GDS_SHAPE["MechanismShape"]
        props = list(g.objects(mech_shape, SH.property))
        # One of the property shapes should have path = updatesEntry
        paths = []
        for p in props:
            path_vals = list(g.objects(p, SH.path))
            paths.extend(path_vals)
        assert GDS_CORE["updatesEntry"] in paths


class TestGenericShapes:
    def test_returns_graph(self) -> None:
        g = build_generic_shapes()
        assert isinstance(g, Graph)

    def test_has_g004_shape(self) -> None:
        g = build_generic_shapes()
        from gds_owl.shacl import GDS_SHAPE

        assert (GDS_SHAPE["G004DanglingWiringShape"], RDF.type, SH.NodeShape) in g


class TestSemanticShapes:
    def test_returns_graph(self) -> None:
        g = build_semantic_shapes()
        assert isinstance(g, Graph)

    def test_has_sc005_shape(self) -> None:
        g = build_semantic_shapes()
        from gds_owl.shacl import GDS_SHAPE

        assert (GDS_SHAPE["SC005ParamRefShape"], RDF.type, SH.NodeShape) in g


class TestAllShapes:
    def test_combines_all(self) -> None:
        g = build_all_shapes()
        assert isinstance(g, Graph)
        structural = build_structural_shapes()
        generic = build_generic_shapes()
        semantic = build_semantic_shapes()
        # Combined should have at least as many triples
        assert len(g) >= max(len(structural), len(generic), len(semantic))


@pytest.mark.skipif(not HAS_PYSHACL, reason="pyshacl not installed")
class TestValidation:
    def test_valid_spec_conforms(self, thermostat_spec: GDSSpec) -> None:
        from gds_owl.shacl import validate_graph

        data = spec_to_graph(thermostat_spec)
        conforms, _, _ = validate_graph(data)
        assert conforms is True

    def test_valid_system_ir_conforms(self, thermostat_ir: SystemIR) -> None:
        from gds_owl.shacl import validate_graph

        data = system_ir_to_graph(thermostat_ir)
        conforms, _, _ = validate_graph(data)
        assert conforms is True

    def test_invalid_spec_fails(self) -> None:
        """A GDSSpec with no name should fail validation."""
        from gds_owl.shacl import validate_graph

        g = Graph()
        # Create a GDSSpec individual with no name
        spec_uri = BNode()
        g.add((spec_uri, RDF.type, GDS_CORE["GDSSpec"]))
        conforms, _, _text = validate_graph(g)
        assert conforms is False
        assert "name" in _text.lower()

    def test_invalid_mechanism_fails(self) -> None:
        """A Mechanism with no updatesEntry should fail."""
        from gds_owl.shacl import validate_graph

        g = Graph()
        mech_uri = BNode()
        g.add((mech_uri, RDF.type, GDS_CORE["Mechanism"]))
        g.add((mech_uri, GDS_CORE["name"], Literal("BadMech")))
        conforms, _, _text = validate_graph(g)
        assert conforms is False

    def test_report_conforms(self, thermostat_report) -> None:
        from gds_owl.shacl import validate_graph

        data = report_to_graph(thermostat_report)
        conforms, _, _ = validate_graph(data)
        assert conforms is True


@pytest.mark.skipif(HAS_PYSHACL, reason="pyshacl is installed")
class TestValidationWithoutPyshacl:
    def test_raises_import_error(self, thermostat_spec: GDSSpec) -> None:
        from gds_owl.shacl import validate_graph

        data = spec_to_graph(thermostat_spec)
        with pytest.raises(ImportError, match="pyshacl"):
            validate_graph(data)
