# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-core` — monorepo for the Generalized Dynamical Systems ecosystem. Typed compositional specifications for complex systems, grounded in [GDS theory](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc). Fourteen packages managed as a uv workspace.

## Packages

| Package | Import | Location | Role |
|---------|--------|----------|------|
| gds-framework | `gds` | `packages/gds-framework/` | Core engine |
| gds-viz | `gds_viz` | `packages/gds-viz/` | Mermaid + phase portraits |
| gds-games | `ogs` | `packages/gds-games/` | Game theory DSL |
| gds-stockflow | `stockflow` | `packages/gds-stockflow/` | Stock-flow DSL |
| gds-control | `gds_control` | `packages/gds-control/` | Control systems DSL |
| gds-software | `gds_software` | `packages/gds-software/` | Software architecture DSL |
| gds-business | `gds_business` | `packages/gds-business/` | Business dynamics DSL |
| gds-sim | `gds_sim` | `packages/gds-sim/` | Discrete-time simulation |
| gds-continuous | `gds_continuous` | `packages/gds-continuous/` | Continuous-time ODE engine |
| gds-symbolic | `gds_symbolic` | `packages/gds-symbolic/` | SymPy bridge for control |
| gds-analysis | `gds_analysis` | `packages/gds-analysis/` | Spec-to-sim bridge |
| gds-psuu | `gds_psuu` | `packages/gds-psuu/` | Parameter sweep + Optuna |
| gds-owl | `gds_owl` | `packages/gds-owl/` | OWL/SHACL/SPARQL export |
| gds-examples | — | `packages/gds-examples/` | Tutorials + examples |

## Commands

```bash
# Install all packages (workspace-linked)
uv sync --all-packages

# Run tests per-package
uv run --package gds-framework pytest packages/gds-framework/tests -v
uv run --package gds-viz pytest packages/gds-viz/tests -v
uv run --package gds-games pytest packages/gds-games/tests -v
uv run --package gds-stockflow pytest packages/gds-stockflow/tests -v
uv run --package gds-control pytest packages/gds-control/tests -v
uv run --package gds-software pytest packages/gds-software/tests -v
uv run --package gds-continuous pytest packages/gds-continuous/tests -v
uv run --package gds-symbolic pytest packages/gds-symbolic/tests -v
uv run --package gds-analysis pytest packages/gds-analysis/tests -v
uv run --package gds-sim pytest packages/gds-sim/tests -v
uv run --package gds-owl pytest packages/gds-owl/tests -v
uv run --package gds-examples pytest packages/gds-examples -v

# Run a single test
uv run --package gds-framework pytest packages/gds-framework/tests/test_blocks.py::TestStackComposition::test_rshift_operator -v

# Run all tests across all packages
uv run --package gds-framework pytest packages/gds-framework/tests packages/gds-viz/tests packages/gds-games/tests packages/gds-stockflow/tests packages/gds-control/tests packages/gds-software/tests packages/gds-continuous/tests packages/gds-symbolic/tests packages/gds-analysis/tests packages/gds-sim/tests packages/gds-owl/tests packages/gds-examples -v

# Lint & format
uv run ruff check packages/
uv run ruff format --check packages/

# Build a specific package
uv build --package gds-framework

# Docs
uv sync --all-packages --group docs
uv run mkdocs build --strict
uv run mkdocs serve
```

## Architecture

This is a **uv workspace** monorepo. The root `pyproject.toml` declares `packages/*` as workspace members. Each package has its own `pyproject.toml` with package-specific dependencies and build config. Shared tooling (ruff, docs) is configured at the root.

### Dependency Graph

```
gds-framework  ←  core engine (pydantic only, no upstream deps)
    ↑
    ├── gds-viz        ←  Mermaid diagrams + phase portraits [matplotlib]
    ├── gds-games      ←  game theory DSL + Nash equilibrium [nashpy]
    ├── gds-stockflow  ←  stock-flow DSL
    ├── gds-control    ←  control systems DSL
    ├── gds-software   ←  software architecture DSL
    ├── gds-business   ←  business dynamics DSL (CLD, SCN, VSM)
    └── gds-owl        ←  OWL/SHACL/SPARQL export (rdflib, pyshacl)
         ↑
    gds-symbolic       ←  SymPy bridge (extends gds-control) [sympy]
         ↑
    gds-examples       ←  tutorials (depends on most DSLs + viz)

gds-sim            ←  discrete-time simulation (standalone, pydantic only)
    ↑
    ├── gds-analysis   ←  spec→sim bridge, reachability (gds-framework + gds-sim + gds-continuous[opt])
    └── gds-psuu       ←  parameter sweep + Optuna (gds-sim)

gds-continuous     ←  continuous-time ODE engine (standalone, pydantic only) [scipy]
```

### gds-framework: Two-Layer Design

**Layer 0 — Composition Algebra** (`blocks/`, `compiler/`, `ir/`, `verification/generic_checks.py`):
Domain-neutral engine. Blocks with bidirectional typed interfaces, composed via four operators (`>>`, `|`, `.feedback()`, `.loop()`). A 3-stage compiler flattens composition trees into flat IR (blocks + wirings + hierarchy). Six generic verification checks (G-001..G-006) validate structural properties on the IR.

**Layer 1 — Specification Framework** (`spec.py`, `canonical.py`, `state.py`, `spaces.py`, `types/`):
Where GDS theory lives. `GDSSpec` is the central registry for types, spaces, entities, blocks, wirings, and parameters. `project_canonical()` derives the formal `h = f ∘ g` decomposition. Nine semantic checks (SC-001..SC-009) validate domain properties on the spec.

