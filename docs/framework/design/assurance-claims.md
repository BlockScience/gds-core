# Assurance Claims and Residual Gaps

This document explicitly states what `verify()` does and does not prove, maps
each check to an assurance layer, lists residual verification obligations by
domain, and provides a verification passport template for practitioners.

A practitioner who sees all checks pass should know exactly what guarantees
they hold -- and what evidence they still need to collect.

---

## 1. The Verification Pyramid

GDS verification is organized in layers. Each layer depends on the layers below
it. The framework currently implements the bottom two layers; the upper layers
require external evidence.

```
                    /\
                   /  \    Full V&V (external evidence required)
                  /----\
                 /      \    Behavioral (trajectory predicates -- future T2-2)
                /--------\
               /          \    Semantic (SC-001..SC-010 on GDSSpec)
              /------------\
             /              \    Structural (G-001..G-006 on SystemIR)
            /----------------\
```

**Structural** checks validate the composition algebra: the wiring graph is a
well-formed mathematical object with compatible ports, no dangling references,
and acyclic forward flow.

**Semantic** checks validate the specification: state coverage is complete,
updates are deterministic, references resolve, and the canonical decomposition
`h = f . g` is well-defined.

**Behavioral** checks would validate trajectory properties: invariants hold
under execution, states remain bounded, goals are eventually reached. This
layer does not exist yet (planned as T2-2).

**Full V&V** requires evidence that the framework cannot produce: simulation
results, formal proofs, physical testing, or domain expert review.

---

## 2. Check-to-Layer Mapping

| Layer | Checks | What They Prove | Operates On |
|-------|--------|-----------------|-------------|
| Structural (topology) | G-001..G-006 | Wiring graph is well-formed: type-compatible, complete signatures, acyclic forward flow, no dangling references | `SystemIR` |
| Semantic (specification) | SC-001..SC-009, SC-010 | Spec is internally consistent: complete state coverage, deterministic updates, reachable signals, valid references, canonical wellformedness, ControlAction pathway separation | `GDSSpec` |
| Behavioral (trajectory) | None yet | Would prove: trajectory invariants hold under execution | Future (T2-2) |
| Full assurance | -- | Requires simulation evidence, formal proofs, or physical testing | External |

### Structural checks (Layer 0)

These operate on `SystemIR` and are run automatically by `verify(system)`.

| Check | Property |
|-------|----------|
| G-001 | Covariant wiring labels are token-subsets of source output or target input |
| G-002 | Every block has non-degenerate interface (at least one input and one output) |
| G-003 | No direction flag contradictions; contravariant port-slot matching |
| G-004 | Wiring endpoints reference blocks or inputs that exist |
| G-005 | Stack wiring labels match both source output and target input |
| G-006 | Forward (covariant) flow graph is a directed acyclic graph |

### Semantic checks (Layer 1)

These operate on `GDSSpec` and are called individually.

| Check | Property |
|-------|----------|
| SC-001 | Every state variable is updated by at least one mechanism |
| SC-002 | No variable updated by multiple mechanisms in the same wiring |
| SC-003 | Signal path exists between two named blocks (reachability) |
| SC-004 | Wire space references resolve to registered spaces |
| SC-005 | Block `params_used` match registered parameter names |
| SC-006 | At least one mechanism exists (state transition f is non-empty) |
| SC-007 | At least one state variable exists (state space X is non-empty) |
| SC-008 | Admissibility constraints reference valid blocks and variables |
| SC-009 | Transition signatures reference valid mechanisms and variables |
| SC-010 | ControlAction outputs do not route back to Policy or BoundaryAction blocks |

---

## 3. What the Framework Does NOT Prove

A `verify()` pass establishes structural well-formedness and specification
consistency. It does **not** establish any of the following properties:

**Behavioral safety** -- no state reaches an unsafe region. Requires simulation
or formal proof. A structurally valid system can still drive state variables to
dangerous values.

**Liveness** -- the system eventually reaches a goal state. Requires temporal
logic model checking or bounded simulation. A well-formed spec says nothing
about whether desired states are ever attained.

**Stability** -- trajectories converge or remain bounded. Requires Lyapunov
analysis or simulation. This is the primary concern of the gds-control DSL
domain and gds-continuous integration.

**Conservation** -- quantities are preserved across transitions. Requires
trajectory invariant checks (flow balance audits). This is the primary concern
of the gds-stockflow DSL domain, where stock levels should satisfy
`d(Stock)/dt = sum(inflows) - sum(outflows)`.

**Optimality** -- decisions maximize or minimize an objective. Requires
optimization analysis. Verification checks that blocks are wired correctly,
not that the policies they implement are optimal.

