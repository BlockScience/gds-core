# Synthesis of GDS-Core Reviews: Zargham vs. Jamsheed

**Date:** 2026-04-03
**Sources:**
- `gds_core_briefing.md`, `gds_core_improvement_roadmap.md`, `gds_core_risk_register_and_doctrines.md` — Engineering review (Zargham + Claude understudy)
- `math-review.md` — Mathematical review (Jamsheed)

---

## Executive Summary

Both reviews validate the theoretical foundation but identify critical gaps in notation alignment with the paper, `ControlAction` semantics, and temporal agnosticism documentation. Jamsheed focuses on mathematical formalism fidelity to Zargham & Shorish (2022); Zargham provides a 14-item engineering roadmap with risks and doctrines. Their recommendations are ~85% aligned, with minor divergences on tier ordering.

---

## Where the Reviews Agree

### 1. ControlAction = Output Map (Not Admissibility Constraint)

| Review | Finding |
|--------|---------|
| **Zargham T0-3** | `ControlAction` is unused by all six DSLs; should be `y = C(x,d)` for controller-plant duality |
| **Jamsheed** | "erroneously referred to in the codebase as 'admissibility constraint'" — should be output observable for composition |

**Consensus:** Same signal `y` is:
- **Inside perspective:** plant's output map
- **Outside perspective:** control action on the next system

### 2. Notation Must Harmonize with Paper

| Issue | Codebase | Paper/Bosch | Fix |
|-------|----------|-------------|-----|
| External factors | `u` | `z` (or `varepsilon`) | Rename to `z` or distinct from action `u` |
| "Input Space U" | Used for external factors | `U_x` is admissible input space | Clarify terminology |
| Policy mapping | `g(x,u)` | `g(x)` or `g(x,z)` | Align with paper's intent |

### 3. Core is Time-Agnostic (Structural Recurrence)

| Review | Framing |
|--------|---------|
| **Zargham T0-4** | "Core is time-agnostic" — `is_temporal=True` is structural boundary marker only |
| **Jamsheed** | "Structural recurrence primitive regardless of `is_temporal`" — uses semigroup `(N, +)` for sequencing |

**Consensus:** The three-layer temporal stack:
- Layer 0 (core): Structural recurrence only — no time model
- Layer 1 (DSL): `ExecutionContract` declares time model
- Layer 2 (sim): Solver/runner implements time model

### 4. Representation-Agnostic Architecture

Both confirm the core should not commit to numerical, relational, or any substrate. Arithmetic enters at DSL layer.

---

## Where the Reviews Diverge

### Tier Ordering Disagreements

| Item | Zargham's Tier | Jamsheed's View |
|------|---------------|-----------------|
| **Continuous-time formalization** | Tier 2 (medium priority) | Move to Tier 1 — "ambitious objective... many limit conceptions possible" |
| **Stochastic extensions** | Tier 3 (research frontier) | "Most crucial... could be Tier in own right or Tier 2" |
| **Discrete-time framework** | Moore as default in T1-1 | Elevate Mealy machines — "Mealy includes Moore as subclass" |

### Scope Differences

| Aspect | Zargham | Jamsheed |
|--------|---------|----------|
| **Primary output** | 14-item roadmap with risks/doctrines | Mathematical corrections + architectural feedback |
| **ControlAction taxonomy** | Deep dive on controller-plant duality, perspective inversion, observability connection | Suggests `Output`/`OutputObservable` class with typing for plant vs control action |
| **Time agnosticism** | Three-layer stack with formal invariant | Emphasizes "before/after" semantic structure; notes OGS proves degenerate case works |

---

## The Criticisms: A Taxonomy

### Tier 0 (Must Fix Before Anything Else)

| ID | Issue | Severity | Reviews Citing |
|----|-------|----------|---------------|
| T0-1 | Checks lack formal property statements | **Critical** | Zargham (C1 violation) |
| T0-2 | Tests lack requirement traceability | **Critical** | Zargham (C1, C3) |
| T0-3 | `ControlAction` role unresolved | **Critical** | **Both** — Zargham's T0-3, Jamsheed's General Comments |
| T0-4 | Temporal agnosticism not formally stated | **Critical** | **Both** — Zargham's T0-4, Jamsheed's time agnosticism section |

