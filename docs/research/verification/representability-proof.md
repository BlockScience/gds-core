# R1/R2 Decidability Bounds and Partition Independence

**Claim.** Every GDS concept classified as R1 is expressible in
$\mathcal{SROIQ}(\mathcal{D})$ + SHACL-core. Every R2 concept is
expressible in SPARQL 1.1. The alignment between $G_{\text{struct}} /
G_{\text{behav}}$ and R1+R2 / R3 is a structural consequence of the
canonical decomposition, not a tautology.

---

## Part A: R1 Decidability (Constructive Proof)

**Method.** For each R1 concept, we exhibit a constructive witness — the
`gds-owl` export function that serializes it to OWL/RDF, and the SHACL
shape that validates it. The existence of a correct serialization +
validation pair constitutes a proof that the concept is expressible in
the formalism.

### R1 Concepts and Their Witnesses

| Concept | Export witness | SHACL witness | OWL construct |
|---|---|---|---|
| Composition tree | `_block_to_rdf()` | BlockIRShape | `rdf:type` dispatch to role subclasses |
| Block interfaces | `_block_to_rdf():160-186` | BoundaryActionShape | Port as blank node, `typeToken` as `xsd:string` |
| Role partition | `_block_to_rdf():118-140` | class dispatch | `owl:disjointUnionOf` on role classes |
| Wiring topology | `_wiring_to_rdf()` | WiringIRShape | Wire blank nodes with `wireSource`, `wireTarget` |
| Update targets ($f_{\text{struct}}$) | `_block_to_rdf():202-220` | MechanismShape | UpdateMapEntry blank nodes |
| Parameter schema | `_parameter_to_rdf()` | TypeDefShape | ParameterDef class with `lowerBound`, `upperBound` |
| Space/entity structure | `_space_to_rdf()`, `_entity_to_rdf()` | SpaceShape, EntityShape | SpaceField/StateVariable blank nodes |
| Admissibility graph ($U_{x,\text{struct}}$) | `spec_to_graph():341-374` | AdmissibleInputConstraintShape | AdmissibilityDep blank nodes |
| Transition read deps ($f_{\text{read}}$) | `spec_to_graph():377-406` | TransitionSignatureShape | TransitionReadEntry blank nodes |

**Proof sketch for each concept:**

All R1 concepts share the same structure: a *finite set of named entities*
with *typed attributes* and *binary relations* to other named entities.
This maps directly to OWL DL:

$$
\text{GDS concept} \xrightarrow{\rho} \text{RDF individual} + \text{OWL class membership} + \text{datatype/object properties}
$$

The SHACL shapes enforce:
- **Cardinality**: `sh:minCount 1`, `sh:maxCount 1` for required fields
  (e.g., every block has exactly one name)
- **Datatype**: `sh:datatype xsd:string`, `xsd:boolean`, `xsd:float`
- **Class membership**: `sh:class` constraints (e.g., mechanism updates
  reference entities)

These are all within the decidable fragment of $\mathcal{SROIQ}(\mathcal{D})$.
Specifically:

- Cardinality restrictions → qualified number restrictions (QNR) in
  $\mathcal{SROIQ}$
- Datatype constraints → concrete domain $\mathcal{D}$ with XSD datatypes
- Class dispatch → concept subsumption ($C \sqsubseteq D$)
- Disjoint roles → role disjointness axioms

Reasoning over these axioms is 2NExpTime-complete but *decidable*, which is
the requirement for R1. $\square$

---

## Part B: R2 Decidability (Constructive Proof)

**Method.** For each R2 concept, we exhibit the SPARQL 1.1 feature required
to validate it, and show that the query terminates.

### R2 Concepts and Their Witnesses

