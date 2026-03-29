# GDS-Core Improvement Roadmap

> Architectural review and phased execution plan for the GDS ecosystem.
>
> **Origin:** External review by Chief Engineer + Claude Sonnet 4.6 (2026-03-28),
> reconciled against current codebase state and augmented with detailed phase plans.
>
> **Theoretical basis:** Zargham & Shorish (2022), *Generalized Dynamical Systems, Part I: Foundations*
> ([DOI](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc))

---

## Current State Summary

Before planning improvements, this section reconciles the review's assumptions against the actual codebase as of 2026-03-29.

### Test Coverage

The review cited "347 tests at 99% line coverage." Actual counts across the workspace:

| Package | Tests | Notes |
|---------|-------|-------|
| gds-framework | ~474 | Core engine, composition algebra, verification |
| gds-games | ~302 | OGS DSL, canonical bridge, equilibrium |
| gds-software | ~223 | 6 diagram types, 27 domain checks |
| gds-examples | ~212 | Tutorials, AdmissibleInputConstraint demos |
| gds-owl | ~185 | OWL/SHACL/SPARQL, SC-008/SC-009 shapes |
| gds-business | ~175 | CLD, SCN, VSM |
| gds-stockflow | ~172 | Stock-flow DSL, TransitionSignature |
| gds-psuu | ~133 | Parameter sweep, Optuna |
| gds-control | ~103 | State-space control, TransitionSignature |
| gds-sim | ~88 | Discrete-time simulation engine |
| gds-viz | ~79 | Mermaid + phase portraits |
| gds-analysis | ~61 | Spec→sim bridge, reachability |
| gds-continuous | ~46 | ODE engine (standalone) |
| gds-symbolic | ~39 | SymPy bridge |
| **Total** | **~2,292** | |

### Verification Checks (15 total, not 13)

**Generic (G-001..G-006)** — structural, operate on `SystemIR`:

| Check | Property |
|-------|----------|
| G-001 | Domain/codomain port label consistency |
| G-002 | Signature completeness (every block has inputs + outputs; BoundaryAction exempt from input requirement) |
| G-003 | Direction consistency (no COVARIANT+feedback or CONTRAVARIANT+temporal contradictions) |
| G-004 | Dangling wirings (source/target must exist in system) |
| G-005 | Sequential type compatibility (wiring labels subset of source out ∩ target in) |
| G-006 | Covariant acyclicity (covariant flow graph is a DAG) |

**Semantic (SC-001..SC-009)** — domain properties, operate on `GDSSpec`:

| Check | Property |
|-------|----------|
| SC-001 | Completeness — every entity variable updated by ≥1 mechanism |
| SC-002 | Determinism — no two mechanisms update the same variable within a wiring |
| SC-003 | Reachability — signals can reach between connected blocks |
| SC-004 | Type safety — wire spaces match block port expectations |
| SC-005 | Parameter references — all `params_used` resolve to registered parameters |
| SC-006 | Canonical wellformedness — at least one mechanism exists (f non-empty) |
| SC-007 | Canonical wellformedness — state space has entity variables (X non-empty) |
| SC-008 | Admissibility references — AdmissibleInputConstraint entries reference valid blocks and state variables |
| SC-009 | Transition reads — TransitionSignature entries reference valid mechanisms and state variables |

### Already Implemented (Review Missed)

The review was conducted from documentation, not code. Several items it proposes are partially or fully addressed:

| Concept | Paper Reference | Status | Location |
|---------|----------------|--------|----------|
| AdmissibleInputConstraint | Def 2.5 (U_x) | Structural skeleton implemented | `gds/constraints.py` — `boundary_block`, `depends_on`, optional `constraint` callable |
| TransitionSignature | Def 2.7 (f\|_x) | Structural skeleton implemented | `gds/constraints.py` — `mechanism`, `reads`, `depends_on_blocks` |
| StateMetric | Assumption 3.2 | Structural skeleton implemented | `gds/constraints.py` — `variables`, `metric_type`, optional `distance` callable |
| SC-008 validation | — | Implemented | `gds/verification/spec_checks.py` |
| SC-009 validation | — | Implemented | `gds/verification/spec_checks.py` |
| StockFlow TransitionSignature emission | — | Compilers emit | `stockflow/dsl/compile.py` |
| Control TransitionSignature emission | — | Compilers emit | `gds_control/dsl/compile.py` |
| Insurance + thermostat examples | — | Demonstrate AdmissibleInputConstraint | `packages/gds-examples/` |
| Reachability analysis | Def 4.1, 4.2 | Forward + backward implemented | `gds_analysis/reachability.py`, `backward_reachability.py` |
| Spec→sim bridge | — | Implemented | `gds_analysis/adapter.py` — `spec_to_model()` |

### CanonicalGDS Current Fields

The `CanonicalGDS` dataclass (in `gds/canonical.py`) currently contains:

- `state_variables` — (entity, variable) tuples representing X
- `parameter_schema` — Θ
- `input_ports` — (block_name, port_name) from BoundaryAction outputs
- `decision_ports` — (block_name, port_name) from Policy outputs
- `boundary_blocks`, `control_blocks`, `policy_blocks`, `mechanism_blocks` — block names by role
- `update_map` — mechanism → (entity, variable) write dependencies
- `admissibility_map` — constraint → (entity, variable) read dependencies
- `read_map` — mechanism → (entity, variable) read dependencies

Notably: `control_blocks` is already a field (blocks with role `ControlAction`), but no DSL populates it.

### What Does NOT Exist Yet

| Concept | Status |
|---------|--------|
| ExecutionContract | Not implemented — no time model declaration anywhere |
| Output map (Y, C) in CanonicalGDS | Not extracted — ControlAction outputs not projected |
| Disturbance/controlled input partition | No tagging convention |
| Behavioral verification (trajectory predicates) | Not implemented |
| Cross-lens queries (PatternIR × CanonicalGDS) | Not implemented |
| PSUU ↔ ParameterSchema validation | Completely disconnected |
| gds-continuous ↔ GDSSpec bridge | gds-continuous is standalone, no adapter |
| Formal check specification documents | Checks are code + docstrings only |

---

## Prioritization Criteria

Each item is evaluated against four criteria that jointly determine tier placement:

| Code | Criterion | Description |
|------|-----------|-------------|
| C1 | **Soundness** | Does the gap undermine the correctness of a formal claim the framework already makes? |
| C2 | **Completeness** | Does the gap leave a stated capability undelivered? |
| C3 | **Production readiness** | Does the gap block use in a regulated or assurance-critical engineering context? |
| C4 | **Leverage** | Does resolving it unlock downstream improvements across multiple other areas? |

**Tier definitions:**

- **Tier 0** — C1 violations. Undermine existing correctness claims. Fix before adding new capabilities.
- **Tier 1** — C2 + C3 high, or C4 high. Required for meaningful V&V and cross-DSL use.
- **Tier 2** — C2 + C3 moderate, or high C4. Important extensions that unlock new domains.
- **Tier 3** — Research frontier. Architecturally premature; triggered by future concrete work.

