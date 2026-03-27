# Representability Analysis: GDS in OWL/SHACL/SPARQL

A design rationale document classifying which GDS concepts can and cannot
be represented in semantic web formalisms, grounded in the
compositionality-temporality boundary and the canonical decomposition
h = f ∘ g.

---

## Overview

### The representation boundary is h = f ∘ g

The GDS canonical decomposition h = f ∘ g is not just mathematical
notation — it is the exact line where formal representation changes
character:

- **g** (policy mapping): which blocks connect to what, in what roles,
  through what wires. Fully representable — by design, GDSSpec stores no
  behavioral content here.
- **f_struct** (update map): "Mechanism M updates Entity E variable V."
  Fully representable — a finite relation.
- **f_behav** (transition function): "Given state x and decisions d,
  compute new state x'." Not representable — arbitrary computation.

Everything to the left of f_behav is topology. Everything at f_behav and
beyond is computation. OWL/SHACL/SPARQL live on the topology side. Python
lives on both sides.

### Composition: structure preserved, process lost

The five composition operators (>>, |, feedback, loop) and their resulting
trees survive OWL round-trip perfectly. You can reconstruct exactly how a
system was assembled.

The *process* of composition — auto-wiring via token overlap, port
matching, construction-time validation — requires Python string computation
that SPARQL cannot replicate. But this gap is **moot in practice**: gds-owl
materializes both the tokens (as `typeToken` literals) and the wired
connections (as explicit `WiringIR` edges) during export. The RDF consumer
never needs to recompute what Python already computed.

This reveals a general design principle: **materialize computation results
as data before export, and the representation gap closes for practical
purposes.**

### Temporality: structure preserved, semantics lost

A `TemporalLoop` (physical state at t feeds sensors at t+1) and a
`CorecursiveLoop` (decisions at round t feed observations at round t+1)
have identical RDF representation: covariant wiring from inner.forward_out
to inner.forward_in with an exit_condition string. OWL captures "there is
a loop" but not "what kind of time this loop means." The interpretation
requires knowing which DSL compiled the system — that is metadata
(preserved via `gds-ir:sourceLabel`), not topology.

State evolution itself — computing x_{t+1} = f(x_t, g(x_t, u_t)) — is
fundamentally not representable. You need a runtime, period.

### The data/computation duality

The same pattern recurs at every level of GDS:

| Data (representable) | Computation (not representable) |
|---|---|
| Token sets on ports | The `tokenize()` function that produces them |
| Wired connections | The auto-wiring process that discovers them |
| Constraint bounds (0 <= x <= 1) | Arbitrary `Callable[[Any], bool]` constraints |
| Update map (M updates E.V) | Transition function (how V changes) |
| Equilibrium structure (which games compose how) | Equilibrium computation (finding Nash equilibria) |
| Wiring graph topology (can A reach B?) | Signal propagation (does A's output actually affect B?) |

If you materialize computation results as data before crossing the
boundary, the gap shrinks to what genuinely requires a runtime: simulation,
constraint evaluation, and equilibrium solving.

### The validation stack

The three semantic web formalisms serve architecturally distinct roles —
a validation stack, not a containment chain:

| Layer | Formalism | Role | Example |
|---|---|---|---|
| Vocabulary | OWL | Defines what things *are* | "A Mechanism is a kind of AtomicBlock" |
| Local constraints | SHACL-core | Validates individual nodes | "Every Mechanism must update >= 1 state variable" |
| Graph patterns | SPARQL | Validates cross-node relationships | "No two mechanisms update the same (entity, variable) pair" |
| Computation | Python | Evaluates functions, evolves state | "Given x=0.5, f(x) = 0.7" |

Each step adds expressiveness and loses decidability guarantees. The
R1/R2/R3 tier system in this document maps directly onto this stack.

### Architectural consequences

1. **RDF is a viable structural interchange format.** Of 13 verification
   checks, 4 are SHACL-expressible, 6 more with SPARQL, only 2 genuinely
   need Python. The structural skeleton carries the vast majority of system
   information.

2. **Games are naturally ontological.** When h = g (no state, no f), the
   GDSSpec projection is lossless. Games are morphisms between spaces, not
   state machines. Game composition maps cleanly to OWL because it is all
   structure.

3. **Dynamical systems degrade gracefully.** Each mechanism contributes one
   representable fact (what it updates) and one non-representable fact (how
   it computes). The structural skeleton is always complete; what degrades
   is the fraction of total content it represents.

4. **The canonical form is architecturally load-bearing.** By separating
   "what connects to what" (g) from "what the connections compute"
   (f_behav), GDS provides a clean cut point for partial representation,
   cross-tool interop, and formal reasoning.

The representability boundary is Rice's theorem applied to system
specifications: you can represent everything about a system except what
its programs actually do. The canonical decomposition h = f ∘ g makes this
boundary explicit and exploitable.

---

## 1. Preliminaries

### 1.1 GDS Formal Objects

**Definition 1.1 (Composition Algebra).** The GDS composition algebra is
a tuple (Block, >>, |, fb, loop) with operations inspired by symmetric
monoidal categories with feedback. The operations satisfy the expected
algebraic properties (associativity of >> and |, commutativity of |) by
construction, but the full categorical axioms (interchange law, coherence
conditions, traced monoidal structure for feedback) have not been formally
verified.

The components are:

- **Objects** are Interfaces: I = (F_in, F_out, B_in, B_out), each a tuple
  of Ports
- **Morphisms** are Blocks: typed components with bidirectional interfaces
- **>>** (sequential): first ; second with token-overlap validation
- **|** (parallel): left tensor right, no shared wires
- **fb** (feedback): contravariant backward flow within timestep
- **loop** (temporal): covariant forward flow across timesteps

**Definition 1.2 (Token System).** Port names carry structural type
information via tokenization:

```
tokenize : PortName -> P(Token)

Split on {' + ', ', '}, then lowercase each part.
"Temperature + Setpoint" |-> {"temperature", "setpoint"}
"Heater Command"         |-> {"heater command"}
```

Token overlap is the auto-wiring predicate:

```
compatible(p1, p2) := tokenize(p1.name) ∩ tokenize(p2.name) != empty
```

**Definition 1.3 (GDSSpec).** A specification is a 6-tuple:

```
S = (T, Sp, E, B, W, Theta)

T     : Name -> TypeDef           (type registry)
Sp    : Name -> Space             (typed product spaces)
E     : Name -> Entity            (state holders with typed variables)
B     : Name -> Block             (typed compositional blocks)
W     : Name -> SpecWiring        (named compositions with explicit wires)
Theta : Name -> ParameterDef      (configuration space)
```

While presented as a 6-tuple, these components are cross-referencing:
blocks reference types, wirings reference blocks, entities reference types.
GDSSpec is more precisely a labeled graph of registries with typed edges.

**Definition 1.4 (Canonical Decomposition).** The projection
pi : GDSSpec -> CanonicalGDS yields:

```
C = (X, U, D, Theta, g, f, h)

X = product_{(e,v) in E} TypeDef(e.variables[v])    state space
U = {(b, p) : b in B_boundary, p in b.forward_out}  input space
D = {(b, p) : b in B_policy, p in b.forward_out}    decision space
g : X x U -> D                                       policy mapping
f : X x D -> X                                       state transition
h_theta : X -> X  where  h = f ∘ g                   composed transition
```

**Definition 1.5 (Role Partition).** Blocks partition into disjoint roles:

```
B = B_boundary  disjoint-union  B_control  disjoint-union  B_policy  disjoint-union  B_mechanism

B_boundary  : forward_in = empty                (exogenous input)
B_mechanism : backward_in = backward_out = empty (state update)
B_policy    : no structural constraints           (decision logic)
B_control   : no structural constraints           (endogenous feedback)
```

**Definition 1.6 (TypeDef).** A type definition carries two levels:

```
TypeDef = (name, python_type, constraint, units)

python_type : type                  (language-level type object)
constraint  : Optional[Any -> bool] (runtime validation predicate)
```

The constraint field admits arbitrary Callable — this is Turing-complete.

### 1.2 Semantic Web Formal Objects

**Definition 1.7 (OWL DL).** OWL DL is based on the description logic
SROIQ(D). It provides class-level entailment under the **open-world
assumption** (OWA): absence of a statement does not imply its negation.

- **Class declarations**: C, with subsumption C1 sqsubseteq C2
- **Object properties**: R : C1 -> C2 (binary relations between individuals)
- **Datatype properties**: R : C -> Literal (attributes with XSD types)
- **Restrictions**: cardinality (min/max), value constraints, disjointness

Key property: **every entailment query terminates** (decidable).

**Definition 1.8 (SHACL).** The Shapes Constraint Language validates RDF
graphs against declared shapes under the **closed-world assumption** (CWA):
the graph is taken as complete, and missing data counts as a violation.

- **Node shapes**: target a class, constrain its properties
- **Property shapes**: cardinality (sh:minCount, sh:maxCount), datatype,
  class membership
- **SPARQL-based constraints**: sh:sparql embeds SELECT queries as validators

SHACL is not a reasoning system — it validates data, not entailment.

**Definition 1.9 (SPARQL 1.1).** A query language for pattern matching
and aggregation over RDF graphs:

- **Property paths**: transitive closure (p+), alternatives (p1|p2)
- **Negation**: FILTER NOT EXISTS { pattern }
- **Aggregation**: GROUP BY, HAVING, COUNT
- **Graph patterns**: triple patterns with variables, OPTIONAL, UNION

Key limitation: **no mutable state, no unbounded recursion, no string
computation** beyond regex matching.

**Remark 1.10 (Complementary formalisms).** OWL, SHACL, and SPARQL solve
different problems under different assumptions:

- OWL DL: class-level entailment (OWA, monotonic)
- SHACL: graph shape validation (CWA, non-monotonic)
- SPARQL: graph pattern queries with aggregation and negation

They do not form a simple containment chain. However, for the specific
purpose of **enforcing constraints on GDS-exported RDF graphs**, we
distinguish three tiers of validation expressiveness:

```
SHACL-core (node/property shapes)  <  SPARQL graph patterns  <  Turing-complete
```

OWL defines the vocabulary (classes, properties, subsumption). SHACL-core
— node shapes, property shapes with cardinality/datatype/class constraints,
but *without* sh:sparql — validates individual nodes against local
constraints. SPARQL graph patterns (standalone or embedded in SHACL via
sh:sparql) can express cross-node patterns: negation-as-failure, transitive
closure, aggregation. None can express arbitrary computation.

This three-level ordering directly motivates the R1/R2/R3 tiers in
Definition 2.2: R1 maps to OWL + SHACL-core, R2 maps to SPARQL, R3
exceeds all three formalisms.

---

## 2. Representability Classification

**Definition 2.1 (Representation Function).** Let rho be the mapping from
GDS concepts to RDF graphs implemented by gds-owl's export functions:

```
rho_spec : GDSSpec -> Graph       (spec_to_graph)
rho_ir   : SystemIR -> Graph      (system_ir_to_graph)
rho_can  : CanonicalGDS -> Graph  (canonical_to_graph)
rho_ver  : VerificationReport -> Graph  (report_to_graph)
```

And rho^{-1} the inverse mapping (import functions):

```
rho^{-1}_spec : Graph -> GDSSpec       (graph_to_spec)
rho^{-1}_ir   : Graph -> SystemIR      (graph_to_system_ir)
rho^{-1}_can  : Graph -> CanonicalGDS  (graph_to_canonical)
rho^{-1}_ver  : Graph -> VerificationReport  (graph_to_report)
```

**Remark 2.1 (Bijectivity caveats).** rho is injective on structural
fields but not surjective onto all possible RDF graphs (only well-formed
GDS graphs are in the image). rho^{-1} is a left inverse on structural
fields: rho^{-1}(rho(c)) =_struct c. Three edge cases weaken strict
bijectivity:

1. **Ordering**: RDF multi-valued properties are unordered. Port lists and
   wire lists may return in different order after round-trip. Equality is
   set-based, not sequence-based.
2. **Blank nodes**: Space fields and update map entries use RDF blank nodes.
   These have no stable identity across serializations. Structural equality
   compares by content (field name + type), not by node identity.
3. **Lossy fields**: TypeDef.constraint is always None after import.
   TypeDef.python_type falls back to `str` for types not in the built-in
   map. These are documented R3 losses, not bijectivity failures.

The round-trip suite (test_roundtrip.py: TestSpecRoundTrip,
TestSystemIRRoundTrip, TestCanonicalRoundTrip, TestReportRoundTrip)
verifies structural equality under these conventions for all four
rho/rho^{-1} pairs.

**Definition 2.2 (Representability Tiers).** A GDS concept c belongs to:

**R1 (Fully representable)** if rho^{-1}(rho(c)) is structurally equal
to c. The round-trip preserves all fields. Invariants on c are expressible
as OWL class/property structure or SHACL cardinality/class shapes.

**R2 (Structurally representable)** if rho preserves identity, topology,
and classification, but loses behavioral content. Validation requires
SPARQL graph pattern queries (negation-as-failure, transitive closure,
aggregation) that exceed SHACL's node/property shape expressiveness. The
behavioral projection, if any, is not representable.

**R3 (Not representable)** if no finite OWL/SHACL/SPARQL expression can
capture the concept. The gap is fundamental — it follows from:
- **Rice's theorem**: any non-trivial semantic property of programs is
  undecidable
- **The halting problem**: arbitrary Callable may not terminate
- **Computational class separation**: string parsing and temporal execution
  exceed the expressiveness of all three formalisms

---

## 3. Layer 0 Representability: Composition Algebra

**Property 3.1 (Composition Tree is R1).** The block composition tree —
including all 5 block types (AtomicBlock, StackComposition,
ParallelComposition, FeedbackLoop, TemporalLoop) with their structural
fields — is fully representable in OWL.

*Argument.* The representation function rho maps:

```
AtomicBlock         |-> gds-core:AtomicBlock  (owl:Class)
StackComposition    |-> gds-core:StackComposition + first, second (owl:ObjectProperty)
ParallelComposition |-> gds-core:ParallelComposition + left, right
FeedbackLoop        |-> gds-core:FeedbackLoop + inner
TemporalLoop        |-> gds-core:TemporalLoop + inner
```

The OWL class hierarchy mirrors the Python class hierarchy. The
`first`, `second`, `left`, `right`, `inner` object properties capture the
tree structure. The round-trip test `test_roundtrip.py::
TestSystemIRRoundTrip` verifies structural equality after
Graph -> Turtle -> Graph -> Pydantic.

The interface (F_in, F_out, B_in, B_out) is represented via four
object properties (hasForwardIn, hasForwardOut, hasBackwardIn,
hasBackwardOut) each pointing to Port individuals with portName and
typeToken datatype properties. Port ordering within a direction may differ
(RDF is unordered), but the *set* of ports is preserved.

**Property 3.2 (Token Data R1, Auto-Wiring Process R3).** The materialized
token data (the frozenset of strings on each Port) is R1. The auto-wiring
process that uses tokenize() to discover connections is R3.

*Argument.* Each Port stores `type_tokens: frozenset[str]`. These are
exported as multiple `gds-core:typeToken` literals per Port individual. The
round-trip preserves the token set exactly (unordered collection ->
multi-valued RDF property -> unordered collection).

Since gds-owl already materializes tokens during export, the RDF consumer
never needs to run tokenize(). The tokens are data, not computation. The
R3 classification applies specifically to **auto-wiring as a process**:
discovering which ports should connect by computing token overlap from port
name strings. This requires the tokenize() function (string splitting +
lowercasing). While SPARQL CONSTRUCT can generate new triples from pattern
matches, it cannot generate an unbounded number of new nodes from a single
string value — the split points must be known at query-write time. Since
GDS port names use variable numbers of delimiters, a fixed SPARQL query
cannot handle all cases.

In practice this is a moot point: the *wired connections* are exported as
explicit WiringIR edges (R1). Only the *process of discovering them* is not
replicable.

**Property 3.3 (Block Roles are R1).** The role partition
B = B_boundary disjoint-union B_control disjoint-union B_policy disjoint-union B_mechanism
is fully representable as OWL disjoint union classes (owl:disjointUnionOf).

*Argument.* Each role maps to an OWL class (gds-core:BoundaryAction,
gds-core:Policy, gds-core:Mechanism, gds-core:ControlAction), all declared
as subclasses of gds-core:AtomicBlock. Role-specific structural constraints
are SHACL-expressible:

- BoundaryAction: `sh:maxCount 0` on `hasForwardIn` (no forward inputs)
- Mechanism: `sh:maxCount 0` on `hasBackwardIn` and `hasBackwardOut`
- Mechanism: `sh:minCount 1` on `updatesEntry` (must update state)

**Proposition 3.4 (Operators: Structure R1, Validation R3).** The
composition operators `>>`, `|`, `.feedback()`, `.loop()` are R1 as
*structure* (the resulting tree is preserved in RDF) but R3 as *process*
(the validation logic run during construction cannot be replicated).

Specifically:
- `>>` validates token overlap between first.forward_out and
  second.forward_in — requires tokenize() (R3)
- `.loop()` enforces COVARIANT-only on temporal_wiring — the flag check
  is R1 (SHACL on direction property), but port matching uses tokens (R3)

---

## 4. Layer 1 Representability: Specification Framework

**Property 4.1 (GDSSpec Structure is R1).** The 6-tuple
S = (T, Sp, E, B, W, Theta) round-trips through OWL losslessly for all
structural fields.

*Argument.* Each component maps to an OWL class with named properties:

```
TypeDef     |-> gds-core:TypeDef       + name, pythonType, units, hasConstraint
Space       |-> gds-core:Space         + name, description, hasField -> SpaceField
Entity      |-> gds-core:Entity        + name, description, hasVariable -> StateVariable
Block       |-> gds-core:{role class}  + name, kind, hasInterface, usesParameter, ...
SpecWiring  |-> gds-core:SpecWiring    + name, wiringBlock, hasWire -> Wire
ParameterDef|-> gds-core:ParameterDef  + name, paramType, lowerBound, upperBound
```

The `test_roundtrip.py::TestSpecRoundTrip` suite verifies: types, spaces,
entities, blocks (with role, params, updates), parameters, and wirings all
survive the round-trip. The documented exception is TypeDef.constraint
(Property 4.2).

**Property 4.2 (Constraint Predicates).** The constraints used in practice
across all GDS DSLs (numeric bounds, non-negativity, probability ranges)
are expressible in SHACL (`sh:minInclusive`, `sh:maxInclusive`). This
covers Probability, NonNegativeFloat, PositiveInt, and most GDS built-in
types. These specific constraints are R2.

The general case — TypeDef.constraint : Optional[Callable[[Any], bool]] —
is R3. By Rice's theorem, any non-trivial semantic property of such
functions is undecidable:

- Given two constraints c1, c2, the question "do c1 and c2 accept the
  same values?" is undecidable (equivalence of arbitrary programs)
- Given a constraint c, the question "does c accept any value?" is
  undecidable (non-emptiness of the accepted set)

OWL DL is decidable (SROIQ). SHACL with SPARQL constraints is decidable
on finite graphs. Neither can embed an undecidable problem. This
theoretical limit rarely applies to real GDS specifications, where
constraints are simple numeric bounds.

**Observation 4.3 (Policy Mapping g is R1 by Design).** By design, GDSSpec
stores no behavioral content for policy blocks. A Policy block is defined
by what it connects to (interface, wiring position, parameter dependencies),
not by what it computes. Consequently, the policy mapping g in the
canonical form h = f ∘ g is fully characterized by structural fields, all
of which are R1 (Property 3.1, 3.3, 4.1).

This is a design decision, not a mathematical necessity — one could
imagine a framework that attaches executable policy functions to blocks.
GDS deliberately does not, keeping the specification layer structural.

**Property 4.4 (State Transition f Decomposes).** The state transition f
decomposes as a tuple f = ⟨f_struct, f_behav⟩ where:

```
f_struct : B_mechanism -> P(E x V)
    The explicit topological mapping from mechanisms to state variables.
    "Mechanism M updates Entity E variable V."
    This is a finite relation — R1.

f_behav : X x D -> X
    The endomorphism on the state space parameterized by decisions.
    "Given current state x and decisions d, compute next state x'."
    This is an arbitrary computable function — R3.
```

The composed system h = f ∘ g inherits: the structural decomposition
(which blocks compose into h, via what wirings) is R1. The execution
semantics (what h actually computes given inputs) is R3.

---

## 5. Verification Check Classification

Each of the 13 GDS verification checks is classified by whether
SHACL/SPARQL can express it on the exported RDF graph, with practical
impact noted.

### 5.1 Generic Checks (on SystemIR)

| Check | Property | Tier | Justification | Practical Impact |
|---|---|---|---|---|
| **G-001** | Domain/codomain matching | **R3** | Requires tokenize() — string splitting computation | Low: wired connections already exported as explicit edges |
| **G-002** | Signature completeness | **R1** | Cardinality check on signature fields. SHACL sh:minCount. | Covered by SHACL |
| **G-003** | Direction consistency | **R1** (flags) / **R3** (ports) | Flag contradiction is boolean — SHACL expressible. Port matching uses tokens (R3). | Flags covered; port check deferred to Python |
| **G-004** | Dangling wirings | **R2** | WiringIR source/target are string literals (datatype properties), not object property references. Checking that a string name appears in the set of BlockIR names requires SPARQL negation-as-failure on string matching. Unlike SC-005 where `usesParameter` is an object property. | Expressible via SPARQL |
| **G-005** | Sequential type compatibility | **R3** | Same tokenize() requirement as G-001 | Low: same mitigation as G-001 |
| **G-006** | Covariant acyclicity (DAG) | **R2** | Cycle detection = self-reachability under transitive closure on materialized covariant edges. SPARQL: `ASK { ?v gds-ir:covariantSuccessor+ ?v }`. Requires materializing the filtered edge relation (direction="covariant" and is_temporal=false) first. | Expressible with preprocessing |

### 5.2 Semantic Checks (on GDSSpec)

| Check | Property | Tier | Justification | Practical Impact |
|---|---|---|---|---|
| **SC-001** | Completeness | **R2** | SPARQL: LEFT JOIN Entity.variables with Mechanism.updatesEntry, FILTER NOT EXISTS for orphans. | Expressible |
| **SC-002** | Determinism | **R2** | SPARQL: GROUP BY (entity, variable) within wiring, HAVING COUNT(mechanism) > 1. | Expressible |
| **SC-003** | Reachability | **R2** | SPARQL property paths on the wiring graph. Note: follows directed wiring edges (wireSource -> wireTarget), respecting flow direction. | Expressible |
| **SC-004** | Type safety | **R2** | Wire.space is a string literal; checking membership in the set of registered Space names requires SPARQL, not SHACL sh:class (which works on object properties, as in SC-005). | Expressible via SPARQL |
| **SC-005** | Parameter references | **R1** | SHACL sh:class on usesParameter targets. Already implemented in gds-owl shacl.py. | Covered by SHACL |
| **SC-006** | f non-empty | **R1** | Equivalent to SHACL `sh:qualifiedMinCount 1` with `sh:qualifiedValueShape [sh:class gds-core:Mechanism]` on the spec node. (SPARQL illustration: `ASK { ?m a gds-core:Mechanism }`) | Covered by SHACL-core |
| **SC-007** | X non-empty | **R1** | Same pattern: SHACL `sh:qualifiedMinCount 1` for StateVariable. (SPARQL illustration: `ASK { ?sv a gds-core:StateVariable }`) | Covered by SHACL-core |

### 5.3 Summary

```
R1 (SHACL-core):     G-002, SC-005, SC-006, SC-007              = 4
R2 (SPARQL):          G-004, G-006, SC-001, SC-002, SC-003, SC-004 = 6
R3 (Python-only):     G-001, G-005                                = 2
Mixed (R1 + R3):      G-003 (flag check R1, port matching R3)     = 1
```

The R1/R2 boundary is mechanically determined: R1 = expressible in
SHACL-core (no sh:sparql), R2 = requires SPARQL graph patterns.

The R3 checks share a single root cause: **token-based port name matching
requires string computation that exceeds SPARQL's value space operations**.
In practice, this is mitigated by materializing tokens during export — the
connections themselves are always R1 as explicit wiring edges.

---

## 6. Classification Summary

**Definition 6.1 (Structural/Behavioral Partition).** We define:

```
G_struct = { composition tree, block interfaces, role partition,
             wiring topology, update targets, parameter schema,
             space/entity structure, canonical form metadata }

G_behav  = { transition functions (f_behav), constraint predicates,
             auto-wiring process, construction-time validation,
             scheduling/execution semantics }
```

**Consistency Check 6.1.** The structural/behavioral partition we define
aligns exactly with the R1+R2 / R3 classification. This is a consistency
property of our taxonomy, not an independent mathematical result — we
defined G_struct and G_behav to capture what is and isn't representable.

By exhaustive classification in Sections 3-5:

G_struct concepts and their tiers:
- Composition tree: R1 (Property 3.1)
- Block interfaces: R1 (Property 3.1)
- Role partition: R1 (Property 3.3)
- Wiring topology: R1 (Property 4.1)
- Update targets: R1 (Property 4.4, f_struct)
- Parameter schema: R1 (Property 4.1)
- Space/entity structure: R1 (Property 4.1)
- Acyclicity: R2 (Section 5.1, G-006)
- Completeness/determinism: R2 (Section 5.2, SC-001, SC-002)
- Reference validation (dangling wirings): R2 (Section 5.1, G-004)

G_behav concepts and their tiers:
- Transition functions: R3 (Property 4.4, f_behav)
- Constraint predicates: R3 (Property 4.2, general case)
- Auto-wiring process: R3 (Property 3.2)
- Construction validation: R3 (Proposition 3.4)
- Scheduling semantics: R3 (not stored in GDSSpec — external)

No G_struct concept is R3. No G_behav concept is R1 or R2.

**Property 6.2 (Canonical Form as Representability Boundary).** In the
decomposition h = f ∘ g:

```
g   is entirely in G_struct    (R1, by Observation 4.3)
f   = ⟨f_struct, f_behav⟩     (R1 + R3, by Property 4.4)
h   = structural skeleton + behavioral core
```

The canonical form cleanly separates what ontological formalisms can
express (g, f_struct) from what requires a runtime (f_behav).

**Corollary 6.3 (GDSSpec Projection of Games is Fully Representable).**
When h = g (the OGS case: X = empty, f = empty), the GDSSpec-level
structure is fully representable. The OGS canonical bridge
(spec_bridge.py) maps all atomic games to Policy blocks, producing h = g
with no behavioral f component. By Observation 4.3, g is entirely R1.

Note: game-theoretic behavioral content — payoff functions, utility
computation, equilibrium strategies — resides in OpenGame subclass methods
and external solvers, outside GDSSpec scope, and is therefore R3. The
corollary applies to the specification-level projection, not to full game
analysis.

**Corollary 6.4 (Dynamical Systems Degrade Gracefully).** For systems
with h = f ∘ g where f != empty, the structural skeleton (g + f_struct)
is always complete in OWL. Each mechanism adds one update target to
f_struct (R1) and one transition function to f_behav (R3). The "what" is
never lost — only the "how."

**Remark 6.5 (TemporalLoop vs CorecursiveLoop in OWL).** OWL cannot
distinguish a temporal loop (physical state persistence, e.g., control
systems) from a corecursive loop (strategic message threading, e.g.,
repeated games). CorecursiveLoop (defined in gds-games as
`ogs.dsl.composition.CorecursiveLoop`, a TemporalLoop subclass for
repeated game semantics) shares identical structural representation: both
use covariant wiring from inner.forward_out to inner.forward_in with an
exit_condition string. The semantic difference — "state at t feeds sensors
at t+1" vs "decisions at round t feed observations at round t+1" — is an
interpretation, not topology.

In practice this is benign: gds-owl preserves the DSL source label
(gds-ir:sourceLabel on SystemIR), so consumers can recover which DSL
compiled the system and interpret temporal wirings accordingly.

---

## 7. Analysis Domain Classification

Each type of analysis on a GDS specification maps to a representability
tier based on what it requires:

### 7.1 R1: Fully Expressible (OWL Classes + Properties)

| Analysis | Nature | GDS Implementation | Why R1 |
|---|---|---|---|
| What connects to what | Static topology | SpecQuery.dependency_graph() | Wiring graph is R1 |
| How blocks compose | Static structure | HierarchyNodeIR tree | Composition tree is R1 |
| Which blocks are which roles | Static classification | project_canonical() partition | Role partition is R1 |
| Which params affect which blocks | Static dependency | SpecQuery.param_to_blocks() | usesParameter relation is R1 |
| Game classification | Static strategic | PatternIR game_type field | Metadata on blocks, R1 |

### 7.2 R2: SPARQL-Expressible (Graph Queries + Aggregation)

| Analysis | Nature | GDS Implementation | Why R2 |
|---|---|---|---|
| Is the wiring graph acyclic? | Structural invariant | G-006 (DFS) | Transitive self-reachability on finite graph |
| Does every state variable have an updater? | Structural invariant | SC-001 | Left-join with negation |
| Are there write conflicts? | Structural invariant | SC-002 | Group-by with count > 1 |
| Are all references valid? | Structural invariant | G-004, SC-004 | Reference validation |
| Can block A reach block B? | Structural reachability | SC-003 | Property path on wiring graph |

### 7.3 R3: Python-Only (Requires Runtime)

| Analysis | Nature | GDS Implementation | Why R3 |
|---|---|---|---|
| State evolution over time | Dynamic temporal | gds-sim execution | Requires evaluating f repeatedly |
| Constraint satisfaction | Dynamic behavioral | TypeDef.constraint() | General case: Rice's theorem |
| Auto-wiring computation | Dynamic structural | tokenize() + overlap | String parsing exceeds SPARQL |
| Actual signal propagation | Dynamic behavioral | simulation with concrete values | Requires computing g(x, u) |
| Scheduling/delay semantics | Dynamic temporal | execution model | Not stored in GDS — external |
| Equilibrium computation | Dynamic strategic | game solvers | Computing Nash equilibria is PPAD-complete |

Note the distinction: **equilibrium structure** (which games exist, how
they compose) is R1. **Equilibrium computation** (finding the actual
equilibrium strategies) is R3. This parallels the f_struct / f_behav
split: the structure of the analysis is representable; the computation
of the analysis is not.

---

## 8. Five Formal Correspondences

### Correspondence 1: Static Topology <-> OWL Class/Property Hierarchy

```
rho : (blocks, wirings, interfaces, ports) <-> OWL individuals + object properties
```

R1. The composition tree, wiring graph, and port structure map to OWL
individuals connected by named object properties.

### Correspondence 2: Structural Invariants <-> SHACL Shapes + SPARQL Queries

```
{G-002, G-004, G-006, SC-001..SC-007} <-> SHACL + SPARQL
```

R1 or R2 depending on the check. SHACL-core captures cardinality and
class-membership constraints (4 checks). SPARQL captures graph-pattern
queries requiring negation, transitivity, aggregation, or cross-node
string matching (6 checks). The 2 remaining checks (G-001, G-005) require
tokenization. G-003 splits: flag check R1, port matching R3.

### Correspondence 3: Dynamic Behavior <-> Python Runtime Only

```
{TypeDef.constraint (general), f_behav, auto-wiring, scheduling} <-> Python
```

R3. Fundamental. These require Turing-complete computation. The boundary
is Rice's theorem (for predicates) and computational class separation
(for string parsing and temporal execution).

### Correspondence 4: Equilibrium Structure <-> Naturally Structural

```
h = g  (OGS canonical form) <-> GDSSpec projection is lossless
```

R1 for the specification-level projection. When a system has no state
(X = empty, f = empty), its GDSSpec is purely compositional. Game-theoretic
behavioral content (payoff functions, equilibrium solvers) is outside
GDSSpec and therefore R3.

### Correspondence 5: Reachability <-> Structural Part R2, Dynamical Part R3

```
Structural reachability : "can signals reach from A to B?"     -> R2 (SPARQL property paths)
Dynamical reachability  : "does signal actually propagate?"    -> R3 (requires evaluating g and f)
```

The structural question asks about the *topology* of the wiring graph.
SPARQL property paths (`?a successor+ ?b`) answer this on finite graphs.
The dynamical question asks about *actual propagation* given concrete
state values and policy functions — this requires executing the system.
