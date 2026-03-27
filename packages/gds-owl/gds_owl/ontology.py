"""GDS core ontology — OWL class hierarchy and property definitions (TBox).

Builds the GDS ontology programmatically as an rdflib Graph. This defines
the *schema* (classes, properties, domain/range) — not instance data.
"""

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal

from gds_owl._namespace import GDS, GDS_CORE, GDS_IR, GDS_VERIF, PREFIXES


def _bind_prefixes(g: Graph) -> None:
    """Bind all GDS prefixes to a graph."""
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)


def _add_class(
    g: Graph,
    cls: str,
    ns: type = GDS_CORE,
    *,
    parent: str | None = None,
    parent_ns: type | None = None,
    label: str = "",
    comment: str = "",
) -> None:
    """Declare an OWL class with optional subclass relation."""
    uri = ns[cls]
    g.add((uri, RDF.type, OWL.Class))
    if label:
        g.add((uri, RDFS.label, Literal(label)))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment)))
    if parent:
        p_ns = parent_ns or ns
        g.add((uri, RDFS.subClassOf, p_ns[parent]))


def _add_object_property(
    g: Graph,
    name: str,
    ns: type = GDS_CORE,
    *,
    domain: str | None = None,
    domain_ns: type | None = None,
    range_: str | None = None,
    range_ns: type | None = None,
    label: str = "",
) -> None:
    """Declare an OWL object property."""
    uri = ns[name]
    g.add((uri, RDF.type, OWL.ObjectProperty))
    if label:
        g.add((uri, RDFS.label, Literal(label)))
    if domain:
        d_ns = domain_ns or ns
        g.add((uri, RDFS.domain, d_ns[domain]))
    if range_:
        r_ns = range_ns or ns
        g.add((uri, RDFS.range, r_ns[range_]))


def _add_datatype_property(
    g: Graph,
    name: str,
    ns: type = GDS_CORE,
    *,
    domain: str | None = None,
    domain_ns: type | None = None,
    range_: str = "string",
    label: str = "",
) -> None:
    """Declare an OWL datatype property."""
    uri = ns[name]
    g.add((uri, RDF.type, OWL.DatatypeProperty))
    if label:
        g.add((uri, RDFS.label, Literal(label)))
    if domain:
        d_ns = domain_ns or ns
        g.add((uri, RDFS.domain, d_ns[domain]))
    xsd_type = getattr(XSD, range_, XSD.string)
    g.add((uri, RDFS.range, xsd_type))


def _build_composition_algebra(g: Graph) -> None:
    """Layer 0: Block hierarchy and composition operators."""
    # Block hierarchy
    _add_class(g, "Block", label="Block", comment="Abstract base for all GDS blocks")
    _add_class(
        g,
        "AtomicBlock",
        parent="Block",
        label="Atomic Block",
        comment="Leaf node — non-decomposable block",
    )
    _add_class(
        g,
        "StackComposition",
        parent="Block",
        label="Stack Composition",
        comment="Sequential composition (>> operator)",
    )
    _add_class(
        g,
        "ParallelComposition",
        parent="Block",
        label="Parallel Composition",
        comment="Side-by-side composition (| operator)",
    )
    _add_class(
        g,
        "FeedbackLoop",
        parent="Block",
        label="Feedback Loop",
        comment="Backward feedback within a timestep (.feedback())",
    )
    _add_class(
        g,
        "TemporalLoop",
        parent="Block",
        label="Temporal Loop",
        comment="Forward iteration across timesteps (.loop())",
    )

    # Block roles
    _add_class(
        g,
        "BoundaryAction",
        parent="AtomicBlock",
        label="Boundary Action",
        comment="Exogenous input (admissible input set U)",
    )
    _add_class(
        g,
        "Policy",
        parent="AtomicBlock",
        label="Policy",
        comment="Decision logic (maps signals to mechanism inputs)",
    )
    _add_class(
        g,
        "Mechanism",
        parent="AtomicBlock",
        label="Mechanism",
        comment="State update (only block that writes state)",
    )
    _add_class(
        g,
        "ControlAction",
        parent="AtomicBlock",
        label="Control Action",
        comment="Endogenous control (reads state, emits signals)",
    )

    # Interface and Port
    _add_class(
        g, "Interface", label="Interface", comment="Bidirectional typed interface"
    )
    _add_class(g, "Port", label="Port", comment="Named typed port on an interface")

    # Composition properties
    _add_object_property(g, "first", domain="StackComposition", range_="Block")
    _add_object_property(g, "second", domain="StackComposition", range_="Block")
    _add_object_property(g, "left", domain="ParallelComposition", range_="Block")
    _add_object_property(g, "right", domain="ParallelComposition", range_="Block")
    _add_object_property(g, "inner", domain="FeedbackLoop", range_="Block")

    # Block -> Interface -> Port
    _add_object_property(g, "hasInterface", domain="Block", range_="Interface")
    _add_object_property(g, "hasForwardIn", domain="Interface", range_="Port")
    _add_object_property(g, "hasForwardOut", domain="Interface", range_="Port")
    _add_object_property(g, "hasBackwardIn", domain="Interface", range_="Port")
    _add_object_property(g, "hasBackwardOut", domain="Interface", range_="Port")

    # Port datatype properties
    _add_datatype_property(g, "portName", domain="Port")
    _add_datatype_property(g, "typeToken", domain="Port")