| Concept | Verification check | SPARQL feature required | Why SHACL-core is insufficient |
|---|---|---|---|
| Acyclicity (G-006) | Covariant wiring has no cycles | Property paths (`p+` transitive closure) | SHACL-core has no transitive closure operator |
| Completeness (SC-001) | Every mechanism input is wired | `FILTER NOT EXISTS` (negation-as-failure) | SHACL cannot express "for all X, there exists Y such that..." |
| Determinism (SC-002) | No two mechanisms update the same $(E, V)$ pair | `GROUP BY` + `HAVING (COUNT > 1)` | SHACL cannot aggregate across nodes |
| Dangling wirings (G-004) | Wiring source/target reference existing blocks | `FILTER NOT EXISTS` | SHACL `sh:class` checks class membership, not name existence |

**Proof sketch.**

SPARQL 1.1 is a query language over finite RDF graphs. Key properties:

1. **Termination**: every SPARQL query over a finite graph terminates,
   because:
   - Pattern matching is bounded by the graph size
   - Property paths (`p+`) are bounded by the number of nodes
   - Aggregation operates over finite result sets
   - There is no recursion, no mutable state, no unbounded iteration

2. **Expressiveness**: SPARQL 1.1 is equivalent in expressive power to
   relational algebra extended with transitive closure and aggregation.
   This suffices for the four R2 properties:

   - *Acyclicity*: Express as `ASK { ?x gds:wiresTo+ ?x }` — if the query
     returns true, a cycle exists. The `+` operator computes transitive
     closure over finitely many nodes.

   - *Completeness*: Express as negation-as-failure: `SELECT ?port WHERE {
     ?block gds:hasPort ?port . FILTER NOT EXISTS { ?wiring gds:wireTarget
     ?port } }` — unmatched ports indicate incompleteness.

   - *Determinism*: Express as aggregation: `SELECT ?entity ?var WHERE {
     ?mech gds:updatesEntity ?entity ; gds:updatesVariable ?var } GROUP BY
     ?entity ?var HAVING (COUNT(?mech) > 1)` — results indicate
     non-deterministic updates.

   - *Dangling references*: Express as negation-as-failure: `SELECT ?wiring
     WHERE { ?wiring gds:wireSource ?name . FILTER NOT EXISTS { ?block
     gds:hasName ?name } }` — unresolved references.