Each item specifies its type: **[MATH]** foundational/theoretical work, **[DOC]** documentation, **[CODE]** implementation.

---

## Phase Execution Plan

The 15 roadmap items are organized into 5 phases. Phases respect the dependency graph: no item starts until its prerequisites are complete. Within each phase, independent work streams are identified for parallel execution.

```
Phase 1 ─── T0-1, T0-3, T0-4 (parallel)     ── Foundations
Phase 2 ─── T0-2, T1-2, T1-4 (parallel)      ── Traceability & Quick Wins
Phase 3 ─── T1-1, T1-3 (sequential)           ── Execution Semantics
Phase 4 ─── T2-1, T2-2, T2-3, T2-4 (parallel) ── Analysis & Behavioral
Phase 5 ─── T3-1, T3-2, T3-3 (triggered)      ── Research Frontier
```

---

### Phase 1 — Foundations

**Goal:** Establish the formal language for check specifications, resolve the ControlAction role, and state temporal agnosticism as an invariant. These three items have no mutual dependencies and proceed in parallel.

#### Stream 1A: T0-1 — Formalize Check Specifications as Requirements

**Type:** [MATH] [DOC] | **Criteria:** C1

**Problem:** Each check (G-001..G-006, SC-001..SC-009) is described in code docstrings and prose. There is no formal statement of: (a) the property being checked, (b) the invariant it enforces, (c) the conditions under which a pass is sound vs. merely necessary.

**Steps:**

1. **Create check specification template.** Define a structured format:
    ```
    Check ID:    G-003
    Type:        Structural (Layer 0)
    Statement:   The SystemIR covariant wiring graph contains no directed
                 cycles. (Temporal wirings excluded from cycle detection.)
    Rationale:   Acyclicity is necessary for the canonical projection
                 h = f ∘ g to be well-defined as a function rather than
                 an implicit equation.
    Failure:     A cycle in covariant wirings implies the canonical form
                 is undefined for this composition.
    Proof:       Topological sort of covariant subgraph; cycle detection
                 via DFS in generic_checks.py:check_covariant_acyclicity.
    Layer:       Structural (SystemIR)
    ```

2. **Write specifications for all 6 generic checks (G-001..G-006).** Each specification must link the check to a property of the composition algebra or the canonical form. Source: `gds/verification/generic_checks.py`.

3. **Write specifications for all 9 semantic checks (SC-001..SC-009).** Each specification must link the check to a property of `GDSSpec` or the canonical decomposition. Source: `gds/verification/spec_checks.py`. Note: SC-008 and SC-009 (admissibility/transition references) link to paper Defs 2.5 and 2.7.

4. **Publish as `docs/research/verification/check-specifications.md`.** One page, all 15 checks, structured per the template. Cross-reference the [paper implementation gap](paper-implementation-gap.md) for paper-linked checks.

5. **Define requirement IDs.** Each check specification becomes a traceable requirement (used by T0-2). IDs are the check IDs themselves: `G-001` through `G-006`, `SC-001` through `SC-009`.

**Deliverables:**

- [ ] Check specification template (standardized format)
- [ ] 6 generic check specifications (G-001..G-006)
- [ ] 9 semantic check specifications (SC-001..SC-009)
- [ ] `docs/research/verification/check-specifications.md`

---

#### Stream 1B: T0-3 — Resolve ControlAction Role; Document Controller-Plant Duality

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C1, C2

**Problem:** `ControlAction` is defined in `gds/blocks/roles.py` but unused by all 7 validated DSLs. All non-state-updating blocks resolve to `Policy`. This conceals a structural gap: the framework has no explicit output map `y = C(x, d)` and therefore no formal basis for observability analysis.

**Codebase context:** `CanonicalGDS` already has a `control_blocks` field — it's always empty. The role class exists with `kind: str = "control"`, no structural constraints, and fields `options`, `params_used`, `constraints`.

**Steps:**

1. **Write the controller-plant duality as a mathematical proposition.**

    *Statement:* At every `>>` composition boundary, one system's `ControlAction` output is isomorphic to the next system's `BoundaryAction` input. The same signal is simultaneously the plant's output and a control action on the coupled system.

    | Role | Inside (plant) perspective | Outside (controller) perspective |
    |------|---------------------------|----------------------------------|
    | BoundaryAction | Exogenous input u | Output from previous system |
    | Policy | Decision d = g(x, u) | Internal — opaque to outside |
    | Mechanism | State update x' = f(x, d) | Internal — opaque to outside |
    | ControlAction | Output map y = C(x, d) | Action this system exerts on the next |

2. **Extend `CanonicalGDS` to extract (Y, C).** Add two fields:
    - `output_ports: tuple[tuple[str, str], ...]` — (block_name, port_name) from ControlAction `forward_out`
    - `output_map: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]` — ControlAction block → state variables it reads (parallel to `update_map` for mechanisms)

    Modify `project_canonical()` in `gds/canonical.py` to populate these fields from ControlAction blocks already classified into `control_blocks`.

3. **Design the SC-check for ControlAction routing.** New check: ControlAction blocks' `forward_out` ports must not wire directly to Policy or BoundaryAction `forward_in` ports in the *non-feedback, non-temporal* wiring subgraph. In feedback compositions (`.feedback()`), the signal correctly routes back — this is not a violation. The check enforces directional semantics of the output map in the forward path only.

    > **Nuance from codebase review:** The original review proposed "ControlAction must not appear in the g pathway" without qualification. This is overly restrictive — feedback loops exist precisely to route observations back to policy. The check must distinguish forward-path (restrict) from feedback-path (allow).

4. **Write the duality documentation page.** Create `docs/research/controller-plant-duality.md`:
    - The duality diagram (inside vs. outside perspective)
    - Role naming convention from both perspectives
    - Port direction semantics (forward_out = output/control action; forward_in = input/boundary)
    - The observability connection (ControlAction enables asking "what can be observed?")
    - Connection to disturbance formalization (T1-3)

5. **Write a worked example.** Reread the thermostat model from both perspectives simultaneously in the duality doc. Show: temperature sensor output is simultaneously a plant observation (inside) and a control signal to the controller (outside).

6. **Implement and test.**
    - Add `output_ports` and `output_map` to `CanonicalGDS`
    - Update `project_canonical()` to populate them
    - Add the new SC-check (tentatively SC-010)
    - Add tests for: (a) ControlAction blocks correctly classified, (b) output_ports/output_map populated, (c) SC-010 passes for valid topologies, (d) SC-010 catches forward-path violations, (e) SC-010 allows feedback-path routing
    - Update DSL examples that should use ControlAction (thermostat sensor → ControlAction rather than Policy)

**Deliverables:**

- [ ] Mathematical proposition: controller-plant duality at `>>` boundaries
- [ ] Extended `CanonicalGDS` with `output_ports` and `output_map`
- [ ] Updated `project_canonical()` implementation
- [ ] SC-010: ControlAction forward-path routing check
- [ ] `docs/research/controller-plant-duality.md`
- [ ] Thermostat worked example (both perspectives)
- [ ] Tests for all new code

---

