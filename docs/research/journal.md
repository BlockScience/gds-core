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

## Entry 003 — 2026-03-28

**Subject:** Phase 1a + Phase 3 — audit fixes and CI reproducibility

### Motivation

Code review of PBT tests identified 7 issues (2 critical, 4 important,
1 minor). Hypothesis tests also needed deterministic seeds for CI
reproducibility.

### Fixes Applied

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | Critical | `stackable_pair` duplicate port names | `port_tuples` now accepts `exclude` param; shared token excluded |
| 2 | Critical | Missing backward port assertions for `>>` | Added `backward_in` + `backward_out` assertions |
| 3 | Important | Identity tests only covered right-identity | Split into 4 tests: left/right for both `>>` and `\|` |
| 4 | Important | `gds_specs` generated 0 Policies 25% of the time | Changed `min_blocks=2` to `min_blocks=3` |
| 5 | Important | Vacuous lossiness test | Removed (fixture test in `test_roundtrip.py` covers real lossiness) |
| 6 | Important | Wire round-trip only checked count | Now checks `(source, target, space)` set equality |
| 7 | Minor | Inline import of `Mechanism` | Moved to module level |

### Reproducibility

Added Hypothesis profiles for deterministic CI:

- `ci` profile: `derandomize=True`, `database=None` — same inputs every
  run, no `.hypothesis/` database needed
- `dev` profile: randomized (default) — broader exploration locally
- CI workflow sets `HYPOTHESIS_PROFILE=ci` env var
- Both profiles auto-loaded via `settings.load_profile(os.getenv(...))`

Commit: `65cd552`

### Updated Test Counts

| Suite | Tests | Random examples |
|---|---|---|
| Composition algebra (Phase 1a) | 13 (+2 identity tests) | ~2,600 |
| OWL round-trip (Phase 3) | 13 (-1 vacuous, +1 wire content) | ~1,300 |

---

## Entry 004 — 2026-03-28

**Subject:** Phase 2 — formal proofs for R1/R2/R3 representability

### Motivation

The R1/R2/R3 taxonomy in `formal-representability.md` is acknowledged as
a designed classification (Check 6.1). Phase 2 elevates it to a theorem
with formal proofs.

### Method

Produced two documents in `docs/research/verification/`:

**`r3-undecidability.md`** — R3 non-representability proofs.

Key structural improvement: R3 has two distinct sub-classifications:

