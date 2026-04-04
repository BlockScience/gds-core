"""SysML v2 model → RDF graph conversion via OSLC vocabulary.

Converts a parsed SysMLModel into an rdflib.Graph using:
1. OSLC SysML v2 vocabulary for SysML elements (PartDefinition, ActionUsage, etc.)
2. GDS-core ontology for GDS-specific concepts (blocks, roles, entities, etc.)

The graph can then be consumed by gds_owl.graph_to_spec() to produce a GDSSpec.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef

from gds_owl._namespace import DEFAULT_BASE_URI, GDS_CORE, PREFIXES
from gds_sysml._namespace import GDS_SYSML, SYSML_OSLC

if TYPE_CHECKING:
    from gds_sysml.model import (
        GDSAnnotation,
        SysMLAttribute,
        SysMLModel,
    )

# ── SysML type → Python type mapping ───────────────────────────

_SYSML_TYPE_MAP: dict[str, str] = {
    "Real": "float",
    "Integer": "int",
    "Boolean": "bool",
    "String": "str",
    "Natural": "int",
    "Positive": "int",
    "ScalarValues::Real": "float",
    "ScalarValues::Integer": "int",
    "ScalarValues::Boolean": "bool",
    "ScalarValues::String": "str",
}

# ── SysML unit → GDS unit mapping ──────────────────────────────

_UNIT_MAP: dict[str, str] = {
    "K": "kelvin",
    "kelvin": "kelvin",
    "Kelvin": "kelvin",
    "W": "watts",
    "watts": "watts",
    "Watts": "watts",
    "kg": "kg",
    "m": "meters",
    "s": "seconds",
    "A": "amperes",
    "V": "volts",
    "rad": "radians",
    "deg": "degrees",
    "rad/s": "rad/s",
    "N": "newtons",
    "Nm": "newton-meters",
    "m/s": "m/s",
    "m/s^2": "m/s^2",
    "kg/m^2": "kg/m^2",
    "": "",
}


def _bind(g: Graph) -> None:
    """Bind standard prefixes to graph."""
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns)
    for prefix, ns in {
        "gds-core": GDS_CORE,
        "sysml": SYSML_OSLC,
        "gds-sysml": GDS_SYSML,
    }.items():
        g.bind(prefix, ns)


def _ns(base_uri: str, model_name: str) -> Namespace:
    """Build an instance namespace for a SysML model."""
    safe = quote(model_name or "sysml_model", safe="")
    return Namespace(f"{base_uri}{safe}/")


def _uri(ns: Namespace, category: str, name: str) -> URIRef:
    """Build a deterministic instance URI."""
    safe = quote(name, safe="")
    return ns[f"{category}/{safe}"]


def _get_gds_role(annotations: list[GDSAnnotation]) -> str:
    """Determine GDS block role from @GDS* annotations.

    Returns one of: "boundary", "policy", "mechanism", "control".
    Defaults to "policy" if no role annotation found.
    """
    role_map = {
        "BoundaryAction": "boundary",
        "Boundary": "boundary",
        "Policy": "policy",
        "Mechanism": "mechanism",
        "ControlAction": "control",
        "Control": "control",
    }
    for ann in annotations:
        if ann.kind in role_map:
            return role_map[ann.kind]
    return "policy"


def _get_annotation(
    annotations: list[GDSAnnotation], kind: str
) -> GDSAnnotation | None:
    """Find a specific annotation by kind."""
    for ann in annotations:
        if ann.kind == kind:
            return ann
    return None


def _python_type_str(sysml_type: str) -> str:
    """Map SysML type name to Python type string."""
    return _SYSML_TYPE_MAP.get(sysml_type, "float")


def _map_units(raw_units: str) -> str:
    """Map SysML/user units to normalized GDS units."""
    return _UNIT_MAP.get(raw_units, raw_units)


# ── Main conversion ────────────────────────────────────────────


def sysml_to_rdf(
    model: SysMLModel,
    *,
    base_uri: str = DEFAULT_BASE_URI,
) -> Graph:
    """Convert a parsed SysMLModel to an RDF graph.

    The output graph uses GDS-core ontology classes so it can be consumed
    directly by ``gds_owl.graph_to_spec()``.

    Args:
        model: Parsed SysML v2 model from the parser layer.
        base_uri: Base URI for instance data.

    Returns:
        An rdflib.Graph with GDS-core ontology triples.
    """
    g = Graph()
    _bind(g)
    ns = _ns(base_uri, model.name)

    # Create spec individual
    spec_uri = ns["spec"]
    g.add((spec_uri, RDF.type, GDS_CORE["GDSSpec"]))
    g.add((spec_uri, GDS_CORE["name"], Literal(model.name or "SysMLModel")))
    g.add((spec_uri, GDS_CORE["description"], Literal("")))

    # Track URIs for cross-referencing
    type_uris: dict[str, URIRef] = {}
    entity_uris: dict[str, URIRef] = {}
    block_uris: dict[str, URIRef] = {}
    param_uris: dict[str, URIRef] = {}

    # 1. Extract TypeDefs from attributes with @GDSStateVariable or @GDSParameter
    _emit_typedefs(g, ns, spec_uri, model, type_uris)

    # 2. Extract Entities from parts with @GDS* state variable attributes
    _emit_entities(g, ns, spec_uri, model, type_uris, entity_uris)

    # 3. Extract Parameters from attributes with @GDSParameter
    _emit_parameters(g, ns, spec_uri, model, type_uris, param_uris)

    # 4. Extract Blocks from actions with @GDS* role annotations
    _emit_blocks(g, ns, spec_uri, model, type_uris, entity_uris, param_uris, block_uris)

    # 5. Extract Wirings from connections
    _emit_wirings(g, ns, spec_uri, model, block_uris)

    # 6. Extract TransitionSignatures from @GDSDynamics annotations
    _emit_transition_signatures(g, ns, spec_uri, model, entity_uris)

    return g


# ── TypeDef emission ────────────────────────────────────────────


def _emit_typedefs(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    type_uris: dict[str, URIRef],
) -> None:
    """Emit TypeDef triples from SysML attributes with type annotations."""
    seen_types: set[str] = set()

    for part in model.parts.values():
        for attr in part.attributes:
            _maybe_emit_typedef(g, ns, spec_uri, attr, type_uris, seen_types)

    for action in model.actions.values():
        for attr in action.attributes:
            _maybe_emit_typedef(g, ns, spec_uri, attr, type_uris, seen_types)

    # Also emit types referenced by ports
    for action in model.actions.values():
        for port in action.ports:
            if port.type_name and port.type_name not in seen_types:
                _emit_typedef_for_port(
                    g, ns, spec_uri, port.type_name, type_uris, seen_types
                )


def _maybe_emit_typedef(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    attr: SysMLAttribute,
    type_uris: dict[str, URIRef],
    seen: set[str],
) -> None:
    """Emit a TypeDef if we haven't seen this type name yet."""
    # Use the attribute's type_name as the TypeDef name
    type_name = attr.type_name or attr.name
    if type_name in seen:
        return
    seen.add(type_name)

    uri = _uri(ns, "type", type_name)
    type_uris[type_name] = uri

    g.add((uri, RDF.type, GDS_CORE["TypeDef"]))
    g.add((uri, GDS_CORE["name"], Literal(type_name)))
    g.add((uri, GDS_CORE["description"], Literal("")))
    g.add((uri, GDS_CORE["pythonType"], Literal(_python_type_str(attr.type_name))))
    g.add((uri, GDS_CORE["hasConstraint"], Literal(False, datatype=XSD.boolean)))

    # Check for units from @GDS* annotations
    for ann in attr.annotations:
        units = ann.properties.get("units", "")
        if isinstance(units, str) and units:
            g.add((uri, GDS_CORE["units"], Literal(_map_units(units))))

    g.add((spec_uri, GDS_CORE["hasType"], uri))