#### Stream 1C: T0-4 — Formally State Temporal Agnosticism of the Core Algebra

**Type:** [MATH] [DOC] | **Criteria:** C1

**Problem:** The core algebra is already time-agnostic — `is_temporal=True` encodes structural recurrence only. The OGS case proves this: iterated games compile with temporal wirings and no time model. But documentation undermines this with discrete-index trajectory notation and step-based `.loop()` descriptions.

**Steps:**

1. **Write the formal invariant statement.**

    > *The composition algebra of `gds-framework` is temporally agnostic. The flag `is_temporal=True` on a wiring asserts structural recurrence and nothing else. No time model is implied or required by the core. The canonical form `h = f ∘ g` is an atemporal map. Time models are DSL-layer declarations.*

2. **Prove consistency of composition operators.** By inspection of the operator definitions in `gds/blocks/composition.py`, show that `>>`, `|`, `.feedback()`, and `.loop()` do not introduce a time model as a side effect. `.loop()` creates a temporal wiring (`is_temporal=True`) but does not commit to what temporal means — discrete step, continuous interval, event trigger, or nothing (OGS).

3. **Define the three-layer temporal stack.**

    ```
    Layer 0 — gds-framework (core)
      is_temporal=True encodes structural recurrence only.
      h = f ∘ g is a single atemporal map application.

    Layer 1 — DSL (ExecutionContract, defined in Phase 3 / T1-1)
      Declares what "temporal boundary" means for the domain:
        discrete | continuous | event | atemporal

    Layer 2 — Simulation (gds-sim, gds-continuous, future)
      Instantiates the time model concretely.
      Required only for execution, not for specification or verification.
    ```

4. **Audit and correct framework documentation.** Search all docs under `docs/framework/` for:
    - Discrete-index trajectory notation (`x₀, x₁, ...`, `x[t], x[t+1]`) — replace with representation-neutral language
    - Step-based `.loop()` descriptions ("next step", "next iteration") — replace with "temporal boundary", "recurrence"
    - Any language implying Moore synchronous discrete-time is *the* execution model rather than *one* execution model

5. **Cite the OGS existence proof.** OGS iterated games compile and verify with temporal wirings and `f = ∅`, `X = ∅` — no time model required. This is not a special case; it is existence proof that the algebra is genuinely time-agnostic.

6. **Publish the temporal stack diagram.** Add to `docs/research/temporal-agnosticism.md`:
    - The formal invariant statement
    - The three-layer temporal stack
    - The OGS existence proof
    - ExecutionContract time_domain values table (forward reference to T1-1):

    | `time_domain` | Meaning at DSL layer | Example DSL |
    |---|---|---|
    | `discrete` | Temporal boundary is a discrete index step | gds-stockflow, gds-control |
    | `continuous` | Temporal boundary is a continuous-time interval | gds-continuous |
    | `event` | Temporal boundary is triggered by an event | Future |
    | `atemporal` | Temporal boundary carries no time semantics | gds-games (OGS) |

**Deliverables:**

- [ ] Named invariant: temporal agnosticism of the composition algebra
- [ ] Operator consistency proof (by inspection)
- [ ] Documentation audit and correction (framework docs)
- [ ] `docs/research/temporal-agnosticism.md` with three-layer stack
- [ ] OGS existence proof documented

---

### Phase 2 — Traceability & Quick Wins

**Begins after:** Phase 1 (T0-1 required for T0-2 and T1-4; T1-2 is independent).

**Goal:** Connect tests to formal requirements, connect PSUU to declared parameters, and map the assurance boundary. Three independent streams.

#### Stream 2A: T0-2 — Requirement Traceability for the Test Suite

**Type:** [DOC] [CODE] | **Criteria:** C1, C3 | **Depends on:** T0-1

**Problem:** ~2,292 tests exist but there is no documented mapping from tests to the requirements formalized in T0-1. Coverage of lines ≠ coverage of properties.

**Steps:**

1. **Define the traceability mechanism.** Use pytest markers referencing requirement IDs from T0-1:
    ```python
    @pytest.mark.requirement("G-003")
    def test_acyclic_non_temporal_wirings():
        ...
    ```
    Register the marker in `conftest.py` to avoid unknown-marker warnings.

2. **Audit existing tests against requirements.** For each of the 15 checks (G-001..G-006, SC-001..SC-009), identify which existing tests exercise that check. Many tests already ARE property tests — they just lack the marker.

3. **Add markers to existing tests.** Tag tests that exercise specific requirements. Prioritize:
    - `packages/gds-framework/tests/test_verification.py` — most G-checks tested here
    - `packages/gds-framework/tests/test_spec.py` — most SC-checks tested here
    - DSL-level verification tests that delegate to G/SC checks

4. **Identify coverage gaps.** After marking, generate a traceability matrix: requirement → test(s). Any requirement with zero covering tests needs new tests written.

5. **Write missing tests.** Fill gaps identified in step 4. Each new test must have the `@pytest.mark.requirement` marker.

6. **Publish traceability matrix.** Add to `docs/research/verification/traceability-matrix.md`. Format: requirement ID → test file:function → what the test proves.

**Deliverables:**

- [ ] `@pytest.mark.requirement` marker registered in conftest
- [ ] Existing tests tagged with requirement markers
- [ ] Coverage gap analysis
- [ ] New tests for uncovered requirements
- [ ] `docs/research/verification/traceability-matrix.md`

---

#### Stream 2B: T1-2 — Connect PSUU Parameter Sweep to Declared Θ

**Type:** [CODE] | **Criteria:** C2, C3 | **Depends on:** T0-1

**Problem:** `gds-psuu` defines `ParameterSpace` (search domain with `Continuous`, `Integer`, `Discrete` dimensions). `gds-framework` declares `ParameterSchema` (structural metadata with `ParameterDef` entries carrying `TypeDef` and optional `bounds`). These are completely disconnected. A sweep can silently explore values outside declared TypeDef constraints.

**Codebase context:**

- `ParameterSchema` (`gds/parameters.py`): `dict[str, ParameterDef]` where `ParameterDef` has `name`, `typedef: TypeDef`, `description`, `bounds: tuple[Any, Any] | None`
- `ParameterSpace` (`gds_psuu/space.py`): `dict[str, Dimension]` where `Dimension` is `Continuous | Integer | Discrete`
- No code connects the two

**Steps:**

1. **Add a `from_parameter_schema()` class method to `ParameterSpace`.** Reads a `ParameterSchema` and creates a `ParameterSpace` with dimensions derived from `ParameterDef.bounds` and `ParameterDef.typedef`. This is a convenience constructor, not a hard coupling — users can still build `ParameterSpace` manually.

2. **Add a `validate_against_schema()` method to `ParameterSpace`.** Given a `ParameterSchema`, checks:
    - All swept parameter names exist in the schema
    - Sweep bounds are within declared `TypeDef` constraints / `ParameterDef.bounds`
    - Dimension types are compatible (e.g., `Continuous` for float typedef, `Integer` for int typedef)
    - Returns a list of violations (typed error objects, not strings)