**Incentive compatibility** -- agents' equilibrium strategies align with
desired outcomes. Requires Nash equilibrium computation. This is the primary
concern of the gds-games DSL domain, which provides nashpy integration for
this purpose.

**Convergence** -- iterative processes terminate or approach a limit. Requires
convergence analysis or fixed-point computation. Feedback loops are
structurally validated (G-006 checks acyclicity of covariant flow), but
convergence of the dynamics they represent is not assessed.

**Adequacy to purpose** -- the model correctly represents the real-world
system it is intended to describe. Requires domain expert validation, physical
testing, and stakeholder review. This is fundamentally outside any framework's
scope.

---

## 4. Residual Verification Obligations

For each property that `verify()` cannot establish, the table below identifies
what evidence is needed and which layer of the ecosystem is responsible.

| Property | Required Evidence | Responsible Layer |
|----------|-------------------|-------------------|
| Stability | Simulation + Lyapunov analysis | gds-control DSL + gds-continuous |
| Conservation | Trajectory invariant checks (flow balance) | gds-stockflow DSL + gds-sim |
| Incentive compatibility | Nash equilibrium computation | gds-games DSL (nashpy) |
| Safety | Behavioral predicates on reachable states | Future T2-2 + gds-analysis |
| Liveness | Temporal logic model checking or bounded simulation | Future (not planned) |
| Convergence | Fixed-point analysis or bounded iteration testing | Domain-specific |
| Optimality | Objective function evaluation over trajectories | Domain-specific + gds-psuu |
| Adequacy | Domain expert review, physical testing | Outside framework scope |

The key takeaway: passing all 16 checks (G-001..G-006, SC-001..SC-010)
establishes that the specification is a well-formed, internally consistent
mathematical object. It says nothing about whether that object faithfully
models reality or behaves safely when executed.

---

## 5. Verification Passport Template

The following template provides a one-page assessment format for any
GDS-specified system. Copy and fill it in for each system you verify.

```markdown
# Verification Passport: [System Name]

## System Identity
- **GDSSpec name:** [name]
- **Version:** [version/commit hash]
- **DSL:** [which DSL, if applicable]
- **Date:** [assessment date]

## Structural Verification (Layer 0)
- [ ] G-001 through G-006: [PASS/FAIL]
- **SystemIR compiled from:** [composition tree description]
- **Findings:** [count] errors, [count] warnings

## Semantic Verification (Layer 1)
- [ ] SC-001 through SC-010: [PASS/FAIL]
- **Canonical form:** [formula() output]
- **State space dimension:** [|X|]
- **Findings:** [count] errors, [count] warnings

## Claims Supported by Framework Checks
Based on passing structural and semantic verification:
- Wiring topology is well-formed (no type mismatches, no dangling references)
- State variables have complete, deterministic update coverage
- Canonical decomposition h = f . g is well-defined
- [Additional claims based on specific checks passed]

## Residual Obligations (NOT covered by framework)
| Property | Status | Evidence |
|----------|--------|----------|
| Stability | [ ] Verified / [ ] Not assessed | [method + results] |
| Safety | [ ] Verified / [ ] Not assessed | [method + results] |
| Conservation | [ ] Verified / [ ] Not assessed | [method + results] |
| Incentive compatibility | [ ] Verified / [ ] Not assessed | [method + results] |
| Convergence | [ ] Verified / [ ] Not assessed | [method + results] |
| Optimality | [ ] Verified / [ ] Not assessed | [method + results] |
| Adequacy | [ ] Verified / [ ] Not assessed | [method + results] |

## Sign-off
- **Structural verification by:** [automated -- gds-framework v___]
- **Behavioral evidence by:** [person/system]
- **Domain adequacy by:** [domain expert]
```

---

## 6. Cross-References

- [Verification Check Specifications](check-specifications.md) -- formal
  property statements, invariant connections, and soundness conditions for
  all 15 core checks
- [Traceability Matrix](traceability-matrix.md) -- mapping from checks to
  test cases and code locations
- [Verification Check Catalog](../guide/verification.md) -- user-facing
  reference with examples for every check
- [Controller-Plant Duality](controller-plant-duality.md) -- design rationale
  for SC-010 (ControlAction pathway separation)
- T2-2 (behavioral verification layer) -- planned future work for trajectory
  predicate checking via gds-analysis and gds-sim
- **Verification humility doctrine (MD-4)** -- the principle that structural
  verification is necessary but not sufficient, and that the framework must
  never overstate its assurance claims. Verification proves well-formedness
  of the mathematical object, not correctness of the model it represents.
