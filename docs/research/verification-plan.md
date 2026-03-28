# GDS Formal Verification Plan

## Context

The GDS composition algebra `(Block, >>, |, fb, loop)` and its canonical
decomposition `h = f . g` are the structural foundation for five domain DSLs.
Three claims in [formal-representability.md](formal-representability.md) remain
unverified:

1. **Categorical axioms** -- interchange law, coherence conditions, and traced
   monoidal structure for feedback have not been formally proved (Def 1.1)
2. **R1/R2/R3 taxonomy** -- acknowledged as a designed classification, not an
   independently derived mathematical result (Consistency Check 6.1)
3. **Round-trip bijectivity** -- `rho^{-1}(rho(c)) =_struct c` holds by test
   suite, but not by proof; blank node isomorphism and ordering are handled
   ad-hoc

This plan establishes a phased verification roadmap with strict dependency
ordering. Each phase produces artifacts that the next phase depends on.

---

## Phase 1: Composition Algebra (Categorical Semantics)

**Goal:** Prove the GDS block algebra is a symmetric monoidal category with
traced structure.

### 1a. Interchange Law

Prove: `(g >> f) | (j >> h) = (g | j) >> (f | h)` for all suitably typed
blocks.

This is the gate. If it fails, parallel and sequential composition are
order-dependent, and the diagrammatic syntax is ambiguous.

**Approach:** Property-based testing first (Hypothesis), then mechanized proof.

- **Hypothesis (Python):** Generate random `AtomicBlock` instances with
  compatible interfaces, compose both ways, assert structural equality of
  the resulting `ComposedBlock` interface signatures.
- **Coq (ViCAR):** Formalize `Interface` as objects, `Block` as morphisms,
  `>>` as composition, `|` as tensor. Prove interchange via ViCAR's
  automated rewriting tactics for string diagrams.

### 1b. Mac Lane Coherence

Prove: any two well-typed morphisms built from structural isomorphisms
(associator, unitor, braiding) and identity via `>>` and `|` are equal.

**Approach:** Coq/ViCAR. Once the interchange law is mechanized, coherence
follows from the standard construction. ViCAR provides this for symmetric
monoidal categories out of the box once the algebra is instantiated.

### 1c. Traced Monoidal Structure

Prove the Joyal-Street-Verity axioms for `fb` (contravariant, within-timestep)
and `loop` (covariant, across-timestep):

| Axiom | Statement |
|---|---|
| Vanishing | Tracing over the unit object is identity |
| Superposing | Trace commutes with parallel composition |
| Yanking | Tracing the braiding yields identity |
| Sliding | Morphisms slide around the feedback loop |
| Tightening | Trace of a tensor = sequential traces |

**Approach:** Coq with Interaction Trees library. The two feedback operators
have different variance, so they require separate trace instances:

- `fb`: contravariant trace (backward ports looped within timestep)
- `loop`: covariant trace (forward ports carried across timesteps)

Hasegawa's correspondence (Conway fixed-point <-> categorical trace) validates
that `fb` computes within-timestep fixed points soundly.

### 1d. Token System Formalization

The auto-wiring predicate (token overlap) must be formalized as part of the
categorical structure. Tokens define when `>>` is well-typed: sequential
composition requires `overlap(out_tokens(f), in_tokens(g))`.

**Approach:** Formalize token sets as a preorder on port names. Show that
token overlap induces a well-defined composition predicate compatible with
the monoidal structure.

### Artifacts

| Artifact | Location | Format |
|---|---|---|
| Hypothesis interchange tests | `packages/gds-framework/tests/test_algebra_properties.py` | Python |
| Coq formalization | `docs/research/verification/coq/` | Coq (`.v`) |
| Proof summary | `docs/research/verification/proofs.md` | Markdown |

### Dependencies

None -- this is the foundation.

---

## Phase 2: Representability Boundaries (R1/R2/R3 as Theorem)

**Goal:** Elevate the R1/R2/R3 classification from taxonomy to theorem.

### 2a. R3 Undecidability Reduction

Prove: for any non-trivial property P of `f_behav`, determining whether P
holds is undecidable.