def _build_spec_framework(g: Graph) -> None:
    """Layer 1: GDSSpec, types, spaces, entities, wirings, parameters."""
    # Spec registry
    _add_class(
        g,
        "GDSSpec",
        label="GDS Specification",
        comment="Central registry for a GDS system specification",
    )

    # Type system
    _add_class(
        g, "TypeDef", label="Type Definition", comment="Runtime-constrained type"
    )
    _add_class(g, "Space", label="Space", comment="Typed product space for data flow")
    _add_class(
        g,
        "SpaceField",
        label="Space Field",
        comment="Named field within a Space (reified field-name + TypeDef)",
    )

    # State model
    _add_class(
        g, "Entity", label="Entity", comment="Named state holder (actor/resource)"
    )
    _add_class(
        g,
        "StateVariable",
        label="State Variable",
        comment="Single typed state variable within an entity",
    )

    # Wiring model
    _add_class(
        g,
        "SpecWiring",
        label="Spec Wiring",
        comment="Named composition of blocks connected by wires",
    )
    _add_class(
        g,
        "Wire",
        label="Wire",
        comment="Connection within a wiring (source -> target through space)",
    )

    # Parameters
    _add_class(
        g,
        "ParameterDef",
        label="Parameter Definition",
        comment="Parameter in the configuration space Theta",
    )

    # Canonical decomposition
    _add_class(
        g,
        "CanonicalGDS",
        label="Canonical GDS",
        comment="Formal h = f . g decomposition of a GDS specification",
    )

    # Update map entry (reified: mechanism -> entity + variable)
    _add_class(
        g,
        "UpdateMapEntry",
        label="Update Map Entry",
        comment="Reified (mechanism, entity, variable) update relationship",
    )

    # Structural annotations (Paper Defs 2.5, 2.7)
    _add_class(
        g,
        "AdmissibleInputConstraint",
        label="Admissible Input Constraint",
        comment="State-dependent constraint on BoundaryAction outputs (U_x)",
    )
    _add_class(
        g,
        "AdmissibilityDep",
        label="Admissibility Dependency",
        comment="Reified (entity, variable) dependency for admissibility",
    )
    _add_class(
        g,
        "TransitionSignature",
        label="Transition Signature",
        comment="Structural read signature of a mechanism transition (f|_x)",
    )
    _add_class(
        g,
        "TransitionReadEntry",
        label="Transition Read Entry",
        comment="Reified (entity, variable) read dependency",
    )

    # GDSSpec -> children
    _add_object_property(g, "hasBlock", domain="GDSSpec", range_="Block")
    _add_object_property(g, "hasType", domain="GDSSpec", range_="TypeDef")
    _add_object_property(g, "hasSpace", domain="GDSSpec", range_="Space")
    _add_object_property(g, "hasEntity", domain="GDSSpec", range_="Entity")
    _add_object_property(g, "hasWiring", domain="GDSSpec", range_="SpecWiring")
    _add_object_property(g, "hasParameter", domain="GDSSpec", range_="ParameterDef")
    _add_object_property(g, "hasCanonical", domain="GDSSpec", range_="CanonicalGDS")
    _add_object_property(
        g,
        "hasAdmissibilityConstraint",
        domain="GDSSpec",
        range_="AdmissibleInputConstraint",
    )
    _add_object_property(
        g,
        "hasTransitionSignature",
        domain="GDSSpec",
        range_="TransitionSignature",
    )

    # Entity -> StateVariable
    _add_object_property(g, "hasVariable", domain="Entity", range_="StateVariable")

    # Space -> SpaceField -> TypeDef
    _add_object_property(g, "hasField", domain="Space", range_="SpaceField")
    _add_object_property(g, "fieldType", domain="SpaceField", range_="TypeDef")
    _add_datatype_property(g, "fieldName", domain="SpaceField")

    # StateVariable -> TypeDef
    _add_object_property(g, "usesType", domain="StateVariable", range_="TypeDef")

    # Block -> ParameterDef
    _add_object_property(g, "usesParameter", domain="Block", range_="ParameterDef")

    # Mechanism updates (via reified UpdateMapEntry)
    _add_object_property(g, "updatesEntry", domain="Mechanism", range_="UpdateMapEntry")
    _add_object_property(g, "updatesEntity", domain="UpdateMapEntry", range_="Entity")
    _add_object_property(
        g, "updatesVariable", domain="UpdateMapEntry", range_="StateVariable"
    )

    # SpecWiring -> blocks and wires
    _add_object_property(g, "wiringBlock", domain="SpecWiring", range_="Block")
    _add_object_property(g, "hasWire", domain="SpecWiring", range_="Wire")

    # Wire properties
    _add_datatype_property(g, "wireSource", domain="Wire")
    _add_datatype_property(g, "wireTarget", domain="Wire")
    _add_object_property(g, "wireSpace", domain="Wire", range_="Space")
    _add_datatype_property(g, "wireOptional", domain="Wire", range_="boolean")

    # ParameterDef -> TypeDef
    _add_object_property(g, "paramType", domain="ParameterDef", range_="TypeDef")
    _add_datatype_property(g, "lowerBound", domain="ParameterDef")
    _add_datatype_property(g, "upperBound", domain="ParameterDef")

    # TypeDef datatype properties
    _add_datatype_property(g, "pythonType", domain="TypeDef")
    _add_datatype_property(g, "units", domain="TypeDef")
    _add_datatype_property(g, "hasConstraint", domain="TypeDef", range_="boolean")

    # StateVariable datatype properties
    _add_datatype_property(g, "symbol", domain="StateVariable")

    # Canonical decomposition properties
    _add_object_property(g, "boundaryBlock", domain="CanonicalGDS", range_="Block")
    _add_object_property(g, "controlBlock", domain="CanonicalGDS", range_="Block")
    _add_object_property(g, "policyBlock", domain="CanonicalGDS", range_="Block")
    _add_object_property(g, "mechanismBlock", domain="CanonicalGDS", range_="Block")
    _add_datatype_property(g, "formula", domain="CanonicalGDS")

    # AdmissibleInputConstraint properties
    _add_object_property(
        g,
        "constrainsBoundary",
        domain="AdmissibleInputConstraint",
        range_="BoundaryAction",
    )
    _add_datatype_property(
        g, "constraintBoundaryBlock", domain="AdmissibleInputConstraint"
    )
    _add_datatype_property(
        g,
        "admissibilityHasConstraint",
        domain="AdmissibleInputConstraint",
        range_="boolean",
    )
    _add_object_property(
        g,
        "hasDependency",
        domain="AdmissibleInputConstraint",
        range_="AdmissibilityDep",
    )
    _add_datatype_property(g, "depEntity", domain="AdmissibilityDep")
    _add_datatype_property(g, "depVariable", domain="AdmissibilityDep")

    # TransitionSignature properties
    _add_object_property(
        g,
        "signatureForMechanism",
        domain="TransitionSignature",
        range_="Mechanism",
    )
    _add_datatype_property(
        g, "signatureMechanism", domain="TransitionSignature"
    )
    _add_datatype_property(
        g, "dependsOnBlock", domain="TransitionSignature"
    )
    _add_datatype_property(
        g, "preservesInvariant", domain="TransitionSignature"
    )
    _add_object_property(
        g,
        "hasReadEntry",
        domain="TransitionSignature",
        range_="TransitionReadEntry",
    )
    _add_datatype_property(g, "readEntity", domain="TransitionReadEntry")
    _add_datatype_property(g, "readVariable", domain="TransitionReadEntry")

    # Shared datatype properties
    _add_datatype_property(g, "name")
    _add_datatype_property(g, "description")
    _add_datatype_property(g, "kind", domain="AtomicBlock")
    _add_datatype_property(g, "constraint", domain="Block")
    _add_datatype_property(g, "option", domain="Block")


