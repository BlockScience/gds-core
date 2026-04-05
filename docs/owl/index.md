# gds-owl

[![PyPI](https://img.shields.io/pypi/v/gds-owl)](https://pypi.org/project/gds-owl/)
[![Python](https://img.shields.io/pypi/pyversions/gds-owl)](https://pypi.org/project/gds-owl/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**OWL/Turtle, SHACL, and SPARQL for GDS specifications** — semantic web interoperability for compositional systems.

## What is this?

`gds-owl` exports GDS specifications to RDF/OWL and imports them back, enabling interoperability with semantic web tooling. It provides:

- **OWL ontology** — class hierarchy mirroring GDS types (blocks, roles, entities, spaces, parameters)
- **RDF export/import** — lossless round-trip for structural fields (Pydantic → Turtle → Pydantic)
- **SHACL shapes** — constraint validation on exported RDF graphs (structural + semantic)
- **SPARQL queries** — pre-built query templates for common GDS analysis patterns
- **Formal representability analysis** — documented classification of what survives the OWL boundary

## Architecture

```
gds-framework (pip install gds-framework)
|
|  Domain-neutral composition algebra, typed spaces,
|  state model, verification engine, flat IR compiler.
|
+-- gds-owl (pip install gds-interchange)
    |
    |  OWL ontology (TBox), RDF export/import (ABox),
    |  SHACL validation, SPARQL query templates.
    |
    +-- Your application
        |
        |  Ontology browsers, SPARQL endpoints,
        |  cross-tool interoperability.
```

## Key Concepts

### Representability Tiers

Not everything in a GDS specification can be represented in OWL:

| Tier | What | Formalism | Example |
|------|------|-----------|---------|
| **R1** | Fully representable | OWL + SHACL | Block interfaces, role partition, wiring topology |
| **R2** | Structurally representable | SPARQL | Cycle detection, completeness, determinism |
| **R3** | Not representable | Python only | Transition functions, constraint predicates, auto-wiring |

The canonical decomposition `h = f . g` is the boundary: `g` (policy mapping) is entirely R1, `f` splits into structural (R1) and behavioral (R3).

### Round-Trip Guarantees

The export/import cycle preserves all structural fields. Known lossy fields:

- `TypeDef.constraint` — arbitrary `Callable`, imported as `None`
- `TypeDef.python_type` — falls back to `str` for unmapped types
- `AdmissibleInputConstraint.constraint` — same as TypeDef.constraint

### Four Export Targets

| Function | Input | Output |
|----------|-------|--------|
| `spec_to_graph()` | `GDSSpec` | RDF graph (ABox) |
| `system_ir_to_graph()` | `SystemIR` | RDF graph (ABox) |
| `canonical_to_graph()` | `CanonicalGDS` | RDF graph (ABox) |
| `report_to_graph()` | `VerificationReport` | RDF graph (ABox) |

## Installation

```bash
pip install gds-interchange

# With SHACL validation support:
pip install gds-interchange[shacl]
```

## Quick Example

```python
from gds import GDSSpec
from gds_interchange.owl import spec_to_graph, to_turtle, graph_to_spec

# Export a spec to Turtle
spec = GDSSpec(name="My System")
graph = spec_to_graph(spec)
print(to_turtle(graph))

# Import back
spec2 = graph_to_spec(graph)
assert spec2.name == spec.name
```