def _emit_typedef_for_port(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    type_name: str,
    type_uris: dict[str, URIRef],
    seen: set[str],
) -> None:
    """Emit a TypeDef for a port type reference."""
    seen.add(type_name)
    uri = _uri(ns, "type", type_name)
    type_uris[type_name] = uri

    g.add((uri, RDF.type, GDS_CORE["TypeDef"]))
    g.add((uri, GDS_CORE["name"], Literal(type_name)))
    g.add((uri, GDS_CORE["description"], Literal("")))
    g.add((uri, GDS_CORE["pythonType"], Literal("float")))
    g.add((uri, GDS_CORE["hasConstraint"], Literal(False, datatype=XSD.boolean)))
    g.add((spec_uri, GDS_CORE["hasType"], uri))


# ── Entity emission ─────────────────────────────────────────────


def _emit_entities(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    type_uris: dict[str, URIRef],
    entity_uris: dict[str, URIRef],
) -> None:
    """Emit Entity triples from SysML parts with @GDSStateVariable attributes."""
    for part in model.parts.values():
        state_vars = [
            attr
            for attr in part.attributes
            if _get_annotation(attr.annotations, "StateVariable") is not None
        ]
        if not state_vars:
            continue

        entity_uri = _uri(ns, "entity", part.name)
        entity_uris[part.name] = entity_uri

        g.add((entity_uri, RDF.type, GDS_CORE["Entity"]))
        g.add((entity_uri, GDS_CORE["name"], Literal(part.name)))
        g.add((entity_uri, GDS_CORE["description"], Literal("")))

        for attr in state_vars:
            var_uri = _uri(ns, f"entity/{quote(part.name, safe='')}/var", attr.name)
            g.add((entity_uri, GDS_CORE["hasVariable"], var_uri))
            g.add((var_uri, RDF.type, GDS_CORE["StateVariable"]))
            g.add((var_uri, GDS_CORE["name"], Literal(attr.name)))
            g.add((var_uri, GDS_CORE["description"], Literal("")))

            # Symbol from annotation properties
            sv_ann = _get_annotation(attr.annotations, "StateVariable")
            symbol = ""
            if sv_ann:
                sym = sv_ann.properties.get("symbol", "")
                if isinstance(sym, str):
                    symbol = sym
            g.add((var_uri, GDS_CORE["symbol"], Literal(symbol)))

            # Type reference
            type_name = attr.type_name or attr.name
            if type_name in type_uris:
                g.add((var_uri, GDS_CORE["usesType"], type_uris[type_name]))

        g.add((spec_uri, GDS_CORE["hasEntity"], entity_uri))