def _build_ir_classes(g: Graph) -> None:
    """IR layer: SystemIR, BlockIR, WiringIR, HierarchyNodeIR, InputIR."""
    _add_class(g, "SystemIR", GDS_IR, label="System IR", comment="Top-level flat IR")
    _add_class(
        g, "BlockIR", GDS_IR, label="Block IR", comment="Flat atomic block in IR"
    )
    _add_class(
        g,
        "WiringIR",
        GDS_IR,
        label="Wiring IR",
        comment="Directed edge between blocks in IR",
    )
    _add_class(
        g,
        "HierarchyNodeIR",
        GDS_IR,
        label="Hierarchy Node IR",
        comment="Composition tree node",
    )
    _add_class(g, "InputIR", GDS_IR, label="Input IR", comment="External system input")

    # SystemIR -> children
    _add_object_property(g, "hasBlockIR", GDS_IR, domain="SystemIR", range_="BlockIR")
    _add_object_property(g, "hasWiringIR", GDS_IR, domain="SystemIR", range_="WiringIR")
    _add_object_property(g, "hasInputIR", GDS_IR, domain="SystemIR", range_="InputIR")
    _add_object_property(
        g, "hasHierarchy", GDS_IR, domain="SystemIR", range_="HierarchyNodeIR"
    )

    # BlockIR properties
    _add_datatype_property(g, "blockType", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "signatureForwardIn", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "signatureForwardOut", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "signatureBackwardIn", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "signatureBackwardOut", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "logic", GDS_IR, domain="BlockIR")
    _add_datatype_property(g, "colorCode", GDS_IR, domain="BlockIR", range_="integer")

    # WiringIR properties
    _add_datatype_property(g, "source", GDS_IR, domain="WiringIR")
    _add_datatype_property(g, "target", GDS_IR, domain="WiringIR")
    _add_datatype_property(g, "label", GDS_IR, domain="WiringIR")
    _add_datatype_property(g, "wiringType", GDS_IR, domain="WiringIR")
    _add_datatype_property(g, "direction", GDS_IR, domain="WiringIR")
    _add_datatype_property(g, "isFeedback", GDS_IR, domain="WiringIR", range_="boolean")
    _add_datatype_property(g, "isTemporal", GDS_IR, domain="WiringIR", range_="boolean")
    _add_datatype_property(g, "category", GDS_IR, domain="WiringIR")

    # HierarchyNodeIR properties
    _add_datatype_property(g, "compositionType", GDS_IR, domain="HierarchyNodeIR")
    _add_datatype_property(g, "blockName", GDS_IR, domain="HierarchyNodeIR")
    _add_datatype_property(g, "exitCondition", GDS_IR, domain="HierarchyNodeIR")
    _add_object_property(
        g,
        "hasChild",
        GDS_IR,
        domain="HierarchyNodeIR",
        range_="HierarchyNodeIR",
    )

    # SystemIR datatype properties
    _add_datatype_property(g, "compositionTypeSystem", GDS_IR, domain="SystemIR")
    _add_datatype_property(g, "sourceLabel", GDS_IR, domain="SystemIR")


