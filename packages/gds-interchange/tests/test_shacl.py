"""Tests for SHACL shape library."""

import importlib.util

import pytest
from rdflib import RDF, SH, BNode, Graph, Literal

from gds import GDSSpec, SystemIR
from gds_interchange.owl._namespace import GDS_CORE
from gds_interchange.owl.export import (
    report_to_graph,
    spec_to_graph,
    system_ir_to_graph,
)
from gds_interchange.owl.shacl import (
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
        from gds_interchange.owl.shacl import GDS_SHAPE

        spec_shape = GDS_SHAPE["GDSSpecShape"]
        targets = list(g.objects(spec_shape, SH.targetClass))
        assert GDS_CORE["GDSSpec"] in targets

    def test_mechanism_shape_requires_updates(self) -> None:
        g = build_structural_shapes()
        from gds_interchange.owl.shacl import GDS_SHAPE

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
        from gds_interchange.owl.shacl import GDS_SHAPE

        assert (GDS_SHAPE["G004DanglingWiringShape"], RDF.type, SH.NodeShape) in g


class TestSemanticShapes:
    def test_returns_graph(self) -> None:
        g = build_semantic_shapes()
        assert isinstance(g, Graph)

    def test_has_sc005_shape(self) -> None:
        g = build_semantic_shapes()
        from gds_interchange.owl.shacl import GDS_SHAPE

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


class TestConstraintShapes:
    def test_constraint_shapes_for_probability(self, thermostat_spec: GDSSpec) -> None:
        """SHACL constraint shapes are generated for TypeDefs with constraint_kind."""
        from gds.types.typedef import Probability
        from gds_interchange.owl.shacl import GDS_SHAPE, build_constraint_shapes

        thermostat_spec.register_type(Probability)
        data = spec_to_graph(thermostat_spec)
        shapes = build_constraint_shapes(data)

        # Should have a shape for Probability
        prob_shape = GDS_SHAPE["TypeDefConstraint_ProbabilityShape"]
        assert (prob_shape, RDF.type, SH.NodeShape) in shapes

    def test_no_constraint_shapes_without_kind(self) -> None:
        """TypeDefs without constraint_kind produce no constraint shapes."""
        from gds.types.typedef import TypeDef
        from gds_interchange.owl.shacl import build_constraint_shapes

        plain = TypeDef(name="Plain", python_type=float, constraint=lambda x: x > 0)
        spec = GDSSpec(name="plain_test")
        spec.register_type(plain)
        data = spec_to_graph(spec)
        shapes = build_constraint_shapes(data)

        # Should have no node shapes (only prefix bindings)
        node_shapes = list(shapes.subjects(RDF.type, SH.NodeShape))
        assert len(node_shapes) == 0

    def test_bounded_constraint_shape(self) -> None:
        """Bounded constraint_kind produces minInclusive/maxInclusive shapes."""
        from gds.types.typedef import TypeDef
        from gds_interchange.owl.shacl import GDS_SHAPE, build_constraint_shapes

        bounded = TypeDef(
            name="Score",
            python_type=float,
            constraint=lambda x: 0 <= x <= 100,
            constraint_kind="bounded",
            constraint_bounds=(0.0, 100.0),
        )
        spec = GDSSpec(name="bounded_test")
        spec.register_type(bounded)
        data = spec_to_graph(spec)
        shapes = build_constraint_shapes(data)

        score_shape = GDS_SHAPE["TypeDefConstraint_ScoreShape"]
        assert (score_shape, RDF.type, SH.NodeShape) in shapes

        # Verify the shape has property constraints
        props = list(shapes.objects(score_shape, SH.property))
        assert len(props) >= 1


@pytest.mark.skipif(not HAS_PYSHACL, reason="pyshacl not installed")
class TestValidation:
    def test_valid_spec_conforms(self, thermostat_spec: GDSSpec) -> None:
        from gds_interchange.owl.shacl import validate_graph

        data = spec_to_graph(thermostat_spec)
        conforms, _, _ = validate_graph(data)
        assert conforms is True

    def test_valid_system_ir_conforms(self, thermostat_ir: SystemIR) -> None:
        from gds_interchange.owl.shacl import validate_graph

        data = system_ir_to_graph(thermostat_ir)
        conforms, _, _ = validate_graph(data)
        assert conforms is True

    def test_invalid_spec_fails(self) -> None:
        """A GDSSpec with no name should fail validation."""
        from gds_interchange.owl.shacl import validate_graph

        g = Graph()
        # Create a GDSSpec individual with no name
        spec_uri = BNode()
        g.add((spec_uri, RDF.type, GDS_CORE["GDSSpec"]))
        conforms, _, _text = validate_graph(g)
        assert conforms is False
        assert "name" in _text.lower()

    def test_invalid_mechanism_fails(self) -> None:
        """A Mechanism with no updatesEntry should fail."""
        from gds_interchange.owl.shacl import validate_graph

        g = Graph()
        mech_uri = BNode()
        g.add((mech_uri, RDF.type, GDS_CORE["Mechanism"]))
        g.add((mech_uri, GDS_CORE["name"], Literal("BadMech")))
        conforms, _, _text = validate_graph(g)
        assert conforms is False

    def test_report_conforms(self, thermostat_report) -> None:
        from gds_interchange.owl.shacl import validate_graph

        data = report_to_graph(thermostat_report)
        conforms, _, _ = validate_graph(data)
        assert conforms is True


@pytest.mark.skipif(HAS_PYSHACL, reason="pyshacl is installed")
class TestValidationWithoutPyshacl:
    def test_raises_import_error(self, thermostat_spec: GDSSpec) -> None:
        from gds_interchange.owl.shacl import validate_graph

        data = spec_to_graph(thermostat_spec)
        with pytest.raises(ImportError, match="pyshacl"):
            validate_graph(data)
