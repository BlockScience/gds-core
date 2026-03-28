# R1/R2 Decidability Bounds and Partition Independence

**Claim.** Every GDS concept classified as R1 is expressible in
$\mathcal{SROIQ}(\mathcal{D})$ + SHACL-core. Every R2 concept is
expressible in SPARQL 1.1. The alignment between $G_{\text{struct}} /
G_{\text{behav}}$ and R1+R2 / R3 is a structural consequence of the
canonical decomposition, not a tautology.

---

## Part A: R1 Decidability (Constructive Proof)

**Method.** For each R1 concept, we exhibit a constructive witness — the
`gds-owl` export function that serializes it to OWL/RDF, and the SHACL-core
shape that validates it. The existence of a correct serialization +
validation pair constitutes a proof that the concept is expressible in the
formalism.

### R1 Concepts and Their Witnesses

| Concept | Export witness | SHACL-core witness | OWL construct |
|---|---|---|---|
| Composition tree | `_block_to_rdf()` | BlockIRShape | `rdf:type` dispatch to role subclasses |
| Block interfaces | `_block_to_rdf()` | BoundaryActionShape | Port as blank node, `typeToken` as `xsd:string` |
| Role partition | `_block_to_rdf()` | class dispatch | `owl:disjointUnionOf` on role classes |
| Wiring topology | `_wiring_to_rdf()` | WiringIRShape | Wire blank nodes with `wireSource`, `wireTarget` |
| Update targets ($f_{\text{struct}}$) | `_block_to_rdf()` | MechanismShape | UpdateMapEntry blank nodes |
| Parameter schema | `_parameter_to_rdf()` | TypeDefShape | ParameterDef class with bounds |
| Space/entity structure | `_space_to_rdf()`, `_entity_to_rdf()` | SpaceShape, EntityShape | SpaceField/StateVariable blank nodes |
| Admissibility graph ($U_{x,\text{struct}}$) | `spec_to_graph()` | AdmissibleInputConstraintShape | AdmissibilityDep blank nodes |
| Transition read deps ($f_{\text{read}}$) | `spec_to_graph()` | TransitionSignatureShape | TransitionReadEntry blank nodes |

**Proof sketch for each concept:**

All R1 concepts share the same structure: a *finite set of named entities*
with *typed attributes* and *binary relations* to other named entities.
This maps directly to OWL DL:

$$
\text{GDS concept} \xrightarrow{\rho} \text{RDF individual} + \text{OWL class membership} + \text{datatype/object properties}
$$

The SHACL-core shapes enforce:
- **Cardinality**: `sh:minCount 1`, `sh:maxCount 1` for required fields
  (e.g., every block has exactly one name)
- **Datatype**: `sh:datatype xsd:string`, `xsd:boolean`, `xsd:float`
- **Class membership**: `sh:class` constraints (e.g., mechanism updates
  reference entities)

These are all within the decidable fragment of $\mathcal{SROIQ}(\mathcal{D})$.
Specifically:

- Cardinality restrictions $\to$ qualified number restrictions (QNR) in
  $\mathcal{SROIQ}$
- Datatype constraints $\to$ concrete domain $\mathcal{D}$ with XSD datatypes
- Class dispatch $\to$ concept subsumption ($C \sqsubseteq D$)
- Disjoint roles $\to$ role disjointness axioms

Reasoning over these axioms is 2NExpTime-complete but *decidable*, which is
the requirement for R1. $\square$

---

## Part B: R2 Decidability (Constructive Proof)

**Method.** For each R2 concept, we exhibit the SPARQL 1.1 feature required
to validate it, and show that the query terminates. We demonstrate that
SHACL-core (without `sh:sparql` embedding) is insufficient.

### R2 Concepts and Their Witnesses

