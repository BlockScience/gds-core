# gds-owl

[![PyPI](https://img.shields.io/pypi/v/gds-owl)](https://pypi.org/project/gds-owl/)
[![Python](https://img.shields.io/pypi/pyversions/gds-owl)](https://pypi.org/project/gds-owl/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](https://github.com/DynamicalSystemsGroup/gds-core/blob/main/LICENSE)

**OWL/Turtle, SHACL, and SPARQL for GDS specifications** — semantic web interoperability for compositional systems.

## Package Identity

| Distribution | Import path | Purpose |
|--------------|-------------|---------|
| `gds-interchange` | `gds_interchange.owl` | Current package for OWL/Turtle, SHACL, SPARQL, and RDF round-trip tooling |
| `gds-owl` | `gds_interchange.owl` | Compatibility distribution and legacy documentation label |

## What is this?

`gds-owl` exports GDS specifications to RDF/OWL and imports them back, enabling interoperability with semantic web tooling. It provides:

- **OWL ontology** — class hierarchy mirroring GDS types (blocks, roles, entities, spaces, parameters)
- **RDF export/import** — lossless round-trip for structural fields (Pydantic → Turtle → Pydantic)
- **SHACL shapes** — constraint validation on exported RDF graphs (structural + semantic)
- **SPARQL queries** — pre-built query templates for common GDS analysis patterns
- **Formal representability analysis** — documented classification of what survives the OWL boundary

## When to Use It

Use this package when you need to:

- Export GDS specifications, compiled systems, or verification reports to RDF/Turtle.
- Validate exported graphs with SHACL constraints.
- Query GDS structures with SPARQL or load them into semantic-web infrastructure.
- Document which parts of a model survive an OWL boundary and which remain Python behavior.

Use [`gds-framework`](../framework/index.md) directly when you only need to build or verify models in Python. Use `gds-interchange` when those models need to move across semantic-web or RDF-based tooling.

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

## Relationship to the Ecosystem

`gds-owl` is the semantic interchange layer for GDS. It depends on `gds-framework` structures, consumes specifications and reports produced by the framework and proof packages, and emits RDF artifacts that can be inspected outside Python.

It complements the execution packages rather than replacing them: [`gds-sim`](../sim/index.md) runs dynamics, [`gds-analysis`](../analysis/index.md) studies results, and `gds-owl` makes structural and verification artifacts portable.

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