# ── Parameter emission ──────────────────────────────────────────


def _emit_parameters(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    type_uris: dict[str, URIRef],
    param_uris: dict[str, URIRef],
) -> None:
    """Emit ParameterDef triples from attributes with @GDSParameter."""
    seen: set[str] = set()

    for part in model.parts.values():
        for attr in part.attributes:
            if _get_annotation(attr.annotations, "Parameter") is None:
                continue
            if attr.name in seen:
                continue
            seen.add(attr.name)

            param_uri = _uri(ns, "parameter", attr.name)
            param_uris[attr.name] = param_uri

            g.add((param_uri, RDF.type, GDS_CORE["ParameterDef"]))
            g.add((param_uri, GDS_CORE["name"], Literal(attr.name)))
            g.add((param_uri, GDS_CORE["description"], Literal("")))

            type_name = attr.type_name or attr.name
            if type_name in type_uris:
                g.add((param_uri, GDS_CORE["hasTypeDef"], type_uris[type_name]))

            g.add((spec_uri, GDS_CORE["hasParameter"], param_uri))


# ── Block emission ──────────────────────────────────────────────


def _emit_blocks(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    type_uris: dict[str, URIRef],
    entity_uris: dict[str, URIRef],
    param_uris: dict[str, URIRef],
    block_uris: dict[str, URIRef],
) -> None:
    """Emit Block triples from SysML actions with @GDS* role annotations."""
    for action in model.actions.values():
        role = _get_gds_role(action.annotations)
        block_uri = _uri(ns, "block", action.name)
        block_uris[action.name] = block_uri

        # Map role to RDF class
        role_class = {
            "boundary": "BoundaryAction",
            "policy": "Policy",
            "mechanism": "Mechanism",
            "control": "ControlAction",
        }.get(role, "AtomicBlock")

        g.add((block_uri, RDF.type, GDS_CORE[role_class]))
        g.add((block_uri, GDS_CORE["name"], Literal(action.name)))
        g.add((block_uri, GDS_CORE["kind"], Literal(role)))

        # Build interface from ports
        iface_node = BNode()
        g.add((block_uri, GDS_CORE["hasInterface"], iface_node))
        g.add((iface_node, RDF.type, GDS_CORE["Interface"]))

        for port in action.ports:
            port_node = BNode()
            g.add((port_node, RDF.type, GDS_CORE["Port"]))
            port_label = port.type_name or port.name
            g.add((port_node, GDS_CORE["portName"], Literal(port_label)))

            if port.direction == "in":
                g.add((iface_node, GDS_CORE["hasForwardIn"], port_node))
            elif port.direction == "out":
                g.add((iface_node, GDS_CORE["hasForwardOut"], port_node))
            else:
                # Default: use port name heuristics
                if "out" in port.name.lower() or "emit" in port.name.lower():
                    g.add((iface_node, GDS_CORE["hasForwardOut"], port_node))
                else:
                    g.add((iface_node, GDS_CORE["hasForwardIn"], port_node))

        # For mechanisms: emit update map from @GDSDynamics
        if role == "mechanism":
            dynamics = _get_annotation(action.annotations, "Dynamics")
            if dynamics:
                writes = dynamics.properties.get("writes", [])
                if isinstance(writes, list):
                    for write_ref in writes:
                        _emit_update_entry(g, block_uri, write_ref, model, entity_uris)

        # Parameter references from @GDS* annotations
        for ann in action.annotations:
            params_used = ann.properties.get("params", [])
            if isinstance(params_used, list):
                for p in params_used:
                    g.add((block_uri, GDS_CORE["paramUsed"], Literal(p)))

        g.add((spec_uri, GDS_CORE["hasBlock"], block_uri))


