# Representation Gap: Pydantic vs OWL/RDF

## The Core Insight

Python (Pydantic) and OWL/RDF are not in a hierarchy — they are **complementary representation systems** with different strengths. The bidirectional round-trip in `gds-owl` proves they overlap almost completely, but the small gap between them is revealing.

## What Each Representation Captures

### What OWL/RDF captures that Python doesn't

| Capability | OWL/RDF | Python/Pydantic |
|---|---|---|
| **Cross-system linking** | Native. A GDSSpec in one graph can reference entities in another via URIs. | Requires custom serialization + shared registries. |
| **Open-world reasoning** | OWL reasoners can infer facts not explicitly stated (e.g., "if X is a Mechanism and X updatesEntry Y, then X affects Entity Z"). | Closed-world only. You must write the inference logic yourself. |
| **Schema evolution** | Add new properties without breaking existing consumers. Unknown triples are simply ignored. | Adding a field to a frozen Pydantic model is a breaking change. |
| **Federated queries** | SPARQL can query across multiple GDS specs in a single query, even from different sources. | Requires loading all specs into memory and writing custom join logic. |
| **Provenance** | PROV-O gives audit trails for free (who created this spec, when, derived from what). | Must be implemented manually. |
| **Self-describing data** | A Turtle file contains its own schema context via prefixes and class declarations. | A JSON file requires external schema knowledge to interpret. |

### What Python captures that OWL/RDF doesn't

| Capability | Python/Pydantic | OWL/RDF |
|---|---|---|
| **Constraint functions** | `TypeDef.constraint = lambda x: 0 <= x <= 1` — a runtime predicate that validates actual data values. | Cannot represent arbitrary predicates. Can document them as annotations, but cannot execute them. |
| **Composition operators** | `sensor >> controller >> heater` — the `>>`, `|`, `.feedback()`, `.loop()` DSL is Python syntax. | Can represent the *result* of composition (the tree structure), but not the *act* of composing. |
| **Construction-time validation** | `@model_validator(mode="after")` enforces invariants the instant a model is created. | SHACL validates after the fact, not during construction. Invalid data can exist in a graph. |
| **Type-level computation** | Token-based auto-wiring: `"Temperature + Setpoint"` splits on ` + `, lowercases, and checks set overlap. This is a runtime computation. | Can store the resulting tokens as RDF lists, but cannot compute the tokenization. |
| **IDE ergonomics** | Autocomplete, type checking, refactoring, debugging. The Python type system is a development tool. | Protege exists, but the tooling ecosystem is smaller and less integrated with modern dev workflows. |
| **Performance** | Pydantic model construction: microseconds. | rdflib graph construction: 10-100x slower. SHACL validation via pyshacl: significantly slower than `@model_validator`. |

## The Lossy Fields (Documented)

These are the specific fields lost during round-trip. Each reveals a category boundary:

### 1. `TypeDef.constraint` — Runtime Predicate

```python
# Python: executable constraint
Temperature = TypeDef(
    name="Temperature",
    python_type=float,
    constraint=lambda x: -273.15 <= x <= 1000.0,  # physically meaningful range
    units="celsius",
)

# RDF: can only record that a constraint exists
# gds-core:hasConstraint "true"^^xsd:boolean
```

**Why it's lossy**: A Python `Callable[[Any], bool]` is Turing-complete. OWL DL is decidable. You cannot embed an arbitrary program in an ontology and have it remain decidable.

**Workaround**: Export the constraint as a human-readable annotation (`rdfs:comment`), or as a SHACL `sh:pattern` / `sh:minInclusive` / `sh:maxInclusive` for simple numeric bounds. Complex predicates require linking to the source code via `rdfs:seeAlso`.

### 2. `TypeDef.python_type` — Language-Specific Type

```python
# Python: actual runtime type
TypeDef(name="Temperature", python_type=float)

# RDF: string representation
# gds-core:pythonType "float"^^xsd:string
```

**Why it's lossy**: `float` is a Python concept. OWL has `xsd:float`, `xsd:double`, etc., but the mapping isn't 1:1 (Python `float` is IEEE 754 double-precision, which maps to `xsd:double`, not `xsd:float`). For round-trip, we map common type names back via a lookup table, but custom types (e.g., `numpy.float64`) would need a registry.

**Impact**: Low. The built-in type map covers `float`, `int`, `str`, `bool` — which account for all current GDS usage.

### 3. Composition Tree — Structural vs Behavioral

```python
# Python: live composition with operators
system = (sensor | observer) >> controller >> heater
system = system.feedback(wiring=[...])

# RDF: can represent the resulting tree
# :system gds-core:first :sensor_observer_parallel .
# :system gds-core:second :controller_heater_stack .
```

