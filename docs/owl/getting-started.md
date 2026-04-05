# Getting Started

## Installation

```bash
pip install gds-interchange
```

For SHACL validation:

```bash
pip install gds-interchange[shacl]
```

## Build an Ontology

The core ontology defines OWL classes and properties for all GDS concepts:

```python
from gds_interchange.owl import build_core_ontology, to_turtle

ontology = build_core_ontology()
print(to_turtle(ontology))
```

This produces a Turtle document with classes like `gds-core:GDSSpec`, `gds-core:Mechanism`, `gds-core:Policy`, etc.

## Export a Spec to RDF

```python
from gds import GDSSpec, typedef, entity, state_var
from gds.blocks.roles import Mechanism
from gds.types.interface import Interface, port
from gds_interchange.owl import spec_to_graph, to_turtle

# Build a minimal spec
Float = typedef("Float", float)
spec = GDSSpec(name="Example")
spec.collect(
    Float,
    entity("Tank", level=state_var(Float)),
    Mechanism(
        name="Fill",
        interface=Interface(forward_in=(port("Flow Rate"),)),
        updates=[("Tank", "level")],
    ),
)

# Export to RDF
graph = spec_to_graph(spec)
print(to_turtle(graph))
```

## Import Back from RDF

```python
from rdflib import Graph
from gds_interchange.owl import graph_to_spec, to_turtle, spec_to_graph

# Round-trip: Pydantic -> Turtle -> Pydantic
graph = spec_to_graph(spec)
turtle_str = to_turtle(graph)

g2 = Graph()
g2.parse(data=turtle_str, format="turtle")
spec2 = graph_to_spec(g2)

assert spec2.name == "Example"
assert "Tank" in spec2.entities
```

## Validate with SHACL

```python
from gds_interchange.owl import build_all_shapes, validate_graph, spec_to_graph

graph = spec_to_graph(spec)
shapes = build_all_shapes()

conforms, results_graph, results_text = validate_graph(graph, shapes)
print(f"Conforms: {conforms}")
if not conforms:
    print(results_text)
```

## Query with SPARQL

```python
from gds_interchange.owl import TEMPLATES, spec_to_graph

graph = spec_to_graph(spec)

# List all blocks
for template in TEMPLATES:
    if template.name == "list_blocks":
        results = graph.query(template.query)
        for row in results:
            print(row)
```