def _emit_update_entry(
    g: Graph,
    block_uri: URIRef,
    write_ref: str,
    model: SysMLModel,
    entity_uris: dict[str, URIRef],
) -> None:
    """Emit an UpdateMapEntry for a mechanism's write target.

    The write_ref can be "entity.variable" or just "variable" (resolved
    by searching all entities).
    """
    if "." in write_ref:
        entity_name, var_name = write_ref.split(".", 1)
    else:
        # Search for the variable across all entities
        entity_name = ""
        var_name = write_ref
        for part in model.parts.values():
            for attr in part.attributes:
                if attr.name == write_ref:
                    entity_name = part.name
                    break
            if entity_name:
                break

    if entity_name:
        entry = BNode()
        g.add((block_uri, GDS_CORE["updatesEntry"], entry))
        g.add((entry, RDF.type, GDS_CORE["UpdateMapEntry"]))
        g.add((entry, GDS_CORE["updatesEntity"], Literal(entity_name)))
        g.add((entry, GDS_CORE["updatesVariable"], Literal(var_name)))


# ── Wiring emission ─────────────────────────────────────────────


def _emit_wirings(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    block_uris: dict[str, URIRef],
) -> None:
    """Emit SpecWiring triples from SysML connections."""
    if not model.connections:
        return

    wiring_uri = _uri(ns, "wiring", "main")
    g.add((wiring_uri, RDF.type, GDS_CORE["SpecWiring"]))
    g.add((wiring_uri, GDS_CORE["name"], Literal("main")))
    g.add((wiring_uri, GDS_CORE["description"], Literal("")))

    # Collect all referenced block names
    block_names: set[str] = set()

    for conn in model.connections:
        source_block = conn.source.split(".")[0]
        target_block = conn.target.split(".")[0]
        block_names.add(source_block)
        block_names.add(target_block)

        wire_node = BNode()
        g.add((wiring_uri, GDS_CORE["hasWire"], wire_node))
        g.add((wire_node, RDF.type, GDS_CORE["Wire"]))
        g.add((wire_node, GDS_CORE["source"], Literal(source_block)))
        g.add((wire_node, GDS_CORE["target"], Literal(target_block)))
        g.add((wire_node, GDS_CORE["optional"], Literal(False, datatype=XSD.boolean)))

    for name in block_names:
        g.add((wiring_uri, GDS_CORE["blockName"], Literal(name)))

    g.add((spec_uri, GDS_CORE["hasWiring"], wiring_uri))


# ── Transition signature emission ───────────────────────────────


def _emit_transition_signatures(
    g: Graph,
    ns: Namespace,
    spec_uri: URIRef,
    model: SysMLModel,
    entity_uris: dict[str, URIRef],
) -> None:
    """Emit TransitionSignature triples from @GDSDynamics annotations."""
    for action in model.actions.values():
        dynamics = _get_annotation(action.annotations, "Dynamics")
        if not dynamics:
            continue

        reads = dynamics.properties.get("reads", [])
        if not isinstance(reads, list) or not reads:
            continue

        ts_uri = _uri(ns, "transition", action.name)
        g.add((ts_uri, RDF.type, GDS_CORE["TransitionSignature"]))
        g.add((ts_uri, GDS_CORE["name"], Literal(action.name)))
        g.add((ts_uri, GDS_CORE["signatureMechanism"], Literal(action.name)))
        g.add((ts_uri, GDS_CORE["preservesInvariant"], Literal("")))

        for read_ref in reads:
            if "." in read_ref:
                entity_name, var_name = read_ref.split(".", 1)
            else:
                entity_name = _find_entity_for_var(read_ref, model)
                var_name = read_ref

            if entity_name:
                entry = BNode()
                g.add((ts_uri, GDS_CORE["hasReadEntry"], entry))
                g.add((entry, RDF.type, GDS_CORE["TransitionReadEntry"]))
                g.add((entry, GDS_CORE["readEntity"], Literal(entity_name)))
                g.add((entry, GDS_CORE["readVariable"], Literal(var_name)))

        g.add((spec_uri, GDS_CORE["hasTransitionSignature"], ts_uri))


def _find_entity_for_var(var_name: str, model: SysMLModel) -> str:
    """Search model parts for the entity containing a state variable."""
    for part in model.parts.values():
        for attr in part.attributes:
            if attr.name == var_name:
                return part.name
    return ""
