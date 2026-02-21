# View Stratification After Canonical Integration

## Context

With `compile_pattern_to_spec()` proven across three DSLs, we now have three
distinct representations of a composed system. Each carries information at a
different abstraction level. Views (reports, visualizations, dashboards)
should consume from the representation that is authoritative for their concern.

## The Three Representations

```
Domain Model (Pattern, StockFlowModel, ControlModel)
 ├─ compile_to_ir()              → Domain IR        → domain vocabulary
 ├─ compile_*_to_spec()          → GDSSpec           → semantic classification
 │                                 └─ project_canonical() → CanonicalGDS
 └─ compile_to_system()          → SystemIR          → structural topology
```

| Representation | Abstraction Level | Authoritative For |
|---|---|---|
| **Domain IR** (PatternIR, etc.) | Domain-specific | Domain vocabulary: game types, signatures, flow types, stock/flow semantics, control matrices, action spaces, terminal conditions, domain tags |
| **GDSSpec / CanonicalGDS** | Semantic (GDS theory) | Role classification (Policy/Mechanism/BoundaryAction), state variables, canonical decomposition h = f ∘ g, update map, decision/input ports |
| **SystemIR** | Structural (topology) | Block graph, wiring connections, hierarchy tree, composition operators |

## Authority Rules

### CanonicalGDS is the semantic authority

`project_canonical()` is a derivation, not a projection. When it classifies a
block as Policy, that is a structural consequence of the block's interface and
role type. Domain-level classifications (game_type, flow_type, stock vs auxiliary)
are refinements within canonical categories, not alternatives to them.

The relationship is **refinement**:

```
CanonicalGDS:  "This is a Policy block"            ← universal (GDS layer)
Domain IR:     "This is a DecisionGame(X,Y,R,S)"   ← domain-specific (OGS layer)
               "This is an Auxiliary computing net flow" ← domain-specific (StockFlow layer)
               "This is a Sensor reading plant state"   ← domain-specific (Control layer)
```

Every DecisionGame is a Policy. Every Auxiliary is a Policy. Every Sensor is a
Policy. Not every Policy is a DecisionGame. Domain IRs refine within canonical
categories.

### What must never be inferred from domain IRs

- MSML role classification (Policy / Mechanism / BoundaryAction / ControlAction)
- State variable identification
- The canonical decomposition (which blocks are in f vs g)
- The update map (which mechanisms update which state variables)

These are GDS-layer semantics. Deriving them from domain-specific type enums
(game_type, element kind, etc.) is a layer violation: it reimplements
`project_canonical()` ad-hoc and can drift from the authoritative source.

### What must always come from domain IRs

Each DSL's IR carries vocabulary that has no GDS counterpart:

- **OGS**: `game_type`, `signature (X,Y,R,S)`, `flow_type`, `terminal_conditions`, `action_spaces`, `initialization`, `is_corecursive`, domain `tags`
- **StockFlow**: stock/flow/auxiliary distinctions, accumulation semantics, flow equations
- **Control**: plant/sensor/controller structure, state-space matrices (A,B,C,D when present)

These fields are the domain's analytical vocabulary. They exist only in domain
IRs and are invisible to GDSSpec and SystemIR.

### What should come from SystemIR

- Block-to-block wiring graph
- Hierarchy tree (composition nesting)
- Composition type at each hierarchy node
- Feedback and temporal loop detection

SystemIR is the structural truth. Domain IRs may carry a projection
(e.g., `PatternIR.to_system_ir()`), but views that only need topology
should consume SystemIR directly.

## View Classification by Source

Views built on domain models naturally fall into categories by data source:

| View Concern | Authoritative Source | Examples |
|---|---|---|
| Domain semantics | Domain IR | Game signatures, flow types, stock/flow diagrams, action spaces, terminal conditions |
| Role classification (MSML) | CanonicalGDS | Policy/Mechanism/BoundaryAction partitioning, state variables, update map |
| Structural topology | SystemIR | Hierarchy tree, wiring graph, composition operators, feedback detection |
| Formal verification | SystemIR + Domain IR | Generic checks (G-001..G-006) on SystemIR; domain checks on domain IR |
| Cross-domain analysis | Domain IR (tags) | Domain coupling matrices, cross-domain flow detection |

The key migration target: any view that currently infers MSML roles from
domain-specific type enums should be refactored to read from `CanonicalGDS`.

## Invariant

No view should ever re-derive what `project_canonical()` computes.

If a view needs to know whether a block is a Policy or a Mechanism, it asks
`CanonicalGDS`. If it needs to know whether a Policy is specifically a
DecisionGame, it asks the domain IR. If it needs to know what that block
connects to, it asks SystemIR.

Three sources. Three concerns. No overlap in authority.

## Architectural Guard Rails

### Canonical is analytical, not executable

`CanonicalGDS` is a structural projection. It tells you the decomposition
`h = f ∘ g` — which blocks observe/decide (g) and which update state (f).

It does not encode:

- Temporal ordering (which block evaluates first)
- Scheduling semantics (synchronous vs staged)
- Constraint satisfaction (feasibility of transitions)
- Composition topology (which specific wires connect blocks)

If downstream tools (simulation, formal verification exports) depend on
canonical, they must augment it with execution semantics from the domain
layer. Canonical alone is insufficient for execution. This boundary must
remain explicit to avoid the illusion that `h = f ∘ g` is a runnable program.

See [RQ2 (timestep semantics)](research-boundaries.md#research-question-2-what-does-a-timestep-mean-across-dsls)
and [RQ4 (cross-lens analysis)](research-boundaries.md#research-question-4-cross-lens-analysis-when-equilibrium-and-reachability-disagree).

### Semantic enrichment must remain opt-in

The three-source architecture creates pressure to enrich representations:
add fields to GDSSpec for game vocabulary, add fields to domain IRs for
canonical results, add fields to SystemIR for domain metadata.

Resist this. Each representation should carry exactly what it is authoritative
for and no more. The principle:

> Structural composition is mandatory. Semantic enrichment is opt-in.

If a view needs data from two sources, it should receive two arguments — not
a merged super-representation that conflates concerns.

### Domain IRs are not being demoted

This stratification does not reduce the role of domain IRs. It clarifies them.
Domain IRs are the authoritative source for domain-specific vocabulary — the
only place where game-theoretic signatures, stock-flow accumulation semantics,
or control-theoretic state-space structure exist. Removing or collapsing them
would destroy domain semantics that no other representation carries.

The change is: stop asking domain IRs questions they shouldn't answer (role
classification), and start asking them questions only they can answer (domain
semantics).
