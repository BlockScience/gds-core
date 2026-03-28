# CLAUDE.md -- gds-owl

## Package Identity

`gds-owl` provides OWL/Turtle, SHACL validation, and SPARQL queries for `gds-framework` specifications. Implements the R1/R2 representability tiers from the formal analysis.

- **Import**: `import gds_owl`
- **Dependencies**: `gds-framework>=0.2.3`, `rdflib>=7.0`
- **Optional**: `pyshacl>=0.27` for SHACL validation

## Architecture

| Module | Purpose | R-tier |
|--------|---------|--------|
| `export.py` | `spec_to_graph()`, `system_ir_to_graph()`, `canonical_to_graph()`, `report_to_graph()` | R1 |
| `import_.py` | `graph_to_spec()`, `graph_to_system_ir()`, `graph_to_canonical()`, `graph_to_report()` | R1 |
| `ontology.py` | `build_core_ontology()` — OWL class hierarchy | R1 |
| `shacl.py` | `validate_graph()`, `build_all_shapes()` — 13 SHACL shapes | R1 |
| `sparql.py` | `run_query(graph, template_name)` — pre-built SPARQL templates | R2 |
| `serialize.py` | `to_turtle()`, `to_jsonld()`, `to_ntriples()` | — |
| `_namespace.py` | `GDS`, `GDS_CORE`, `GDS_IR`, `GDS_VERIF`, `PREFIXES` | — |

### Round-trip fidelity

The `rho` mapping: `GDSSpec → RDF → GDSSpec` preserves all R1 fields (names, types, units, spaces, entities, blocks, roles, wirings, updates). R3 fields (`TypeDef.constraint`, `f_behav`) are correctly lossy — they become `None` after round-trip.

### SHACL shapes

13 shapes validating structural properties:
- `BlockIRShape`, `BoundaryActionShape`, `MechanismShape` — role constraints
- `WiringIRShape` — wire source/target
- `TypeDefShape`, `SpaceShape`, `EntityShape` — data model
- `AdmissibleInputConstraintShape`, `TransitionSignatureShape` — annotations

### SPARQL templates

Pre-built queries: `blocks_by_role`, `dependency_path`, `reachability`, `loop_detection`, `parameter_impact`, `entity_update_map`.

## Commands

```bash
uv run --package gds-owl pytest packages/gds-owl/tests -v
```
