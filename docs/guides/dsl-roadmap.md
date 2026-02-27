# DSL Roadmap

## Current Status

Layer 0 (Composition Core) is stable and sealed. Three domain DSLs are implemented and validated:

| DSL | Domain | Package | Tests | Canonical |
|---|---|---|---|---|
| **OGS** | Compositional game theory | `gds-games` | Mature | Projected via `to_system_ir()` |
| **StockFlow** | System dynamics | `gds-stockflow` | 215 | Clean — verified by cross-built equivalence |
| **Control** | State-space control | `gds-control` | 117 | Clean — verified by cross-built equivalence + parametric invariants |

All three compile to `GDSSpec` / `SystemIR` and produce clean canonical decompositions without modification to the core.

### Validated Architectural Claims

- **Canonical `h = f ∘ g` is correctly minimal.** Three independent domains have not required extensions.
- **`ControlAction` is unnecessary.** All non-state-updating blocks across all DSLs map to `Policy`. The role system (Boundary, Policy, Mechanism) covers all three domains.
- **A convergent composition pattern has emerged:**
  ```
  (peripheral observers | exogenous inputs)
      >> (decision logic)
      >> (state dynamics)
  .loop(state → observers)
  ```
- **GDS IR is the IR.** No domain has needed a parallel IR stack. Domain-specific IR (OGS `PatternIR`) projects to `SystemIR` for cross-cutting tools.

## DSL Contract Checklist

Every new DSL must answer the [Semantic Layer Contract](../framework/guide/architecture.md#4-the-semantic-layer-contract) — eight questions that fully specify how a domain maps onto the composition algebra:

1. **Block semantics** — what does a block represent?
2. **Sequential (`>>`)** — what operation is induced?
3. **Parallel (`|`)** — what is the product structure?
4. **Feedback (`.feedback()`)** — what fixed-point or closure?
5. **Temporal (`.loop()`)** — what cross-step semantics?
6. **Execution model** — static? discrete-time? continuous? equilibrium?
7. **Validation layer** — what domain invariants? What checks?
8. **Canonical projection** (recommended) — what is the domain normal form?

### Implementation Checklist

For each new DSL package:

- [ ] Subclass `AtomicBlock` with domain-specific block types (or reuse GDS roles)
- [ ] Define domain IR models (extending or wrapping `BlockIR`, `WiringIR`) — or compile directly to `GDSSpec`
- [ ] Implement compilation using `compile_model()` → `GDSSpec` and `compile_to_system()` → `SystemIR`
- [ ] Implement domain verification checks (pluggable `Callable[[DomainModel], list[Finding]]`)
- [ ] Optional: delegate to G-001..G-006 via `compile_to_system()` + `verify()`
- [ ] Validate canonical projection (parametric invariant tests recommended)
- [ ] Add cross-built equivalence tests (DSL-compiled vs hand-built GDSSpec)
- [ ] Add per-package `CLAUDE.md` documenting architecture
- [ ] Add tests covering compilation, verification, and projection

### Release Gates

Before the first external release of a new DSL:

- [ ] All tests pass (domain + GDS generic checks via projection)
- [ ] Lint clean (`ruff check`)
- [ ] Architecture document updated with the filled-out semantic layer contract
- [ ] At least one worked example model in `gds-examples`
- [ ] API docs generated via mkdocstrings
- [ ] Independent PyPI publishing via tag-based workflow

## Potential Future DSLs

These formalisms are in-scope per the [architecture scope boundary](../framework/guide/architecture.md#5-scope-boundary) and should compile to the existing substrate without architectural changes:

| Formalism | Expected Mapping | Complexity |
|---|---|---|
| Signal processing | Blocks = filters/transforms, `>>` = pipeline, `\|` = multichannel | Low |
| Compartmental models | Blocks = compartments/transfers, similar to stockflow | Low |
| Queueing networks | Blocks = queues/servers, `>>` = routing, `\|` = parallel servers | Medium |
| Bayesian networks | Blocks = conditional distributions, `>>` = dependency chain | Medium |
| Reinforcement learning | Blocks = agent/environment, follows convergent composition pattern | Medium |

If a candidate DSL cannot compile to `GDSSpec` without modifying canonical or the role system, that is a signal that the scope boundary has been reached — not that the architecture needs extension.

## Layer Interaction Rules

From the architecture document — these are non-negotiable:

- Layer 0 must not import Layer 1 or Layer 2
- Layer 1 may depend on Layer 0
- Layer 2 may depend on Layer 1
- Layer 3 (models) depends on Layer 2
- Layer 4 (views) may depend on any lower layer but must not modify them
- Architectural acyclicity is required

## Open Research Directions

See [Research Boundaries and Open Questions](research-boundaries.md) for detailed analysis of:

1. **MIMO semantics** — scalar ports vs vector-valued spaces
2. **Timestep semantics** — what `.loop()` means across DSLs when execution is introduced
