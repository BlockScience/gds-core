"""Stage 5 — Querying Your Specification.

Use the SpecQuery API to explore the thermostat model's structure:
which parameters affect which blocks, which mechanisms update which
entities, and what the causal chain looks like.

New concepts:
    - SpecQuery: dependency analysis engine for GDSSpec
    - param_to_blocks(): parameter -> blocks that use it
    - entity_update_map(): entity -> variable -> mechanisms that update it
    - blocks_by_kind(): blocks grouped by GDS role
    - blocks_affecting(): causal chain from all influencing blocks to a variable
    - dependency_graph(): full block-to-block DAG from wirings

SpecQuery answers: "How does information flow through my specification?"
"""

from gds.query import SpecQuery
from gds.spec import GDSSpec
from guides.getting_started.stage3_dsl import build_spec


def build_query(spec: GDSSpec | None = None) -> SpecQuery:
    """Create a SpecQuery for the thermostat model."""
    if spec is None:
        spec = build_spec()
    return SpecQuery(spec)


def show_param_influence(query: SpecQuery) -> dict[str, list[str]]:
    """Which blocks does each parameter affect?

    For the thermostat DSL model, the 'heater' input is registered as
    a parameter (exogenous reference). This map shows which blocks
    reference each parameter via their params_used field.
    """
    return query.param_to_blocks()


def show_entity_updates(query: SpecQuery) -> dict[str, dict[str, list[str]]]:
    """Which mechanisms update each entity variable?

    Returns: {entity_name: {variable_name: [mechanism_names]}}

    For the thermostat, this shows that "temperature Dynamics" updates
    the "temperature" entity's "value" variable.
    """
    return query.entity_update_map()


def show_blocks_by_role(query: SpecQuery) -> dict[str, list[str]]:
    """Group all blocks by their GDS role.

    Roles: boundary, policy, mechanism, control, generic.
    The DSL maps: Input -> boundary, Sensor/Controller -> policy,
    State -> mechanism.
    """
    return query.blocks_by_kind()


def show_causal_chain(query: SpecQuery, entity: str, variable: str) -> list[str]:
    """Which blocks can transitively affect a specific state variable?

    Traces backwards through the dependency graph to find every block
    that can influence the given entity.variable, including direct
    mechanisms and upstream blocks that feed them.
    """
    return query.blocks_affecting(entity, variable)


def show_dependency_graph(query: SpecQuery) -> dict[str, set[str]]:
    """Full block-to-block dependency DAG from spec wirings.

    Returns: {source_block: {target_blocks}}

    This is the information flow graph: who feeds whom.
    """
    return query.dependency_graph()


if __name__ == "__main__":
    spec = build_spec()
    query = build_query(spec)

    print("=== Parameter Influence ===")
    for param, blocks in show_param_influence(query).items():
        print(f"  {param} -> {blocks}")

    print("\n=== Entity Update Map ===")
    for entity, vars_map in show_entity_updates(query).items():
        for var, mechs in vars_map.items():
            print(f"  {entity}.{var} <- {mechs}")

    print("\n=== Blocks by Role ===")
    for role, blocks in show_blocks_by_role(query).items():
        if blocks:
            print(f"  {role}: {blocks}")

    print("\n=== Causal Chain: temperature.value ===")
    affecting = show_causal_chain(query, "temperature", "value")
    print(f"  Blocks affecting temperature.value: {affecting}")

    print("\n=== Dependency Graph ===")
    for source, targets in show_dependency_graph(query).items():
        print(f"  {source} -> {targets}")
