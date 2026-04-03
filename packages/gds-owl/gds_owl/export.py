"""Export GDS Pydantic models to RDF graphs (ABox instance data).

Mirrors the pattern in ``gds.serialize.spec_to_dict()`` but targets
``rdflib.Graph`` instead of plain dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from rdflib import RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef

from gds_owl._namespace import (
    DEFAULT_BASE_URI,
    GDS_CORE,
    GDS_IR,
    GDS_VERIF,
    PREFIXES,
)

if TYPE_CHECKING:
    from gds.blocks.base import Block
    from gds.canonical import CanonicalGDS
    from gds.ir.models import BlockIR, HierarchyNodeIR, SystemIR, WiringIR
    from gds.parameters import ParameterDef
    from gds.spaces import Space
    from gds.spec import GDSSpec, SpecWiring
    from gds.state import Entity
    from gds.types.typedef import TypeDef
    from gds.verification.findings import VerificationReport


def _bind(g: Graph) -> None:
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns)


def _ns(base_uri: str, spec_name: str) -> Namespace:
    """Build an instance namespace for a spec."""
    safe = quote(spec_name, safe="")
    uri = f"{base_uri}{safe}/"
    return Namespace(uri)


def _uri(ns: Namespace, category: str, name: str) -> URIRef:
    """Build a deterministic instance URI."""
    safe = quote(name, safe="")
    return ns[f"{category}/{safe}"]


# ── TypeDef ──────────────────────────────────────────────────────────


def _typedef_to_rdf(g: Graph, ns: Namespace, t: TypeDef) -> URIRef:
    uri = _uri(ns, "type", t.name)
    g.add((uri, RDF.type, GDS_CORE["TypeDef"]))
    g.add((uri, GDS_CORE["name"], Literal(t.name)))
    g.add((uri, GDS_CORE["description"], Literal(t.description)))
    g.add((uri, GDS_CORE["pythonType"], Literal(t.python_type.__name__)))
    g.add(
        (
            uri,
            GDS_CORE["hasConstraint"],
            Literal(t.constraint is not None, datatype=XSD.boolean),
        )
    )
    if t.units:
        g.add((uri, GDS_CORE["units"], Literal(t.units)))
    if t.constraint_kind:
        g.add((uri, GDS_CORE["constraintKind"], Literal(t.constraint_kind)))
    if t.constraint_bounds is not None:
        g.add(
            (
                uri,
                GDS_CORE["constraintLow"],
                Literal(t.constraint_bounds[0], datatype=XSD.double),
            )
        )
        g.add(
            (
                uri,
                GDS_CORE["constraintHigh"],
                Literal(t.constraint_bounds[1], datatype=XSD.double),
            )
        )
    if t.constraint_values is not None:
        for v in t.constraint_values:
            g.add((uri, GDS_CORE["constraintValue"], Literal(str(v))))
    return uri


# ── Space ────────────────────────────────────────────────────────────


def _space_to_rdf(
    g: Graph, ns: Namespace, s: Space, type_uris: dict[str, URIRef]
) -> URIRef:
    uri = _uri(ns, "space", s.name)
    g.add((uri, RDF.type, GDS_CORE["Space"]))
    g.add((uri, GDS_CORE["name"], Literal(s.name)))
    g.add((uri, GDS_CORE["description"], Literal(s.description)))
    for field_name, typedef in s.fields.items():
        field_node = BNode()
        g.add((field_node, RDF.type, GDS_CORE["SpaceField"]))
        g.add((field_node, GDS_CORE["fieldName"], Literal(field_name)))
        if typedef.name in type_uris:
            g.add((field_node, GDS_CORE["fieldType"], type_uris[typedef.name]))
        g.add((uri, GDS_CORE["hasField"], field_node))
    return uri


# ── Entity ───────────────────────────────────────────────────────────


def _entity_to_rdf(
    g: Graph, ns: Namespace, e: Entity, type_uris: dict[str, URIRef]
) -> URIRef:
    uri = _uri(ns, "entity", e.name)
    g.add((uri, RDF.type, GDS_CORE["Entity"]))
    g.add((uri, GDS_CORE["name"], Literal(e.name)))
    g.add((uri, GDS_CORE["description"], Literal(e.description)))
    for var_name, sv in e.variables.items():
        sv_uri = _uri(ns, f"entity/{quote(e.name, safe='')}/var", var_name)
        g.add((sv_uri, RDF.type, GDS_CORE["StateVariable"]))
        g.add((sv_uri, GDS_CORE["name"], Literal(sv.name)))
        g.add((sv_uri, GDS_CORE["description"], Literal(sv.description)))
        g.add((sv_uri, GDS_CORE["symbol"], Literal(sv.symbol)))
        if sv.typedef.name in type_uris:
            g.add((sv_uri, GDS_CORE["usesType"], type_uris[sv.typedef.name]))
        g.add((uri, GDS_CORE["hasVariable"], sv_uri))
    return uri


# ── Block ────────────────────────────────────────────────────────────


def _block_to_rdf(
    g: Graph,
    ns: Namespace,
    b: Block,
    param_uris: dict[str, URIRef],
    entity_uris: dict[str, URIRef],
) -> URIRef:
    from gds.blocks.roles import (
        BoundaryAction,
        ControlAction,
        HasConstraints,
        HasOptions,
        HasParams,
        Mechanism,
        Policy,
    )

    uri = _uri(ns, "block", b.name)

    # Determine OWL class from role
    if isinstance(b, BoundaryAction):
        owl_cls = GDS_CORE["BoundaryAction"]
    elif isinstance(b, Mechanism):
        owl_cls = GDS_CORE["Mechanism"]
    elif isinstance(b, Policy):
        owl_cls = GDS_CORE["Policy"]
    elif isinstance(b, ControlAction):
        owl_cls = GDS_CORE["ControlAction"]
    else:
        owl_cls = GDS_CORE["AtomicBlock"]

    g.add((uri, RDF.type, owl_cls))
    g.add((uri, GDS_CORE["name"], Literal(b.name)))

    kind = getattr(b, "kind", "generic")
    g.add((uri, GDS_CORE["kind"], Literal(kind)))

    # Interface
    iface_uri = _uri(ns, f"block/{quote(b.name, safe='')}", "interface")
    g.add((iface_uri, RDF.type, GDS_CORE["Interface"]))
    g.add((uri, GDS_CORE["hasInterface"], iface_uri))

    for port in b.interface.forward_in:
        p_uri = BNode()
        g.add((p_uri, RDF.type, GDS_CORE["Port"]))
        g.add((p_uri, GDS_CORE["portName"], Literal(port.name)))
        for token in sorted(port.type_tokens):
            g.add((p_uri, GDS_CORE["typeToken"], Literal(token)))
        g.add((iface_uri, GDS_CORE["hasForwardIn"], p_uri))

    for port in b.interface.forward_out:
        p_uri = BNode()
        g.add((p_uri, RDF.type, GDS_CORE["Port"]))
        g.add((p_uri, GDS_CORE["portName"], Literal(port.name)))
        for token in sorted(port.type_tokens):
            g.add((p_uri, GDS_CORE["typeToken"], Literal(token)))
        g.add((iface_uri, GDS_CORE["hasForwardOut"], p_uri))

    for port in b.interface.backward_in:
        p_uri = BNode()
        g.add((p_uri, RDF.type, GDS_CORE["Port"]))
        g.add((p_uri, GDS_CORE["portName"], Literal(port.name)))
        g.add((iface_uri, GDS_CORE["hasBackwardIn"], p_uri))

    for port in b.interface.backward_out:
        p_uri = BNode()
        g.add((p_uri, RDF.type, GDS_CORE["Port"]))
        g.add((p_uri, GDS_CORE["portName"], Literal(port.name)))
        g.add((iface_uri, GDS_CORE["hasBackwardOut"], p_uri))

    # Role-specific properties
    if isinstance(b, HasParams):
        for param_name in b.params_used:
            if param_name in param_uris:
                g.add((uri, GDS_CORE["usesParameter"], param_uris[param_name]))

    if isinstance(b, HasConstraints):
        for c in b.constraints:
            g.add((uri, GDS_CORE["constraint"], Literal(c)))

    if isinstance(b, HasOptions):
        for opt in b.options:
            g.add((uri, GDS_CORE["option"], Literal(opt)))

    if isinstance(b, Mechanism):
        for entity_name, var_name in b.updates:
            entry = BNode()
            g.add((entry, RDF.type, GDS_CORE["UpdateMapEntry"]))
            g.add(
                (
                    entry,
                    GDS_CORE["updatesEntity"],
                    Literal(entity_name),
                )
            )
            g.add(
                (
                    entry,
                    GDS_CORE["updatesVariable"],
                    Literal(var_name),
                )
            )
            g.add((uri, GDS_CORE["updatesEntry"], entry))

    return uri


# ── SpecWiring ───────────────────────────────────────────────────────


def _wiring_to_rdf(
    g: Graph,
    ns: Namespace,
    w: SpecWiring,
    block_uris: dict[str, URIRef],
    space_uris: dict[str, URIRef],
) -> URIRef:
    uri = _uri(ns, "wiring", w.name)
    g.add((uri, RDF.type, GDS_CORE["SpecWiring"]))
    g.add((uri, GDS_CORE["name"], Literal(w.name)))
    g.add((uri, GDS_CORE["description"], Literal(w.description)))

    for bname in w.block_names:
        if bname in block_uris:
            g.add((uri, GDS_CORE["wiringBlock"], block_uris[bname]))

    for wire in w.wires:
        wire_node = BNode()
        g.add((wire_node, RDF.type, GDS_CORE["Wire"]))
        g.add((wire_node, GDS_CORE["wireSource"], Literal(wire.source)))
        g.add((wire_node, GDS_CORE["wireTarget"], Literal(wire.target)))
        if wire.space:
            g.add((wire_node, GDS_CORE["wireSpace"], Literal(wire.space)))
        g.add(
            (
                wire_node,
                GDS_CORE["wireOptional"],
                Literal(wire.optional, datatype=XSD.boolean),
            )
        )
        g.add((uri, GDS_CORE["hasWire"], wire_node))

    return uri


# ── ParameterDef ─────────────────────────────────────────────────────


def _parameter_to_rdf(
    g: Graph, ns: Namespace, p: ParameterDef, type_uris: dict[str, URIRef]
) -> URIRef:
    uri = _uri(ns, "parameter", p.name)
    g.add((uri, RDF.type, GDS_CORE["ParameterDef"]))
    g.add((uri, GDS_CORE["name"], Literal(p.name)))
    g.add((uri, GDS_CORE["description"], Literal(p.description)))
    if p.typedef.name in type_uris:
        g.add((uri, GDS_CORE["paramType"], type_uris[p.typedef.name]))
    if p.bounds is not None:
        g.add((uri, GDS_CORE["lowerBound"], Literal(str(p.bounds[0]))))
        g.add((uri, GDS_CORE["upperBound"], Literal(str(p.bounds[1]))))
    return uri


# ── GDSSpec (top-level) ─────────────────────────────────────────────


def spec_to_graph(
    spec: GDSSpec,
    *,
    base_uri: str = DEFAULT_BASE_URI,
) -> Graph:
    """Export a GDSSpec to an RDF graph (ABox instance data)."""
    g = Graph()
    _bind(g)
    ns = _ns(base_uri, spec.name)
    g.bind("inst", ns)

    spec_uri = ns["spec"]
    g.add((spec_uri, RDF.type, GDS_CORE["GDSSpec"]))
    g.add((spec_uri, GDS_CORE["name"], Literal(spec.name)))
    g.add((spec_uri, GDS_CORE["description"], Literal(spec.description)))

    # Types
    type_uris: dict[str, URIRef] = {}
    for name, t in spec.types.items():
        type_uris[name] = _typedef_to_rdf(g, ns, t)
        g.add((spec_uri, GDS_CORE["hasType"], type_uris[name]))

    # Also export parameter typedefs that may not be in spec.types
    for p in spec.parameter_schema.parameters.values():
        if p.typedef.name not in type_uris:
            type_uris[p.typedef.name] = _typedef_to_rdf(g, ns, p.typedef)

    # Spaces
    space_uris: dict[str, URIRef] = {}
    for name, s in spec.spaces.items():
        space_uris[name] = _space_to_rdf(g, ns, s, type_uris)
        g.add((spec_uri, GDS_CORE["hasSpace"], space_uris[name]))

    # Entities
    entity_uris: dict[str, URIRef] = {}
    for name, e in spec.entities.items():
        entity_uris[name] = _entity_to_rdf(g, ns, e, type_uris)
        g.add((spec_uri, GDS_CORE["hasEntity"], entity_uris[name]))

    # Parameters
    param_uris: dict[str, URIRef] = {}
    for name, p in spec.parameter_schema.parameters.items():
        param_uris[name] = _parameter_to_rdf(g, ns, p, type_uris)
        g.add((spec_uri, GDS_CORE["hasParameter"], param_uris[name]))

    # Blocks
    block_uris: dict[str, URIRef] = {}
    for name, b in spec.blocks.items():
        block_uris[name] = _block_to_rdf(g, ns, b, param_uris, entity_uris)
        g.add((spec_uri, GDS_CORE["hasBlock"], block_uris[name]))

    # Wirings
    for _name, w in spec.wirings.items():
        w_uri = _wiring_to_rdf(g, ns, w, block_uris, space_uris)
        g.add((spec_uri, GDS_CORE["hasWiring"], w_uri))

    # Admissibility constraints
    for ac_name, ac in spec.admissibility_constraints.items():
        ac_uri = _uri(ns, "admissibility", ac_name)
        g.add((ac_uri, RDF.type, GDS_CORE["AdmissibleInputConstraint"]))
        g.add((ac_uri, GDS_CORE["name"], Literal(ac_name)))
        g.add(
            (
                ac_uri,
                GDS_CORE["constraintBoundaryBlock"],
                Literal(ac.boundary_block),
            )
        )
        if ac.boundary_block in block_uris:
            g.add(
                (
                    ac_uri,
                    GDS_CORE["constrainsBoundary"],
                    block_uris[ac.boundary_block],
                )
            )
        g.add(
            (
                ac_uri,
                GDS_CORE["admissibilityHasConstraint"],
                Literal(ac.constraint is not None, datatype=XSD.boolean),
            )
        )
        g.add((ac_uri, GDS_CORE["description"], Literal(ac.description)))
        for entity_name, var_name in ac.depends_on:
            dep = BNode()
            g.add((dep, RDF.type, GDS_CORE["AdmissibilityDep"]))
            g.add((dep, GDS_CORE["depEntity"], Literal(entity_name)))
            g.add((dep, GDS_CORE["depVariable"], Literal(var_name)))
            g.add((ac_uri, GDS_CORE["hasDependency"], dep))
        g.add((spec_uri, GDS_CORE["hasAdmissibilityConstraint"], ac_uri))

    # Transition signatures
    for mname, ts in spec.transition_signatures.items():
        ts_uri = _uri(ns, "transition_sig", mname)
        g.add((ts_uri, RDF.type, GDS_CORE["TransitionSignature"]))
        g.add((ts_uri, GDS_CORE["name"], Literal(mname)))
        g.add((ts_uri, GDS_CORE["signatureMechanism"], Literal(ts.mechanism)))
        if ts.mechanism in block_uris:
            g.add(
                (
                    ts_uri,
                    GDS_CORE["signatureForMechanism"],
                    block_uris[ts.mechanism],
                )
            )
        for bname in ts.depends_on_blocks:
            g.add((ts_uri, GDS_CORE["dependsOnBlock"], Literal(bname)))
        if ts.preserves_invariant:
            g.add(
                (
                    ts_uri,
                    GDS_CORE["preservesInvariant"],
                    Literal(ts.preserves_invariant),
                )
            )
        for entity_name, var_name in ts.reads:
            entry = BNode()
            g.add((entry, RDF.type, GDS_CORE["TransitionReadEntry"]))
            g.add((entry, GDS_CORE["readEntity"], Literal(entity_name)))
            g.add((entry, GDS_CORE["readVariable"], Literal(var_name)))
            g.add((ts_uri, GDS_CORE["hasReadEntry"], entry))
        g.add((spec_uri, GDS_CORE["hasTransitionSignature"], ts_uri))

    # State metrics
    for sm_name, sm in spec.state_metrics.items():
        sm_uri = _uri(ns, "state_metric", sm_name)
        g.add((sm_uri, RDF.type, GDS_CORE["StateMetric"]))
        g.add((sm_uri, GDS_CORE["name"], Literal(sm_name)))
        if sm.metric_type:
            g.add((sm_uri, GDS_CORE["metricType"], Literal(sm.metric_type)))
        g.add(
            (
                sm_uri,
                GDS_CORE["metricHasDistance"],
                Literal(sm.distance is not None, datatype=XSD.boolean),
            )
        )
        g.add((sm_uri, GDS_CORE["description"], Literal(sm.description)))
        for entity_name, var_name in sm.variables:
            entry = BNode()
            g.add((entry, RDF.type, GDS_CORE["MetricVariableEntry"]))
            g.add((entry, GDS_CORE["metricEntity"], Literal(entity_name)))
            g.add((entry, GDS_CORE["metricVariable"], Literal(var_name)))
            g.add((sm_uri, GDS_CORE["hasMetricVariable"], entry))
        g.add((spec_uri, GDS_CORE["hasStateMetric"], sm_uri))

    return g


# ── SystemIR ─────────────────────────────────────────────────────────


def _block_ir_to_rdf(g: Graph, ns: Namespace, b: BlockIR) -> URIRef:
    uri = _uri(ns, "block", b.name)
    g.add((uri, RDF.type, GDS_IR["BlockIR"]))
    g.add((GDS_CORE["name"], RDFS.label, Literal("name")))  # property hint
    g.add((uri, GDS_CORE["name"], Literal(b.name)))
    g.add((uri, GDS_IR["blockType"], Literal(b.block_type)))
    fwd_in, fwd_out, bwd_in, bwd_out = b.signature
    g.add((uri, GDS_IR["signatureForwardIn"], Literal(fwd_in)))
    g.add((uri, GDS_IR["signatureForwardOut"], Literal(fwd_out)))
    g.add((uri, GDS_IR["signatureBackwardIn"], Literal(bwd_in)))
    g.add((uri, GDS_IR["signatureBackwardOut"], Literal(bwd_out)))
    g.add((uri, GDS_IR["logic"], Literal(b.logic)))
    g.add((uri, GDS_IR["colorCode"], Literal(b.color_code, datatype=XSD.integer)))
    return uri


def _wiring_ir_to_rdf(g: Graph, ns: Namespace, w: WiringIR, idx: int) -> URIRef:
    uri = _uri(ns, "wiring", f"{w.source}-{w.target}-{idx}")
    g.add((uri, RDF.type, GDS_IR["WiringIR"]))
    g.add((uri, GDS_IR["source"], Literal(w.source)))
    g.add((uri, GDS_IR["target"], Literal(w.target)))
    g.add((uri, GDS_IR["label"], Literal(w.label)))
    g.add((uri, GDS_IR["wiringType"], Literal(w.wiring_type)))
    g.add((uri, GDS_IR["direction"], Literal(w.direction.value)))
    g.add((uri, GDS_IR["isFeedback"], Literal(w.is_feedback, datatype=XSD.boolean)))
    g.add((uri, GDS_IR["isTemporal"], Literal(w.is_temporal, datatype=XSD.boolean)))
    g.add((uri, GDS_IR["category"], Literal(w.category)))
    return uri


def _hierarchy_to_rdf(g: Graph, ns: Namespace, node: HierarchyNodeIR) -> URIRef:
    uri = _uri(ns, "hierarchy", node.id)
    g.add((uri, RDF.type, GDS_IR["HierarchyNodeIR"]))
    g.add((uri, GDS_CORE["name"], Literal(node.name)))
    if node.composition_type:
        g.add((uri, GDS_IR["compositionType"], Literal(node.composition_type.value)))
    if node.block_name:
        g.add((uri, GDS_IR["blockName"], Literal(node.block_name)))
    if node.exit_condition:
        g.add((uri, GDS_IR["exitCondition"], Literal(node.exit_condition)))
    for child in node.children:
        child_uri = _hierarchy_to_rdf(g, ns, child)
        g.add((uri, GDS_IR["hasChild"], child_uri))
    return uri


def system_ir_to_graph(
    system: SystemIR,
    *,
    base_uri: str = DEFAULT_BASE_URI,
) -> Graph:
    """Export a SystemIR to an RDF graph."""
    g = Graph()
    _bind(g)
    ns = _ns(base_uri, system.name)
    g.bind("inst", ns)

    sys_uri = ns["system"]
    g.add((sys_uri, RDF.type, GDS_IR["SystemIR"]))
    g.add((sys_uri, GDS_CORE["name"], Literal(system.name)))
    g.add(
        (
            sys_uri,
            GDS_IR["compositionTypeSystem"],
            Literal(system.composition_type.value),
        )
    )
    if system.source:
        g.add((sys_uri, GDS_IR["sourceLabel"], Literal(system.source)))

    for b in system.blocks:
        b_uri = _block_ir_to_rdf(g, ns, b)
        g.add((sys_uri, GDS_IR["hasBlockIR"], b_uri))

    for idx, w in enumerate(system.wirings):
        w_uri = _wiring_ir_to_rdf(g, ns, w, idx)
        g.add((sys_uri, GDS_IR["hasWiringIR"], w_uri))

    for inp in system.inputs:
        inp_uri = _uri(ns, "input", inp.name)
        g.add((inp_uri, RDF.type, GDS_IR["InputIR"]))
        g.add((inp_uri, GDS_CORE["name"], Literal(inp.name)))
        g.add((sys_uri, GDS_IR["hasInputIR"], inp_uri))

    if system.hierarchy:
        h_uri = _hierarchy_to_rdf(g, ns, system.hierarchy)
        g.add((sys_uri, GDS_IR["hasHierarchy"], h_uri))

    return g


# ── CanonicalGDS ─────────────────────────────────────────────────────


def canonical_to_graph(
    canonical: CanonicalGDS,
    *,
    base_uri: str = DEFAULT_BASE_URI,
    name: str = "canonical",
) -> Graph:
    """Export a CanonicalGDS to an RDF graph."""
    g = Graph()
    _bind(g)
    ns = _ns(base_uri, name)
    g.bind("inst", ns)

    can_uri = ns["canonical"]
    g.add((can_uri, RDF.type, GDS_CORE["CanonicalGDS"]))
    g.add((can_uri, GDS_CORE["formula"], Literal(canonical.formula())))

    # State variables
    for entity_name, var_name in canonical.state_variables:
        sv_uri = _uri(ns, "state_var", f"{entity_name}.{var_name}")
        g.add((sv_uri, RDF.type, GDS_CORE["StateVariable"]))
        g.add((sv_uri, GDS_CORE["name"], Literal(var_name)))
        g.add((sv_uri, GDS_CORE["description"], Literal(f"{entity_name}.{var_name}")))
        g.add((can_uri, GDS_CORE["hasVariable"], sv_uri))

    # Block role partitions
    for bname in canonical.boundary_blocks:
        g.add((can_uri, GDS_CORE["boundaryBlock"], Literal(bname)))
    for bname in canonical.control_blocks:
        g.add((can_uri, GDS_CORE["controlBlock"], Literal(bname)))
    for bname in canonical.policy_blocks:
        g.add((can_uri, GDS_CORE["policyBlock"], Literal(bname)))
    for bname in canonical.mechanism_blocks:
        g.add((can_uri, GDS_CORE["mechanismBlock"], Literal(bname)))

    # Update map
    for mech_name, updates in canonical.update_map:
        for entity_name, var_name in updates:
            entry = BNode()
            g.add((entry, RDF.type, GDS_CORE["UpdateMapEntry"]))
            g.add((entry, GDS_CORE["name"], Literal(mech_name)))
            g.add((entry, GDS_CORE["updatesEntity"], Literal(entity_name)))
            g.add((entry, GDS_CORE["updatesVariable"], Literal(var_name)))
            g.add((can_uri, GDS_CORE["updatesEntry"], entry))

    return g


# ── VerificationReport ───────────────────────────────────────────────


def report_to_graph(
    report: VerificationReport,
    *,
    base_uri: str = DEFAULT_BASE_URI,
) -> Graph:
    """Export a VerificationReport to an RDF graph."""
    g = Graph()
    _bind(g)
    ns = _ns(base_uri, report.system_name)
    g.bind("inst", ns)

    report_uri = ns["report"]
    g.add((report_uri, RDF.type, GDS_VERIF["VerificationReport"]))
    g.add((report_uri, GDS_VERIF["systemName"], Literal(report.system_name)))

    for idx, f in enumerate(report.findings):
        f_uri = _uri(ns, "finding", f"{f.check_id}-{idx}")
        g.add((f_uri, RDF.type, GDS_VERIF["Finding"]))
        g.add((f_uri, GDS_VERIF["checkId"], Literal(f.check_id)))
        g.add((f_uri, GDS_VERIF["severity"], Literal(f.severity.value)))
        g.add((f_uri, GDS_VERIF["message"], Literal(f.message)))
        g.add((f_uri, GDS_VERIF["passed"], Literal(f.passed, datatype=XSD.boolean)))
        for elem in f.source_elements:
            g.add((f_uri, GDS_VERIF["sourceElement"], Literal(elem)))
        if f.exportable_predicate:
            g.add(
                (
                    f_uri,
                    GDS_VERIF["exportablePredicate"],
                    Literal(f.exportable_predicate),
                )
            )
        g.add((report_uri, GDS_VERIF["hasFinding"], f_uri))

    return g
