"""SPARQL query templates for GDS RDF graphs.

Pre-built queries for common analyses: dependency paths, reachability,
loop detection, parameter impact, block grouping, and entity update maps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rdflib import Graph


@dataclass(frozen=True)
class SPARQLTemplate:
    """A named, parameterized SPARQL query template."""

    name: str
    description: str
    query: str


# ── Template Registry ────────────────────────────────────────────────

TEMPLATES: dict[str, SPARQLTemplate] = {}


def _register(t: SPARQLTemplate) -> SPARQLTemplate:
    TEMPLATES[t.name] = t
    return t


# ── Pre-built Queries ────────────────────────────────────────────────

_register(
    SPARQLTemplate(
        name="blocks_by_role",
        description="Group all blocks by their role (kind).",
        query="""\
PREFIX gds-core: <https://gds.block.science/ontology/core/>

SELECT ?block_name ?kind
WHERE {
    ?block gds-core:kind ?kind .
    ?block gds-core:name ?block_name .
}
ORDER BY ?kind ?block_name
""",
    )
)

_register(
    SPARQLTemplate(
        name="dependency_path",
        description="All wired connections in a GDSSpec.",
        query="""\
PREFIX gds-core: <https://gds.block.science/ontology/core/>

SELECT ?wiring_name ?source ?target ?space ?optional
WHERE {
    ?wiring a gds-core:SpecWiring ;
            gds-core:name ?wiring_name ;
            gds-core:hasWire ?wire .
    ?wire gds-core:wireSource ?source ;
          gds-core:wireTarget ?target .
    OPTIONAL { ?wire gds-core:wireSpace ?space }
    OPTIONAL { ?wire gds-core:wireOptional ?optional }
}
ORDER BY ?wiring_name ?source ?target
""",
    )
)

_register(
    SPARQLTemplate(
        name="entity_update_map",
        description="Which mechanisms update which entity variables.",
        query="""\
PREFIX gds-core: <https://gds.block.science/ontology/core/>

SELECT ?block_name ?entity ?variable
WHERE {
    ?block a gds-core:Mechanism ;
           gds-core:name ?block_name ;
           gds-core:updatesEntry ?entry .
    ?entry gds-core:updatesEntity ?entity ;
           gds-core:updatesVariable ?variable .
}
ORDER BY ?block_name ?entity ?variable
""",
    )
)

_register(
    SPARQLTemplate(
        name="param_impact",
        description="Which parameters are used by which blocks.",
        query="""\
PREFIX gds-core: <https://gds.block.science/ontology/core/>

SELECT ?param_name ?block_name ?kind
WHERE {
    ?block gds-core:usesParameter ?param .
    ?param gds-core:name ?param_name .
    ?block gds-core:name ?block_name .
    ?block gds-core:kind ?kind .
}
ORDER BY ?param_name ?block_name
""",
    )
)

_register(
    SPARQLTemplate(
        name="ir_block_list",
        description="List all BlockIR nodes in a SystemIR with their types.",
        query="""\
PREFIX gds-core: <https://gds.block.science/ontology/core/>
PREFIX gds-ir: <https://gds.block.science/ontology/ir/>

SELECT ?block_name ?block_type ?logic
WHERE {
    ?block a gds-ir:BlockIR ;
           gds-core:name ?block_name .
    OPTIONAL { ?block gds-ir:blockType ?block_type }
    OPTIONAL { ?block gds-ir:logic ?logic }
}
ORDER BY ?block_name
""",
    )
)

_register(
    SPARQLTemplate(
        name="ir_wiring_list",
        description="List all WiringIR edges in a SystemIR.",
        query="""\
PREFIX gds-ir: <https://gds.block.science/ontology/ir/>

SELECT ?source ?target ?label ?direction ?is_feedback ?is_temporal
WHERE {
    ?wiring a gds-ir:WiringIR ;
            gds-ir:source ?source ;
            gds-ir:target ?target .
    OPTIONAL { ?wiring gds-ir:label ?label }
    OPTIONAL { ?wiring gds-ir:direction ?direction }
    OPTIONAL { ?wiring gds-ir:isFeedback ?is_feedback }
    OPTIONAL { ?wiring gds-ir:isTemporal ?is_temporal }
}
ORDER BY ?source ?target
""",
    )
)

_register(
    SPARQLTemplate(
        name="verification_summary",
        description="Summary of verification findings by check ID and severity.",
        query="""\
PREFIX gds-verif: <https://gds.block.science/ontology/verification/>

SELECT ?check_id ?severity ?passed ?message
WHERE {
    ?finding a gds-verif:Finding ;
             gds-verif:checkId ?check_id ;
             gds-verif:severity ?severity ;
             gds-verif:passed ?passed .
    OPTIONAL { ?finding gds-verif:message ?message }
}
ORDER BY ?check_id
""",
    )
)


# ── Query Execution ──────────────────────────────────────────────────


def run_query(
    graph: Graph,
    template_name: str,
    **params: str,
) -> list[dict[str, Any]]:
    """Run a registered SPARQL template against a graph.

    Parameters can be substituted into the query using Python string
    formatting ({param_name} placeholders).

    Returns a list of dicts, one per result row, with variable names as keys.
    """
    if template_name not in TEMPLATES:
        raise KeyError(
            f"Unknown template '{template_name}'. Available: {sorted(TEMPLATES.keys())}"
        )
    template = TEMPLATES[template_name]
    query = template.query.format(**params) if params else template.query
    results = graph.query(query)
    return [{str(var): row[i] for i, var in enumerate(results.vars)} for row in results]