**Why it's partially lossy**: The RDF graph captures the *structure* of the composition tree (what blocks are composed how), but not the *process* of building it. The `>>` operator includes validation logic (token overlap checking) that runs at construction time. This validation is captured in SHACL shapes, but the dynamic dispatch and error messages are Python-specific.

**Impact**: None for GDSSpec export (blocks are already composed). Only relevant if you wanted to *construct* a composition from RDF, which would require a builder that re-applies the validation logic.

## Why OWL/SHACL Can't Store "What Things Do"

Your intuition — circuit diagrams vs circuit simulations — is almost exactly right. But the deeper reason is worth understanding, because it's not an engineering limitation. It's a mathematical one.

### The Decidability Trade-off

OWL is based on **Description Logic** (specifically OWL DL uses SROIQ). Description Logics are fragments of first-order logic that are deliberately restricted so that:

1. **Every query terminates.** Ask "is X a subclass of Y?" and you are guaranteed an answer in finite time.
2. **Consistency is checkable.** Ask "can this ontology ever contain a contradiction?" and you get a definitive yes/no.
3. **Classification is automatic.** The reasoner can infer the complete class hierarchy without human guidance.

These guarantees come at a cost: you cannot express arbitrary computation. The moment you allow unrestricted recursion, loops, or Turing-complete predicates, you lose decidability — some queries would run forever.

A Python `lambda x: 0 <= x <= 1` is trivial, but the type signature `Callable[[Any], bool]` admits *any* computable function, including ones that don't halt. OWL cannot embed that and remain OWL.

### The Circuit Analogy (Refined)

| | Circuit Diagram | Circuit Simulation |
|---|---|---|
| **Analog in GDS** | OWL ontology + RDF instance data | Python Pydantic models + runtime |
| **What it captures** | Components, connections, topology, constraints | Voltage, current, timing, behavior over time |
| **Can answer** | "Is this resistor connected to ground?" | "What voltage appears at node 3 at t=5ms?" |
| **Cannot answer** | "What happens when I flip this switch?" | "Is this the only valid topology?" (needs the diagram) |

This is correct, but the analogy goes deeper:

**A circuit diagram is a specification. A simulation is an execution.** You can derive a simulation from a diagram (given initial conditions and a solver), but you cannot derive the diagram from a simulation (infinitely many circuits could produce the same waveform).

Similarly:

- **OWL/RDF is specification.** It says what types exist, how blocks connect, what constraints hold.
- **Python is execution.** It actually validates data, composes blocks, runs the token-overlap algorithm.

You can derive the RDF from the Python (that's what `spec_to_graph()` does). You can mostly derive the Python from the RDF (that's what `graph_to_spec()` does). But the execution semantics — the `lambda`, the `>>` operator's validation logic, the `@model_validator` — live only in the runtime.

### Three Levels of "Knowing"

This maps to a well-known hierarchy in formal systems:

| Level | What it captures | GDS example | Formalism |
|---|---|---|---|
| **Syntax** | Structure, names, connections | Block names, port names, wiring topology | RDF triples |
| **Semantics** | Meaning, types, constraints | "Temperature is a float in celsius", "Mechanism must update state" | OWL classes + SHACL shapes |
| **Pragmatics** | Behavior, computation, execution | `constraint=lambda x: x >= 0`, `>>` auto-wiring by token overlap | Python runtime |

OWL lives at levels 1 and 2. Python lives at all three. The gap is level 3 — and it's the same gap that separates every declarative specification language from every imperative programming language. It's not a bug in OWL. It's the price of decidability.

### SHACL Narrows the Gap (But Doesn't Close It)

SHACL pushes closer to behavior than OWL alone:

```turtle
# SHACL can express: "temperature must be between -273.15 and 1000"
:TemperatureConstraint a sh:NodeShape ;
    sh:property [
        sh:path :value ;
        sh:minInclusive -273.15 ;
        sh:maxInclusive 1000.0 ;
    ] .
```

This covers many real GDS constraints. But SHACL's `sh:sparql` constraints, while powerful, are still not Turing-complete — SPARQL queries always terminate on finite graphs. You cannot write a SHACL shape that says "validate this value by running an arbitrary Python function."

SWRL (Semantic Web Rule Language) gets even closer — it can express Horn-clause rules. But it still can't express negation-as-failure, higher-order functions, or stateful computation.

The boundary is fundamental: **decidable formalisms cannot embed undecidable computation**. This is not a limitation of OWL's design. It's a consequence of the halting problem.

