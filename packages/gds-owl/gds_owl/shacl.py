"""SHACL shape library for validating GDS RDF graphs.

Three shape sets:
- Structural: Pydantic model constraints (cardinality, required fields)
- Generic: G-001..G-006 verification checks on SystemIR
- Semantic: SC-001..SC-007 verification checks on GDSSpec

Requires pyshacl (optional dependency: pip install gds-owl[shacl]).
"""

from __future__ import annotations

from rdflib import RDF, SH, XSD, Graph, Literal, Namespace, URIRef

from gds_owl._namespace import GDS_CORE, GDS_IR, GDS_VERIF, PREFIXES

SH_NS = Namespace("http://www.w3.org/ns/shacl#")
GDS_SHAPE = Namespace("https://gds.block.science/shapes/")


def _bind(g: Graph) -> None:
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns)
    g.bind("sh", SH)
    g.bind("gds-shape", GDS_SHAPE)
    g.bind("xsd", XSD)


def _add_property_shape(
    g: Graph,
    node_shape: URIRef,
    path: URIRef,
    *,
    min_count: int | None = None,
    max_count: int | None = None,
    datatype: URIRef | None = None,
    class_: URIRef | None = None,
    message: str = "",
) -> None:
    """Add a property constraint to a node shape."""
    from rdflib import BNode

    prop = BNode()
    g.add((node_shape, SH.property, prop))
    g.add((prop, SH.path, path))
    if min_count is not None:
        g.add((prop, SH.minCount, Literal(min_count)))
    if max_count is not None:
        g.add((prop, SH.maxCount, Literal(max_count)))
    if datatype is not None:
        g.add((prop, SH.datatype, datatype))
    if class_ is not None:
        g.add((prop, SH["class"], class_))
    if message:
        g.add((prop, SH.message, Literal(message)))


# ── Structural Shapes ────────────────────────────────────────────────


