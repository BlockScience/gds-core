# R3 Undecidability: Formal Reduction

**Claim.** No finite OWL/SHACL/SPARQL expression can capture the semantic
properties of GDS concepts classified as R3. The gap is fundamental, not a
limitation of the current implementation.

---

## Preliminaries

**Definition (R3).** A GDS concept $c$ is R3 if no finite expression in
$\mathcal{SROIQ}(\mathcal{D})$ (OWL DL), SHACL, or SPARQL 1.1 can decide
whether an arbitrary instance of $c$ satisfies a given non-trivial semantic
property.

**Theorem (Rice, 1953).** For any non-trivial semantic property $P$ of
partial recursive functions, the set $\{i \mid \varphi_i \in P\}$ is
undecidable. A property $P$ is *non-trivial* if it is satisfied by some
but not all partial recursive functions.

**Theorem (Turing, 1936).** The halting problem is undecidable: there is no
algorithm that, given an arbitrary program and input, determines whether
the program terminates.

---

## R3 Concepts in GDS

Six GDS concepts are classified as R3 in the formal representability
analysis (Def 6.1). We prove undecidability for each.

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

More concretely: OWL DL reasoning is in 2NExpTime (decidable) precisely
because $\mathcal{SROIQ}(\mathcal{D})$ restricts to the decidable fragment
of first-order logic. It cannot express the fixed-point semantics required
to evaluate $f_{\text{behav}}(x, d)$ for arbitrary inputs. $\square$

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

SHACL can express specific constraint patterns (e.g.,
`sh:minInclusive`, `sh:maxInclusive`) for the common cases used in
practice (Probability, NonNegativeFloat, PositiveInt). These are R2. But
the *general* `Callable[[Any], bool]` is R3. $\square$

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
$f_{\text{behav}}$. The argument from Proposition 1 applies directly.

Specifically: "Given state $x$, is the set of admissible inputs non-empty?"
requires evaluating $\exists u.\, \text{constraint}(x, u) = \text{True}$,
which reduces to the halting problem by the same construction as
Proposition 2(b). $\square$

### 4. Auto-Wiring Process

**Definition.** The `>>` operator discovers connections between blocks by
computing token overlap: `tokenize(port_name) -> frozenset[str]`, then
checking `frozenset` intersection.

**Proposition 4.** The auto-wiring *process* is R3, even though its
*results* are R1.

*Proof.* The `tokenize()` function performs string operations (Unicode NFC
normalization, splitting on ` + ` and `, `, lowercasing, stripping) that
exceed the expressiveness of SPARQL's regex matching. SPARQL 1.1 provides
`REGEX()` and `STRAFTER()`/`STRBEFORE()`, but:

- Unicode NFC normalization is not expressible in SPARQL
- The specific splitting semantics (` + ` vs `, ` vs plain space) require
  ordered multi-pass string processing
- Token set intersection requires computing and comparing sets, which
  SPARQL cannot do over dynamically generated elements

However, the *output* of auto-wiring (the discovered `WiringIR` edges) is
exported as explicit RDF triples and is fully R1. Only the *computation*
that discovers them is R3. $\square$

### 5. Construction Validation

**Definition.** The `@model_validator` decorators on `StackComposition`,
`FeedbackLoop`, `TemporalLoop`, and block roles (`BoundaryAction`,
`Mechanism`) enforce invariants at Python object construction time.

**Proposition 5.** Construction validation is R3.

*Proof.* The validators execute arbitrary Python code at construction time.
For example, `StackComposition._compute_interface_and_validate()` calls
`_collect_tokens()` (which invokes `tokenize()`, proven R3 in Proposition
4) and raises `GDSTypeError` on token mismatch.

More generally, `@model_validator` can contain arbitrary logic — it is a
Turing-complete computation that runs during object instantiation. Whether
a given set of constructor arguments will pass validation is undecidable in
the general case. $\square$

### 6. Scheduling Semantics

**Definition.** The temporal execution order of blocks within and across
timesteps is not stored in `GDSSpec` — it is an external concern determined
by the simulation engine (`gds-sim`).

**Proposition 6.** Scheduling semantics are R3.

*Proof.* Scheduling requires:

- Evaluating temporal dependencies between blocks (which may involve
  $f_{\text{behav}}$ to determine data readiness)
- Fixed-point computation for within-timestep feedback loops
- Arbitrary termination conditions for temporal loops (`exit_condition`)

Each of these involves Turing-complete computation. Additionally,
scheduling is not even *stored* in the GDS specification — it exists only
at runtime, making it trivially non-representable in any static
formalism. $\square$

---

## Summary

| R3 Concept | Undecidability Source | Reduction |
|---|---|---|
| $f_{\text{behav}}$ | Rice's theorem | Non-trivial semantic property of programs |
| TypeDef.constraint | Rice's + halting problem | Equivalence and satisfiability of predicates |
| $U_{x,\text{behav}}$ | Rice's theorem | Same as $f_{\text{behav}}$ (arbitrary callable) |
| Auto-wiring process | Computational separation | String processing exceeds SPARQL expressiveness |
| Construction validation | Turing-completeness | Arbitrary Python in `@model_validator` |
| Scheduling semantics | Not stored + Turing-complete | Runtime-only, involves $f_{\text{behav}}$ evaluation |

The R3 boundary is not a gap in the implementation — it is a mathematical
impossibility. Any system that attempts to statically represent these
concepts in a decidable logic must either:

1. Restrict to a decidable fragment (which GDS does via the R1/R2 tiers), or
2. Embed an undecidable logic (which would make reasoning intractable).

GDS chooses (1), and the `rho` mapping faithfully implements this choice by
exporting structural skeletons and documenting R3 losses.