**Approach:** Standard reduction from the halting problem. The formal
representability doc already states the argument (Properties 4.2, 4.4);
this phase writes it as a proper proof.

- `TypeDef.constraint: Callable[[Any], bool]` -- equivalence of two
  constraints is undecidable (Rice's theorem)
- `f_behav: (x, u) -> x'` -- any non-trivial semantic property of the
  transition function is undecidable

**Format:** Pen-and-paper proof in LaTeX, optionally mechanized.

### 2b. R1/R2 Decidability Bounds

Prove: all concepts classified as R1 are expressible in SROIQ(D) + SHACL-core,
and all R2 concepts are expressible in SPARQL 1.1.

**Approach:** Constructive -- the gds-owl export functions are the witness.
For each R1 concept, show the OWL class/property structure is a valid SROIQ
axiom. For each R2 concept, show the SPARQL query terminates and correctly
validates the property.

The existing SHACL shapes (`gds_owl.shacl`) and SPARQL queries
(`gds_owl.sparql`) serve as constructive evidence. The proof obligation is
to show they are *complete* for their respective tiers.

### 2c. Partition Independence

Prove: the alignment between `G_struct/G_behav` and R1+R2/R3 is not
tautological.

This is the hardest part. The formal-representability doc acknowledges this
is "a consistency property of our taxonomy, not an independent mathematical
result." To strengthen it:

- Define `G_struct` and `G_behav` independently of representability (e.g.,
  via the canonical decomposition: `g` and `f_struct` are structural,
  `f_behav` is behavioral)
- Define R1/R2/R3 independently via expressiveness of SROIQ/SPARQL
- Show the two partitions coincide

**Approach:** Formal argument. May remain a conjecture if the definitions
are inherently coupled.

### Artifacts

| Artifact | Location | Format |
|---|---|---|
| R3 undecidability proof | `docs/research/verification/r3-undecidability.md` | Markdown + LaTeX |
| R1/R2 completeness argument | `docs/research/verification/representability-proof.md` | Markdown |

### Dependencies

Phase 1 (the topology `g` must be unambiguous before separating it from `f_behav`).

---

## Phase 3: Round-Trip Fidelity (Property-Based Testing)

**Goal:** Strengthen round-trip correctness from fixture-based tests to
property-based testing with random generation.

### 3a. Hypothesis Strategies for GDSSpec

Write Hypothesis strategies that generate valid, random `GDSSpec` instances:

```
strategy: GDSSpec
  = draw(types: dict[str, TypeDef])       # random type names + python_type
  + draw(spaces: dict[str, Space])        # fields referencing drawn types
  + draw(entities: dict[str, Entity])     # variables referencing drawn spaces
  + draw(blocks: dict[str, AtomicBlock])  # role-partitioned, valid interfaces
  + draw(wirings: dict[str, SpecWiring])  # source/target referencing drawn blocks
  + draw(params: ParameterSchema)         # optional parameter defs
```

Constraints on generation:
- Block interfaces must have valid port names (tokenizable)
- Wirings must reference existing blocks
- Mechanism.updates must reference existing entity variables
- R3 fields (constraint callables) set to `None` -- they are lossy by design

### 3b. Structural Equality Checks

The round-trip assertion `rho^{-1}(rho(c)) =_struct c` requires:

- **Set-based comparison** for ports, wires, blocks (RDF triples are unordered)
- **Content-based blank node matching** (field name + type, not node ID)
- **R3 field exclusion** (constraints, python_type fallback to `str`)

Implement a `structural_eq(spec1, spec2) -> bool` helper that handles these.

### 3c. SHACL/SPARQL Validation Gate

Before reimporting, validate the exported RDF against:
- SHACL shapes (R1 tier) -- all node/property constraints pass
- SPARQL queries (R2 tier) -- no structural violations detected

Only graphs passing both gates are reimported and compared.

### 3d. Extend to SystemIR, CanonicalGDS, VerificationReport

The existing `test_roundtrip.py` covers all four `rho/rho^{-1}` pairs with
the thermostat fixture. Extend each with Hypothesis strategies:

| Round-trip | Current tests | PBT target |
|---|---|---|
| `GDSSpec` | 11 fixture tests | Random spec generation |
| `SystemIR` | 4 fixture tests | Random IR from compiled specs |
| `CanonicalGDS` | 2 fixture tests | Random canonical from `project_canonical()` |
| `VerificationReport` | 2 fixture tests | Random reports with varied findings |

### Artifacts

| Artifact | Location | Format |
|---|---|---|
| Hypothesis strategies | `packages/gds-owl/tests/strategies.py` | Python |
| PBT round-trip tests | `packages/gds-owl/tests/test_roundtrip_pbt.py` | Python |
| Structural equality helper | `packages/gds-owl/tests/helpers.py` | Python |

### Dependencies

Phase 2 (must know which fields are structural vs lossy before writing
equality checks).

---

## Phase 4: Dynamical Invariants (Future)

**Goal:** Verify existence and controllability properties from Zargham &
Shorish (2022).

### 4a. Existence of Solutions (Paper Theorem 3.6)

Prove: if the constraint set `C(x, t; g)` is compact, convex, and continuous,
then an attainability correspondence exists.

This is a runtime/R3 concern -- it requires evaluating `f` on concrete state.
The `gds-analysis` package now exists with reachability (`reachable_set`,
`configuration_space`, `backward_reachable_set`) but existence proofs
require additional analytical machinery beyond trajectory sampling.

### 4b. Local Controllability (Paper Theorem 4.4)

Prove: under Lipschitzian correspondence with closed convex values, the system
is 0-controllable from a neighborhood around equilibrium.

### 4c. Connection to Bridge Proposal

Steps 3-7 of the bridge proposal in [paper-implementation-gap.md](paper-implementation-gap.md)
map to this phase. Steps 1-5 are complete (AdmissibleInputConstraint,
TransitionSignature, StateMetric, reachable_set, configuration_space).
Steps 6-7 remain open (#142).

### Dependencies

Phases 1-3 (structural soundness must be established before reasoning about
dynamics).

---

## Prover Selection Summary

| Component | Tool | Rationale |
|---|---|---|
| Interchange law (quick check) | Hypothesis (Python) | Fast iteration, catches bugs early |
| Interchange + coherence (proof) | Coq + ViCAR | String diagram tactics, ZX-calculus heritage |
| Traced monoidal structure | Coq + Interaction Trees | Coinductive bisimulation for feedback |
| R3 undecidability | LaTeX (pen-and-paper) | Standard reduction, no mechanization needed |
| Round-trip fidelity | Hypothesis (Python) | Property-based testing with shrinking |
| Dynamical invariants | TBD (gds-analysis) | Requires runtime execution engine |

---

## Execution Priority

```
Phase 1a (interchange PBT)     -- immediate, high value, low cost
Phase 3a-b (round-trip PBT)    -- immediate, extends existing test_roundtrip.py
Phase 1a-c (Coq proofs)        -- medium-term, requires Coq expertise
Phase 2a (R3 reduction)        -- medium-term, pen-and-paper
Phase 2b-c (R1/R2 bounds)      -- medium-term, constructive from existing code
Phase 4 (dynamics)             -- long-term, blocked on gds-analysis
```

The two immediate actions are:
1. `test_algebra_properties.py` -- Hypothesis tests for interchange law
2. `test_roundtrip_pbt.py` -- Hypothesis strategies for random GDSSpec generation

Both produce concrete test artifacts that increase confidence while the
formal proofs are developed in parallel.

---

## References

- Joyal, Street, Verity. "Traced monoidal categories." (1996)
- Hasegawa. "Recursion from cyclic sharing." (1997)
- Mac Lane. "Categories for the Working Mathematician." (1971)
- Zargham, Shorish. "Generalized Dynamical Systems Part I: Foundations." (2022)
- ViCAR: https://github.com/inQWIRE/ViCAR
- Interaction Trees: https://github.com/DeepSpec/InteractionTrees
- [formal-representability.md](formal-representability.md) -- Def 1.1, Properties 4.2/4.4, Check 6.1
- [deep_research.md](deep_research.md) -- Full literature review
- [paper-implementation-gap.md](paper-implementation-gap.md) -- Bridge proposal Steps 1-7