def _build_verification_classes(g: Graph) -> None:
    """Verification layer: Finding and VerificationReport."""
    _add_class(
        g,
        "Finding",
        GDS_VERIF,
        label="Finding",
        comment="A single verification check result",
    )
    _add_class(
        g,
        "VerificationReport",
        GDS_VERIF,
        label="Verification Report",
        comment="Aggregated verification results for a system",
    )

    # Report -> Finding
    _add_object_property(
        g,
        "hasFinding",
        GDS_VERIF,
        domain="VerificationReport",
        range_="Finding",
    )

    # Finding properties
    _add_datatype_property(g, "checkId", GDS_VERIF, domain="Finding")
    _add_datatype_property(g, "severity", GDS_VERIF, domain="Finding")
    _add_datatype_property(g, "message", GDS_VERIF, domain="Finding")
    _add_datatype_property(g, "passed", GDS_VERIF, domain="Finding", range_="boolean")
    _add_datatype_property(g, "sourceElement", GDS_VERIF, domain="Finding")
    _add_datatype_property(g, "exportablePredicate", GDS_VERIF, domain="Finding")

    # Report properties
    _add_datatype_property(g, "systemName", GDS_VERIF, domain="VerificationReport")


def build_core_ontology() -> Graph:
    """Build the complete GDS core ontology as an OWL graph (TBox).

    Returns an rdflib Graph containing all OWL class declarations,
    object properties, and datatype properties for the GDS ecosystem.

    This is the schema — use the export functions to produce instance data (ABox).
    """
    g = Graph()
    _bind_prefixes(g)

    # Ontology metadata
    g.add((GDS["ontology"], RDF.type, OWL.Ontology))
    g.add(
        (
            GDS["ontology"],
            RDFS.label,
            Literal("Generalized Dynamical Systems Ontology"),
        )
    )
    g.add(
        (
            GDS["ontology"],
            RDFS.comment,
            Literal(
                "OWL ontology for typed compositional specifications "
                "of complex systems, grounded in GDS theory."
            ),
        )
    )

    _build_composition_algebra(g)
    _build_spec_framework(g)
    _build_ir_classes(g)
    _build_verification_classes(g)

    return g