### What This Means in Practice

For GDS specifically, the practical impact is small:

- **95% of GDS structure** round-trips perfectly through RDF
- **Most constraints** are simple numeric bounds expressible in SHACL
- **The composition tree** is fully captured as structure
- **Only `Callable` predicates** and language-specific types are truly lost

The circuit analogy holds: you design the circuit (OWL), you simulate it (Python), and the design document captures everything except the electrons moving through the wires.

## The GDS Compositionality-Temporality Boundary Is the Same Boundary

GDS already discovered this gap internally — between game-theoretic composition
and dynamical systems composition. The OWL representation gap is the same
boundary, seen from the outside.

### What GDS Found

The canonical spectrum across five domains revealed a structural divide:

| Domain | dim(X) | dim(f) | Form | Character |
|---|---|---|---|---|
| OGS (games) | 0 | 0 | h = g | Stateless — pure maps |
| Control | n | n | h = f . g | Stateful — observation + state update |
| StockFlow | n | n | h = f . g | Stateful — accumulation dynamics |
| Software (DFD/SM/C4/ERD) | 0 or n | 0 or n | varies | Diagram-dependent |
| Business (CLD/SCN/VSM) | 0 or n | 0 or n | varies | Domain-dependent |

Games compute equilibria. They don't write to persistent state. Even corecursive
loops (repeated games) carry information forward as *observations*, not as
*entity mutations*. In category-theoretic terms: open games are morphisms in
a symmetric monoidal category with feedback. They are maps, not machines.

Control and stock-flow systems are the opposite. They have state variables (X),
state update functions (f), and the temporal loop carries physical state forward
across timesteps.

Both use the **same structural composition operators** (`>>`, `|`, `.feedback()`,
`.loop()`). The algebra is identical. The semantics are orthogonal.

### OWL Lives on the Game-Theory Side of This Boundary

This is the key insight: **OWL/RDF is inherently atemporal**. An RDF graph is a
set of (subject, predicate, object) triples — relations between things. There is
no built-in notion of "before and after," "state at time t," or "update."

This means OWL naturally represents the compositional/structural side of GDS
(the `g` in `h = f . g`) far better than the temporal/behavioral side (the `f`):

| GDS Component | Nature | OWL Fit |
|---|---|---|
| **g** (policy, observation, decision) | Structural mapping — signals in, signals out | Excellent. Object properties capture flow topology. |
| **f** (state update, mechanism) | Temporal mutation — state at t becomes state at t+1 | Partial. Can describe *what* f updates, but not *how*. |
| **Composition tree** (>>, \|) | Structural nesting | Excellent. `first`, `second`, `left`, `right` properties. |
| **FeedbackLoop** (.feedback()) | Within-timestep backward flow | Good. Structural — just backward edges. |
| **TemporalLoop** (.loop()) | Across-timestep forward recurrence | Structural part captured, temporal semantics lost. |
| **CorecursiveLoop** (OGS) | Across-round strategic iteration | Same structure as TemporalLoop — OWL can't distinguish them. |

The last row is the critical one: **OWL cannot distinguish a corecursive game loop
from a temporal state loop**, because the distinction is semantic (what does iteration
*mean*?), not structural (how are the wires connected?).

This is exactly the same problem GDS faced at Layer 0. The composition algebra
treats `TemporalLoop` and `CorecursiveLoop` identically — same wiring pattern,
same structural validation. The difference is domain semantics, which lives in
the DSL layer (Layer 1+), not in the algebra.

### The Three-Way Isomorphism

```
Game-theoretic composition     ←→   OWL/RDF representation
    (atemporal, structural,          (atemporal, structural,
     maps between spaces)              relations between entities)

Dynamical systems execution    ←→   Python runtime
    (temporal, behavioral,            (temporal, behavioral,
     state evolving over time)         computation producing results)
```

Games and ontologies are both **declarative**: they describe what things are and how
they relate. Dynamical systems and programs are both **imperative**: they describe
what happens over time.

GDS bridges these two worlds with the canonical form `h = f . g`:
- `g` is the declarative part (composable, structural, OWL-friendly)
- `f` is the imperative part (state-updating, temporal, Python-native)
- `h` is the complete system (both sides unified)

The round-trip gap in gds-owl is precisely the `f` side leaking through.

### Why OGS Round-Trips Better Than Control

This predicts something testable: **OGS specifications should round-trip through
OWL with less information loss than control or stock-flow specifications**, because
OGS is `h = g` (purely structural/compositional, no state update semantics to lose).

