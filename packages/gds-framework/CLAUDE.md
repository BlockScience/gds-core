# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-framework` — typed compositional specifications for complex systems, grounded in Generalized Dynamical Systems theory. Published on PyPI as `gds-framework`, imported as `gds`.

## Commands

```bash
uv sync                                    # Install dependencies
uv run pytest tests/ -v                    # Run all 336 tests
uv run pytest tests/test_blocks.py -v      # Single test file
uv run pytest tests/test_blocks.py::TestStackComposition::test_rshift_operator -v  # Single test
uv build                                   # Build wheel (gds_framework-*.whl)
uv run python -c "import gds; print(gds.__version__)"  # Verify install
```

## Architecture

### Two-Layer Design

**Layer 1 — Composition Algebra** (the engine):
Blocks with bidirectional typed interfaces, composed via four operators (`>>`, `|`, `.feedback()`, `.loop()`). A 3-stage compiler flattens composition trees into flat IR (blocks + wirings + hierarchy). Six generic verification checks (G-001..G-006) validate structural properties on the IR.

**Layer 2 — Specification Layer** (the framework):
TypeDef with runtime constraints, typed Spaces, Entities with StateVariables, Block roles (BoundaryAction/Policy/Mechanism/ControlAction), GDSSpec registry, ParameterSchema (Θ), canonical projection (CanonicalGDS), Tagged mixin, semantic verification (SC-001..SC-007), SpecQuery for dependency analysis, and JSON serialization.

### Two Type Systems

These coexist at different levels and serve different purposes:

1. **Token-based** (`types/tokens.py`) — lightweight structural matching at composition/wiring time. Port names auto-tokenize; `tokens_subset()` and `tokens_overlap()` check set containment. Used by composition validators, auto-wiring, and G-001/G-005 checks.

2. **TypeDef-based** (`types/typedef.py`) — rich runtime validation at the data level. TypeDef wraps a Python type + optional constraint predicate. Used by Spaces and Entities to validate actual data values.

### Compilation Pipeline

```
Block tree  →  flatten()  →  list[AtomicBlock]  →  block_compiler()  →  list[BlockIR]
            →  _walk_wirings()  →  list[WiringIR]  (explicit + auto-wired)
            →  _extract_hierarchy()  →  HierarchyNodeIR tree  →  _flatten_sequential_chains()
            =  SystemIR(blocks, wirings, hierarchy)
```

Auto-wiring for `>>` matches `forward_out` ports to `forward_in` ports by token overlap. Feedback marks `is_feedback=True`; temporal marks `is_temporal=True`.

### Block Hierarchy

The composition algebra is **sealed** — only 5 concrete Block types exist:
- `AtomicBlock` — leaf node (domain packages subclass this, never the composition operators)
- `StackComposition` (`>>`) — sequential, validates token overlap
- `ParallelComposition` (`|`) — independent, no type validation
- `FeedbackLoop` (`.feedback()`) — backward within timestep
- `TemporalLoop` (`.loop()`) — forward across timesteps, enforces COVARIANT only

Block roles (`BoundaryAction`, `Policy`, `Mechanism`, `ControlAction`) subclass `AtomicBlock` and add constraints: BoundaryAction enforces `forward_in=()`, Mechanism enforces `backward_in=()` and `backward_out=()`.

### Verification

Pluggable: `verify(system, checks=None)` runs check functions against SystemIR. Each check is `Callable[[SystemIR], list[Finding]]`. Generic checks (G-001..G-006) validate IR topology. Semantic checks (SC-001..SC-007) validate GDSSpec properties (completeness, determinism, reachability, type safety, parameter references, canonical wellformedness).

### Parameter System

`ParameterDef` + `ParameterSchema` define the configuration space Θ at the specification level. Parameters are structural metadata — GDS does not assign values or bind them. `GDSSpec.parameter_schema` holds the registry; blocks reference parameters via `params_used: list[str]`.

### Canonical Projection

`project_canonical(spec: GDSSpec) → CanonicalGDS` is a pure function that derives the formal GDS decomposition: X (state), U (input), D (decision), Θ (parameters), g (policy), f (mechanism). Operates on GDSSpec (not SystemIR) because SystemIR is flat and lacks role/entity info.

### Tagged Mixin

`Tagged` is a BaseModel mixin providing `tags: dict[str, str]` with `with_tag()`, `with_tags()`, `has_tag()`, `get_tag()`. Applied to Block, Entity, GDSSpec. Tags are inert — stripped at compile time (BlockIR/SystemIR have no tags field), never affect verification or composition.

## Key Conventions

- **All data models are Pydantic v2 `BaseModel`** — not dataclasses, not plain classes
- **Frozen models** for value objects: Port, Interface, Wiring, Space, TypeDef, StateVariable, Wire, SpecWiring
- **`@model_validator(mode="after")` returning `Self`** for construction-time validation (composition operators, role constraints)
- **`ConfigDict(arbitrary_types_allowed=True)`** on models storing `type` or `Callable` fields (TypeDef, Space, StateVariable, GDSSpec)
- **Absolute imports only** — always `from gds.blocks.base import ...`, never relative
- **`TYPE_CHECKING` guard** in `blocks/base.py` to break circular dependency with `blocks/composition.py`
- **`Field(default_factory=list)`** for mutable defaults, never bare `[]`
- **`@property`** for computed attributes on models, not `computed_field()`
- **String enums** (`str, Enum`) for JSON-friendly serialization (FlowDirection, CompositionType, Severity)
- **Custom exceptions** inherit from `GDSError` base: `GDSTypeError` for port mismatches, `GDSCompositionError` for structural constraint violations
- All public symbols re-exported through `gds/__init__.py` with explicit `__all__`
- Package name on PyPI is `gds-framework`, import name is `gds` (mapped via `[tool.hatch.build.targets.wheel] packages = ["gds"]`)

## Intellectual Lineage

The design synthesizes: GDS theory (Roxin; Zargham & Shorish), MSML (BlockScience), BDP-lib, and categorical cybernetics (Ghani, Hedges). See `docs/gds_deepdive.md` for the full analysis and `docs/gds_improvement_plan.md` for the roadmap.
