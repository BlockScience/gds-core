# R3 Non-Representability: Formal Proofs

**Claim.** No finite OWL/SHACL/SPARQL expression can capture the semantic
properties of GDS concepts classified as R3. The gap has two distinct
sources: *undecidability* (Rice's theorem, halting problem) and
*computational class separation* (decidable operations that exceed the
expressiveness of all three formalisms).

---

## Preliminaries

**Definition (R3, per formal-representability.md Def 2.2).** A GDS concept
$c$ is R3 if no finite OWL/SHACL/SPARQL expression can capture it. The gap
follows from one or more of:

- **Rice's theorem**: any non-trivial semantic property of programs is
  undecidable
- **The halting problem**: arbitrary `Callable` may not terminate
- **Computational class separation**: string parsing and temporal execution
  exceed the expressiveness of all three formalisms

R3 concepts subdivide into:

- **R3-undecidable**: concepts whose semantic properties are undecidable
  (Rice's theorem / halting problem)
- **R3-separation**: concepts that are decidable but exceed SPARQL's
  computational model (no mutable state, no unbounded string computation,
  no multi-pass processing)

**Theorem (Rice, 1953).** For any non-trivial semantic property $P$ of
partial recursive functions, the set $\{i \mid \varphi_i \in P\}$ is
undecidable. A property $P$ is *non-trivial* if it is satisfied by some
but not all partial recursive functions.

---

## R3-Undecidable Concepts

### 1. Transition Functions ($f_{\text{behav}}$)

**Definition.** In the canonical decomposition $h = f \circ g$, the state
update decomposes as $f = \langle f_{\text{struct}}, f_{\text{read}},
f_{\text{behav}} \rangle$ where $f_{\text{behav}} : (x, d) \mapsto x'$ is
an arbitrary Python callable implementing the mechanism's state transition.

**Proposition 1.** Any non-trivial semantic property of $f_{\text{behav}}$
is undecidable.

*Proof.* Let $P$ be a non-trivial semantic property of transition functions
(e.g., "reaches equilibrium", "preserves non-negativity", "is monotone").
Each $f_{\text{behav}}$ is implemented as a Python callable, which is
Turing-complete. The set of Python callables is recursively enumerable and
can encode any partial recursive function.

By Rice's theorem, $\{f \mid f \in P\}$ is undecidable. Therefore no
static analysis — including any OWL reasoner, SHACL validator, or SPARQL
query operating over a finite RDF graph — can determine whether an
arbitrary $f_{\text{behav}}$ satisfies $P$.

OWL DL reasoning is in 2NExpTime (decidable) precisely because
$\mathcal{SROIQ}(\mathcal{D})$ restricts to the decidable fragment of
first-order logic. It cannot express the fixed-point semantics required to
evaluate $f_{\text{behav}}(x, d)$ for arbitrary inputs. $\square$

**Classification:** R3-undecidable.

### 2. Constraint Predicates ($\text{TypeDef.constraint}$)

**Definition.** `TypeDef.constraint: Optional[Callable[[Any], bool]]` is
an arbitrary predicate over values of a given type.

**Proposition 2.** The equivalence and satisfiability of constraint
predicates are undecidable.

*Proof.* Consider two constraints $c_1, c_2 :
\texttt{Callable[[Any], bool]}$.

(a) *Equivalence*: "Do $c_1$ and $c_2$ accept the same values?" is the
question $\forall x.\, c_1(x) = c_2(x)$. This is equivalence of arbitrary
programs, which is undecidable by Rice's theorem (the property "computes
the same function as $c_2$" is non-trivial and semantic).

(b) *Satisfiability*: "Does $c$ accept any value?" is the question
$\exists x.\, c(x) = \text{True}$. This reduces to the halting problem:
given a program $M$, define $c(x) = [\text{run } M \text{ for } x
\text{ steps and check if it halts}]$. Then $c$ is satisfiable iff $M$
halts.

SHACL-core can express specific constraint patterns (e.g.,
`sh:minInclusive`, `sh:maxInclusive`) for the common cases used in
practice (Probability, NonNegativeFloat, PositiveInt). These are R2. But
the *general* `Callable[[Any], bool]` is R3. $\square$

**Classification:** R3-undecidable.

### 3. Admissibility Predicates ($U_{x,\text{behav}}$)

**Definition.** `AdmissibleInputConstraint.constraint:
Optional[Callable[[dict, dict], bool]]` maps `(state, input) -> bool`,
determining whether an input is admissible given the current state.

**Proposition 3.** Any non-trivial semantic property of admissibility
predicates is undecidable.

*Proof.* The structural skeleton $U_{x,\text{struct}}$ (which boundary
block, which entity-variable dependencies) is R1 — it is a finite relation
exported as RDF triples. But the behavioral component
$U_{x,\text{behav}}$ is a `Callable` with the same Turing-completeness as
$f_{\text{behav}}$. By Rice's theorem, any non-trivial semantic property
of this callable is undecidable (same argument as Proposition 1).

Specifically: "Given state $x$, is the set of admissible inputs non-empty?"
requires evaluating $\exists u.\, \text{constraint}(x, u) = \text{True}$,
which reduces to the halting problem by the same construction as
Proposition 2(b). $\square$

**Classification:** R3-undecidable.

---

## R3-Separation Concepts

These concepts are *decidable* — they terminate in polynomial time. But
they exceed SPARQL 1.1's computational model, which lacks mutable state,
multi-pass string processing, and ordered set operations over dynamically
generated elements.

### 4. Auto-Wiring Process

**Definition.** The `>>` operator discovers connections between blocks by
computing token overlap: `tokenize(port_name) -> frozenset[str]`, then
checking `frozenset` intersection.

**Proposition 4.** The auto-wiring process exceeds SPARQL's expressiveness,
despite being decidable in $O(n)$ time.

*Proof.* The `tokenize()` function (`tokens.py`) performs:

1. Unicode NFC normalization
2. Split on ` + ` (space-plus-space delimiter)
3. Split each part on `, ` (comma-space delimiter)
4. Strip whitespace and lowercase each token
5. Discard empty strings

This is $O(n)$ string processing that always terminates. However, SPARQL
1.1 cannot replicate it because:

- **NFC normalization** requires stateful multi-pass character rewriting,
  which SPARQL's `REGEX()` and string functions cannot express
- **Multi-delimiter splitting** with ordered priority (` + ` before `, `)
  requires sequential processing absent from SPARQL's declarative model
- **Dynamic set construction** (tokenizing two port names, then computing
  set intersection) requires mutable intermediate state

The *output* of auto-wiring (the discovered `WiringIR` edges) is exported
as explicit RDF triples and is fully R1. Only the *computation that
discovers them* is R3. $\square$

**Classification:** R3-separation (decidable, O(n), but beyond SPARQL).

### 5. Construction Validation

**Definition.** The `@model_validator` decorators on composition operators
and block roles enforce invariants at Python object construction time.

**Proposition 5.** The GDS construction validators are decidable but exceed
SPARQL's expressiveness. The framework's extensibility makes the *general*
case Turing-complete.

*Proof.* The *current* GDS validators are decidable and efficient:

- `StackComposition`: calls `tokenize()` (O(n), Prop 4) + set intersection
  (O(min(|A|,|B|)))
- `BoundaryAction`: checks `forward_in == ()` (constant time)
- `Mechanism`: checks `backward_in == ()` and `backward_out == ()` (constant
  time)
- `TemporalLoop`: checks `direction == COVARIANT` for each wiring (O(k))

These are all polynomial. However, they involve `tokenize()` (proven beyond
SPARQL in Prop 4), so they exceed SPARQL's expressiveness.

Additionally, the framework is extensible: domain DSLs subclass
`AtomicBlock` and may add arbitrary `@model_validator` logic. Since Python
`@model_validator` can contain arbitrary code, the *system-level* guarantee
is that construction validation is not bounded to any fixed complexity
class. Any specific DSL may introduce Turing-complete validators.

Therefore: the current validators are R3-separation; the framework's open
extension points make the general case R3-undecidable. $\square$

**Classification:** R3-separation (current validators), R3-undecidable
(general extensible case).

### 6. Scheduling Semantics

**Definition.** The temporal execution order of blocks within and across
timesteps is not stored in `GDSSpec` — it is an external concern determined
by the simulation engine (`gds-sim`).

**Proposition 6.** Scheduling semantics are R3 because they are not
represented in the data model.

*Proof.* Scheduling is not a field on any GDS data structure. It exists
only at runtime, external to the specification. A concept that does not
appear in the data model cannot be serialized to RDF, and therefore cannot
be captured by any OWL/SHACL/SPARQL expression operating over the RDF
export. $\square$

**Classification:** R3 (trivially — absent from the data model).

---

## Summary

| R3 Concept | Sub-classification | Source | Decidable? |
|---|---|---|---|
| $f_{\text{behav}}$ | R3-undecidable | Rice's theorem | No |
| TypeDef.constraint | R3-undecidable | Rice's + halting | No |
| $U_{x,\text{behav}}$ | R3-undecidable | Rice's theorem | No |
| Auto-wiring process | R3-separation | Computational class | Yes, O(n) |
| Construction validation | R3-separation / undecidable | Class + extensibility | Current: yes; general: no |
| Scheduling semantics | R3 (absent) | Not in data model | N/A |

The R3 boundary has two distinct mechanisms:

1. **Undecidability** (Props 1-3): Arbitrary `Callable` can encode any
   partial recursive function. No decidable logic can determine non-trivial
   semantic properties of these functions.

2. **Computational separation** (Props 4-5): The specific operations
   (tokenization, set intersection) are decidable but exceed what SPARQL
   1.1 can express. SPARQL lacks mutable state, multi-pass string
   processing, and dynamic set construction.

Both mechanisms produce the same practical outcome: the concept cannot be
represented in OWL/SHACL/SPARQL. The distinction matters for formal
precision — R3-undecidable concepts *cannot* be captured by *any* finite
formalism, while R3-separation concepts could theoretically be captured by
a more expressive but still decidable formalism (e.g., a language with
built-in Unicode normalization and set operations).