### Documentation Issues

| Issue | Jamsheed's Words | Zargham's Mitigation |
|-------|------------------|---------------------|
| `ControlAction` misnamed | "erroneously referred to... as admissibility constraint" | T0-3 deliverable 2: dedicated duality documentation page |
| Input space conflation | "erroneously referred to as the 'Input Space U'" | OC-6: distinct categories for `U_c`, `W`, `D`, `Y` |
| Discrete-time bias | "documentation quietly undermines [time agnosticism]" | T0-4 deliverable 3: audit + correction of trajectory notation |

### Ontological Commitments

Jamsheed's review confirms Zargham's OC-1 through OC-10 but adds nuance:

> "Generalized refers to general data structures (representation generality, architecture principle 1), while dynamical refers to both the trajectory sequencing and its computational implementability (architecture principles 2 and 3)."

This directly validates Zargham's:
- OC-3 (Space as compatibility token — "generalized")
- OC-7 (Structural recurrence — "dynamical")
- OC-10 (Simulation is instrumentation — "computational implementability")

---

## Actionable Steps: Unified Priority

### Immediate (Tier 0 — No New Code)

**1. T0-3: Resolve ControlAction** — Both reviews agree this is foundational
- Formalize `y = C(x,d)` as output map
- Document controller-plant duality with thermostat example
- Add `(Y, C)` to canonical projection
- Create SC-check preventing ControlAction in `g` pathway

**2. Notation Harmonization** — Jamsheed's math review + Zargham's OC-6
- External factors: change `u` to `z` (or distinct symbol)
- Rename "Input Space U" to "External Factor Space Z"
- Policy: clarify `g(x)` vs `g(x,z)` vs `g(x,u_c)` with controlled inputs

**3. T0-4: Formalize Temporal Agnosticism**
- State invariant: `is_temporal=True` = structural recurrence only
- Three-layer stack diagram
- Audit docs: replace "next step" with "temporal boundary"

### Near-Term (Tier 1)

**4. T1-1: ExecutionContract** — Elevate per Jamsheed's feedback on Mealy machines
- Add `update_ordering: Literal["Moore", "Mealy"]` field
- Default remains Moore, but Mealy is explicitly supported

**5. T1-3: Disturbance Inputs** — Resolves Jamsheed's `z` notation concern
- Formal partition: `U_c` (controlled) vs `W` (disturbance)
- Tagged mixin: `{"role": "disturbance"}`
- DST-001 check: disturbance bypasses policy layer

### Medium-Term (Tier 2 — Per Jamsheed's Recommendations)

**6. T2-4: Continuous-Time** — Consider moving to Tier 1 per Jamsheed
- `SolverInterface` contract separates spec from simulation
- Scope: real-valued subspaces only (explicit constraint)

**7. Stochastic Extensions** — Jamsheed's "most crucial" item
- Consider Tier 2 placement (not Tier 3) per Jamsheed's recommendation
- Requires T1-1 (`ExecutionContract`) and T2-2 (behavioral verification) stable first

---

## Key Architectural Decisions Pending

1. **Should continuous-time formalization move to Tier 1?** Jamsheed argues yes for earlier operationalization; Zargham placed it Tier 2 for scope discipline.

2. **Should stochastic extensions be elevated to Tier 2 (or own Tier)?** Jamsheed sees this as crucial; roadmap currently has it Tier 3.

3. **Mealy vs Moore as discrete-time framework:** Jamsheed suggests elevating Mealy as the general case (Moore as subclass). Currently roadmap has Moore as default with Mealy as option.

4. **External factor notation:** `z` (Bosch presentation), `varepsilon` (past usage), or keep `u` with clear subscripting? Jamsheed flags conflict with action `u`.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-04-03 | Initial synthesis from both reviews |
