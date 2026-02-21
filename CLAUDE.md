# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-core` — monorepo for the Generalized Dynamical Systems ecosystem. Typed compositional specifications for complex systems, grounded in [GDS theory](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc). Four packages managed as a uv workspace.

## Packages

| Package | Import | Location |
|---------|--------|----------|
| gds-framework | `gds` | `packages/gds-framework/` |
| gds-viz | `gds_viz` | `packages/gds-viz/` |
| gds-games | `ogs` | `packages/gds-games/` |
| gds-examples | — | `packages/gds-examples/` |

## Commands

```bash
# Install all packages (workspace-linked)
uv sync --all-packages

# Run tests per-package
uv run --package gds-framework pytest packages/gds-framework/tests -v
uv run --package gds-viz pytest packages/gds-viz/tests -v
uv run --package gds-games pytest packages/gds-games/tests -v
uv run --package gds-examples pytest packages/gds-examples -v

# Run a single test
uv run --package gds-framework pytest packages/gds-framework/tests/test_blocks.py::TestStackComposition::test_rshift_operator -v

# Run all tests
uv run --package gds-framework pytest packages/gds-framework/tests packages/gds-viz/tests packages/gds-games/tests packages/gds-examples -v

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
gds-framework  ←  core engine (no GDS dependencies)
    ↑
gds-viz        ←  visualization (depends on gds-framework)
gds-games      ←  game theory DSL (depends on gds-framework)
    ↑
gds-examples   ←  tutorials (depends on gds-framework + gds-viz)
```

### gds-framework: Two-Layer Design

**Layer 1 — Composition Algebra** (`blocks/`, `compiler/`, `ir/`, `verification/generic_checks.py`):
Domain-neutral engine. Blocks with bidirectional typed interfaces, composed via four operators (`>>`, `|`, `.feedback()`, `.loop()`). A 3-stage compiler flattens composition trees into flat IR (blocks + wirings + hierarchy). Six generic verification checks (G-001..G-006) validate structural properties on the IR.

**Layer 2 — Specification Framework** (`spec.py`, `canonical.py`, `state.py`, `spaces.py`, `types/`):
Where GDS theory lives. `GDSSpec` is the central registry for types, spaces, entities, blocks, wirings, and parameters. `project_canonical()` derives the formal `h = f ∘ g` decomposition. Seven semantic checks (SC-001..SC-007) validate domain properties on the spec.

These layers are loosely coupled — you can use the composition algebra without `GDSSpec`, and `GDSSpec` does not depend on the compiler.

### Two Type Systems

These coexist at different levels:

1. **Token-based** (`types/tokens.py`) — structural set matching at composition/wiring time. Port names auto-tokenize (split on spaces, lowercase → frozenset). The `>>` operator and auto-wiring use token overlap for matching. `"Heater Command"` auto-wires to `"Command Signal"` because they share the token `"command"`.

2. **TypeDef-based** (`types/typedef.py`) — runtime validation at the data level. TypeDef wraps a Python type + optional constraint predicate. Used by Spaces and Entities to validate actual data values. Never called during compilation.

### Compilation Pipeline

```
Block tree  →  flatten()  →  list[AtomicBlock]  →  block_compiler()  →  list[BlockIR]
            →  _walk_wirings()  →  list[WiringIR]  (explicit + auto-wired)
            →  _extract_hierarchy()  →  HierarchyNodeIR tree
            =  SystemIR(blocks, wirings, hierarchy)
```

### How gds-games Extends gds-framework

`gds-games` subclasses `AtomicBlock` as `OpenGame`, adding a `Signature(Interface)` that maps game theory's `(X, Y, R, S)` to GDS's `(forward_in, forward_out, backward_in, backward_out)`. It adds 6 atomic game types, a `Pattern` container (analogous to `GDSSpec`), its own compiler (`compile_to_ir()` → `PatternIR`), and 13 OGS-specific verification checks.

The critical interop bridge is `PatternIR.to_system_ir()` — projects OGS IR to GDS `SystemIR`, enabling reuse of all 6 generic GDS verification checks without duplication. OGS also adds `CorecursiveLoop` (`.corecursive()`), which maps to GDS `TemporalLoop` at the IR level.

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
- **Semantic checks (SC-001..SC-007)** operate on `GDSSpec` — domain properties (completeness, determinism, reachability, type safety, parameter references, canonical wellformedness)

### Key Conventions

- All data models are Pydantic v2 `BaseModel` — frozen for value objects, mutable for registries
- `@model_validator(mode="after")` returning `Self` for construction-time invariant enforcement
- Absolute imports only (never relative)
- `TYPE_CHECKING` guard in `blocks/base.py` to break circular dependency with `blocks/composition.py`
- Ruff config at root: line-length 88, rules `E, W, F, I, UP, B, SIM, TCH, RUF`
- Tags (`Tagged` mixin) are inert — stripped at compile time, never affect verification
- Parameters (Θ) are structural metadata — GDS never assigns values or binds them
- `GDSSpec.collect()` type-dispatches TypeDef/Space/Entity/Block/ParameterDef; SpecWiring stays explicit via `register_wiring()`
- Each package published independently to PyPI via tag-based workflow (`gds-framework/v0.3.1`)
- Per-package CLAUDE.md files contain package-specific architecture details
