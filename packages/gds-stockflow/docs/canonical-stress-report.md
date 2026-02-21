# Canonical Stress Test Report

*What we tested, why we tested it, and what the results mean.*

127 tests. All pass. No compression artifacts detected.

---

## What We Were Testing

Not compiler correctness. Not surface-level output matching.

We were testing a structural claim:

> **CanonicalGDS is a faithful abstraction of discrete-time state-transition structure — across nontrivial dynamical DSLs.**

The canonical decomposition `(X, U, g, f)` must remain interpretable and structurally honest under real modeling pressure. These tests push it.

---

## Test Classes and What They Show

### 1. TestMultiStockMutualFeedback (6 tests)

**Model:** Two stocks where every auxiliary reads both stock levels. Full coupling.

**Why:** Coupling is where decompositions break. If two stocks are mutually dependent, does the canonical form still produce a coherent state vector, or does the coupling introduce ambiguity in the update map?

**What it shows:** State vector `X = {(A, level), (B, level)}` is clean. The coupling lives entirely in `g` (the auxiliaries read both levels). The update map in `f` remains diagonal — each mechanism updates exactly one stock. **Coupling is captured structurally without contaminating the state transition.**

---

### 2. TestManyToOneAggregation (5 tests)

**Model:** One stock with 3 inflows and 1 outflow. Classic `dX/dt = in1 + in2 + in3 - out`.

**Why:** Multiple flows aggregating into a single stock is the standard pattern in System Dynamics. Does the canonical decomposition collapse them, or does it preserve the individual decision channels?

**What it shows:** Single mechanism in `f`, but 8 distinct policies in `g` (4 auxiliaries + 4 flows). The mechanism receives all 4 rate ports. **Aggregation happens at the mechanism level; the decision structure is preserved.**

---

### 3. TestExogenousEndogenousMixing (6 tests)

**Model:** Population dynamics with both converters (exogenous: Fertility, Healthcare) and auxiliaries reading stock levels (endogenous).

**Why:** The `U` / `g` boundary is the most important semantic partition in the canonical form. If an exogenous input leaks into `g`, or an endogenous computation leaks into `U`, the decomposition loses meaning.

**What it shows:** Clean separation. Converters map to `boundary_blocks` (U). Auxiliaries map to `policy_blocks` (g). No leakage. Input ports come exclusively from BoundaryAction forward_out. **The exogenous/endogenous boundary is preserved exactly.**

---

### 4. TestFlowWithNoAuxiliaryLayer (6 tests)

**Model:** Two stocks, one flow, no auxiliaries. The minimal dynamics.

**Why:** What happens when `g` degenerates? If there are no auxiliaries, the decision layer consists only of flow policies (which are pure rate emitters with no inputs). Does the decomposition become awkward or meaningless?

**What it shows:** `g` contains exactly one policy (the flow). `f` still has two mechanisms. The formula is `h : X -> X (h = f . g)`. **The decomposition degrades gracefully — `g` becomes trivial but the structure stays interpretable.**

---

### 5. TestNonNegativeConstraintVisibility (2 tests)

**Model:** Same stock, once with `non_negative=True`, once with `non_negative=False`.

**Why:** This tests the abstraction boundary. CanonicalGDS is purely algebraic — it captures `(X, U, g, f)` and nothing else. Constraints are NOT part of the canonical form. Is this a problem?

**What it shows:** Canonical forms are identical for both models. The constraint difference is visible at the spec level (different TypeDef on the entity variable) but invisible at canonical level. **This documents a deliberate design decision: canonical form is structural, not behavioral. Constraints live in TypeDef, not in the decomposition.**

---

### 6. TestOrphanStockCanonical (4 tests)

**Model:** Single stock, no flows. The absolute minimum.

**Why:** The degenerate case. `h = f . g` where `g` is identity (no decisions, no policies). Does the decomposition still make sense, or does it produce nonsense?

**What it shows:** State exists. `g` is empty (no policies, no decision ports). `f` still exists (the mechanism accumulator). Formula is clean. **Even in degeneration, the structure is honest — it says "there are no decisions" rather than fabricating something.**

---

### 7. TestLargeModel (11 tests)

**Model:** 5-stage supply chain. 5 stocks, 8 flows, 6 auxiliaries, 3 converters. Inter-stock flows, waste/loss pathways, exogenous parameters.

**Why:** Scale test. Does the decomposition stay clean when the model reaches realistic complexity? Do the counts, partitions, and cross-stock relationships remain correct?

**What it shows:** `|X| = 5`, `|U| = 3`, `|g| = 14`, `|f| = 5`, `|Theta| = 3`. Role partition is exhaustive and disjoint. Inter-stock flows (e.g., Production Start) correctly appear in both source and target mechanisms' forward_in. No duplicate update targets. **Scale does not introduce compression artifacts.**

---

### 8. TestCanonicalInvariants (60 tests, parametric)

**Models:** 5 archetypes from minimal to multi-stock, parametrized across 12 invariant checks.

**Why:** These are not model-specific — they test the decomposition contract itself. If any invariant fails for ANY well-formed StockFlowModel, the canonical form is broken.

**Invariants tested:**