3. **Add PSUU-001 check.** A verification check callable `check_parameter_space_compatibility(space: ParameterSpace, schema: ParameterSchema) -> list[Finding]` following the same pattern as G/SC checks. Finding severity: ERROR for out-of-bounds, WARNING for missing-from-schema.

4. **Integration point.** In `gds_psuu/sweep.py`, add an optional `parameter_schema` argument to the sweep runner. When provided, run PSUU-001 validation before starting the sweep. Raise `ParameterSpaceViolation` on ERROR findings.

5. **Tests.** Cover:
    - `from_parameter_schema()` produces correct dimensions from various TypeDef types
    - `validate_against_schema()` catches: out-of-bounds, missing parameters, type mismatches
    - `validate_against_schema()` passes for valid configurations
    - PSUU-001 check produces correct Finding objects
    - Sweep runner with `parameter_schema` raises on violations

6. **Document the relationship.** Add a section to `docs/psuu/guide/spaces.md` explaining: ParameterSchema is what the specification declares; ParameterSpace is what the optimizer searches; validation ensures the search respects the declaration.

**Deliverables:**

- [ ] `ParameterSpace.from_parameter_schema()` class method
- [ ] `ParameterSpace.validate_against_schema()` method
- [ ] PSUU-001 check function
- [ ] Sweep runner integration (optional validation)
- [ ] Tests for all new code
- [ ] Documentation in PSUU guide

---

#### Stream 2C: T1-4 — Assurance Triangle: V&V Activity Mapping

**Type:** [DOC] | **Criteria:** C2, C3 | **Depends on:** T0-1, T0-2

**Problem:** The framework uses "verification" language but all current checks are structural well-formedness. A practitioner could treat `verify()` pass as evidence of broader assurance than the framework provides.

**Steps:**

1. **Map each check to its assurance layer.** Using the check specifications from T0-1:

    | Layer | Checks | What they prove |
    |-------|--------|-----------------|
    | Structural (topology) | G-001..G-006 | Wiring graph is well-formed |
    | Semantic (specification) | SC-001..SC-009 | Spec is internally consistent |
    | Behavioral (trajectory) | None yet | — |
    | Full assurance | — | Requires simulation, testing, or formal proof |

2. **Document what the framework does NOT prove.** Explicitly list: behavioral safety, liveness, stability, conservation, optimality, incentive compatibility, convergence — none of these are established by structural or semantic checks alone.

3. **List residual verification obligations.** For each property the framework cannot check, state what additional evidence is needed:
    - Stability → simulation + Lyapunov analysis (gds-control DSL-level)
    - Conservation → simulation + trajectory invariant checks (gds-stockflow DSL-level)
    - Incentive compatibility → equilibrium computation (gds-games DSL-level)
    - Safety → behavioral predicates on trajectories (future T2-2)

4. **Create the verification passport template.** A one-page template for any GDS-specified system:
    - System identification (GDSSpec name, DSL, canonical form)
    - Structural checks passed (G-xxx, SC-xxx)
    - Claims supported by structural checks alone
    - Residual obligations (what additional evidence is required)
    - Simulation results (if available)
    - Sign-off

5. **Publish.** `docs/research/verification/assurance-claims.md` containing the mapping, the explicit negatives, and the passport template.

**Deliverables:**

- [ ] Check-to-layer mapping table
- [ ] Explicit "what we do NOT prove" list
- [ ] Residual verification obligations
- [ ] Verification passport template
- [ ] `docs/research/verification/assurance-claims.md`

---

### Phase 3 — Execution Semantics

**Begins after:** Phase 1 complete (T0-3 and T0-4 required).

**Goal:** Introduce the `ExecutionContract` mechanism and formalize the disturbance partition. These are sequential: T1-3 depends on T1-1.

#### Stream 3A: T1-1 — Formalize ExecutionContract and Default Simulation Semantics

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C2, C4 | **Depends on:** T0-1, T0-3, T0-4

**Problem:** The core is time-agnostic (T0-4). Time models must enter at the DSL layer. But no mechanism exists for DSLs to declare their time model, and the framework has no formal statement of default execution semantics.

**Steps:**

1. **Define the `ExecutionContract` dataclass.** In `gds-framework` (likely `gds/execution.py`):
    ```python
    @dataclass(frozen=True)
    class ExecutionContract:
        time_domain: Literal["discrete", "continuous", "event", "atemporal"]
        synchrony: Literal["synchronous", "asynchronous"] = "synchronous"
        observation_delay: int = 0   # 0 = Moore; discrete only
        update_ordering: Literal["Moore", "Mealy"] = "Moore"
    ```
    Fields `synchrony`, `observation_delay`, `update_ordering` are meaningful only for `time_domain="discrete"`.

2. **Attach to GDSSpec as optional.** Add `execution_contract: ExecutionContract | None = None` to `GDSSpec`. Absent means the spec carries no time model — valid for structural verification, not executable.

3. **Formally state Moore discrete-time semantics.** The default execution model for `time_domain="discrete", synchrony="synchronous"`:
    ```
    d[t]   = g(x[t], u[t])         # policy map
    x[t+1] = f(x[t], d[t])         # state update
    y[t]   = C(x[t], d[t])         # output map (T0-3)
    ```
    State well-definedness conditions: acyclicity (G-006), type compatibility (SC-004).

4. **Add cross-composition compatibility check.** New SC-check (tentatively SC-011): if two GDSSpecs are composed and both carry ExecutionContracts, the contracts must be compatible. Incompatible contracts (e.g., discrete composed with continuous without an explicit interface) emit an ERROR.

5. **Add algebraic loop check for discrete-time.** New G-check (tentatively G-007): SystemIR compiled from a GDSSpec with `time_domain="discrete"` must have no algebraic loops in the non-temporal wiring graph. (G-006 already checks covariant acyclicity — G-007 may be a specialization or may already be covered; verify during implementation.)

6. **Reference runner in gds-sim.** Ensure `gds-sim` can read the `ExecutionContract` from a compiled spec and validate it is `time_domain="discrete"` before running. This is a validation gate, not a new runner — `gds-sim` already implements Moore discrete-time semantics.

7. **Update DSL compilers to emit contracts.** Each DSL compiler's `compile_model()` should attach an appropriate `ExecutionContract`:
    - `gds-stockflow`: `discrete, synchronous, Moore`
    - `gds-control`: `discrete, synchronous, Moore`
    - `gds-games`: `atemporal`
    - `gds-software`: `atemporal` (most diagrams) or `discrete` (state machines)
    - `gds-business`: varies by diagram type (CLD: atemporal, SCN: discrete, VSM: varies)

8. **Write the execution semantics document.** `docs/research/execution-semantics.md`:
    - Three-layer temporal stack (from T0-4)
    - ExecutionContract field definitions and semantics
    - Moore discrete-time as a named instantiation
    - What is NOT covered (continuous, event, async — addressed by T2-4 and future)
    - Table mapping each DSL to its ExecutionContract values

**Deliverables:**