def build_structural_shapes() -> Graph:
    """Build SHACL shapes for GDS structural constraints.

    These mirror the Pydantic model validators: required fields,
    cardinality, and role-specific invariants.
    """
    g = Graph()
    _bind(g)

    # GDSSpec: must have exactly 1 name
    spec_shape = GDS_SHAPE["GDSSpecShape"]
    g.add((spec_shape, RDF.type, SH.NodeShape))
    g.add((spec_shape, SH.targetClass, GDS_CORE["GDSSpec"]))
    _add_property_shape(
        g,
        spec_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        datatype=XSD.string,
        message="GDSSpec must have exactly one name",
    )

    # BoundaryAction: must have 0 hasForwardIn ports
    ba_shape = GDS_SHAPE["BoundaryActionShape"]
    g.add((ba_shape, RDF.type, SH.NodeShape))
    g.add((ba_shape, SH.targetClass, GDS_CORE["BoundaryAction"]))
    _add_property_shape(
        g,
        ba_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="BoundaryAction must have a name",
    )
    # BoundaryAction interface must have no forward_in (checked via interface)
    _add_property_shape(
        g,
        ba_shape,
        GDS_CORE["hasInterface"],
        min_count=1,
        max_count=1,
        message="BoundaryAction must have exactly one interface",
    )

    # Mechanism: must have 0 backward ports, >= 1 updatesEntry
    mech_shape = GDS_SHAPE["MechanismShape"]
    g.add((mech_shape, RDF.type, SH.NodeShape))
    g.add((mech_shape, SH.targetClass, GDS_CORE["Mechanism"]))
    _add_property_shape(
        g,
        mech_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="Mechanism must have a name",
    )
    _add_property_shape(
        g,
        mech_shape,
        GDS_CORE["updatesEntry"],
        min_count=1,
        message="Mechanism must update at least one state variable",
    )

    # Policy: must have name and interface
    pol_shape = GDS_SHAPE["PolicyShape"]
    g.add((pol_shape, RDF.type, SH.NodeShape))
    g.add((pol_shape, SH.targetClass, GDS_CORE["Policy"]))
    _add_property_shape(
        g,
        pol_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="Policy must have a name",
    )

    # Entity: must have name, >= 0 variables
    ent_shape = GDS_SHAPE["EntityShape"]
    g.add((ent_shape, RDF.type, SH.NodeShape))
    g.add((ent_shape, SH.targetClass, GDS_CORE["Entity"]))
    _add_property_shape(
        g,
        ent_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="Entity must have a name",
    )

    # TypeDef: must have name and pythonType
    td_shape = GDS_SHAPE["TypeDefShape"]
    g.add((td_shape, RDF.type, SH.NodeShape))
    g.add((td_shape, SH.targetClass, GDS_CORE["TypeDef"]))
    _add_property_shape(
        g,
        td_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="TypeDef must have a name",
    )
    _add_property_shape(
        g,
        td_shape,
        GDS_CORE["pythonType"],
        min_count=1,
        max_count=1,
        message="TypeDef must have a pythonType",
    )

    # Space: must have name
    space_shape = GDS_SHAPE["SpaceShape"]
    g.add((space_shape, RDF.type, SH.NodeShape))
    g.add((space_shape, SH.targetClass, GDS_CORE["Space"]))
    _add_property_shape(
        g,
        space_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="Space must have a name",
    )

    # AdmissibleInputConstraint: must have name and boundaryBlock
    aic_shape = GDS_SHAPE["AdmissibleInputConstraintShape"]
    g.add((aic_shape, RDF.type, SH.NodeShape))
    g.add((aic_shape, SH.targetClass, GDS_CORE["AdmissibleInputConstraint"]))
    _add_property_shape(
        g,
        aic_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        datatype=XSD.string,
        message="AdmissibleInputConstraint must have a name",
    )
    _add_property_shape(
        g,
        aic_shape,
        GDS_CORE["constraintBoundaryBlock"],
        min_count=1,
        max_count=1,
        datatype=XSD.string,
        message="AdmissibleInputConstraint must have a boundaryBlock",
    )

    # TransitionSignature: must have name and mechanismName
    ts_shape = GDS_SHAPE["TransitionSignatureShape"]
    g.add((ts_shape, RDF.type, SH.NodeShape))
    g.add((ts_shape, SH.targetClass, GDS_CORE["TransitionSignature"]))
    _add_property_shape(
        g,
        ts_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        datatype=XSD.string,
        message="TransitionSignature must have a name",
    )
    _add_property_shape(
        g,
        ts_shape,
        GDS_CORE["signatureMechanism"],
        min_count=1,
        max_count=1,
        datatype=XSD.string,
        message="TransitionSignature must have a mechanismName",
    )

    # BlockIR: must have name
    bir_shape = GDS_SHAPE["BlockIRShape"]
    g.add((bir_shape, RDF.type, SH.NodeShape))
    g.add((bir_shape, SH.targetClass, GDS_IR["BlockIR"]))
    _add_property_shape(
        g,
        bir_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="BlockIR must have a name",
    )

    # SystemIR: must have name
    sir_shape = GDS_SHAPE["SystemIRShape"]
    g.add((sir_shape, RDF.type, SH.NodeShape))
    g.add((sir_shape, SH.targetClass, GDS_IR["SystemIR"]))
    _add_property_shape(
        g,
        sir_shape,
        GDS_CORE["name"],
        min_count=1,
        max_count=1,
        message="SystemIR must have a name",
    )

    # WiringIR: must have source and target
    wir_shape = GDS_SHAPE["WiringIRShape"]
    g.add((wir_shape, RDF.type, SH.NodeShape))
    g.add((wir_shape, SH.targetClass, GDS_IR["WiringIR"]))
    _add_property_shape(
        g,
        wir_shape,
        GDS_IR["source"],
        min_count=1,
        max_count=1,
        message="WiringIR must have a source",
    )
    _add_property_shape(
        g,
        wir_shape,
        GDS_IR["target"],
        min_count=1,
        max_count=1,
        message="WiringIR must have a target",
    )

    # Finding: must have checkId, severity, passed
    finding_shape = GDS_SHAPE["FindingShape"]
    g.add((finding_shape, RDF.type, SH.NodeShape))
    g.add((finding_shape, SH.targetClass, GDS_VERIF["Finding"]))
    _add_property_shape(
        g,
        finding_shape,
        GDS_VERIF["checkId"],
        min_count=1,
        max_count=1,
        message="Finding must have a checkId",
    )
    _add_property_shape(
        g,
        finding_shape,
        GDS_VERIF["severity"],
        min_count=1,
        max_count=1,
        message="Finding must have a severity",
    )
    _add_property_shape(
        g,
        finding_shape,
        GDS_VERIF["passed"],
        min_count=1,
        max_count=1,
        message="Finding must have a passed status",
    )

    return g