- **R3-undecidable**: concepts whose semantic properties are undecidable
  (Rice's theorem / halting problem). Applies to `f_behav`, `TypeDef.constraint`,
  `U_x_behav`.
- **R3-separation**: decidable computations that exceed SPARQL's model.
  Applies to auto-wiring (O(n) but needs NFC + multi-pass splitting) and
  construction validation (polynomial but needs tokenize()).

Six propositions proved:
1. `f_behav` — Rice's theorem (R3-undecidable)
2. `TypeDef.constraint` — Rice's + halting problem (R3-undecidable)
3. `U_x_behav` — Rice's theorem (R3-undecidable)
4. Auto-wiring — SPARQL expressiveness gap (R3-separation)
5. Construction validation — current: R3-separation; extensible: R3-undecidable
6. Scheduling — not in data model (trivially R3)

**`representability-proof.md`** — R1/R2 decidability + partition
independence.

- Part A: 9 R1 concepts with constructive witnesses (export functions +
  13 SHACL-core shapes)
- Part B: 4 R2 concepts with SPARQL witnesses (transitive closure,
  negation-as-failure, aggregation)
- Part C: Theorem C.3 proving $G_{\text{struct}} = \text{R1} \cup
  \text{R2}$ and $G_{\text{behav}} = \text{R3}$

Commit: `384e32c`

### Audit and Revisions

Two rounds of review identified 9 issues total:

**Round 1 (8 findings):**

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | Critical | R3 definition inconsistency between documents | Aligned to Def 2.2; introduced R3-undecidable/R3-separation |
| 2 | Critical | Auto-wiring called "undecidable" but is O(n) | Reclassified as R3-separation |
| 3 | Critical | Construction validation proved general case only | Split current (decidable) vs extensible (undecidable) |
| 4 | Important | "OWL (R1)" should be "R1 ∪ R2" | Fixed in Theorem C.3 reverse containment |
| 5 | Important | Missing Rice's theorem in forward containment | Added explicit invocation |
| 6 | Important | SHACL-core qualifier dropped in Part B | Consistent throughout; added SHACL-SPARQL note |
| 7 | Minor | Fragile line-number references | Replaced with function names |
| 8 | Minor | Redundant argument in Prop 6 | Simplified to "not in data model" |

Commit: `3072f5c`

**Round 2 (1 finding):**

Definition C.1 mentioned "computation beyond SPARQL" while claiming not to
reference SPARQL — a self-contradiction that weakened the non-tautology
argument. Fixed by replacing with intrinsic computational characterization:
"computation requiring mutable intermediate state or ordered multi-pass
processing." This makes the counterfactual genuine: extending SPARQL with
NFC primitives would move auto-wiring from R3 to R2, but it stays in
$G_{\text{behav}}$ (still requires multi-pass processing), so the
partitions diverge — proving non-tautology.

### Observations

1. The R3-undecidable/R3-separation distinction is a genuine structural
   improvement. It clarifies that auto-wiring is a *design choice* (use
   Python string processing) not a *mathematical necessity* (undecidable
   problem). A framework with built-in SPARQL tokenization primitives
   would have a different boundary.

2. Theorem C.3 now depends on two GDS design choices: (a) arbitrary
   `Callable` for behavioral components, (b) Python string processing for
   auto-wiring. Changing either would require revising the theorem.

3. The constructive witnesses (export functions + SHACL shapes + SPARQL
   templates) serve double duty: they are both the *proof* of
   representability and the *implementation* of it.

### Next Steps

- [x] ~~Write R3 undecidability reduction (Phase 2a)~~
- [x] ~~Write R1/R2 decidability bounds (Phase 2b)~~
- [x] ~~Write partition independence argument (Phase 2c)~~
- [ ] Extend `gds_specs` to generate specs with parallel block groups
- [ ] Investigate Coq/ViCAR for mechanized interchange law proof (Phase 1b)

---

## Entry 005 — 2026-03-28

**Subject:** Phase 3c-d — SHACL/SPARQL validation gate + derived property
preservation tests

### Motivation

Phase 3a-b (GDSSpec round-trip PBT) was complete but lacked:
- SHACL validation of exported RDF before reimport (3c)
- Round-trip coverage for SystemIR, CanonicalGDS, VerificationReport (3d)

### Method

#### Phase 3c: Validation Gates

Added two separate test classes to avoid coupling SPARQL tests to pyshacl:

- **TestSHACLConformance** (pyshacl-gated, 30 examples): validates exported
  GDSSpec and SystemIR RDF against structural SHACL shapes
- **TestSPARQLConformance** (no gate, 30 examples): verifies `blocks_by_role`
  query returns expected block names

#### Phase 3d: Derived Property Preservation

New strategies in `strategies.py`:
- `system_irs()`: compose blocks with `>>`, `compile_system()`
- `specs_with_canonical()`: `project_canonical()` on random spec
- `specs_with_report()`: `verify()` on compiled random spec
- `_compose_sequential()`: shared helper for block composition

**TestDerivedPropertyPreservation** (8 tests, 50 examples each):
- SystemIR: name, block names, wiring content (source/target pairs),
  composition type
- CanonicalGDS: boundary/policy/mechanism block sets, state variables
- VerificationReport: system name, finding count + check_id distribution
  (Counter-based, catches collapsed duplicates)

**TestStrategyInvariants** (2 tests, 50 examples each):
- G-002 failures only on BoundaryAction + Mechanism (expected by design)
- Same invariant holds after report round-trip

Commits: `a90cad8`, `e51d53f`

### Audit and Fixes

6 findings from code review:

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | Important | SPARQL test gated behind HAS_PYSHACL | Moved to own TestSPARQLConformance class |
| 2 | Important | G-002 test didn't round-trip, misplaced | Split into TestStrategyInvariants + round-trip version |
| 3 | Important | Finding set comparison lost multiplicity | Counter + len() assertion |
| 4 | Important | SystemIR wiring content not checked | Added source/target pair comparison |
| 5 | Minor | Dead else branch (min_blocks=3) | Removed |
| 6 | Minor | Duplicated composition logic | Extracted `_compose_sequential()` |

### Outcome

| Class | Tests | Examples | Purpose |
|---|---|---|---|
| TestSpecRoundTripPBT | 13 | 100 each | GDSSpec structural fidelity |
| TestSHACLConformance | 2 | 30 each | SHACL shape validation |
| TestSPARQLConformance | 1 | 30 each | SPARQL query correctness |
| TestDerivedPropertyPreservation | 8 | 50 each | IR/Canonical/Report round-trips |
| TestStrategyInvariants | 2 | 50 each | G-002 invariant + survival |
| **Total** | **26** | **~2,060** | |

Combined with Phase 1a (13 algebra tests, ~2,600 examples), total PBT
coverage is **39 tests generating ~4,660 random examples**.

### Issues Closed

- #137 (Phase 3: Property-based round-trip testing for OWL export/import)

### Remaining Open Issues

| Issue | Phase | Status |
|---|---|---|
| #135 | 1b-c: Coq mechanized proofs | Open (long-term, needs Coq expertise) |
| #138 | 4: Dynamical invariants | Closed (superseded by #140-#142) |

---

## Entry 006 — 2026-03-28

**Subject:** StateMetric (bridge Step 3) + gds-analysis package (Steps 4-5)

### Motivation

The bridge proposal (paper-implementation-gap.md) maps paper definitions to
code in 7 incremental steps. Steps 1-2 were done prior. Steps 3-5 were
identified as the next actionable work — Step 3 is structural (same pattern
as Steps 1-2), and Steps 4-5 require runtime but are now unblocked by
gds-sim's existence.

### Actions

#### Step 3: StateMetric (Paper Assumption 3.2)

Added `StateMetric` to gds-framework following the exact
AdmissibleInputConstraint / TransitionSignature pattern:

- `constraints.py`: frozen Pydantic model with `name`, `variables`
  (entity-variable pairs), `metric_type` (annotation), `distance`
  (R3 lossy callable), `description`
- `spec.py`: `GDSSpec.register_state_metric()` + `_validate_state_metrics()`
  (checks entity/variable references exist, rejects empty variables)
- `__init__.py`: exported as public API
- `export.py`: RDF export as `StateMetric` class + `MetricVariableEntry`
  blank nodes
- `import_.py`: round-trip import with `distance=None` (R3 lossy)
- `shacl.py`: `StateMetricShape` (name required, xsd:string)
- 9 new framework tests + 1 OWL round-trip test

Commit: `f9168ee`

#### gds-analysis Package (#140)

New package bridging gds-framework structural annotations to gds-sim
runtime. Dependency graph:

```
gds-framework  <--  gds-sim  <--  gds-analysis
     ^                                  |
     +----------------------------------+
```

Three modules:

- **`adapter.py`**: `spec_to_model(spec, policies, sufs, ...)` maps
  GDSSpec blocks to `gds_sim.Model`. BoundaryAction + Policy → policies,
  Mechanism.updates → SUFs keyed by state variable. Auto-generates initial
  state from entities. Optionally wraps BoundaryAction policies with
  constraint guards.

- **`constraints.py`**: `guarded_policy(fn, constraints)` wraps a policy
  with AdmissibleInputConstraint enforcement. Three violation modes:
  warn (log + continue), raise (ConstraintViolation), zero (empty signal).

- **`metrics.py`**: `trajectory_distances(spec, trajectory)` computes
  StateMetric distances between successive states. Extracts relevant
  variables by `EntityName.VariableName` key, applies distance callable.

21 tests, 93% coverage, including end-to-end thermostat integration
(spec → model → simulate → measure distances).

Commit: `447fc62`

#### Reachable Set R(x) and Configuration Space X_C (#141)

Added `reachability.py` to gds-analysis:

- **`reachable_set(spec, model, state, input_samples)`**: Paper Def 4.1.
  For each input sample, runs one timestep with overridden policy outputs,
  collects distinct reached states. Deduplicates by state fingerprint.

- **`reachable_graph(spec, model, initial_states, input_samples, max_depth)`**:
  BFS expansion from initial states, applying `reachable_set()` at each
  node. Returns adjacency dict of state fingerprints.

- **`configuration_space(graph)`**: Paper Def 4.2. Tarjan's algorithm for
  strongly connected components. Returns SCCs sorted by size — the largest
  is X_C.

11 new tests covering single/multiple/duplicate inputs, empty inputs,
BFS depth expansion, SCC cases (self-loop, cycle, DAG, disconnected),
and end-to-end thermostat integration.

Commit: `081cb9c`

### Bridge Status

| Step | Paper | Annotation / Function | Status |
|---|---|---|---|
| 1 | Def 2.5 | AdmissibleInputConstraint | Done (prior) |
| 2 | Def 2.7 | TransitionSignature | Done (prior) |
| 3 | Assumption 3.2 | StateMetric | **Done** |
| 4 | Def 4.1 | `reachable_set()` | **Done** |
| 5 | Def 4.2 | `configuration_space()` | **Done** |
| 6 | Def 3.3 | Contingent derivative D'F | Open (#142, research) |
| 7 | Theorem 4.4 | Local controllability | Open (#142, research) |

### Issue Tracker

| Issue | Status |
|---|---|
| #134 Phase 1a | Closed |
| #135 Phase 1b-c (Coq) | Open |
| #136 Phase 2 | Closed |
| #137 Phase 3 | Closed |
| #138 Phase 4 (original) | Closed (superseded) |
| #140 gds-analysis | **Closed** |
| #141 R(x) + X_C | **Closed** |
| #142 D'F + controllability | Open (research frontier) |

### Observations

1. gds-sim has zero dependency on gds-framework. This is correct
   architecture — gds-sim is a generic trajectory executor, gds-analysis
   is the GDS-specific bridge. The adapter pattern keeps both packages
   clean.

2. The `_step_once()` implementation creates a temporary Model per input
   sample, which is simple but not performant for large input spaces.
   A future optimization would batch inputs or use gds-sim's parameter
   sweep directly.

3. `reachable_set()` is trajectory-based (Monte Carlo), not symbolic.
   It cannot prove that a state is *unreachable* — only that it wasn't
   reached in the sampled inputs. For formal reachability guarantees,
   symbolic tools (Z3, JuliaReach) would be needed.

4. Steps 6-7 (contingent derivative, controllability) are genuinely
   research-level. They require convergence analysis and Lipschitz
   conditions that go beyond trajectory sampling.

---

## Entry 007 — 2026-03-28

**Subject:** gds-analysis audits and Phase 1-2 fixes

### Motivation

Two independent audits (software architecture + data science methodology)
identified 9+8 findings across gds-analysis. Phase 1 and Phase 2 items
addressed in this session.

### Software Architecture Audit (7 findings)

| # | Finding | Severity |
|---|---|---|
| 1 | Adapter collapses topology (single StateUpdateBlock) | Documented |
| 2 | State key convention undocumented | **Fixed** |
| 3 | Phantom `spec` parameter in reachability | **Fixed** |
| 4 | No batch execution for reachability | Documented (future) |
| 5 | guarded_policy wrapping invisible | Minor (has `__wrapped__`) |
| 6 | No bridge/analysis module separation | Documented (future) |
| 7 | PBT strategies linear-only | Documented (future) |

### Data Science Audit (8 findings)

| # | Finding | Severity |
|---|---|---|
| 1 | No coverage guarantee for Monte Carlo reachability | **Fixed** (ReachabilityResult) |
| 2 | Euclidean distance meaningless on discrete states | Documented |
| 3 | SIR discrete-time lacks stability analysis | Low risk (1e-6 tolerance has 5 orders headroom) |
| 4 | SCC only valid for sampled graph | **Fixed** (documented caveat) |
| 5 | Unreachability by enumeration not proof | **Fixed** (exhaustive flag + comments) |
| 6 | PBT low coverage (same as SW #7) | Documented |
| 7 | No baseline for trajectory distances | Future |
| 8 | 1e-6 conservation tolerance unjustified | Low risk |

### Fixes Applied

**Phase 1 (commits `a304d86`):**
- Removed phantom `spec` parameter from `reachable_set()` and
  `reachable_graph()` (15 call sites updated)
- Documented state key convention ("Entity.Variable") in adapter docstring
- Added multi-update Mechanism warning
- Documented exhaustive/sampled distinction in all reachability docstrings

**Phase 2 (commits `250308b`, `4c5967e`):**
- `ReachabilityResult` dataclass: `states`, `n_samples`, `n_distinct`,
  `is_exhaustive` metadata for coverage tracking
- `float_tolerance` parameter: rounds float values before fingerprinting to
  absorb rounding noise (number of decimal places)
- `exhaustive=True` flag on crosswalk tests (3 inputs are provably
  exhaustive for the discrete space)
- Tightened float tolerance test assertion to `assertEqual(n_distinct, 1)`

**Prior audit fixes (commit `85e2f4a`):**
- `_step_once` strips metadata keys from state dicts
- ControlAction blocks handled by adapter
- `depends_on` projected at runtime in constraint enforcement
- Iterative Tarjan SCC (no recursion limit)
- `assert` replaced with `ValueError` in metrics
- Docstring corrections

### Outcome

gds-analysis now has 52 tests at 94% coverage. The API is cleaner
(no phantom parameters), the reachability results are interpretable
(coverage metadata), and the float fingerprinting is robust.

---

## Entry 008 — 2026-03-28

**Subject:** Session scorecard — full verification + analysis arc

### What Landed (Single Session)

**Verification Framework (Phases 1a, 2, 3):**
- 13 algebra PBT tests (interchange law, associativity, commutativity,
  identity) with Hypothesis CI reproducibility profiles
- R3 undecidability proofs (6 propositions, R3-undecidable/R3-separation
  sub-classification) + R1/R2 decidability bounds + Theorem C.3 partition
  independence
- 26 OWL round-trip PBT tests (SHACL gate, SPARQL conformance, derived
  property preservation, strategy invariants)

**Bridge Proposal Steps 1-5:**
- Step 1: AdmissibleInputConstraint (prior)
- Step 2: TransitionSignature (prior)
- Step 3: StateMetric (this session)
- Step 4: `reachable_set()` with ReachabilityResult metadata
- Step 5: `configuration_space()` via iterative Tarjan SCC

**gds-analysis Package (new):**
- `spec_to_model()` adapter: GDSSpec → gds_sim.Model
- `guarded_policy()`: runtime constraint enforcement with `depends_on`
  projection
- `trajectory_distances()`: StateMetric computation on trajectories
- `reachable_set()` / `reachable_graph()` / `configuration_space()`:
  reachability analysis with float tolerance and exhaustive/sampled
  distinction
- 52 tests, 94% coverage

**Ecosystem Extensions (closed today):**
- #77: Nashpy equilibrium computation (11 tests)
- #122: gds-continuous ODE engine (49 tests)
- #125: SymPy symbolic math (29 tests)
- #126: Phase portrait visualization (10 tests)

**Integration Examples:**
- SIR epidemic: spec → simulate → conservation check → distances →
  reachable set
- Crosswalk: spec → simulate → Markov transition verification →
  reachability graph → SCC (configuration space)
- Heating-cooling example (9 tests)

**Quality:**
- 3 rounds of code review on PBT tests
- 2 independent audits (software architecture + data science methodology)
  with all Phase 1-2 fixes applied
- CI fix: gds-viz phase portrait tests now skip when gds-continuous
  unavailable (was failing CI on main)

**Research Documentation:**
- Verification plan (4 phases)
- Formal proofs (R3 undecidability + representability bounds)
- Research journal (8 entries)
- 5 GitHub issues created and closed, 3 new issues for future work

### Issue Scorecard

| Issue | Title | Status |
|---|---|---|
| #134 | Phase 1a: Interchange law PBT | Closed |
| #135 | Phase 1b-c: Coq mechanized proofs | Open (long-term) |
| #136 | Phase 2: R1/R2/R3 as theorem | Closed |
| #137 | Phase 3: Round-trip PBT | Closed |
| #138 | Phase 4: Dynamical invariants | Closed (superseded) |
| #139 | Verification + StateMetric PR | Merged to main |
| #140 | gds-analysis package | Closed |
| #141 | Reachable set R(x) + X_C | Closed |
| #142 | Contingent derivative (Steps 6-7) | Open (research) |
| #146 | gds-analysis + audits PR | Merged to main |

### Remaining Open

| Issue | Title | Blocker |
|---|---|---|
| #76 | Lean 4 export | Toolchain |
| #123 | Continuous-time differential games | Research |
| #124 | Optimal control / Hamiltonian | Research |
| #127 | Backward reachable set (gds-control) | gds-analysis |
| #135 | Coq mechanized proofs | Toolchain |
| #142 | Contingent derivative + controllability | Research |
| #143 | Package consolidation | Architecture decision |

### Key Observations

1. The bridge proposal (Steps 1-5) is now structurally complete. The
   gap between the paper's mathematical definitions and the code is
   closed for the non-research items. Steps 6-7 remain genuinely
   research-level (contingent derivative, controllability).

2. gds-analysis connects gds-framework to gds-sim without either
   package knowing about the other. The adapter pattern preserves
   the clean dependency graph.

3. The verification framework provides three layers of confidence:
   - PBT (Hypothesis): empirical confidence across random inputs
   - Formal proofs (markdown + LaTeX): mathematical arguments
   - SHACL/SPARQL validation: ontological consistency

4. The R3-undecidable/R3-separation distinction is a genuine
   contribution — it clarifies which GDS design choices create the
   representability boundary and which could be moved by extending
   the formalism.

---