- [ ] `ExecutionContract` dataclass in `gds/execution.py`
- [ ] `GDSSpec.execution_contract` optional field
- [ ] Moore discrete-time semantics formal statement
- [ ] SC-011: cross-composition contract compatibility check
- [ ] G-007: algebraic loop check for discrete-time (if not covered by G-006)
- [ ] gds-sim validation gate for ExecutionContract
- [ ] DSL compiler updates (all 7 DSLs)
- [ ] `docs/research/execution-semantics.md`
- [ ] Tests for all new code

---

#### Stream 3B: T1-3 — Formalize Disturbance Inputs

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C2, C3 | **Depends on:** T1-1, T0-3

**Problem:** Exogenous controlled inputs (u, policy-observable) and disturbances (w, state-forcing, policy-bypassing) are conflated under `BoundaryAction`. Without the distinction, the framework cannot support disturbance rejection analysis or robustness specifications.

**Steps:**

1. **Formally define the input partition.** Two subsets of exogenous inputs:
    - `U_c` (controlled) — observed by policy g, enters f only through d = g(x, u_c)
    - `W` (disturbance) — enters f directly, bypasses g entirely
    - Invariant: no component of W appears in domain of g; no component of U_c appears in f except through d

2. **Define the tagging convention.** Use the existing `Tagged` mixin:
    ```python
    BoundaryAction(
        name="Wind Disturbance",
        forward_out={"Wind Force"},
        tags={"role": "disturbance"}
    )
    ```
    Absence of the tag means controlled input (default). This is a semantic annotation, not a structural type.

3. **Implement DST-001 domain check.** A disturbance-tagged BoundaryAction must not be wired to any Policy block in the non-feedback wiring subgraph. This enforces the bypass-of-decision-layer invariant. Implemented as a domain check (tag-dependent, not pure structural).

4. **Update the extended canonical form.** The full canonical with disturbances:
    ```
    d[t]   = g(x[t], u_c[t])           # g: X × U_c → D
    x[t+1] = f(x[t], d[t], w[t])       # f: X × D × W → X
    y[t]   = C(x[t], d[t])             # C: X × D → Y
    ```
    `CanonicalGDS` gains: `disturbance_ports: tuple[tuple[str, str], ...]` — (block_name, port_name) from disturbance-tagged BoundaryActions. `project_canonical()` partitions input_ports into controlled and disturbance based on tags.

5. **Write documentation.** `docs/research/disturbance-formalization.md`:
    - When to use disturbance-tagged BoundaryAction vs. controlled input
    - What modeling judgment motivates the distinction
    - What DST-001 enforces and what it does not
    - Cross-reference with controller-plant duality (T0-3)

6. **Populate disturbance column in execution semantics table.** Update the DSL ExecutionContract table from T1-1 with which DSLs have disturbance-tagged inputs:
    - gds-control: plant disturbances (noise, external forces)
    - gds-stockflow: exogenous shocks (market events)
    - Others: documented as N/A or TBD

**Deliverables:**

- [ ] Formal input partition definition (U_c, W)
- [ ] Tagging convention: `tags={"role": "disturbance"}`
- [ ] DST-001 domain check implementation
- [ ] Extended CanonicalGDS with disturbance_ports
- [ ] Updated project_canonical() for tag-based partitioning
- [ ] `docs/research/disturbance-formalization.md`
- [ ] Tests for all new code

---

### Phase 4 — Analysis & Behavioral Verification

**Begins after:** Phase 3 complete (T1-1 required for all items).

**Goal:** Build the analysis infrastructure: structural reachability/distinguishability, behavioral trajectory verification, cross-lens queries, and continuous-time formalization. Four independent streams.

#### Stream 4A: T2-1 — Structural Reachability, Distinguishability, and DSL-Layer State Semantics

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C2 | **Depends on:** T1-1, T0-3

**Problem:** The framework needs graph-based reachability and distinguishability analysis that is representation-agnostic. Existing `gds-analysis` reachability operates on concrete simulation state; this item adds structural (topology-only) analysis on SystemIR.

**Codebase context:** `gds_analysis/reachability.py` already implements forward reachability on concrete state via `spec_to_model()`. This item adds a *different* thing: structural reachability on the wiring graph, before any simulation.

**Steps:**

1. **Formalize the abstract channel model.** A Space is a wiring compatibility label. Axioms: (a) two ports are wirable iff their Space tokens are compatible, (b) no arithmetic, metric, topological, or representational structure is assumed. This formalizes what the core already does implicitly.

2. **Define structural reachability on SystemIR.** Given SystemIR, is there a directed wiring path from a BoundaryAction output port to a given Entity variable (via Mechanism updates)? Pure graph traversal — no knowledge of channel content.

3. **Define structural distinguishability on SystemIR.** Given SystemIR, is there a directed wiring path from a given Entity variable to a ControlAction output port (T0-3)? Again, pure graph traversal.

4. **Implement in gds-analysis.** New module `gds_analysis/structural.py`:
    - `structural_reachability(system_ir) -> dict[str, set[tuple[str, str]]]` — maps each BoundaryAction to reachable (entity, variable) pairs
    - `structural_distinguishability(system_ir) -> dict[tuple[str, str], set[str]]` — maps each (entity, variable) to ControlAction blocks that can observe it

5. **Write the DSL author's guide.** `docs/guides/dsl-state-semantics.md`: how to define state transitions, state diffs, behavioral invariants, and how DSL-level reachability/distinguishability connects to structural checks. Two worked examples: numerical (arithmetic) and relational (SPARQL UPDATE).

6. **Add controllability/observability to gds-control only.** Domain-specific check: linear-systems structural controllability and observability (rank conditions on system matrices). Strictly a gds-control DSL check, not framework-level.

**Deliverables:**

- [ ] Abstract channel model formalization
- [ ] Structural reachability definition and implementation
- [ ] Structural distinguishability definition and implementation
- [ ] `gds_analysis/structural.py`
- [ ] `docs/guides/dsl-state-semantics.md`
- [ ] gds-control controllability/observability check
- [ ] Tests

---

#### Stream 4B: T2-2 — Behavioral / Trajectory Verification Layer

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C2, C3 | **Depends on:** T1-1, T0-1

**Problem:** Structural verification confirms well-formedness. It cannot confirm behavioral correctness. A structurally correct spec can exhibit invariant violations, non-convergence, or inadmissible outputs.

**Steps:**

1. **Define abstract behavioral predicate schemas.** Two core check classes operating on opaque channel trajectories:
    - **BV-001** (universal invariant): for all steps in trajectory τ, channel c's value satisfies DSL-supplied predicate P(v)
    - **BV-002** (existential fixed-point): there exists a step t* ≤ N such that P(v[t*], v[t*-1]) holds (e.g., equality/convergence)

    Both are representation-agnostic. The core provides the check structure; DSLs provide concrete predicates.

2. **Define the `BehavioralPredicate` protocol.** Typed protocol that DSL authors implement:
    ```python
    class BehavioralPredicate(Protocol):
        channel: str
        check_type: Literal["invariant", "fixed_point"]
        def evaluate(self, value: Any) -> bool: ...          # BV-001
        def converged(self, prev: Any, curr: Any) -> bool: ... # BV-002
    ```