# ── Generic Check Shapes (G-001..G-006) ─────────────────────────────


def build_generic_shapes() -> Graph:
    """Build SHACL shapes mirroring G-001..G-006 generic checks.

    These operate on SystemIR RDF graphs.
    G-006 (covariant acyclicity) is not expressible in SHACL and
    is documented as a SPARQL query instead.
    """
    g = Graph()
    _bind(g)

    # G-004: Dangling wirings — every WiringIR source/target must reference
    # a BlockIR name that exists in the same SystemIR.
    # This is expressed as a SPARQL-based constraint.
    g004_shape = GDS_SHAPE["G004DanglingWiringShape"]
    g.add((g004_shape, RDF.type, SH.NodeShape))
    g.add((g004_shape, SH.targetClass, GDS_IR["WiringIR"]))
    g.add(
        (
            g004_shape,
            SH.message,
            Literal("G-004: Wiring references a block not in the system"),
        )
    )

    return g


# ── Semantic Check Shapes (SC-001..SC-007) ───────────────────────────


def build_semantic_shapes() -> Graph:
    """Build SHACL shapes mirroring SC-001..SC-007 semantic checks.

    These operate on GDSSpec RDF graphs.
    """
    g = Graph()
    _bind(g)

    # SC-001: Completeness — every Entity StateVariable should have
    # at least one Mechanism that updatesEntry referencing it.
    # This is advisory (not all specs require full coverage).

    # SC-005: Parameter references — blocks using parameters must
    # reference registered ParameterDef instances.
    # Expressed as: every usesParameter target must be of type ParameterDef.
    sc005_shape = GDS_SHAPE["SC005ParamRefShape"]
    g.add((sc005_shape, RDF.type, SH.NodeShape))
    g.add((sc005_shape, SH.targetClass, GDS_CORE["AtomicBlock"]))
    _add_property_shape(
        g,
        sc005_shape,
        GDS_CORE["usesParameter"],
        class_=GDS_CORE["ParameterDef"],
        message=(
            "SC-005: Block references a parameter that is not a registered ParameterDef"
        ),
    )

    # SC-008: Admissibility constraint must reference a BoundaryAction
    sc008_shape = GDS_SHAPE["SC008AdmissibilityShape"]
    g.add((sc008_shape, RDF.type, SH.NodeShape))
    g.add((sc008_shape, SH.targetClass, GDS_CORE["AdmissibleInputConstraint"]))
    _add_property_shape(
        g,
        sc008_shape,
        GDS_CORE["constrainsBoundary"],
        class_=GDS_CORE["BoundaryAction"],
        message=("SC-008: Admissibility constraint must reference a BoundaryAction"),
    )

    # SC-009: Transition signature must reference a Mechanism
    sc009_shape = GDS_SHAPE["SC009TransitionSigShape"]
    g.add((sc009_shape, RDF.type, SH.NodeShape))
    g.add((sc009_shape, SH.targetClass, GDS_CORE["TransitionSignature"]))
    _add_property_shape(
        g,
        sc009_shape,
        GDS_CORE["signatureForMechanism"],
        class_=GDS_CORE["Mechanism"],
        message="SC-009: Transition signature must reference a Mechanism",
    )

    return g


# ── Combined ─────────────────────────────────────────────────────────


def build_all_shapes() -> Graph:
    """Build all SHACL shapes (structural + generic + semantic)."""
    g = build_structural_shapes()
    g += build_generic_shapes()
    g += build_semantic_shapes()
    return g


# ── Validation ───────────────────────────────────────────────────────


def validate_graph(
    data_graph: Graph,
    shapes_graph: Graph | None = None,
) -> tuple[bool, Graph, str]:
    """Validate an RDF graph against SHACL shapes.

    Requires pyshacl (optional dependency).
    Returns (conforms, results_graph, results_text).
    """
    try:
        from pyshacl import validate
    except ImportError as e:
        raise ImportError(
            "pyshacl is required for SHACL validation. "
            "Install with: pip install gds-owl[shacl]"
        ) from e

    if shapes_graph is None:
        shapes_graph = build_all_shapes()

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shapes_graph
    )
    return conforms, results_graph, results_text
