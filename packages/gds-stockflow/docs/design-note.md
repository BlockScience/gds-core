# StockFlow as a Structured GDSSpec Generator

*Internal design note — gds-stockflow architecture decisions*

## 1. Why a DSL over GDS, not a parallel engine

Stock-and-flow diagrams *are* dynamical systems. Stocks are state variables; flows are rates of change; auxiliaries compute intermediate signals; the whole thing iterates over time. This is not an analogy — the mapping from System Dynamics to the GDS formalism `h : X -> X` is structural identity.

Given that, building a separate simulation engine for stock-flow would mean reimplementing composition, verification, canonical projection, and IR serialization — all of which GDS already provides. Instead, `gds-stockflow` is a compiler: it translates the familiar stock-flow vocabulary into GDSSpec registrations and a composition tree. The user writes `Stock`, `Flow`, `Auxiliary`; the compiler emits `Entity`, `Policy`, `Mechanism`, `SpecWiring`. No new runtime semantics are introduced.

## 2. Why no parallel IR exists

GDS IR (`SystemIR`) is the IR. There is no `StockFlowIR`.

The compiler produces a composition tree of GDS blocks (`Policy`, `Mechanism`, `BoundaryAction`) wired together with `StackComposition`, `ParallelComposition`, and `TemporalLoop`. The GDS `compile_system()` function flattens this tree into `SystemIR` — the same flat representation used by `gds-games` (OGS), visualization, and all six generic verification checks.

This means every tool that operates on `SystemIR` works on stock-flow models immediately: Mermaid rendering, topological verification, hierarchy visualization. No adapters, no projection layers, no "compatibility mode." A single source of truth eliminates an entire class of synchronization bugs.

## 3. Why separate semantic spaces matter

All stock-flow quantities are backed by `float`. A naive implementation would use a single type for everything. Instead, the compiler defines three semantically distinct types and spaces:

| Type | Space | Role |
|------|-------|------|
| `LevelType` | `LevelSpace` | Stock accumulation values |
| `RateType` | `RateSpace` | Flow rates of change |
| `SignalType` | `SignalSpace` | Auxiliary/converter signals |

This separation is enforced at the port level through GDS token-based wiring. A `Rate` port cannot accidentally wire to a `Level` input — the tokens don't overlap. This catches structural errors (e.g., wiring a flow directly to another flow's input instead of through a mechanism) at composition time, before any simulation runs.

The `UnconstrainedLevelType` variant allows stocks that can go negative (e.g., financial balances), while the default `LevelType` carries a non-negativity constraint for physical quantities.

## 4. The composition tree design

The compiler builds a 4-tier parallel-sequential structure wrapped in a temporal loop:

```
(converters |) >> (auxiliaries |) >> (flows |) >> (mechanisms |)
    .loop([stock level -> auxiliary inputs])
```

Empty tiers are skipped. Within each tier, blocks compose in parallel (`|`). Across tiers, blocks compose sequentially (`>>`) with explicit inter-tier wirings where token overlap would produce false negatives.

**Flow blocks have no `forward_in` by design.** Source stock levels reach auxiliaries via the temporal loop (`.loop()` wiring from mechanism outputs back to auxiliary inputs at `t+1`). Flows are pure rate producers — their relationship to source/target stocks is captured structurally in the flow declaration and the mechanism's rate ports, not as a sequential data dependency. This avoids composition-time token overlap issues that would arise if flows received stock levels through the sequential tier.

**Mechanisms collect all relevant rate ports.** A stock mechanism's `forward_in` includes rate ports from every flow that sources or targets that stock. The mechanism accumulates these rates and emits the updated stock level via `forward_out`, which the temporal loop feeds back to the next timestep.

## 5. What this validates

Two non-trivial domain DSLs now compile to the same GDS IR substrate:

- **gds-games** (Open Game Semantics): game-theoretic models with `OpenGame` blocks, `Signature` interfaces mapping `(X, Y, R, S)` to GDS's bidirectional ports, corecursive loops, and 13 OGS-specific verification checks. Projection via `PatternIR.to_system_ir()`.

- **gds-stockflow** (System Dynamics): stock-flow diagrams with `Stock`, `Flow`, `Auxiliary`, `Converter` elements, level/rate/signal type separation, and 6 SF-specific verification checks. Projection via `compile_to_system()`.

The `test_cross_domain.py` suite provides concrete evidence: a predator-prey model built two ways — once through the StockFlowModel DSL, once by hand using raw GDS primitives — produces structurally identical results at three levels:

1. **GDSSpec**: same entities, blocks, port names, role types, and parameter schema
2. **CanonicalGDS**: same state variables, role classification, decision ports, and update map
3. **SystemIR**: same block count, wiring count, and temporal wiring source/target pairs

This is the validation that GDS is not merely a specification language for one domain, but a compositional substrate that faithfully represents the structural semantics of multiple modeling paradigms. The IR is shared; the tooling is shared; only the surface syntax differs.