3. **Build the abstract behavioral check runner.** In `gds-analysis`: executes a compiled SystemIR under its ExecutionContract, records channel trajectory, evaluates registered predicates. The runner does not inspect channel values — it passes them to predicates.

4. **DSL predicate registrations.** Each DSL registers concrete predicates:
    - gds-stockflow: stock non-negativity (BV-001), stock steady-state (BV-002), conservation `Σ stocks = const` (DSL-specific, not BV-001)
    - gds-control: output admissibility `y ∈ Y_admissible` (BV-001), state convergence to setpoint (BV-002)
    - gds-games: rationality constraint (BV-001), equilibrium reached (BV-002)

5. **Document the two-level structure.** Framework provides abstract BV-001/BV-002 + runner. DSLs provide concrete predicates. Make explicit: the framework claims nothing about which predicates are appropriate.

**Deliverables:**

- [ ] BV-001 and BV-002 formal definitions
- [ ] `BehavioralPredicate` protocol
- [ ] Abstract check runner in gds-analysis
- [ ] DSL predicate registrations (stockflow, control, games)
- [ ] Documentation
- [ ] Tests

---

#### Stream 4C: T2-3 — Cross-Lens Query Infrastructure

**Type:** [MATH] [CODE] | **Criteria:** C2, C4 | **Depends on:** T1-1, T1-3

**Problem:** The game-theoretic lens (PatternIR → equilibria) and the dynamical lens (CanonicalGDS → reachability, stability) are orthogonal and can disagree. Infrastructure to query across lenses does not exist.

**Steps:**

1. **Define cross-lens agreement/disagreement formally.** When two lenses can be compared (compatible ExecutionContracts). What constitutes meaningful disagreement vs. timestep artifact.

2. **Implement `CrossLensQuery` module.** Consumes both PatternIR and CanonicalGDS. Initial queries:
    - `is_nash_equilibrium_a_fixed_point(pattern_ir, canonical_gds)`
    - `is_stable_attractor_incentive_compatible(canonical_gds, pattern_ir)`
    - `is_reachable_state_individually_rational(canonical_gds, pattern_ir, state)`

3. **Worked case study.** Axelrod tournament: what the game-theoretic lens says, what the dynamical lens says, where they disagree, what the disagreement means.

**Deliverables:**

- [ ] Cross-lens agreement/disagreement definitions
- [ ] `CrossLensQuery` module with initial queries
- [ ] Axelrod case study
- [ ] Tests

---

#### Stream 4D: T2-4 — Continuous-Time Formalization

**Type:** [MATH] [DOC] [CODE] | **Criteria:** C2 | **Depends on:** T1-1, T1-3

**Problem:** `gds-continuous` currently bypasses GDSSpec entirely — it builds `ODEModel` directly with no connection to the canonical form. The specification/simulation separation needs to be made explicit.

**Codebase context:** `gds-continuous` is standalone (pydantic-only, no gds-framework dependency). It provides `ODEModel`, `ODESimulation`, `ODEResults`. The `gds-symbolic` package creates ODE functions from control models but doesn't route through GDSSpec.

**Steps:**

1. **Define continuous-time specification.** When a GDSSpec constitutes a valid continuous-time system: all Mechanism blocks produce vector field terms `dx/dt = ...`; the state subspace is declared real-valued. This is specification only — no solver commitment.

2. **Add continuous-time ExecutionContract entry.** `time_domain="continuous"`, scoped to a declared numerical subspace. No solver metadata.

3. **Define the SolverInterface contract.** Abstract protocol in gds-continuous:
    ```python
    class SolverInterface(Protocol):
        def step(self, f: Callable, x: ndarray, d: Any, dt: float) -> ndarray: ...
    ```
    Concrete solvers (RK4, scipy solve_ivp) implement this.

4. **Refactor gds-continuous.** Read continuous-time ExecutionContract from compiled SystemIR. Dispatch to SolverInterface-compliant implementation. Provide RK4 and scipy as reference implementations.

5. **Build the spec→ODE adapter.** Parallel to `gds_analysis/adapter.py` (spec→sim), create a `spec_to_ode_model()` adapter that bridges GDSSpec with continuous ExecutionContract to `ODEModel`.

6. **Write side-by-side example.** Thermostat as discrete-time GDSSpec vs. continuous-time GDSSpec. Same wiring topology and canonical decomposition; different ExecutionContract and solver.

**Deliverables:**

- [ ] Continuous-time specification definition
- [ ] ExecutionContract `time_domain="continuous"` entry
- [ ] `SolverInterface` protocol in gds-continuous
- [ ] RK4 and scipy reference implementations
- [ ] gds-continuous refactor to read ExecutionContract
- [ ] `spec_to_ode_model()` adapter
- [ ] Side-by-side thermostat example
- [ ] Tests

---

### Phase 5 — Research Frontier

**Triggered by:** Specific future concrete work. Not scheduled; pre-conditions stated.

#### T3-1 — PatternIR Consolidation

**Type:** [MATH] [CODE] | **Criteria:** C2 | **Triggered by:** Stability of report/viz tooling | **Depends on:** T2-2

The bridge `compile_pattern_to_spec()` already proves PatternIR and GDSSpec produce equivalent canonical results. Consolidation is a refactoring question, not a correctness question. Defer until the view layer is stable.

#### T3-2 — Formal Verification Export (Lean 4 / Coq)

**Type:** [MATH] [CODE] | **Criteria:** C3 | **Triggered by:** Safety-critical application requiring machine-checked proof | **Depends on:** T0-1, T0-2

The OWL export handles semantic web representability. A proof assistant export would enable formally certified verification results. Do not pursue until informal verification is well-specified and traceable.

#### T3-3 — Stochastic Extensions

**Type:** [MATH] [CODE] | **Criteria:** C2 | **Triggered by:** Epidemiological, financial, or agent-based model requiring stochastic semantics | **Depends on:** T1-1, T2-2

Extend the canonical form to support stochastic transition maps: `h: X × Ω → X` or `h: X → ΔX`. Requires `StochasticMechanism` role, distribution-valued Space, Monte Carlo harness, and probabilistic behavioral checks. Do not introduce until the deterministic case is well-characterized.

---

## Dependency Graph

```
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  T0-1    │  │  T0-3    │  │  T0-4    │   Phase 1
        │  Check   │  │  Control │  │  Temporal │   (parallel)
        │  Specs   │  │  Action  │  │  Agnostic │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │
     ┌───────┼──────────────┼──────────────┘
     │       │              │
     ▼       │              │
┌──────────┐ │         ┌─────────────────────────┐
│  T0-2    │ │         │  T1-1                   │   Phase 2-3
│  Trace-  │ │         │  ExecutionContract      │
│  ability │ │         │  (needs T0-1,T0-3,T0-4) │
└────┬─────┘ │         └────────┬────────────────┘
     │       │                  │
     │  ┌────┴─────┐     ┌─────┴──────┐
     │  │  T1-2    │     │  T1-3      │
     │  │  PSUU↔Θ  │     │  Disturb.  │
     │  │(needs T0-1)    │(needs T1-1)│
     │  └──────────┘     └────────────┘
     │
     ▼
┌──────────┐
│  T1-4    │
│  Assur.  │
│  (T0-1+2)│
└──────────┘
             ┌──────────────────────────────────┐
             │  Phase 4 (all need T1-1)         │
             │                                  │
             │  T2-1  T2-2  T2-3  T2-4         │
             │  Reach  Behav Cross  Cont.       │
             │  Dist.  Verif Lens   Time        │
             └──────────────────────────────────┘

             ┌──────────────────────────────────┐
             │  Phase 5 (triggered, not sched.) │
             │                                  │
             │  T3-1  T3-2  T3-3               │
             │  PIR   Lean  Stoch.             │
             └──────────────────────────────────┘
```

