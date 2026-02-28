# gds-software CLAUDE.md

Software architecture DSL over GDS. Six diagram types compiled to GDS specifications with 27 verification checks.

## Package

- **PyPI**: `gds-software`
- **Import**: `gds_software`
- **Depends on**: `gds-framework>=0.2.3`, `pydantic>=2.10`

## Diagram Types

| Subpackage | Model | Compiler | Checks |
|------------|-------|----------|--------|
| `dfd/` | `DFDModel` | `compile_dfd`, `compile_dfd_to_system` | DFD-001..005 |
| `statemachine/` | `StateMachineModel` | `compile_sm`, `compile_sm_to_system` | SM-001..006 |
| `component/` | `ComponentModel` | `compile_component`, `compile_component_to_system` | CP-001..004 |
| `c4/` | `C4Model` | `compile_c4`, `compile_c4_to_system` | C4-001..004 |
| `erd/` | `ERDModel` | `compile_erd`, `compile_erd_to_system` | ER-001..004 |
| `dependency/` | `DependencyModel` | `compile_dep`, `compile_dep_to_system` | DG-001..004 |

## Architecture

Each diagram type follows the standard DSL pattern:

1. `elements.py` — frozen Pydantic models for user-facing declarations
2. `model.py` — mutable container with `@model_validator` validation
3. `compile.py` — `compile_*()` → GDSSpec, `compile_*_to_system()` → SystemIR
4. `checks.py` — domain-specific checks returning `list[Finding]`

Shared utilities in `common/`:
- `compile_utils.py` — `parallel_tier()`, `build_inter_tier_wirings()`, `sequential_with_explicit_wiring()`
- `types.py` — `DiagramKind` enum
- `errors.py` — `SWError`, `SWValidationError`, `SWCompilationError`

Union-typed `verify()` in `verification/engine.py` dispatches by model type.

## GDS Role Mappings

- Exogenous inputs (ExternalEntity, Person, Event) → `BoundaryAction`
- Decision/observation logic (Process, Transition, Module, Component) → `Policy`
- State updates (DataStore, State, stateful containers) → `Mechanism` + `Entity`
- Connections (DataFlow, Connector, Dep, Relationship) → `Wiring`

## Composition Tree Patterns

All use tiered parallel-sequential with optional temporal loop:
```
(boundary |) >> (logic |) >> (state |) .loop([state → logic])
```

State machines additionally use `ParallelComposition` for orthogonal regions.

## Port Naming

- DFD: `"{Name} Signal"`, `"{Name} Data"`, `"{Name} Content"`
- SM: `"{Name} Event"`, `"{Name} State"`
- Component: `"{Interface} + Provided"`, `"{Interface} + Required"` (uses ` + ` delimiter for token overlap)
- C4: `"{Name} C4Port"`
- ERD: `"{Name} ERDPort"`
- Dependency: `"{Name} Module"`

## Commands

```bash
uv run --package gds-software pytest packages/gds-software/tests -v
uv run ruff check packages/gds-software/
uv run ruff format --check packages/gds-software/
```
