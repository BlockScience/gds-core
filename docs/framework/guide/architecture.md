# Architecture

## Two-Layer Design

### Layer 1 — Composition Algebra (the engine)

Blocks with bidirectional typed interfaces, composed via four operators (`>>`, `|`, `.feedback()`, `.loop()`). A 3-stage compiler flattens composition trees into flat IR (blocks + wirings + hierarchy). Six generic verification checks (G-001..G-006) validate structural properties on the IR.

### Layer 2 — Specification Layer (the framework)

TypeDef with runtime constraints, typed Spaces, Entities with StateVariables, Block roles (BoundaryAction/Policy/Mechanism/ControlAction), GDSSpec registry, ParameterSchema (Θ), canonical projection (CanonicalGDS), Tagged mixin, semantic verification (SC-001..SC-007), SpecQuery for dependency analysis, and JSON serialization.

### Why Two Layers?

Layer 0 is domain-neutral by design. It knows about blocks with typed ports, four composition operators, and structural topology — nothing about games, stocks, or controllers. This neutrality is what allows five different DSLs to compile to the same IR.

Domain judgment enters at Layer 1: when a modeler decides "this is a Mechanism, not a Policy" or "this variable is part of the system state." Layer 0 cannot make these decisions because they require knowledge of the problem being modeled. The three-stage compiler (flatten, wire, extract hierarchy) is pure algebra. The role annotations (BoundaryAction, Policy, Mechanism) are domain commitments.

This separation means Layer 0 specifications stay verifiable without knowing anything about the domain — they can be composed and checked formally. Layer 1 adds the meaning that makes a specification useful for a particular problem.

## Foundation + Domain Packages

```
gds-framework (pip install gds-framework)
│
│  Domain-neutral composition algebra, typed spaces,
│  state model, verification engine, flat IR compiler.
│  No domain-specific concepts. No simulation. No rendering.
│
├── Domain: Ecology
│   └── Predator-prey dynamics, population models, SIR epidemiology
│
├── Domain: Control Systems
│   └── Controllers, plants, sensors, stability/controllability checks
│
├── Domain: Game Theory
│   └── gds-games — open games DSL, iterated games, equilibrium analysis
│
└── Domain: Multi-Agent Systems
    └── Agent policies, environment dynamics, coordination protocols
```

Each domain package is a thin layer. The heavy lifting — composition, compilation, verification, querying — lives in `gds-framework`.

## Compilation Pipeline

The compiler is decomposed into three reusable stages, each exposed as a public function with generic callbacks:

```
flatten_blocks(root, block_compiler)  →  list[BlockIR]
extract_wirings(root, wiring_emitter) →  list[WiringIR]
extract_hierarchy(root)               →  HierarchyNodeIR

compile_system(name, root, ..., inputs=None) → SystemIR
  # Thin wrapper: calls the three stages + assembles SystemIR
```

Domain packages supply callbacks to produce their own IR types (e.g., OGS provides `_compile_game` → `OpenGameIR` and `_ogs_wiring_emitter` → `FlowIR`). Layer 0 owns traversal; Layer 1 owns vocabulary.

Auto-wiring for `>>` matches `forward_out` ports to `forward_in` ports by token overlap. Feedback marks `is_feedback=True`; temporal marks `is_temporal=True`.

`SystemIR.inputs` accepts `list[InputIR]` — typed external inputs with a `metadata` bag. Layer 0 never infers inputs; domain packages supply them via `compile_system(..., inputs=...)` or by populating them in their own compilation (e.g., OGS `compile_to_ir()`).

## Canonical Projection

`project_canonical(spec: GDSSpec) → CanonicalGDS` derives the formal GDS decomposition:

- **X** — state space (all Entity variables)
- **U** — input space (BoundaryAction outputs)
- **D** — decision space (Policy outputs)
- **Θ** — parameter space (ParameterSchema)
- **g** — policy map (BoundaryAction + Policy blocks)
- **f** — state update map (Mechanism blocks)

This operates on `GDSSpec` (not `SystemIR`) because SystemIR is flat and lacks role/entity info.