3. **SHACL insufficiency**: SHACL validates the *local neighborhood* of a
   node. It cannot express cross-node constraints that require:
   - Transitive closure (reachability across arbitrarily many edges)
   - Negation-as-failure over the entire graph (not just a node's properties)
   - Aggregation across independent nodes

Therefore R2 concepts require SPARQL but remain decidable because SPARQL
queries over finite graphs always terminate. $\square$

---

## Part C: Partition Independence

**Question.** Is the alignment between $G_{\text{struct}} / G_{\text{behav}}$
and R1+R2 / R3 a tautology (we defined them to match) or a structural
consequence (they match because of deeper reasons)?

### Independent Definitions

**Definition C.1 (Structural/Behavioral partition — from canonical
decomposition).**

Given $h = f \circ g$ where $g$ is the policy map and
$f = \langle f_{\text{struct}}, f_{\text{read}}, f_{\text{behav}} \rangle$:

$$
G_{\text{struct}} = \{c \in \text{GDS} \mid c \text{ is determined by } g \text{ or } f_{\text{struct}} \text{ or } f_{\text{read}}\}
$$

$$
G_{\text{behav}} = \{c \in \text{GDS} \mid c \text{ depends on evaluating } f_{\text{behav}} \text{ or a } \texttt{Callable}\}
$$

This definition depends only on the canonical decomposition. It does not
reference OWL, SHACL, or SPARQL.

**Definition C.2 (Representability tiers — from formal language
expressiveness).**

$$
\text{R1} = \{c \mid c \text{ is expressible in } \mathcal{SROIQ}(\mathcal{D}) + \text{SHACL-core}\}
$$

$$
\text{R2} = \{c \mid c \text{ requires SPARQL 1.1 but not Turing-completeness}\}
$$

$$
\text{R3} = \{c \mid c \text{ requires Turing-complete computation}\}
$$

This definition depends only on computational complexity. It does not
reference the canonical decomposition.

### The Coincidence Theorem

**Theorem C.3.** $G_{\text{struct}} = \text{R1} \cup \text{R2}$ and
$G_{\text{behav}} = \text{R3}$.

*Proof.*

($G_{\text{struct}} \subseteq \text{R1} \cup \text{R2}$): Every structural
concept is a finite set of named entities with typed attributes and binary
relations (Part A), or a graph-global property checkable by terminating
query (Part B). These are within the decidable fragment. Proved
constructively in Parts A and B.

($G_{\text{behav}} \subseteq \text{R3}$): Every behavioral concept involves
evaluating an arbitrary `Callable` or performing Turing-complete string
computation. These exceed the expressiveness of any decidable logic. Proved
by reduction in [r3-undecidability.md](r3-undecidability.md).

($\text{R1} \cup \text{R2} \subseteq G_{\text{struct}}$): Suppose a
concept $c \in \text{R1} \cup \text{R2}$ but $c \in G_{\text{behav}}$.
Then $c$ depends on evaluating a `Callable`, which is Turing-complete
(Proposition 1-6 in the R3 proof). But R1 $\cup$ R2 concepts are decidable
by definition. Contradiction.

($\text{R3} \subseteq G_{\text{behav}}$): Suppose $c \in \text{R3}$ but
$c \in G_{\text{struct}}$. Then $c$ is determined by $g$ or
$f_{\text{struct}}$ or $f_{\text{read}}$, all of which are finite
relations over named entities. But finite relations are expressible in OWL
(R1). This contradicts $c \in \text{R3}$.

Therefore the partition coincides. $\square$

### Why This Is Not Tautological

The formal-representability document (Check 6.1) states: "we defined
$G_{\text{struct}}$ and $G_{\text{behav}}$ to capture what is and isn't
representable." This is true *operationally* — the definitions were
designed with representability in mind. But the coincidence is not
*logically* tautological because:

1. The definitions are *independently testable*. Given a new GDS concept,
   you can classify it as structural/behavioral by examining the canonical
   decomposition, and independently classify it by representability tier by
   attempting to express it in OWL/SPARQL. If the partition were
   tautological, these would be the same test. They are not — one asks
   "does this depend on a `Callable`?" and the other asks "can
   $\mathcal{SROIQ}$ express this?"

2. The coincidence *could fail* in a modified framework. If GDS stored
   transition functions as symbolic expressions (e.g., polynomial
   arithmetic over state variables), then $f_{\text{behav}}$ would move
   from R3 to R2 (polynomial evaluation is decidable). The structural/
   behavioral partition would remain the same, but the representability
   boundary would shift. The fact that they coincide *in this framework* is
   a consequence of the design choice to allow arbitrary `Callable` for
   behavioral components.

3. The key structural insight is: **the canonical decomposition $h = f
   \circ g$ separates topology from computation, and
   $\mathcal{SROIQ}(\mathcal{D})$ can express exactly topology.** This is
   not a definition — it is a claim about the expressiveness of description
   logic relative to the structure of GDS specifications.

### Status

We consider Theorem C.3 **proved** under the current GDS design (arbitrary
`Callable` for behavioral components). The theorem would need revision if
the framework constrained behavioral components to a decidable fragment.

---

## References

- [r3-undecidability.md](r3-undecidability.md) — R3 undecidability proofs
- [formal-representability.md](../formal-representability.md) — Properties
  3.1-4.6, Check 6.1, Property 6.2
- [deep_research.md](../deep_research.md) — SROIQ expressiveness analysis
- Horrocks, I. et al. "The Even More Irresistible SROIQ." (2006) —
  2NExpTime decidability of $\mathcal{SROIQ}$
- Rice, H.G. "Classes of Recursively Enumerable Sets and Their Decision
  Problems." (1953)
