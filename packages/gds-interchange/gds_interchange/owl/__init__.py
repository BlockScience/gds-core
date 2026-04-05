"""OWL/Turtle, SHACL, and SPARQL for gds-framework specifications."""

from gds_interchange.owl._namespace import (
    GDS,
    GDS_CORE,
    GDS_IR,
    GDS_VERIF,
    PREFIXES,
)
from gds_interchange.owl.export import (
    canonical_to_graph,
    report_to_graph,
    spec_to_graph,
    system_ir_to_graph,
)
from gds_interchange.owl.import_ import (
    graph_to_canonical,
    graph_to_report,
    graph_to_spec,
    graph_to_system_ir,
)
from gds_interchange.owl.ontology import build_core_ontology
from gds_interchange.owl.serialize import (
    canonical_to_turtle,
    report_to_turtle,
    spec_to_turtle,
    system_ir_to_turtle,
    to_jsonld,
    to_ntriples,
    to_turtle,
)
from gds_interchange.owl.shacl import (
    build_all_shapes,
    build_constraint_shapes,
    build_generic_shapes,
    build_semantic_shapes,
    build_structural_shapes,
    validate_graph,
)
from gds_interchange.owl.sparql import TEMPLATES, run_query

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
