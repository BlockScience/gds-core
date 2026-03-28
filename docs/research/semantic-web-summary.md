# Semantic Web Integration: What We Learned

A team summary of GDS + OWL/SHACL/SPARQL integration via `gds-owl`.

## The Short Version

We can export **85% of a GDS specification** to Turtle/RDF files and
import it back losslessly. The 15% we lose is Python callables (transition
functions, constraint predicates, distance functions). This is a
mathematical certainty, not a gap we can close.

## What Gets Exported (R1 -- Fully Representable)

Everything structural round-trips perfectly through Turtle:

| GDS Concept | RDF Representation | Validated By |
|---|---|---|
| Block names, roles, interfaces | OWL classes + properties | SHACL shapes |
| Port names and type tokens | Literals on Port nodes | SHACL datatype |
| Wiring topology (who connects to whom) | Wire nodes with source/target | SHACL cardinality |
| Entity/StateVariable declarations | Entity + StateVariable nodes | SHACL |
| TypeDef (name, python_type, units) | TypeDef node + properties | SHACL |
| Space fields | SpaceField blank nodes | SHACL |
| Parameter schema (names, types, bounds) | ParameterDef nodes | SHACL |
| Mechanism update targets (what writes where) | UpdateMapEntry nodes | SHACL |
| Admissibility dependencies (what reads what) | AdmissibilityDep nodes | SHACL |
| Transition read dependencies | TransitionReadEntry nodes | SHACL |
| State metric variable declarations | MetricVariableEntry nodes | SHACL |
| Canonical decomposition (h = f . g) | CanonicalGDS node | SHACL |
| Verification findings | Finding nodes | SHACL |

**13 SHACL shapes** enforce structural correctness on the RDF graph.
**7 SPARQL query templates** enable cross-node analysis (blocks by role,
dependency paths, entity update maps, parameter impact, verification summaries).

## What Requires SPARQL (R2 -- Structurally Representable)

Some properties can't be checked by SHACL alone (which validates individual
nodes) but CAN be checked by SPARQL queries over the full graph:

| Property | SPARQL Feature | Why SHACL Can't |
|---|---|---|
| Acyclicity (G-006) | Transitive closure (`p+`) | No path traversal in SHACL-core |
| Completeness (SC-001) | `FILTER NOT EXISTS` | No "for all X, exists Y" |
| Determinism (SC-002) | `GROUP BY` + `HAVING` | No cross-node aggregation |
| Dangling wirings (G-004) | `FILTER NOT EXISTS` | Name existence, not class membership |

These all terminate (SPARQL over finite graphs always does) and are decidable.

## What Cannot Be Exported (R3 -- Not Representable)

These are **fundamentally** non-exportable. Not a tooling gap -- a
mathematical impossibility (Rice's theorem for callables, computational
class separation for string processing):

| GDS Concept | Why R3 | What Happens on Export |
|---|---|---|
| `TypeDef.constraint` (e.g. `lambda x: x >= 0`) | Arbitrary Python callable | Exported as boolean flag `hasConstraint`; imported as `None` |
| `f_behav` (transition functions) | Arbitrary computation | Not stored in GDSSpec -- user responsibility |
| `AdmissibleInputConstraint.constraint` | Arbitrary callable | Exported as boolean flag; imported as `None` |
| `StateMetric.distance` | Arbitrary callable | Exported as boolean flag; imported as `None` |
| Auto-wiring token computation | Multi-pass string processing | Results exported (WiringIR edges); process is not |
| Construction validation | Python `@model_validator` logic | Structural result preserved; validation logic is not |

**Key insight:** The *results* of R3 computation are always R1. Auto-wiring
produces WiringIR edges (R1). Validation produces pass/fail (R1). Only the
*process* is lost.

## The Boundary in One Sentence

> **You can represent everything about a system except what its programs
> actually do.** The canonical decomposition `h = f . g` makes this
> boundary explicit: `g` (topology) and `f_struct` (update targets) are
> fully representable; `f_behav` (how state actually changes) is not.

## Practical Implications

### What You Can Do With the Turtle Export

1. **Share specs between tools** -- any RDF-aware tool (Protege, GraphDB,
   Neo4j via neosemantics) can import a GDS spec
2. **Validate specs without Python** -- SHACL processors (TopBraid, pySHACL)
   can check structural correctness
3. **Query specs with SPARQL** -- find all mechanisms that update a given
   entity, trace dependency paths, check acyclicity
4. **Version and diff specs** -- Turtle is text, diffs are meaningful
5. **Cross-ecosystem interop** -- other OWL ontologies can reference GDS
   classes/properties

### What You Cannot Do

1. **Run simulations from Turtle** -- you need the Python callables back
2. **Verify behavioral properties** -- "does this mechanism converge?" requires
   executing `f_behav`
3. **Reproduce auto-wiring** -- the token overlap computation can't run in SPARQL

### Round-Trip Fidelity

Tested with property-based testing (Hypothesis): 100 random GDSSpecs
generated, exported to Turtle, parsed back, reimported. All structural
fields survive. Known lossy fields:

- `TypeDef.constraint` -> `None`
- `TypeDef.python_type` -> falls back to `str` for non-builtin types
- `AdmissibleInputConstraint.constraint` -> `None`
- `StateMetric.distance` -> `None`
- Port/wire ordering -> set-based (RDF is unordered)
- Blank node identity -> content-based comparison, not node ID

## Numbers

| Metric | Count |
|---|---|
| R1 concepts (fully representable) | 13 |
| R2 concepts (SPARQL-needed) | 3 |
| R3 concepts (not representable) | 7 |
| SHACL shapes | 18 |
| SPARQL templates | 7 |
| Verification checks expressible in SHACL | 6 of 15 |
| Verification checks expressible in SPARQL | 6 more |
| Checks requiring Python | 2 of 15 |
| Round-trip PBT tests | 26 |
| Random specs tested | ~2,600 |

## Paper Alignment

The structural/behavioral split is a **framework design choice**, not a
paper requirement. The GDS paper (Zargham & Shorish 2022) defines
`U: X -> P(U)` as a single map; we split it into `U_struct` (dependency
graph, R1) and `U_behav` (constraint predicate, R3) for ontological
engineering. Same for `StateMetric` and `TransitionSignature`. The
canonical decomposition `h = f . g` IS faithful to the paper.

## Open Question: Promoting Common Constraints to R2

Zargham's feedback: *"We can probably classify them as two different
kinds of predicates -- those associated with the model structure
(owl/shacl/sparql) and those associated with the runtime."*

Currently all `TypeDef.constraint` callables are treated as R3 (lossy).
But many common constraints ARE expressible in SHACL:

- `lambda x: x >= 0` --> `sh:minInclusive 0`
- `lambda x: 0 <= x <= 1` --> `sh:minInclusive 0` + `sh:maxInclusive 1`
- `lambda x: x in {-1, 0, 1}` --> `sh:in (-1 0 1)`

A constraint classifier could promote these from R3 to R2, making them
round-trippable through Turtle. The general case (arbitrary callable)
remains R3. See #152 for the design proposal.

## Files

- `packages/gds-owl/` -- the full export/import/SHACL/SPARQL implementation
- `docs/research/formal-representability.md` -- the 800-line formal analysis
- `docs/research/verification/r3-undecidability.md` -- proofs for the R3 boundary
- `docs/research/verification/representability-proof.md` -- R1/R2 decidability + partition independence
