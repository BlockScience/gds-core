# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-stockflow` — declarative stock-flow DSL over GDS semantics. Published as `gds-stockflow`, imported as `stockflow`. System dynamics with formal guarantees.

## Commands

```bash
uv sync                                    # Install deps
uv run pytest tests/ -v                    # Run all tests
uv run pytest tests/test_compile.py -v     # Single test file
```

## Architecture

### DSL over GDS (not a parallel semantic engine)

```
StockFlowModel (user-facing declarations)
       │
       ▼  compile_model()
GDSSpec (entities, blocks, wirings, parameters)
       │
       ▼  compile_to_system()
SystemIR (flat IR for verification + visualization)
```

No parallel IR stack. No domain IR models. GDS IR is the IR. The compiler produces a real `GDSSpec` with real GDS role blocks, entities, and wirings. All downstream GDS tooling works immediately — canonical projection, semantic checks, SpecQuery, serialization, gds-viz.

### Element → GDS Mapping

| Declaration | GDS Block Role | GDS Concept | Port Space |
|---|---|---|---|
| `Converter` | `BoundaryAction` (forward_in=()) | Exogenous input U | SignalSpace |
| `Auxiliary` | `Policy` | Decision logic g | SignalSpace |
| `Flow` | `Policy` (no forward_in) | Rate computation g | RateSpace |
| `Stock` | `Mechanism` + `Entity` | State update f + State X | LevelSpace |

### Semantic Type System

Three distinct semantic spaces, all float-backed but structurally separate:

- **LevelType / LevelSpace** — stock accumulation levels (non-negative by default)
- **RateType / RateSpace** — flow rates of change
- **SignalType / SignalSpace** — auxiliary/converter signal values

Plus **UnconstrainedLevelType / UnconstrainedLevelSpace** for stocks with `non_negative=False`.

### Composition Tree

```
(converters |) >> (auxiliaries |) >> (flows |) >> (stock_mechanisms |)
    .loop([stock forward_out → auxiliary forward_in])
```

Within each tier: parallel (`|`). Across tiers: sequential (`>>`) with explicit inter-tier wirings to avoid false token overlap failures. Empty tiers skipped. Wrapped in `.loop()` for temporal recurrence — stock levels at t feed auxiliaries at t+1.

**Key design choice:** Flow blocks have no `forward_in` ports. Source stock levels arrive via the temporal loop to auxiliaries, not to flows directly. This avoids composition-time token overlap issues while preserving the structural dependency in the model declaration.

Inter-tier wirings use explicit `StackComposition(wiring=[...])` where auto-wiring token overlap doesn't hold, and fall back to `>>` auto-wiring where it does (converter→auxiliary, flow→mechanism).

### Port Naming Convention

- Converter → `"{Name} Signal"`
- Auxiliary → in: `"{InputName} Level"` or `"{InputName} Signal"`, out: `"{Name} Signal"`
- Flow → out: `"{Name} Rate"`
- Stock mechanism → in: `"{FlowName} Rate"`, out: `"{Name} Level"`

### Package Layout

```
stockflow/
├── __init__.py           # Public API + __all__
├── dsl/
│   ├── types.py          # ElementType enum
│   ├── errors.py         # SFError, SFValidationError, SFCompilationError
│   ├── elements.py       # Stock, Flow, Auxiliary, Converter (frozen Pydantic)
│   ├── model.py          # StockFlowModel with construction-time validation
│   └── compile.py        # compile_model() → GDSSpec, compile_to_system() → SystemIR
└── verification/
    ├── engine.py          # verify() — SF checks + optional GDS checks
    └── checks.py          # SF-001..SF-005 on StockFlowModel
```

### Verification

| ID | Name | Severity | Validates |
|---|---|---|---|
| SF-001 | Orphan stocks | WARNING | Every stock has ≥1 connected flow |
| SF-002 | Flow-stock validity | ERROR | Flow source/target are declared stocks |
| SF-003 | Auxiliary acyclicity | ERROR | No cycles in auxiliary dependency graph |
| SF-004 | Converter connectivity | WARNING | Every converter referenced by ≥1 auxiliary |
| SF-005 | Flow completeness | ERROR | Every flow has at least one of source or target |

`verify(model)` runs SF checks on the model, then optionally compiles to SystemIR and runs GDS G-001..G-006. Some G-002 findings (no-input blocks) are expected for BoundaryActions and Flow policies.

## Conventions

- All models are **Pydantic v2 BaseModel** — frozen for value objects
- `@model_validator(mode="after")` returning `Self` for construction-time validation
- **Absolute imports only** — `from stockflow.dsl.types import ...`
- Custom exceptions inherit from `SFError(GDSError)`
- Verification checks are `Callable[[StockFlowModel], list[Finding]]`

## Key GDS Imports

- `gds.blocks.roles.BoundaryAction, Policy, Mechanism` — block roles
- `gds.spec.GDSSpec, SpecWiring, Wire` — specification registry
- `gds.state.Entity, StateVariable` — state modeling
- `gds.spaces.Space` — typed product spaces
- `gds.types.typedef.TypeDef` — constrained type definitions
- `gds.types.interface.Interface, Port, port` — block interfaces
- `gds.compiler.compile.compile_system` — composition tree → SystemIR
- `gds.blocks.composition.StackComposition, Wiring` — explicit composition
- `gds.canonical.project_canonical` — formal GDS decomposition
- `gds.verification.findings.Finding, Severity, VerificationReport` — verification output