| Concept | Verification check | SPARQL feature required | Why SHACL-core is insufficient |
|---|---|---|---|
| Acyclicity (G-006) | Covariant wiring has no cycles | Property paths (`p+` transitive closure) | SHACL-core has no transitive closure operator |
| Completeness (SC-001) | Every mechanism input is wired | `FILTER NOT EXISTS` (negation-as-failure) | SHACL-core cannot express "for all X, there exists Y such that..." |
| Determinism (SC-002) | No two mechanisms update the same $(E, V)$ pair | `GROUP BY` + `HAVING (COUNT > 1)` | SHACL-core cannot aggregate across nodes |
| Dangling wirings (G-004) | Wiring source/target reference existing blocks | `FILTER NOT EXISTS` | SHACL-core `sh:class` checks class membership, not name existence |

**Note on SHACL-core vs SHACL-SPARQL:** SHACL-SPARQL (`sh:sparql`)
embeds SPARQL queries inside SHACL shapes and *can* express everything
SPARQL can. The insufficiency argument above applies only to SHACL-core
(node shapes, property shapes with cardinality/datatype/class constraints,
without `sh:sparql`). This is the distinction that separates R1 from R2.

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

3. **SHACL-core insufficiency**: SHACL-core validates the *local
   neighborhood* of a node. It cannot express cross-node constraints that
   require:
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
G_{\text{struct}} = \{c \in \text{GDS} \mid c \text{ is determined by } g, f_{\text{struct}}, \text{ or } f_{\text{read}}\}
$$

$$
G_{\text{behav}} = \{c \in \text{GDS} \mid c \text{ depends on evaluating } f_{\text{behav}}, \text{ a } \texttt{Callable}, \text{ or a computation requiring mutable intermediate state or ordered multi-pass processing}\}
$$

This definition depends on the canonical decomposition and the
computational character of the concept. It does not reference OWL, SHACL,
or SPARQL — only the intrinsic computational requirements of the concept.

**Remark.** Definition C.1 places auto-wiring and construction validation
in $G_{\text{behav}}$ because they involve computation (tokenization, set
intersection) that goes beyond what the static data model encodes. The
*results* of auto-wiring (WiringIR edges) are $G_{\text{struct}}$; the
*process* is $G_{\text{behav}}$.

**Definition C.2 (Representability tiers — from formal language
expressiveness, per formal-representability.md Def 2.2).**

$$
\text{R1} = \{c \mid c \text{ is expressible in } \mathcal{SROIQ}(\mathcal{D}) + \text{SHACL-core}\}
$$

$$
\text{R2} = \{c \mid c \text{ requires SPARQL 1.1 but is decidable over finite graphs}\}
$$

$$
\text{R3} = \{c \mid \text{no finite OWL/SHACL/SPARQL expression can capture } c\}
$$

R3 has two sub-sources (see [r3-undecidability.md](r3-undecidability.md)):

- **R3-undecidable**: semantic properties of arbitrary `Callable` are
  undecidable by Rice's theorem
- **R3-separation**: decidable computations that exceed SPARQL's model
  (no mutable state, no multi-pass string processing)

This definition depends only on computational expressiveness. It does not
reference the canonical decomposition.

### The Coincidence Theorem

**Theorem C.3.** $G_{\text{struct}} = \text{R1} \cup \text{R2}$ and
$G_{\text{behav}} = \text{R3}$.

*Proof.* Four containments:

**($G_{\text{struct}} \subseteq \text{R1} \cup \text{R2}$):** Every
structural concept is a finite set of named entities with typed attributes
and binary relations (Part A shows these are R1), or a graph-global
property checkable by a terminating SPARQL query (Part B shows these are
R2). Proved constructively above.

**($G_{\text{behav}} \subseteq \text{R3}$):** Every behavioral concept
either involves evaluating an arbitrary `Callable` or performing
computation beyond SPARQL's expressiveness.

- For R3-undecidable concepts ($f_{\text{behav}}$, `TypeDef.constraint`,
  $U_{x,\text{behav}}$): these accept arbitrary `Callable`, which can
  encode any partial recursive function. By Rice's theorem, any
  non-trivial semantic property of such callables is undecidable. Therefore
  no finite OWL/SHACL/SPARQL expression can capture them.

- For R3-separation concepts (auto-wiring, construction validation): these
  involve multi-pass string processing (Unicode NFC + ordered delimiter
  splitting) and dynamic set construction, which exceed SPARQL 1.1's
  computational model (no mutable state, no ordered multi-pass processing).
  Proved in [r3-undecidability.md](r3-undecidability.md), Propositions 4-5.

