# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-control` — state-space control DSL over GDS semantics. Published as `gds-control`, imported as `gds_control`. Control theory with formal guarantees.

## Commands

```bash
uv sync                                    # Install deps
uv run pytest tests/ -v                    # Run all tests
uv run pytest tests/test_compile.py -v     # Single test file
```

## Architecture

### DSL over GDS (not a parallel semantic engine)

```
ControlModel (user-facing declarations)
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
| `Input` | `BoundaryAction` (forward_in=()) | Exogenous input U | ReferenceSpace |
| `Sensor` | `Policy` | Observation g | MeasurementSpace |
| `Controller` | `Policy` | Decision logic g | ControlSpace |
| `State` | `Mechanism` + `Entity` | State update f + State X | StateSpace |

**Key design decision:** All non-state-updating blocks use `Policy`. `ControlAction` is not used — it sits outside canonical `g`, which would break the `(A,B,C,D)` ↔ `(X,U,g,f)` mapping.

### Semantic Type System

Four distinct semantic spaces, all float-backed but structurally separate:

- **StateType / StateSpace** — plant state variables
- **ReferenceType / ReferenceSpace** — exogenous reference/disturbance signals
- **MeasurementType / MeasurementSpace** — sensor measurements
- **ControlType / ControlSpace** — controller outputs

### Composition Tree

```
(inputs | sensors) >> (controllers) >> (state_dynamics)
    .loop([state_dynamics forward_out → sensor forward_in])
```

Within each tier: parallel (`|`). Across tiers: sequential (`>>`) with explicit inter-tier wirings. Wrapped in `.loop()` for temporal recurrence — state outputs at t feed sensors at t+1.

### Port Naming Convention

- Input → `"{Name} Reference"`
- Sensor → in: `"{StateName} State"`, out: `"{Name} Measurement"`
- Controller → in: `"{ReadName} Measurement"` or `"{ReadName} Reference"`, out: `"{Name} Control"`
- State dynamics → in: `"{ControllerName} Control"`, out: `"{Name} State"`

### Package Layout

```
gds_control/
├── __init__.py           # Public API + __all__
├── dsl/
│   ├── types.py          # ElementType enum
│   ├── errors.py         # CSError, CSValidationError, CSCompilationError
│   ├── elements.py       # State, Input, Sensor, Controller (frozen Pydantic)
│   ├── model.py          # ControlModel with construction-time validation
│   └── compile.py        # compile_model() → GDSSpec, compile_to_system() → SystemIR
└── verification/
    ├── engine.py          # verify() — CS checks + optional GDS checks
    └── checks.py          # CS-001..CS-006 on ControlModel
```

### Verification

| ID | Name | Severity | Validates |
|---|---|---|---|
| CS-001 | Undriven states | WARNING | Every state driven by ≥1 controller |
| CS-002 | Unobserved states | WARNING | Every state observed by ≥1 sensor |
| CS-003 | Unused inputs | WARNING | Every input read by ≥1 controller |
| CS-004 | Controller read validity | ERROR | Controller reads reference declared sensors/inputs |
| CS-005 | Controller drive validity | ERROR | Controller drives reference declared states |
| CS-006 | Sensor observe validity | ERROR | Sensor observes reference declared states |

`verify(model)` runs CS checks on the model, then optionally compiles to SystemIR and runs GDS G-001..G-006.

## Conventions

- All models are **Pydantic v2 BaseModel** — frozen for value objects
- `@model_validator(mode="after")` returning `Self` for construction-time validation
- **Absolute imports only** — `from gds_control.dsl.types import ...`
- Custom exceptions inherit from `CSError(GDSError)`
- Verification checks are `Callable[[ControlModel], list[Finding]]`