**Critical path:** T0-1 → T1-1 → Phase 4. Everything eventually flows through ExecutionContract.

**Fastest value delivery:** T1-2 (PSUU ↔ Θ) depends only on T0-1 and is the narrowest scope with highest immediate practical value. Ship first within Phase 2.

---

## Summary Table

| ID | Item | Tier | Phase | Type | Primary Criteria | Depends On |
|----|------|------|-------|------|-----------------|------------|
| T0-1 | Formalize check specifications | 0 | 1 | MATH, DOC | C1 | — |
| T0-2 | Requirement traceability | 0 | 2 | DOC, CODE | C1, C3 | T0-1 |
| T0-3 | ControlAction + controller-plant duality | 0 | 1 | MATH, DOC, CODE | C1, C2 | — |
| T0-4 | Temporal agnosticism invariant | 0 | 1 | MATH, DOC | C1 | — |
| T1-1 | ExecutionContract + simulation semantics | 1 | 3 | MATH, DOC, CODE | C2, C4 | T0-1, T0-3, T0-4 |
| T1-2 | PSUU ↔ Θ connection | 1 | 2 | CODE | C2, C3 | T0-1 |
| T1-3 | Disturbance formalization | 1 | 3 | MATH, DOC, CODE | C2, C3 | T1-1, T0-3 |
| T1-4 | Assurance V&V mapping | 1 | 2 | DOC | C2, C3 | T0-1, T0-2 |
| T2-1 | Structural reachability + distinguishability | 2 | 4 | MATH, DOC, CODE | C2 | T1-1, T0-3 |
| T2-2 | Behavioral trajectory verification | 2 | 4 | MATH, DOC, CODE | C2, C3 | T1-1, T0-1 |
| T2-3 | Cross-lens query infrastructure | 2 | 4 | MATH, CODE | C2, C4 | T1-1, T1-3 |
| T2-4 | Continuous-time formalization | 2 | 4 | MATH, DOC, CODE | C2 | T1-1, T1-3 |
| T3-1 | PatternIR consolidation | 3 | 5 | MATH, CODE | C2 | T2-2 |
| T3-2 | Formal verification export (Lean 4) | 3 | 5 | MATH, CODE | C3 | T0-1, T0-2 |
| T3-3 | Stochastic extensions | 3 | 5 | MATH, CODE | C2 | T1-1, T2-2 |

---

## Extended Canonical Form

The full canonical form after T0-3 (output map) and T1-3 (disturbance partition):

```
Given: (X, U_c, W, D, Y, Θ, g, f, C)

d[t]   = g(x[t], u_c[t])         # g: X × U_c → D    policy map
x[t+1] = f(x[t], d[t], w[t])     # f: X × D × W → X  state update with disturbance
y[t]   = C(x[t], d[t])           # C: X × D → Y      output map

Where:
  u_c ∈ U_c  — controlled / observable exogenous input (seen by g)
  w ∈ W      — disturbance / uncontrolled forcing (enters f directly)
  d ∈ D      — decision (output of g)
  y ∈ Y      — observable output (ControlAction; from outside, a control action)
```

This extension does not change the Layer 0 composition algebra. The partition (U_c, W) is enforced at the semantic layer via tagging and domain checks. C is realized by the existing ControlAction role. The algebra `h = f ∘ g` is preserved; the extended form is a semantic refinement.

---

## Scientific Argument and Evidence Strategy

The 15 roadmap items are not independent improvements. They form a cumulative argument for the core claim of GDS: **`h = f ∘ g` is a universal transition calculus.** Seven DSLs compiling to the same canonical form is structural validation — the weakest form of evidence. The roadmap builds toward progressively stronger evidence:

```
Level 0: Structural — "the composition compiles"               ← current state
Level 1: Formal     — "the checks enforce stated properties"    ← Phase 1-2
Level 2: Semantic   — "the spec carries execution meaning"      ← Phase 3
Level 3: Behavioral — "the system does what the spec says"      ← Phase 4
Level 4: Cross-domain — "lenses agree or disagree meaningfully" ← Phase 4
```

Each level is a stronger scientific claim with a different standard of evidence.

### What Each Phase Proves

**Phase 1 (Foundations)** establishes correspondence between software and mathematics.

- T0-1 transforms check docstrings into verifiable mathematical claims. After T0-1, the answer to "what does G-006 prove?" is: "G-006 establishes that the covariant wiring graph is a DAG, which is a necessary condition for `h = f ∘ g` to be well-defined as a function rather than an implicit equation."
- T0-3 completes the state-space representation. The current canonical `(X, U, D, Θ, g, f)` has no output equation. In control theory the standard form requires both `x' = f(x, u)` (state equation) and `y = C(x, u)` (output equation). Without the output equation, observability questions are unanswerable. T0-3 gives `(X, U, D, Y, Θ, g, f, C)`. The controller-plant duality (one system's output = next system's input at every `>>` boundary) is a theorem about the composition algebra.
- T0-4 makes the strongest theoretical claim: the composition algebra makes no commitment about time. Most frameworks bake in discrete-time or continuous-time at the foundation. The OGS case (temporal wirings, `f = ∅`, `X = ∅`, no time model) is an existence proof of genuine temporal agnosticism. T0-4 makes this proof explicit.

**Phase 2 (Traceability)** makes claims auditable.

- T0-2 answers: does the test suite cover the properties we claim to verify, or just the code paths that happen to exist?
- T1-2 answers: does the optimizer respect the formal parameter space, or can it silently explore undefined regions?
- T1-4 answers: what exactly does a `verify()` pass mean, and what does it not mean?

**Phase 3 (Execution Semantics)** separates specification from simulation.

- T1-1 makes a genuine contribution vs. frameworks where the execution model is built into the specification: a GDSSpec is a valid formal object *without* an execution model. ExecutionContract is what makes it executable — and it's optional. The same spec can be verified structurally without committing to a time model, or simulated under different execution semantics.
- T1-3 enables robustness analysis by formally distinguishing controlled inputs from disturbances — a prerequisite for disturbance rejection, observer design, and robust control.

**Phase 4 (Analysis & Behavioral)** produces falsifiable claims.

