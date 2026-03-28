"""Import RDF graphs back into GDS Pydantic models (round-trip support).

Reconstructs GDSSpec, SystemIR, CanonicalGDS, and VerificationReport
from RDF graphs produced by the export functions.

Known lossy fields:
- TypeDef.constraint: Python callable, not serializable. Imported as None.
- TypeDef.python_type: Mapped from string via _PYTHON_TYPE_MAP for builtins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, XSD, Graph, Literal, URIRef

from gds_owl._namespace import GDS_CORE, GDS_IR, GDS_VERIF

if TYPE_CHECKING:
    from gds.canonical import CanonicalGDS
    from gds.ir.models import HierarchyNodeIR, SystemIR
    from gds.spec import GDSSpec
    from gds.verification.findings import VerificationReport

# Map python_type strings back to actual types
_PYTHON_TYPE_MAP: dict[str, type] = {
    "float": float,
    "int": int,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "complex": complex,
    "bytes": bytes,
}


def _str(g: Graph, subject: URIRef, predicate: URIRef) -> str:
    """Get a single string literal value, or empty string."""
    vals = list(g.objects(subject, predicate))
    return str(vals[0]) if vals else ""


def _bool(g: Graph, subject: URIRef, predicate: URIRef) -> bool:
    """Get a single boolean literal value, or False."""
    vals = list(g.objects(subject, predicate))
    if vals:
        v = vals[0]
        if isinstance(v, Literal) and v.datatype == XSD.boolean:
            return v.toPython()
        return str(v).lower() in ("true", "1")
    return False


def _strs(g: Graph, subject: URIRef, predicate: URIRef) -> list[str]:
    """Get all string literal values for a predicate."""
    return [str(v) for v in g.objects(subject, predicate)]


def _subjects_of_type(g: Graph, rdf_type: URIRef) -> list[URIRef]:
    """Get all subjects of a given RDF type."""
    return [s for s in g.subjects(RDF.type, rdf_type) if isinstance(s, URIRef)]


# ── TypeDef ──────────────────────────────────────────────────────────


def _import_typedef(g: Graph, uri: URIRef) -> dict:
    """Extract TypeDef fields from an RDF node."""
    name = _str(g, uri, GDS_CORE["name"])
    py_type_str = _str(g, uri, GDS_CORE["pythonType"])
    python_type = _PYTHON_TYPE_MAP.get(py_type_str, str)
    description = _str(g, uri, GDS_CORE["description"])
    units = _str(g, uri, GDS_CORE["units"]) or None
    return {
        "name": name,
        "python_type": python_type,
        "description": description,
        "units": units,
        "constraint": None,  # not serializable
    }


# ── GDSSpec ──────────────────────────────────────────────────────────


def graph_to_spec(
    g: Graph,
    *,
    spec_uri: URIRef | None = None,
) -> GDSSpec:
    """Reconstruct a GDSSpec from an RDF graph.

    If spec_uri is None, finds the first GDSSpec individual in the graph.
    """
    from gds import (
        GDSSpec,
        ParameterDef,
        SpecWiring,
        Wire,
    )
    from gds.blocks.roles import BoundaryAction, Mechanism, Policy
    from gds.constraints import AdmissibleInputConstraint, TransitionSignature
    from gds.spaces import Space
    from gds.state import Entity, StateVariable
    from gds.types.interface import Interface, port
    from gds.types.typedef import TypeDef

    if spec_uri is None:
        specs = _subjects_of_type(g, GDS_CORE["GDSSpec"])
        if not specs:
            raise ValueError("No GDSSpec found in graph")
        spec_uri = specs[0]

    spec_name = _str(g, spec_uri, GDS_CORE["name"])
    spec_desc = _str(g, spec_uri, GDS_CORE["description"])
    spec = GDSSpec(name=spec_name, description=spec_desc)

    # Import types
    typedef_map: dict[str, TypeDef] = {}
    type_uris = list(g.objects(spec_uri, GDS_CORE["hasType"]))
    for t_uri in type_uris:
        if not isinstance(t_uri, URIRef):
            continue
        td_fields = _import_typedef(g, t_uri)
        td = TypeDef(**td_fields)
        typedef_map[td.name] = td
        spec.register_type(td)

    # Also collect all TypeDef URIs for parameter types
    all_typedef_uris = _subjects_of_type(g, GDS_CORE["TypeDef"])
    for t_uri in all_typedef_uris:
        td_fields = _import_typedef(g, t_uri)
        if td_fields["name"] not in typedef_map:
            td = TypeDef(**td_fields)
            typedef_map[td.name] = td

    # Import spaces
    space_uris = list(g.objects(spec_uri, GDS_CORE["hasSpace"]))
    for s_uri in space_uris:
        if not isinstance(s_uri, URIRef):
            continue
        s_name = _str(g, s_uri, GDS_CORE["name"])
        s_desc = _str(g, s_uri, GDS_CORE["description"])
        fields: dict[str, TypeDef] = {}
        for field_node in g.objects(s_uri, GDS_CORE["hasField"]):
            field_name = _str(g, field_node, GDS_CORE["fieldName"])
            field_type_uris = list(g.objects(field_node, GDS_CORE["fieldType"]))
            if field_type_uris:
                ft_name = _str(g, field_type_uris[0], GDS_CORE["name"])
                if ft_name in typedef_map:
                    fields[field_name] = typedef_map[ft_name]
        spec.register_space(Space(name=s_name, fields=fields, description=s_desc))

    # Import entities
    entity_uris = list(g.objects(spec_uri, GDS_CORE["hasEntity"]))
    for e_uri in entity_uris:
        if not isinstance(e_uri, URIRef):
            continue
        e_name = _str(g, e_uri, GDS_CORE["name"])
        e_desc = _str(g, e_uri, GDS_CORE["description"])
        variables: dict[str, StateVariable] = {}
        for sv_uri in g.objects(e_uri, GDS_CORE["hasVariable"]):
            if not isinstance(sv_uri, URIRef):
                continue
            sv_name = _str(g, sv_uri, GDS_CORE["name"])
            sv_desc = _str(g, sv_uri, GDS_CORE["description"])
            sv_symbol = _str(g, sv_uri, GDS_CORE["symbol"])
            # Resolve typedef
            sv_type_uris = list(g.objects(sv_uri, GDS_CORE["usesType"]))
            if sv_type_uris:
                sv_type_name = _str(g, sv_type_uris[0], GDS_CORE["name"])
                sv_typedef = typedef_map.get(
                    sv_type_name,
                    TypeDef(name=sv_type_name, python_type=str),
                )
            else:
                sv_typedef = TypeDef(name="unknown", python_type=str)
            variables[sv_name] = StateVariable(
                name=sv_name,
                typedef=sv_typedef,
                description=sv_desc,
                symbol=sv_symbol,
            )
        spec.register_entity(
            Entity(name=e_name, variables=variables, description=e_desc)
        )

    # Import parameters
    param_uris = list(g.objects(spec_uri, GDS_CORE["hasParameter"]))
    param_uri_map: dict[str, URIRef] = {}
    for p_uri in param_uris:
        if not isinstance(p_uri, URIRef):
            continue
        p_name = _str(g, p_uri, GDS_CORE["name"])
        p_desc = _str(g, p_uri, GDS_CORE["description"])
        param_uri_map[p_name] = p_uri
        # Resolve typedef
        pt_uris = list(g.objects(p_uri, GDS_CORE["paramType"]))
        if pt_uris:
            pt_name = _str(g, pt_uris[0], GDS_CORE["name"])
            p_typedef = typedef_map.get(pt_name, TypeDef(name=pt_name, python_type=str))
        else:
            p_typedef = TypeDef(name="unknown", python_type=str)
        spec.register_parameter(
            ParameterDef(name=p_name, typedef=p_typedef, description=p_desc)
        )

    # Import blocks
    block_uris = list(g.objects(spec_uri, GDS_CORE["hasBlock"]))
    # Build reverse lookup: param URI -> param name
    param_name_by_uri: dict[URIRef, str] = {}
    for pname, puri in param_uri_map.items():
        param_name_by_uri[puri] = pname

    for b_uri in block_uris:
        if not isinstance(b_uri, URIRef):
            continue
        b_name = _str(g, b_uri, GDS_CORE["name"])
        b_kind = _str(g, b_uri, GDS_CORE["kind"])

        # Reconstruct interface
        iface_uris = list(g.objects(b_uri, GDS_CORE["hasInterface"]))
        fwd_in_ports: list[str] = []
        fwd_out_ports: list[str] = []
        bwd_in_ports: list[str] = []
        bwd_out_ports: list[str] = []

        if iface_uris:
            iface_uri = iface_uris[0]
            for p in g.objects(iface_uri, GDS_CORE["hasForwardIn"]):
                fwd_in_ports.append(_str(g, p, GDS_CORE["portName"]))
            for p in g.objects(iface_uri, GDS_CORE["hasForwardOut"]):
                fwd_out_ports.append(_str(g, p, GDS_CORE["portName"]))
            for p in g.objects(iface_uri, GDS_CORE["hasBackwardIn"]):
                bwd_in_ports.append(_str(g, p, GDS_CORE["portName"]))
            for p in g.objects(iface_uri, GDS_CORE["hasBackwardOut"]):
                bwd_out_ports.append(_str(g, p, GDS_CORE["portName"]))

        iface = Interface(
            forward_in=tuple(port(n) for n in sorted(fwd_in_ports)),
            forward_out=tuple(port(n) for n in sorted(fwd_out_ports)),
            backward_in=tuple(port(n) for n in sorted(bwd_in_ports)),
            backward_out=tuple(port(n) for n in sorted(bwd_out_ports)),
        )

        # Params used
        params_used = []
        for pu in g.objects(b_uri, GDS_CORE["usesParameter"]):
            if isinstance(pu, URIRef) and pu in param_name_by_uri:
                params_used.append(param_name_by_uri[pu])

        constraints = _strs(g, b_uri, GDS_CORE["constraint"])
        options = _strs(g, b_uri, GDS_CORE["option"])

        # Build block by kind
        if b_kind == "boundary":
            block = BoundaryAction(
                name=b_name,
                interface=iface,
                params_used=params_used,
                constraints=constraints,
                options=options,
            )
        elif b_kind == "mechanism":
            updates: list[tuple[str, str]] = []
            for entry in g.objects(b_uri, GDS_CORE["updatesEntry"]):
                ent = _str(g, entry, GDS_CORE["updatesEntity"])
                var = _str(g, entry, GDS_CORE["updatesVariable"])
                updates.append((ent, var))
            block = Mechanism(
                name=b_name,
                interface=iface,
                updates=updates,
                params_used=params_used,
                constraints=constraints,
            )
        elif b_kind == "policy":
            block = Policy(
                name=b_name,
                interface=iface,
                params_used=params_used,
                constraints=constraints,
                options=options,
            )
        else:
            from gds.blocks.base import AtomicBlock

            block = AtomicBlock(name=b_name, interface=iface)

        spec.register_block(block)

    # Import wirings
    wiring_uris = list(g.objects(spec_uri, GDS_CORE["hasWiring"]))
    for w_uri in wiring_uris:
        if not isinstance(w_uri, URIRef):
            continue
        w_name = _str(g, w_uri, GDS_CORE["name"])
        w_desc = _str(g, w_uri, GDS_CORE["description"])

        block_names = []
        for wb in g.objects(w_uri, GDS_CORE["wiringBlock"]):
            if isinstance(wb, URIRef):
                bn = _str(g, wb, GDS_CORE["name"])
                if bn:
                    block_names.append(bn)

        wires = []
        for wire_node in g.objects(w_uri, GDS_CORE["hasWire"]):
            ws = _str(g, wire_node, GDS_CORE["wireSource"])
            wt = _str(g, wire_node, GDS_CORE["wireTarget"])
            wsp = _str(g, wire_node, GDS_CORE["wireSpace"])
            wo = _bool(g, wire_node, GDS_CORE["wireOptional"])
            wires.append(Wire(source=ws, target=wt, space=wsp, optional=wo))

        spec.register_wiring(
            SpecWiring(
                name=w_name,
                block_names=block_names,
                wires=wires,
                description=w_desc,
            )
        )

    # Import admissibility constraints
    ac_uris = list(g.objects(spec_uri, GDS_CORE["hasAdmissibilityConstraint"]))
    for ac_uri in ac_uris:
        if not isinstance(ac_uri, URIRef):
            continue
        ac_name = _str(g, ac_uri, GDS_CORE["name"])
        ac_boundary = _str(g, ac_uri, GDS_CORE["constraintBoundaryBlock"])
        ac_desc = _str(g, ac_uri, GDS_CORE["description"])
        depends_on: list[tuple[str, str]] = []
        for dep in g.objects(ac_uri, GDS_CORE["hasDependency"]):
            ent = _str(g, dep, GDS_CORE["depEntity"])
            var = _str(g, dep, GDS_CORE["depVariable"])
            depends_on.append((ent, var))
        spec.register_admissibility(
            AdmissibleInputConstraint(
                name=ac_name,
                boundary_block=ac_boundary,
                depends_on=depends_on,
                constraint=None,
                description=ac_desc,
            )
        )

    # Import transition signatures
    ts_uris = list(g.objects(spec_uri, GDS_CORE["hasTransitionSignature"]))
    for ts_uri in ts_uris:
        if not isinstance(ts_uri, URIRef):
            continue
        ts_mech = _str(g, ts_uri, GDS_CORE["signatureMechanism"])
        reads: list[tuple[str, str]] = []
        for entry in g.objects(ts_uri, GDS_CORE["hasReadEntry"]):
            ent = _str(g, entry, GDS_CORE["readEntity"])
            var = _str(g, entry, GDS_CORE["readVariable"])
            reads.append((ent, var))
        depends_on_blocks = _strs(g, ts_uri, GDS_CORE["dependsOnBlock"])
        invariant = _str(g, ts_uri, GDS_CORE["preservesInvariant"])
        spec.register_transition_signature(
            TransitionSignature(
                mechanism=ts_mech,
                reads=reads,
                depends_on_blocks=depends_on_blocks,
                preserves_invariant=invariant,
            )
        )

    return spec


# ── SystemIR ─────────────────────────────────────────────────────────


def graph_to_system_ir(
    g: Graph,
    *,
    system_uri: URIRef | None = None,
) -> SystemIR:
    """Reconstruct a SystemIR from an RDF graph."""
    from gds.ir.models import (
        BlockIR,
        CompositionType,
        FlowDirection,
        InputIR,
        SystemIR,
        WiringIR,
    )

    if system_uri is None:
        systems = _subjects_of_type(g, GDS_IR["SystemIR"])
        if not systems:
            raise ValueError("No SystemIR found in graph")
        system_uri = systems[0]

    name = _str(g, system_uri, GDS_CORE["name"])
    comp_type_str = _str(g, system_uri, GDS_IR["compositionTypeSystem"])
    comp_type = (
        CompositionType(comp_type_str) if comp_type_str else CompositionType.SEQUENTIAL
    )
    source = _str(g, system_uri, GDS_IR["sourceLabel"])

    # Blocks
    blocks = []
    for b_uri in g.objects(system_uri, GDS_IR["hasBlockIR"]):
        if not isinstance(b_uri, URIRef):
            continue
        b_name = _str(g, b_uri, GDS_CORE["name"])
        block_type = _str(g, b_uri, GDS_IR["blockType"])
        fwd_in = _str(g, b_uri, GDS_IR["signatureForwardIn"])
        fwd_out = _str(g, b_uri, GDS_IR["signatureForwardOut"])
        bwd_in = _str(g, b_uri, GDS_IR["signatureBackwardIn"])
        bwd_out = _str(g, b_uri, GDS_IR["signatureBackwardOut"])
        logic = _str(g, b_uri, GDS_IR["logic"])
        color_code_vals = list(g.objects(b_uri, GDS_IR["colorCode"]))
        color_code = int(color_code_vals[0].toPython()) if color_code_vals else 1
        blocks.append(
            BlockIR(
                name=b_name,
                block_type=block_type,
                signature=(fwd_in, fwd_out, bwd_in, bwd_out),
                logic=logic,
                color_code=color_code,
            )
        )

    # Wirings
    wirings = []
    for w_uri in g.objects(system_uri, GDS_IR["hasWiringIR"]):
        if not isinstance(w_uri, URIRef):
            continue
        w_source = _str(g, w_uri, GDS_IR["source"])
        w_target = _str(g, w_uri, GDS_IR["target"])
        w_label = _str(g, w_uri, GDS_IR["label"])
        w_type = _str(g, w_uri, GDS_IR["wiringType"])
        w_dir_str = _str(g, w_uri, GDS_IR["direction"])
        w_dir = FlowDirection(w_dir_str) if w_dir_str else FlowDirection.COVARIANT
        w_fb = _bool(g, w_uri, GDS_IR["isFeedback"])
        w_temp = _bool(g, w_uri, GDS_IR["isTemporal"])
        w_cat = _str(g, w_uri, GDS_IR["category"])
        wirings.append(
            WiringIR(
                source=w_source,
                target=w_target,
                label=w_label,
                wiring_type=w_type,
                direction=w_dir,
                is_feedback=w_fb,
                is_temporal=w_temp,
                category=w_cat or "dataflow",
            )
        )

    # Inputs
    inputs = []
    for inp_uri in g.objects(system_uri, GDS_IR["hasInputIR"]):
        if not isinstance(inp_uri, URIRef):
            continue
        inp_name = _str(g, inp_uri, GDS_CORE["name"])
        inputs.append(InputIR(name=inp_name))

    # Hierarchy
    hierarchy = None
    h_uris = list(g.objects(system_uri, GDS_IR["hasHierarchy"]))
    if h_uris and isinstance(h_uris[0], URIRef):
        hierarchy = _import_hierarchy(g, h_uris[0])

    return SystemIR(
        name=name,
        blocks=blocks,
        wirings=wirings,
        inputs=inputs,
        composition_type=comp_type,
        hierarchy=hierarchy,
        source=source,
    )


def _import_hierarchy(g: Graph, uri: URIRef) -> HierarchyNodeIR:
    """Recursively import a HierarchyNodeIR tree."""
    from gds.ir.models import CompositionType, HierarchyNodeIR

    node_id = str(uri).split("/")[-1]
    name = _str(g, uri, GDS_CORE["name"])
    comp_type_str = _str(g, uri, GDS_IR["compositionType"])
    comp_type = CompositionType(comp_type_str) if comp_type_str else None
    block_name = _str(g, uri, GDS_IR["blockName"]) or None
    exit_condition = _str(g, uri, GDS_IR["exitCondition"])

    children = []
    for child_uri in g.objects(uri, GDS_IR["hasChild"]):
        if isinstance(child_uri, URIRef):
            children.append(_import_hierarchy(g, child_uri))

    return HierarchyNodeIR(
        id=node_id,
        name=name,
        composition_type=comp_type,
        children=children,
        block_name=block_name,
        exit_condition=exit_condition,
    )


# ── CanonicalGDS ─────────────────────────────────────────────────────


def graph_to_canonical(
    g: Graph,
    *,
    canonical_uri: URIRef | None = None,
) -> CanonicalGDS:
    """Reconstruct a CanonicalGDS from an RDF graph."""
    from gds.canonical import CanonicalGDS

    if canonical_uri is None:
        canons = _subjects_of_type(g, GDS_CORE["CanonicalGDS"])
        if not canons:
            raise ValueError("No CanonicalGDS found in graph")
        canonical_uri = canons[0]

    # State variables
    state_variables = []
    for sv_uri in g.objects(canonical_uri, GDS_CORE["hasVariable"]):
        desc = _str(g, sv_uri, GDS_CORE["description"])
        if "." in desc:
            entity_name, var_name = desc.split(".", 1)
            state_variables.append((entity_name, var_name))

    # Role blocks
    boundary_blocks = tuple(_strs(g, canonical_uri, GDS_CORE["boundaryBlock"]))
    control_blocks = tuple(_strs(g, canonical_uri, GDS_CORE["controlBlock"]))
    policy_blocks = tuple(_strs(g, canonical_uri, GDS_CORE["policyBlock"]))
    mechanism_blocks = tuple(_strs(g, canonical_uri, GDS_CORE["mechanismBlock"]))

    # Update map
    update_entries: dict[str, list[tuple[str, str]]] = {}
    for entry in g.objects(canonical_uri, GDS_CORE["updatesEntry"]):
        mech_name = _str(g, entry, GDS_CORE["name"])
        entity_name = _str(g, entry, GDS_CORE["updatesEntity"])
        var_name = _str(g, entry, GDS_CORE["updatesVariable"])
        update_entries.setdefault(mech_name, []).append((entity_name, var_name))

    update_map = tuple(
        (mech, tuple(updates)) for mech, updates in update_entries.items()
    )

    return CanonicalGDS(
        state_variables=tuple(state_variables),
        boundary_blocks=boundary_blocks,
        control_blocks=control_blocks,
        policy_blocks=policy_blocks,
        mechanism_blocks=mechanism_blocks,
        update_map=update_map,
    )


# ── VerificationReport ───────────────────────────────────────────────


def graph_to_report(
    g: Graph,
    *,
    report_uri: URIRef | None = None,
) -> VerificationReport:
    """Reconstruct a VerificationReport from an RDF graph."""
    from gds.verification.findings import Finding, Severity, VerificationReport

    if report_uri is None:
        reports = _subjects_of_type(g, GDS_VERIF["VerificationReport"])
        if not reports:
            raise ValueError("No VerificationReport found in graph")
        report_uri = reports[0]

    system_name = _str(g, report_uri, GDS_VERIF["systemName"])
    findings = []

    for f_uri in g.objects(report_uri, GDS_VERIF["hasFinding"]):
        check_id = _str(g, f_uri, GDS_VERIF["checkId"])
        severity_str = _str(g, f_uri, GDS_VERIF["severity"])
        severity = Severity(severity_str) if severity_str else Severity.INFO
        message = _str(g, f_uri, GDS_VERIF["message"])
        passed = _bool(g, f_uri, GDS_VERIF["passed"])
        source_elements = _strs(g, f_uri, GDS_VERIF["sourceElement"])
        exportable = _str(g, f_uri, GDS_VERIF["exportablePredicate"])
        findings.append(
            Finding(
                check_id=check_id,
                severity=severity,
                message=message,
                passed=passed,
                source_elements=source_elements,
                exportable_predicate=exportable,
            )
        )

    return VerificationReport(system_name=system_name, findings=findings)