These layers are loosely coupled — you can use the composition algebra without `GDSSpec`, and `GDSSpec` does not depend on the compiler.

### Domain DSL Pattern

Five domain DSLs (stockflow, control, games, software, business) compile to GDS. The stockflow, control, software, and business packages follow a shared pattern:

1. **Elements** — frozen Pydantic models for user-facing declarations (not GDS blocks)
2. **Model** — mutable container with `@model_validator` construction-time validation
3. **Compiler** — two public functions:
   - `compile_model(model)` → `GDSSpec` (registers types, spaces, entities, blocks, wirings, parameters)
   - `compile_to_system(model)` → `SystemIR` (builds composition tree, delegates to `gds.compiler.compile.compile_system`)
4. **Verification** — domain-specific checks on the model, plus optional delegation to G-001..G-006 via SystemIR

All DSLs map to the same GDS roles: exogenous inputs → `BoundaryAction`, decision/observation logic → `Policy`, state updates → `Mechanism` + `Entity`. `ControlAction` is unused by DSL compilers (all non-state-updating blocks resolve to Policy). It is available for hand-built models as the output map y = C(x, d). See docs/framework/design/controller-plant-duality.md. Canonical `h = f ∘ g` holds cleanly for all three domains.

The composition tree follows a convergent tiered pattern:
```
(exogenous inputs | observers) >> (decision logic) >> (state dynamics)
    .loop(state dynamics → observers)
```

`gds-games` is more complex — it subclasses `AtomicBlock` as `OpenGame` with its own IR (`PatternIR`), but projects back to `SystemIR` via `PatternIR.to_system_ir()`.

### Two Type Systems

These coexist at different levels:

1. **Token-based** (`types/tokens.py`) — structural set matching at composition/wiring time. Port names auto-tokenize by splitting on ` + ` (space-plus-space) and `, ` (comma-space), then lowercasing each part. Plain spaces are NOT delimiters: `"Heater Command"` is one token `"heater command"`. The `>>` operator and auto-wiring use token overlap for matching. `"Temperature + Setpoint"` auto-wires to `"Temperature"` because they share the token `"temperature"`.

2. **TypeDef-based** (`types/typedef.py`) — runtime validation at the data level. TypeDef wraps a Python type + optional constraint predicate. Used by Spaces and Entities to validate actual data values. Never called during compilation.

### Compilation Pipeline

```
Block tree  →  flatten()  →  list[AtomicBlock]  →  block_compiler()  →  list[BlockIR]
            →  _walk_wirings()  →  list[WiringIR]  (explicit + auto-wired)
            →  _extract_hierarchy()  →  HierarchyNodeIR tree
            =  SystemIR(blocks, wirings, hierarchy)
```

Domain DSLs use explicit `StackComposition(wiring=[...])` between tiers where auto-wiring token overlap doesn't hold, falling back to `>>` auto-wiring where it does.

### Block Hierarchy (Sealed)

Only 5 concrete Block types exist — domain packages subclass `AtomicBlock` only, never the operators:
- `AtomicBlock` — leaf node
- `StackComposition` (`>>`) — sequential, validates token overlap
- `ParallelComposition` (`|`) — independent, no validation
- `FeedbackLoop` (`.feedback()`) — backward within timestep, CONTRAVARIANT
- `TemporalLoop` (`.loop()`) — forward across timesteps, COVARIANT only

Block roles (`BoundaryAction`, `Policy`, `Mechanism`, `ControlAction`) subclass `AtomicBlock` and enforce constraints at construction via `@model_validator`.

### Verification: Two Registries

Both use the pluggable pattern: `Callable[[T], list[Finding]]`.

- **Generic checks (G-001..G-006)** operate on `SystemIR` — structural topology only
- **Semantic checks (SC-001..SC-009)** operate on `GDSSpec` — domain properties (completeness, determinism, reachability, type safety, parameter references, canonical wellformedness, admissibility references, transition read consistency)
- **Domain checks** operate on domain models (e.g., `StockFlowModel`, `ControlModel`) — pre-compilation structural validation

### Branching Workflow

- **`main`** — stable release branch. Only receives merges from `dev`.
- **`dev`** — integration branch. All feature/fix PRs target `dev` first.
- Feature branches branch from `dev` and PR back to `dev`.
- When `dev` is stable and ready for release, merge `dev` → `main`.

### Key Conventions

- All data models are Pydantic v2 `BaseModel` — frozen for value objects, mutable for registries
- `@model_validator(mode="after")` returning `Self` for construction-time invariant enforcement
- Absolute imports only (never relative)
- `TYPE_CHECKING` guard in `blocks/base.py` to break circular dependency with `blocks/composition.py`
- Ruff config at root: line-length 88, rules `E, W, F, I, UP, B, SIM, TCH, RUF`
- Tags (`Tagged` mixin) are inert — stripped at compile time, never affect verification
- Parameters (Θ) are structural metadata — GDS never assigns values or binds them
- `GDSSpec.collect()` type-dispatches TypeDef/Space/Entity/Block/ParameterDef; SpecWiring stays explicit via `register_wiring()`
- **Versioning**: `__version__` in each package's `__init__.py` is the single source of truth — `pyproject.toml` reads it via `dynamic = ["version"]` + `[tool.hatch.version]`. When bumping a version, only edit `__init__.py`. When a package starts using a new gds-framework API, bump its `gds-framework>=` lower bound in the same change.
- Each package published independently to PyPI via tag-based workflow (`gds-framework/v0.3.1`)
- Per-package CLAUDE.md files contain package-specific architecture details