- T2-2 bridges "the spec is well-formed" and "the system behaves correctly." The abstract predicate framework (BV-001: universal invariant, BV-002: existential fixed-point) is as domain-general as the composition algebra — the core says nothing about what predicates are appropriate, only provides the evaluation structure.
- T2-3 is the unique scientific contribution no other framework offers: analyzing the same system through a game-theoretic lens (equilibria, incentive compatibility) and a dynamical lens (reachability, stability), then asking whether the lenses agree. A Nash equilibrium that is a dynamically unstable fixed point is a genuine finding — the equilibrium exists in theory but the system will not stay there. This is the kind of result that merits publication.

### Verification Strategy by Phase

Each phase requires a different standard of evidence.

#### Phase 1-2: Correspondence Proofs

For check specifications (T0-1) and the canonical extension (T0-3), the verification is a correspondence argument: does the software faithfully implement the math?

**Method:** Two-column correspondence table, each row independently verifiable:

| Mathematical property | Software implementation |
|---|---|
| Covariant wiring graph is a DAG | `check_covariant_acyclicity()` — DFS on covariant subgraph of SystemIR |
| h = f ∘ g requires f non-empty | SC-006 verifies ≥1 Mechanism block exists |
| Output map C: X × D → Y | ControlAction blocks' `forward_out` extracted into `CanonicalGDS.output_ports` |

For temporal agnosticism (T0-4), the verification is proof by inspection: show each composition operator's implementation does not reference or introduce a time model. The OGS case is the empirical existence proof.

For traceability (T0-2), the verification is a coverage matrix. After tagging tests with `@pytest.mark.requirement`, any requirement with zero covering tests is a finding. Mutation testing (inject faults into check implementations, verify tagged tests catch them) provides stronger evidence.

For PSUU (T1-2), the verification is property-based testing: generate random ParameterSchema/ParameterSpace pairs, verify the validator catches every out-of-bounds case and accepts every valid case.

#### Phase 3: Cross-Built Equivalence

The gold standard already established for DSL validation extends to ExecutionContract: build the same system two ways (DSL compiler vs. hand-built), verify equivalence at every level (GDSSpec, CanonicalGDS, SystemIR, and now ExecutionContract).

For disturbance formalization, add a new equivalence dimension: build a system with and without the disturbance tag, verify structural wiring is identical but the semantic partition (U_c vs W) differs.

#### Phase 4: Falsification

Behavioral verification is verified by constructing systems that are structurally correct but behaviorally pathological, then showing the behavioral checks catch them:

| System | Structural | Behavioral | Expected result |
|--------|-----------|------------|-----------------|
| Stock-flow with negative stock | G/SC pass | BV-001 (non-negativity) FAIL | Structural ✓, behavioral ✗ |
| Control system that diverges | G/SC pass | BV-002 (convergence) FAIL | Structural ✓, behavioral ✗ |
| Thermostat that oscillates forever | G/SC pass | BV-002 (steady-state) FAIL | Structural ✓, behavioral ✗ |
| Well-designed thermostat | G/SC pass | BV-001 + BV-002 pass | Both ✓ |

This demonstrates the gap between structural and behavioral verification — which is exactly what T1-4 (assurance mapping) documents.

Cross-lens queries (T2-3) are verified by constructing known disagreement cases from textbook results:

- **Prisoner's dilemma with dynamics:** Nash equilibrium (both defect) is dynamically stable. Tit-for-tat cooperation is Pareto-superior but dynamically unstable under invasion. The cross-lens query should surface this disagreement.
- **Hawk-Dove with population dynamics:** Mixed-strategy Nash equilibrium IS a stable fixed point of the replicator dynamics. The query should confirm agreement.

If the infrastructure reproduces known textbook results, it is validated.

### Showcase Artifacts

Three artifacts, in order of impact:

#### 1. Extended Canonical Spectrum Table

The existing table showing 7 DSLs compiling to the same canonical form is the strongest evidence for universality. After Phase 1-3, extend it with the new dimensions:

| Domain | |X| | |f| | |C| | ExecutionContract | Disturbance? | Form |
|--------|-----|-----|-----|-------------------|-------------|------|
| OGS (games) | 0 | 0 | 0 | atemporal | N/A | h = g |
| Control | n | n | m | discrete/Moore | Yes (plant noise) | h = f ∘ g |
| StockFlow | n | n | 0 | discrete/Moore | Yes (shocks) | h = f ∘ g |
| Software (DFD) | 0 | 0 | 0 | atemporal | N/A | h = g |
| Software (SM) | n | n | 0 | discrete/Moore | No | h = f ∘ g |
| Business (CLD) | 0 | 0 | 0 | atemporal | N/A | h = g |
| Business (SCN) | n | n | 0 | discrete/Moore | Yes (demand) | h = f ∘ g |

Each column is independently verifiable. The table tells the whole story at a glance.

#### 2. Verification Pyramid

A visual showing the verification layers, what passes/fails at each level, and the explicit gaps:

```
                  ╱╲
                 ╱  ╲   Full V&V (simulation + formal proof + physical testing)
                ╱────╲
               ╱      ╲   Behavioral (BV-001, BV-002 + DSL predicates)
              ╱────────╲
             ╱          ╲   Semantic (SC-001..SC-011 on GDSSpec)
            ╱────────────╲
           ╱              ╲   Structural (G-001..G-007 on SystemIR)
          ╱────────────────╲
```

With concrete examples at each boundary: "System X passes structural but fails behavioral because..." This is what the verification passport template (T1-4) captures per-system.

#### 3. Cross-Lens Case Study (Publishable Result)

A single system analyzed through both the game-theoretic and dynamical lenses, where the lenses disagree, and the disagreement has real design implications. The Axelrod tournament is the natural candidate: well-known, established game theory, and showing that GDS surfaces the dynamical/strategic tension in a unified framework is a novel contribution.

This is the paper. Everything else is infrastructure that makes this result possible.

### The Fundamental Claim

Phase 1-2 make existing claims *rigorous*. Phase 3 makes them *executable*. Phase 4 makes them *falsifiable*. A falsifiable claim that survives falsification is science.

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-03-28 | Initial external review (Chief Engineer + Claude Sonnet 4.6) |
| 0.2–0.7 | 2026-03-28 | Iterative revisions to T2-1 (representation agnosticism), T0-4 (temporal agnosticism), T1-1 (ExecutionContract), T1-3 (disturbance scope), T2-2 (abstract predicates), T2-4 (solver interface). See original review for detailed changelog. |
| 1.0 | 2026-03-29 | Reconciled against codebase. Added: current state summary, already-implemented features (AdmissibleInputConstraint, TransitionSignature, SC-008/SC-009, reachability analysis), corrected test counts (~2,292 total), updated check count to 15, added phased execution plan with detailed steps for all 15 items, dependency graph, SC-010 feedback-path nuance for T0-3. |
| 1.1 | 2026-03-29 | Added "Scientific Argument and Evidence Strategy" section: cumulative evidence levels (structural → formal → semantic → behavioral → cross-domain), per-phase verification strategies (correspondence proofs, property-based testing, cross-built equivalence, falsification), and three showcase artifacts (extended canonical spectrum table, verification pyramid, cross-lens case study). |
