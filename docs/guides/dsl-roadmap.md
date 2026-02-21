# DSL Roadmap

## Current Status

Layer 0 (Composition Core) is stable and sealed. The architecture document is fully aligned with the codebase. Two semantic interpretations are implemented:

- **GDS semantics** — dynamical systems (`gds/spec.py`, `gds/canonical.py`)
- **OGS semantics** — compositional game theory (`ogs/dsl/`)

## Immediate Next Step: `gds-stockflow`

Stock-flow diagrams are a natural fit for the composition algebra and a high-value DSL target. Key mappings:

| Stock-Flow Concept | GDS Mapping |
|---|---|
| Stock | Entity with accumulation StateVariable |
| Flow | Mechanism block (state update) |
| Auxiliary | Policy block (derived computation) |
| Converter | BoundaryAction (exogenous input) |
| Rate equation | `>>` composition: auxiliary feeds flow |
| Accumulation | `.loop()` — stock at t+1 = stock at t + net flow |

## DSL Contract Checklist

Every new DSL must answer the [Semantic Layer Contract](../architecture.md#4-the-semantic-layer-contract) — eight questions that fully specify how a domain maps onto the composition algebra:

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

- [ ] Subclass `AtomicBlock` with domain-specific block types
- [ ] Define domain IR models (extending or wrapping `BlockIR`, `WiringIR`)
- [ ] Implement compilation using `flatten_blocks` and `extract_wirings` with domain callbacks
- [ ] Implement `to_system_ir()` projection for GDS tooling interop
- [ ] Define domain verification checks (pluggable `Callable[[DomainIR], list[Finding]]`)
- [ ] Optional: delegate to G-001..G-006 via `to_system_ir()` + `verify()`
- [ ] Define canonical projection (if applicable)
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

## Layer Interaction Rules

From the architecture document — these are non-negotiable:

- Layer 0 must not import Layer 1 or Layer 2
- Layer 1 may depend on Layer 0
- Layer 2 may depend on Layer 1
- Layer 3 (models) depends on Layer 2
- Layer 4 (views) may depend on any lower layer but must not modify them
- Architectural acyclicity is required
