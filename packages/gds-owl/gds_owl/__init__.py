"""gds-owl — DEPRECATED: use gds_interchange.owl instead."""

import warnings

warnings.warn(
    "Import from gds_interchange.owl instead of gds_owl. "
    "The gds-owl package will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "0.99.0"

from gds_interchange.owl import (  # noqa: F401, E402
    GDS,
    GDS_CORE,
    GDS_IR,
    GDS_VERIF,
    PREFIXES,
    TEMPLATES,
    build_all_shapes,
    build_constraint_shapes,
    build_core_ontology,
    build_generic_shapes,
    build_semantic_shapes,
    build_structural_shapes,
    canonical_to_graph,
    canonical_to_turtle,
    graph_to_canonical,
    graph_to_report,
    graph_to_spec,
    graph_to_system_ir,
    report_to_graph,
    report_to_turtle,
    run_query,
    spec_to_graph,
    spec_to_turtle,
    system_ir_to_graph,
    system_ir_to_turtle,
    to_jsonld,
    to_ntriples,
    to_turtle,
    validate_graph,
)

__all__ = [
    "GDS",
    "GDS_CORE",
    "GDS_IR",
    "GDS_VERIF",
    "PREFIXES",
    "TEMPLATES",
    "build_all_shapes",
    "build_constraint_shapes",
    "build_core_ontology",
    "build_generic_shapes",
    "build_semantic_shapes",
    "build_structural_shapes",
    "canonical_to_graph",
    "canonical_to_turtle",
    "graph_to_canonical",
    "graph_to_report",
    "graph_to_spec",
    "graph_to_system_ir",
    "report_to_graph",
    "report_to_turtle",
    "run_query",
    "spec_to_graph",
    "spec_to_turtle",
    "system_ir_to_graph",
    "system_ir_to_turtle",
    "to_jsonld",
    "to_ntriples",
    "to_turtle",
    "validate_graph",
]
