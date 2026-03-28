# GDS Formal Verification — Research Journal

Structured log of verification research for the Generalized Dynamical Systems
ecosystem. Each entry records motivation, method, outcome, and next steps.

Verification plan: [verification-plan.md](verification-plan.md)
Issues: [#134](https://github.com/BlockScience/gds-core/issues/134),
[#135](https://github.com/BlockScience/gds-core/issues/135),
[#136](https://github.com/BlockScience/gds-core/issues/136),
[#137](https://github.com/BlockScience/gds-core/issues/137),
[#138](https://github.com/BlockScience/gds-core/issues/138)

---

## Entry 001 — 2026-03-28

**Subject:** Project setup — research directory, verification plan, literature review

### Motivation

Three formal claims in the GDS ecosystem remain unverified:

1. The composition algebra `(Block, >>, |, fb, loop)` satisfies categorical
   axioms (interchange law, coherence, traced monoidal structure) — stated
   in `formal-representability.md` Def 1.1 but not proved.
2. The R1/R2/R3 representability taxonomy is a designed classification, not
   an independently derived result — acknowledged in Check 6.1.
3. Round-trip bijectivity `rho^{-1}(rho(c)) =_struct c` is tested with a
   single thermostat fixture, not with randomized inputs.

### Actions

1. **Consolidated research artifacts** into `docs/research/` to separate
   from published package code (`5a3f1fa`). Moved 5 documents:
   - `research-boundaries.md` (from `docs/guides/`)
   - `paper-implementation-gap.md` (from `docs/guides/`)
   - `formal-representability.md` (from `docs/owl/guide/`)
   - `representation-gap.md` (from `packages/gds-owl/docs/`)
   - `deep_research.md` (from `packages/gds-owl/docs/`)

   Updated all cross-references in mkdocs.yml and 5 markdown files.
   Removed duplicate `packages/gds-owl/docs/formal-representability.md`.
   Verified `mkdocs build --strict` passes.

2. **Literature review** via NotebookLM using three sources:
   - Zargham & Shorish (2022) — GDS foundations paper
   - `formal-representability.md` — representability analysis
   - `deep_research.md` — categorical semantics survey

   Key findings:
   - **Prover selection:** Coq + ViCAR (string diagram tactics) + Interaction
     Trees (traced monoidal categories) is the best fit for GDS's bidirectional
     block algebra with two feedback operators.
   - **PROPs** (Products and Permutations categories) are the natural
     formalization target — objects are natural numbers, tensor is addition.
   - **Hasegawa's correspondence** (Conway fixed-point <-> categorical trace)
     validates that `fb` computes within-timestep fixed points.
   - **Phase ordering matters:** categorical axioms must hold before the
     representability boundary can be cleanly stated, and that boundary must
     be established before round-trip equality checks are meaningful.

3. **Wrote verification plan** (`docs/research/verification-plan.md`) with
   4 phases:
   - Phase 1: Composition algebra (Hypothesis PBT + Coq/ViCAR)
   - Phase 2: Representability boundaries (formal reduction)
   - Phase 3: Round-trip fidelity (Hypothesis PBT)
   - Phase 4: Dynamical invariants (future gds-analysis)

4. **Created 5 GitHub issues** with `verification` label:
   - #134: Phase 1a — interchange law PBT
   - #135: Phase 1b-c — Coq mechanized proofs
   - #136: Phase 2 — R1/R2/R3 as theorem
   - #137: Phase 3 — round-trip PBT
   - #138: Phase 4 — dynamical invariants

### References

- Joyal, Street, Verity. "Traced monoidal categories." (1996)
- Hasegawa. "Recursion from cyclic sharing." (1997)
- Mac Lane. "Categories for the Working Mathematician." (1971)
- ViCAR: https://github.com/inQWIRE/ViCAR
- Interaction Trees: https://github.com/DeepSpec/InteractionTrees

---

## Entry 002 — 2026-03-28

**Subject:** Phase 1a + Phase 3 — property-based testing implementation

### Motivation

The two immediate, low-cost verification actions identified in the plan:
1. Hypothesis tests for the interchange law (Phase 1a, #134)
2. Hypothesis strategies for random GDSSpec round-trip testing (Phase 3, #137)

### Method

#### Phase 1a: Composition Algebra Properties

**File:** `packages/gds-framework/tests/test_algebra_properties.py`

Wrote Hypothesis strategies for:
- `port_tuples` — generate tuples of `Port` with distinct lowercase names
- `interfaces` — random `Interface` with ports on all four slots
- `named_block` — random `AtomicBlock` with name/interface
- `stackable_pair` — two blocks sharing a token for `>>` compatibility
- `interchange_quadruple` — four blocks (f, g, h, j) with two distinct
  shared tokens enabling both sides of the interchange law

Tested properties (200 random examples each):
- **Interchange law:** `(g >> f) | (j >> h)` has same interface as
  `(g | j) >> (f | h)` — port name sets match, flattened block sets match
- **Sequential associativity:** `(a >> b) >> c` = `a >> (b >> c)`
- **Parallel associativity:** `(a | b) | c` = `a | (b | c)`
- **Parallel commutativity:** `a | b` has same port name sets as `b | a`
- **Identity:** empty-interface block is identity for both `>>` and `|`
- **Structural concatenation:** composed interface is tuple concatenation
  of constituent interfaces

**Result:** All 11 tests pass. No interchange law violations found across
2,200+ random compositions.

#### Phase 3: OWL Round-Trip PBT

**File:** `packages/gds-owl/tests/strategies.py`

Wrote `gds_specs()` strategy generating random valid `GDSSpec` instances:
- 1-3 TypeDefs (int/float/str/bool, optional units)
- 1-2 Spaces with 1-2 fields each
- 1 Entity with 1-2 state variables
- 2-5 blocks in a sequential chain (BoundaryAction -> Policy* -> Mechanism)
- 1 SpecWiring connecting the chain
- All R3 fields (constraints) set to None

Generated names filter out Python keyword collisions (`name`, `description`,
`symbol`) with the `gds.space()` / `gds.entity()` factory functions.

**File:** `packages/gds-owl/tests/test_roundtrip_pbt.py`

14 property-based tests (100 random specs each):
- Name, type names, python_types, units survive
- Constraints are correctly lossy (always None after round-trip)
- Space names and field names survive (set-based comparison)
- Entity names and variable names survive
- Block names and roles (kind) survive
- Mechanism.updates survive (set-based comparison)
- Wiring names and wire counts survive

**Result:** All 14 tests pass. No round-trip fidelity violations found
across 1,400 random specifications.

### Outcome

| Suite | Tests | Random examples | Failures |
|---|---|---|---|
| Composition algebra (Phase 1a) | 11 | ~2,200 | 0 |
| OWL round-trip (Phase 3) | 14 | ~1,400 | 0 |
| **Total new coverage** | **25** | **~3,600** | **0** |

Added `hypothesis` as dev dependency for both `gds-framework` and `gds-owl`.

Commit: `835ac83`

### Observations

1. The interchange law test compares **port name sets**, not port tuple order.
   This is correct for the monoidal structure (commutativity of `|`) but a
   stronger test would verify that the flattened block evaluation order is
   consistent — which it is, as confirmed by `test_flatten_same_blocks`.

2. The round-trip strategy generates linear block chains only (no parallel
   composition or feedback in the spec). Future work should extend to
   branching topologies and multiple wirings.

3. The `gds_specs` strategy currently generates 2-5 blocks. Scaling to
   larger specs (10-20 blocks) would stress-test the RDF serialization
   for blank node management and property ordering.

### Next Steps

- [ ] Extend `gds_specs` to generate specs with parallel block groups
- [ ] Add SystemIR, CanonicalGDS, and VerificationReport PBT round-trips
- [ ] Add SHACL/SPARQL validation gate before reimport (Phase 3c)
- [ ] Investigate Coq/ViCAR for mechanized interchange law proof (Phase 1b)
- [ ] Write R3 undecidability reduction (Phase 2a)

---