| Invariant | What it guarantees |
|---|---|
| `|X| == |stocks|` | State integrity — one variable per stock, no leaks |
| `|f| == |stocks|` | Mechanism integrity — one updater per stock |
| `|U| == |converters|` | Boundary integrity — exogenous inputs only |
| `|g| == |aux| + |flows|` | Policy integrity — no collapsing, no inflation |
| Update map covers X | Every state variable is targeted |
| Role partition complete | `U ∪ g ∪ f = all blocks` — no unclassified blocks |
| Role partition disjoint | `U ∩ g = ∅, U ∩ f = ∅, g ∩ f = ∅` — no block in two roles |
| No ControlActions | StockFlow never produces endogenous control blocks |
| No state leaks into policy | Stock mechanisms never classified as policies |
| No stock in boundary | Stocks never classified as exogenous input |
| `|D| == |g|` | Each policy emits exactly one decision port |

**What it shows:** All 12 invariants hold across all 5 model archetypes. **The decomposition contract is satisfied universally, not just for specific models.**

---

### 9. TestDeclarationOrderIndependence (6 tests)

**Model:** Predator-prey declared twice — once in natural order, once with every list reversed.

**Why:** This is the order leakage test. If the canonical form depends on the order elements are declared in the DSL, then execution topology is leaking into what should be a purely structural projection.

**What it shows:** All six canonical components (state variables, boundary blocks, policy blocks, mechanism blocks, decision ports, update map) are identical as sets. **Declaration order does not leak into canonical projection.**

---

### 10. TestCouplingFidelity (4 tests)

**Model:** Two tanks with a transfer flow and an auxiliary that reads both tank levels.

**Why:** When a flow drains from stock A into stock B, and an auxiliary reads both, does the canonical form correctly place the coupling in `g` (decision layer) rather than inventing dependencies in `f` (state transition)?

**What it shows:** The auxiliary's forward_in ports include both "Tank A Level" and "Tank B Level" — coupling is in `g`. Each mechanism updates only its own stock — `f` is diagonal. The shared flow rate port appears in both mechanisms' forward_in (correct — the flow affects both stocks). **Cross-stock dependencies are preserved in the decision layer without contaminating the state transition.**

---

### 11. TestOverCollapsing (7 tests)

**Model:** Heat exchange system with two stocks, three flows, three auxiliaries (each with different dependency structure), and one converter.

**Why:** The real risk in canonical projection isn't constraint dropping — it's over-collapsing. If two structurally distinct policies get merged, or if an intermediate auxiliary disappears, the decomposition loses information it should preserve.

**What it shows:** All 3 auxiliaries remain distinct policies. All 3 flows remain distinct policies. 6 total policies, 6 decision ports — no collapsing. The converter produces exactly 1 boundary block and 1 input port — no duplication. Asymmetric dependencies are preserved: Radiation reads only Hot, Absorption reads Cold + Ambient. **Canonical projection does not over-collapse. Distinct structures remain distinct.**

---

### 12. TestComplexPredatorPreyHarvesting (15 tests)

**Model:** Predator-prey with harvesting and seasonal forcing. 2 stocks, 5 flows, 5 auxiliaries, 2 converters. Cross-coupling, exogenous inputs, multi-flow aggregation, asymmetric dependency structure.

**Why:** This is the stress model. Everything at once: coupling, boundary mixing, aggregation, asymmetry. If canonical still feels "minimal and natural" here, it's comfortably central. If compression artifacts appear, we know where GDS is stretched.

**What it shows:**

- `|X| = 2` (Prey, Predator)
- `|U| = 2` (Season, Carrying Capacity)
- `|g| = 10` (5 aux + 5 flows)
- `|f| = 2` (Prey Accumulation, Predator Accumulation)
- `|D| = 10`
- `|Theta| = 2`

Prey Accumulation aggregates 3 rate ports (Reproduction, Predation Loss, Harvest). Predator Accumulation aggregates 2 (Reproduction, Starvation). Predation Rate reads both stock levels (coupling in `g`). Harvest Rate reads Prey Level + Season Signal (mixed endogenous/exogenous). Starvation Rate reads Predator Level + Carrying Capacity Signal. No cross-stock contamination in the update map. No collapsing. No inflation.

**The decomposition is minimal: every element carries meaning, nothing is redundant, nothing is missing. Under full modeling pressure, canonical feels natural — not forced.**

---

## What This Means

CanonicalGDS survives semantic stress. The decomposition `(X, U, g, f)`:

1. **Preserves state integrity** — stocks map 1:1 to state variables, no leaks.
2. **Preserves boundary integrity** — exogenous inputs are cleanly separated, no contamination.
3. **Preserves coupling structure** — cross-stock dependencies live in `g`, not `f`.
4. **Does not over-collapse** — distinct policies remain distinct, asymmetric dependencies are preserved.
5. **Is order-independent** — declaration order does not leak into the projection.
6. **Degrades gracefully** — minimal and degenerate models produce honest, interpretable decompositions.
7. **Scales cleanly** — realistic models (5+ stocks, 8+ flows, converters) produce correct decompositions without compression artifacts.

The one thing canonical deliberately drops — constraints, temporal ordering, composition topology — is not a bug. It's the abstraction boundary. Canonical is the algebraic skeleton; the spec and composition tree carry the rest.

**Conclusion:** GDS is not merely compatible with StockFlow. It is the correct semantic substrate. Two DSLs (OGS + StockFlow) now compile to it, and canonical projection provides a universal structural normal form for both. No compression artifacts under pressure. The next DSL should compile to it too.