**($\text{R1} \cup \text{R2} \subseteq G_{\text{struct}}$):** Suppose
$c \in \text{R1} \cup \text{R2}$ but $c \in G_{\text{behav}}$. Then $c$
either depends on evaluating an arbitrary `Callable` or involves
computation beyond SPARQL.

- If $c$ depends on an arbitrary `Callable`: by Rice's theorem, any
  non-trivial semantic property of that callable is undecidable. But R1
  $\cup$ R2 concepts are decidable (R1 by 2NExpTime OWL reasoning, R2 by
  SPARQL termination over finite graphs). Contradiction.

- If $c$ involves computation beyond SPARQL but no `Callable`: then $c$
  is R3-separation, which by definition is not in R1 $\cup$ R2.
  Contradiction.

**($\text{R3} \subseteq G_{\text{behav}}$):** Suppose $c \in \text{R3}$
but $c \in G_{\text{struct}}$. Then $c$ is determined by $g$,
$f_{\text{struct}}$, or $f_{\text{read}}$, all of which are finite
relations over named entities. Properties of finite relations over finite
graphs are decidable — expressible in OWL (R1) for local constraints, or
SPARQL (R2) for global constraints. Therefore $c \in \text{R1} \cup
\text{R2}$, contradicting $c \in \text{R3}$. $\square$

### Why This Is Not Tautological

The formal-representability document (Check 6.1) states: "we defined
$G_{\text{struct}}$ and $G_{\text{behav}}$ to capture what is and isn't
representable." This is true *operationally* — the definitions were
designed with representability in mind. But the coincidence is not
*logically* tautological because:

1. **The definitions are independently testable.** Given a new GDS concept,
   you can classify it as structural/behavioral by examining the canonical
   decomposition, and independently classify it by representability tier by
   attempting to express it in OWL/SPARQL. If the partition were
   tautological, these would be the same test. They are not — one asks
   "does this depend on a `Callable` or computation beyond SPARQL?" and
   the other asks "can $\mathcal{SROIQ}$ or SPARQL express this?"

2. **The coincidence could fail in a modified framework.** If GDS stored
   transition functions as symbolic expressions (e.g., polynomial
   arithmetic over state variables), then $f_{\text{behav}}$ would move
   from R3-undecidable to R2 (polynomial evaluation is decidable and
   expressible in SPARQL via arithmetic). The structural/behavioral
   partition would remain the same (it still updates state), but the
   representability boundary would shift. Similarly, if SPARQL were
   extended with Unicode normalization primitives, auto-wiring would move
   from R3-separation to R2.

3. **The key structural insight**: the canonical decomposition $h = f
   \circ g$ separates topology from computation, and the
   OWL+SHACL-core+SPARQL stack can express exactly the topological content.
   This is not a definition — it is a claim about the expressiveness of
   description logic and SPARQL relative to the structure of GDS
   specifications. The claim holds because GDS made the design choice to
   allow arbitrary `Callable` for behavioral components and to use
   string-based tokenization for wiring — different design choices would
   yield a different boundary.

### Status

Theorem C.3 is **proved** under the current GDS design. The proof depends
on two GDS design choices:

1. Behavioral components accept arbitrary `Callable` (making them
   R3-undecidable via Rice's theorem)
2. Auto-wiring uses Python string processing (making it R3-separation via
   computational class gap)

If either design choice changed, the theorem would need revision.

---

## References

- [r3-undecidability.md](r3-undecidability.md) — R3 non-representability
  proofs (Props 1-6)
- [formal-representability.md](../formal-representability.md) — Properties
  3.1-4.6, Def 2.2, Check 6.1, Property 6.2
- [deep_research.md](../deep_research.md) — SROIQ expressiveness analysis
- Horrocks, I. et al. "The Even More Irresistible SROIQ." (2006) —
  2NExpTime decidability of $\mathcal{SROIQ}$
- Rice, H.G. "Classes of Recursively Enumerable Sets and Their Decision
  Problems." (1953)
