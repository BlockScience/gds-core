"""Tests for the GDS core ontology (TBox)."""

from rdflib import OWL, RDF, RDFS, Graph

from gds_interchange.owl._namespace import GDS, GDS_CORE, GDS_IR, GDS_VERIF
from gds_interchange.owl.ontology import build_core_ontology


class TestOntologyStructure:
    def test_returns_graph(self) -> None:
        g = build_core_ontology()
        assert isinstance(g, Graph)

    def test_has_ontology_declaration(self) -> None:
        g = build_core_ontology()
        assert (GDS["ontology"], RDF.type, OWL.Ontology) in g

    def test_has_ontology_label(self) -> None:
        g = build_core_ontology()
        labels = list(g.objects(GDS["ontology"], RDFS.label))
        assert len(labels) == 1
        assert "Generalized Dynamical Systems" in str(labels[0])

    def test_nonempty(self) -> None:
        g = build_core_ontology()
        assert len(g) > 50


class TestBlockHierarchy:
    def test_block_is_owl_class(self) -> None:
        g = build_core_ontology()
        assert (GDS_CORE["Block"], RDF.type, OWL.Class) in g

    def test_atomic_block_subclasses_block(self) -> None:
        g = build_core_ontology()
        assert (GDS_CORE["AtomicBlock"], RDFS.subClassOf, GDS_CORE["Block"]) in g

    def test_composition_operators_subclass_block(self) -> None:
        g = build_core_ontology()
        for cls in [
            "StackComposition",
            "ParallelComposition",
            "FeedbackLoop",
            "TemporalLoop",
        ]:
            assert (GDS_CORE[cls], RDFS.subClassOf, GDS_CORE["Block"]) in g

    def test_roles_subclass_atomic_block(self) -> None:
        g = build_core_ontology()
        for role in ["BoundaryAction", "Policy", "Mechanism", "ControlAction"]:
            assert (GDS_CORE[role], RDFS.subClassOf, GDS_CORE["AtomicBlock"]) in g

    def test_all_block_types_are_owl_classes(self) -> None:
        g = build_core_ontology()
        block_types = [
            "Block",
            "AtomicBlock",
            "StackComposition",
            "ParallelComposition",
            "FeedbackLoop",
            "TemporalLoop",
            "BoundaryAction",
            "Policy",
            "Mechanism",
            "ControlAction",
        ]
        for bt in block_types:
            assert (GDS_CORE[bt], RDF.type, OWL.Class) in g


class TestSpecFramework:
    def test_spec_classes_exist(self) -> None:
        g = build_core_ontology()
        for cls in [
            "GDSSpec",
            "TypeDef",
            "Space",
            "Entity",
            "StateVariable",
            "SpecWiring",
            "Wire",
            "ParameterDef",
            "CanonicalGDS",
        ]:
            assert (GDS_CORE[cls], RDF.type, OWL.Class) in g

    def test_spec_object_properties(self) -> None:
        g = build_core_ontology()
        for prop in [
            "hasBlock",
            "hasType",
            "hasSpace",
            "hasEntity",
            "hasWiring",
            "hasParameter",
        ]:
            assert (GDS_CORE[prop], RDF.type, OWL.ObjectProperty) in g

    def test_entity_has_variable_property(self) -> None:
        g = build_core_ontology()
        assert (GDS_CORE["hasVariable"], RDF.type, OWL.ObjectProperty) in g
        assert (GDS_CORE["hasVariable"], RDFS.domain, GDS_CORE["Entity"]) in g
        assert (GDS_CORE["hasVariable"], RDFS.range, GDS_CORE["StateVariable"]) in g

    def test_state_variable_uses_type(self) -> None:
        g = build_core_ontology()
        assert (GDS_CORE["usesType"], RDF.type, OWL.ObjectProperty) in g

    def test_mechanism_updates_entry(self) -> None:
        g = build_core_ontology()
        assert (GDS_CORE["updatesEntry"], RDF.type, OWL.ObjectProperty) in g
        assert (GDS_CORE["UpdateMapEntry"], RDF.type, OWL.Class) in g

    def test_canonical_properties(self) -> None:
        g = build_core_ontology()
        for prop in ["boundaryBlock", "controlBlock", "policyBlock", "mechanismBlock"]:
            assert (GDS_CORE[prop], RDF.type, OWL.ObjectProperty) in g


class TestIRClasses:
    def test_ir_classes_exist(self) -> None:
        g = build_core_ontology()
        for cls in ["SystemIR", "BlockIR", "WiringIR", "HierarchyNodeIR", "InputIR"]:
            assert (GDS_IR[cls], RDF.type, OWL.Class) in g

    def test_system_ir_properties(self) -> None:
        g = build_core_ontology()
        for prop in ["hasBlockIR", "hasWiringIR", "hasInputIR", "hasHierarchy"]:
            assert (GDS_IR[prop], RDF.type, OWL.ObjectProperty) in g

    def test_block_ir_datatype_properties(self) -> None:
        g = build_core_ontology()
        for prop in [
            "blockType",
            "signatureForwardIn",
            "signatureForwardOut",
            "logic",
            "colorCode",
        ]:
            assert (GDS_IR[prop], RDF.type, OWL.DatatypeProperty) in g

    def test_wiring_ir_properties(self) -> None:
        g = build_core_ontology()
        for prop in [
            "source",
            "target",
            "label",
            "direction",
            "isFeedback",
            "isTemporal",
        ]:
            assert (GDS_IR[prop], RDF.type, OWL.DatatypeProperty) in g

    def test_hierarchy_has_child(self) -> None:
        g = build_core_ontology()
        assert (GDS_IR["hasChild"], RDF.type, OWL.ObjectProperty) in g


class TestVerificationClasses:
    def test_finding_class(self) -> None:
        g = build_core_ontology()
        assert (GDS_VERIF["Finding"], RDF.type, OWL.Class) in g

    def test_report_class(self) -> None:
        g = build_core_ontology()
        assert (GDS_VERIF["VerificationReport"], RDF.type, OWL.Class) in g

    def test_report_has_finding(self) -> None:
        g = build_core_ontology()
        assert (GDS_VERIF["hasFinding"], RDF.type, OWL.ObjectProperty) in g

    def test_finding_properties(self) -> None:
        g = build_core_ontology()
        for prop in [
            "checkId",
            "severity",
            "message",
            "passed",
            "exportablePredicate",
        ]:
            assert (GDS_VERIF[prop], RDF.type, OWL.DatatypeProperty) in g


class TestOntologySerialization:
    def test_serializes_to_turtle(self) -> None:
        g = build_core_ontology()
        ttl = g.serialize(format="turtle")
        assert "gds-core:Block" in ttl
        assert "owl:Class" in ttl

    def test_serializes_to_xml(self) -> None:
        g = build_core_ontology()
        xml = g.serialize(format="xml")
        assert "RDF" in xml

    def test_round_trips_through_turtle(self) -> None:
        g1 = build_core_ontology()
        ttl = g1.serialize(format="turtle")
        g2 = Graph()
        g2.parse(data=ttl, format="turtle")
        assert len(g1) == len(g2)