And indeed:
- OGS blocks are all Policy — no `Mechanism.updates` to reify
- OGS has no Entity/StateVariable — no state space to encode
- The corecursive loop is structurally identical to a temporal loop — no semantic
  distinction is lost because there was no temporal semantics to begin with
- The canonical form `h = g` maps directly to "all blocks are related by composition" —
  which is exactly what OWL expresses

Control and stock-flow systems lose the `f` semantics:
- `Mechanism.updates = [("Room", "temperature")]` becomes a reified triple that
  says *what* gets updated, but not *how* (the state transition function itself is a
  Python callable)
- The temporal loop says "state feeds back" structurally, but not "with what delay"
  or "under what scheduling semantics"

### What This Means for the Research Questions

The GDS research boundaries document (research-boundaries.md) identified
three key open questions. Each maps directly to the OWL representation gap:

**RQ1 (MIMO semantics)**: Should vector-valued spaces become first-class?
- OWL impact: Vector spaces are harder to represent than scalar ports. RDF naturally
  represents named relations, not ordered tuples. This is a structural limitation
  shared by both the composition algebra and OWL.

**RQ2 (What does a timestep mean?)**: Different domains interpret `.loop()` differently.
- OWL impact: This is *exactly* the gap. OWL captures the loop *structure* but not
  the loop *semantics*. A temporal loop in control (physical state persistence) and a
  corecursive loop in OGS (strategic message threading) are the same OWL triples.
  The distinction requires domain-specific annotation — which is what the dual IR
  stack (PatternIR + SystemIR) already provides in Python.

**RQ3 (OGS as degenerate dynamical system)**: Is X=0, f=0, h=g a valid GDS?
- OWL impact: Yes, and it's the *best-represented* case. A system with no state
  variables and no mechanisms is purely compositional — which is the part of GDS
  that OWL captures perfectly. The "degenerate" case is actually the one where
  OWL and Pydantic representations are isomorphic.

### The Circuit Analogy (Revisited)

The earlier analogy — circuit diagrams vs circuit simulations — now sharpens:

| | Circuit Diagram | Schematic + Netlist | SPICE Simulation |
|---|---|---|---|
| GDS analog | OWL ontology | Composition algebra (Layer 0) | Python runtime (gds-sim) |
| Games analog | Strategy profile description | Game tree | Equilibrium solver |
| Dynamics analog | Block diagram | State-space model | ODE integrator |
| Captures | Topology + component types | Topology + port typing + composition rules | Behavior over time |
| Misses | Behavior, timing | Execution semantics | Often loses global structure |

OWL is the diagram. The composition algebra is the netlist. Python is the simulator.
Games live naturally in the diagram/netlist. Dynamics need the simulator.

## What This Means for the "Ontology-First" Future

The gap analysis suggests a three-tier architecture:

```
Tier 1: OWL Ontology (schema)
    - Class hierarchy, property definitions
    - SHACL shapes for structural validation
    - SPARQL queries for analysis
    → Source of truth for: what things ARE

Tier 2: Python DSL (behavior)
    - Composition operators (>>, |, .feedback(), .loop())
    - Runtime constraint predicates
    - Construction-time validation
    → Source of truth for: what things DO

Tier 3: Instance Data (both)
    - Pydantic models ↔ RDF graphs (round-trip proven)
    - Either format can be the serialization layer
    → The overlap zone where both representations agree
```

The key insight: **you don't have to choose one**. The ontology defines the vocabulary and structural rules. Python defines the computational behavior. Instance data lives in both and can be translated freely.

This is analogous to how SQL databases work: the schema (DDL) defines structure, application code defines behavior, and data lives in both the database and application memory. Nobody argues that SQL "stores more" than Python or vice versa — they serve different roles.

## Practical Implications

### When to use OWL/RDF

- Publishing a GDS specification for external consumption
- Querying across multiple specifications simultaneously
- Linking GDS specs to external ontologies (FIBO, ArchiMate, PROV-O)
- Archiving specifications with self-describing metadata
- Running structural validation without Python installed

### When to use Pydantic

- Building and composing specifications interactively
- Running constraint validation on actual data values
- Leveraging IDE tooling (autocomplete, type checking)
- Performance-sensitive operations (construction, validation)
- Anything involving the composition DSL (`>>`, `|`, `.feedback()`, `.loop()`)

### When to use both

- Development workflow: build in Python, export to RDF for publication
- Verification: SHACL for structural checks, Python for runtime checks
- Cross-system analysis: export multiple specs to RDF, query with SPARQL
- Round-trip: start from RDF (e.g., Protege-edited), import to Python for computation
