> [!NOTE]
> **ARCHIVED**: The improvements outlined in this document (Phase 0 and Phase 1) were successfully implemented and merged in release v0.2.0-Alpha. This document is preserved for historical and architectural reference.

# gds-framework: Stabilization, Expansion & Publication Plan

---

## 1. Philosophy & Vision

### 1.1 What this package represents

`gds-framework` is the software crystallization of a line of research that stretches back decades and across multiple projects:

- **Roxin (1960s)** formalized Generalized Dynamical Systems — the idea that state transitions can be composed over arbitrary data structures, not just vector spaces.
- **Zargham & Shorish (2022)** extended this into "Block Diagrams for Categorical Cybernetics" — showing that blocks with typed ports, composed via wiring, are a universal language for specifying socio-technical systems. The composed wiring *is* the transition function h.
- **BlockScience's MSML** (888 commits, 58 files) implemented this as a JSON-spec-first tool with cadCAD integration. It got the domain decomposition right (BoundaryAction, Policy, Mechanism, ControlAction) and proved that parameter crawling, Obsidian reports, and transmission channels are genuinely useful. MSML was designed as an end-to-end pipeline from specification through rendering to simulation — a different goal than ours, which led to natural design choices (JSON-first authoring, integrated rendering, a central `MathSpec` coordinator) that served that use case well.
- **BDP-lib** (Block Diagram Protocol) introduced a clean 2x2 framework of Abstract/Concrete x Structure/Behavior (Space, Wire, Block, Processor) — an elegant architecture for general-purpose block diagrams. BDP was designed to be language-agnostic and domain-neutral, which is valuable for its intended purpose. Our needs are more specific: we require domain-aware primitives (state entities, parameters, GDS block roles) and semantic validation that go beyond structural checks.
- **Categorical cybernetics** (Ghani, Hedges et al.) added a critical dimension that neither MSML nor BDP addressed: **bidirectional flow**. Systems where information flows both forward (observations, decisions) and backward (utility, cost, reward). This insight — that composition must handle contravariant feedback, not just covariant data flow — generalizes to any system with feedback loops, reward signals, or backward induction.

`gds-framework` is the synthesis. It takes:
- **BDP's architecture** — clean layered separation, abstract/concrete distinction
- **MSML's domain knowledge** — block roles, state entities, parameter tracking, typed spaces
- **Categorical cybernetics' bidirectional composition** — forward + backward flow, feedback loops, temporal iteration
- **Our own additions** — token-based structural typing, flat IR compilation, pluggable verification, composition hierarchy for visualization

And packages it as a single, dependency-light Python library that anyone can `pip install` and use to build a compositional specification for *their* domain — token engineering, control systems, supply chains, multi-agent coordination, mechanism design.

### 1.2 The layered ecosystem

`gds-framework` is designed as a **foundation layer**. It provides domain-neutral primitives. Domain-specific packages import from `gds` and add their own block types, wiring conventions, verification rules, and presentation layers:

```
gds-framework (pip install gds-framework)
│
│  The foundation. Domain-neutral composition algebra,
│  typed spaces, state model, verification engine.
│  Published on PyPI. Zero domain-specific concepts.
│
├── Domain Package A (e.g. token engineering)
│   └── Adds: bonding curves, token flows, AMM mechanisms
│
├── Domain Package B (e.g. control systems)
│   └── Adds: controllers, plants, sensors, stability checks
│
├── Domain Package C (e.g. multi-agent systems)
│   └── Adds: agents, environments, negotiation protocols
│
└── Domain Package D (e.g. mechanism design)
    └── Adds: incentive structures, equilibrium checks
```

Each domain package is a thin layer. The heavy lifting — composition, compilation, verification, querying — lives in `gds-framework`.

### 1.3 Design principles

1. **Python-first, JSON-optional** — Users define specs in Python with real types and IDE autocomplete. JSON serialization is an export format, not the authoring format. (A different trade-off from MSML's language-agnostic JSON-first approach, optimized for the Python developer workflow.)

2. **Types that bite** — `TypeDef` carries runtime constraints, not just labels. `Space.validate()` actually checks data against its schema. Errors are caught at spec-time, before simulation.

3. **Spec ≠ Rendering ≠ Execution** — `gds-framework` is ONLY types, blocks, composition, verification, and querying. No Mermaid, no cadCAD, no Obsidian. Those become separate packages that consume a `GDSSpec` or `SystemIR`. (Where MSML chose to integrate these for end-to-end convenience, we separate them for composability.)

4. **Composition is first-class** — Four operators (`>>`, `|`, `.feedback()`, `.loop()`) are built into the Block class. Composition validates types at construction time, not after the fact. (Extending BDP's structural composition with type-level validation.)

5. **Bidirectional by default** — Every block has four port slots: `forward_in`, `forward_out`, `backward_in`, `backward_out`. Domains that don't need backward flow leave those slots empty. This generalizes to any system with feedback, reward signals, or cost propagation. (Drawing from categorical cybernetics, extending both MSML's and BDP's forward-only models.)

6. **Verification ladder** — Level 1: structural (wiring topology, dangling references). Level 2: type-flow (token matching across wires). Level 3: semantic (completeness, determinism, reachability). Each level builds on the last.

---

## 2. Architecture

### 2.1 Current state (composition algebra only)

The package today contains the composition algebra — the mathematical plumbing:

```
gds/                              (~1,200 LOC, 17 files)
├── types/                         Port, Interface, tokenize, tokens_subset
├── blocks/                        Block, AtomicBlock, StackComposition, ParallelComposition,
│                                  FeedbackLoop, TemporalLoop, Wiring, errors
├── compiler/                      compile_system() — flatten → wire → hierarchy
├── ir/                            BlockIR, WiringIR, SystemIR, HierarchyNodeIR, serialization
└── verification/                  6 generic checks (G-001..G-006), verify(), Finding, Report
```

This is solid but only tells half the story. It's the *engine*, not the *framework*. It says "here's how blocks compose" but not "here's what a dynamical system *is*."

### 2.2 What's missing (the specification layer)

The deepdive document (`gds_deepdive.md`) identifies the concepts that connect this package to the GDS/MSML intellectual tradition:

| Concept | GDS Math | What it does | Status |
|---|---|---|---|
| **TypeDef** | Type structure | Runtime-constrained types (not just labels) | Missing |
| **Space** | Action spaces | Typed product spaces that validate data | Missing |
| **Entity + StateVariable** | X (state space) | Persistent state decomposed into typed components | Missing |
| **Block roles** | Components of h | BoundaryAction, Policy, Mechanism, ControlAction | Missing |
| **GDSSpec** | {h, X} | Central registry that ties types, spaces, entities, blocks, wirings together | Missing |
| **SpecVerifier** | GDS properties | Completeness, determinism, reachability, admissibility | Missing |
| **SpecQuery** | Dependency analysis | Parameter crawling, impact analysis, dependency graphs | Missing |

### 2.3 Target architecture

```
gds/
├── types/                         EXISTING — token system + ports + interfaces
│   ├── tokens.py                  tokenize, tokens_subset, tokens_overlap
│   ├── interface.py               Port, Interface, port()
│   └── typedef.py                 NEW — TypeDef with runtime constraints, built-in types
│
├── spaces.py                      NEW — Space (typed product), EMPTY, TERMINAL sentinels
│
├── state.py                       NEW — Entity, StateVariable
│
├── blocks/                        EXISTING + EXPANDED
│   ├── base.py                    Block, AtomicBlock (unchanged)
│   ├── composition.py             StackComposition, ParallelComposition, etc. (unchanged)
│   ├── roles.py                   NEW — BoundaryAction, Policy, Mechanism, ControlAction
│   └── errors.py                  GDSError, GDSTypeError, GDSCompositionError (unchanged)
│
├── compiler/                      EXISTING (unchanged)
│   └── compile.py                 compile_system()
│
├── ir/                            EXISTING (unchanged)
│   ├── models.py                  BlockIR, WiringIR, SystemIR, HierarchyNodeIR
│   └── serialization.py           IRDocument, save_ir, load_ir
│
├── spec.py                        NEW — GDSSpec registry (types, spaces, entities, blocks, wirings, params)
│
├── verification/                  EXISTING + EXPANDED
│   ├── engine.py                  verify() orchestrator (unchanged)
│   ├── generic_checks.py          G-001..G-006 structural checks (unchanged)
│   ├── findings.py                Finding, Severity, VerificationReport (unchanged)
│   └── spec_checks.py             NEW — completeness, determinism, reachability, admissibility
│
├── query.py                       NEW — SpecQuery (param crawling, dependency graph, impact analysis)
│
└── serialize.py                   NEW — spec_to_dict, spec_to_json for GDSSpec
```

### 2.4 Key reconciliation: bidirectional > unidirectional

The deepdive's Block model is unidirectional: `domain → codomain`. Our current Block model is bidirectional: `forward_in/out + backward_in/out`. These are not in conflict — our model is the **generalization**:

| Deepdive concept | Maps to our Interface |
|---|---|
| `domain` | `forward_in` |
| `codomain` | `forward_out` |
| *(not modeled)* | `backward_in` (utility, cost, reward signals) |
| *(not modeled)* | `backward_out` (coutility, experience signals) |

Domains that don't need backward flow (pure MSML mechanisms, control systems without cost signals) simply leave `backward_in` and `backward_out` empty. The block role subclasses enforce this:

- `Mechanism` — always has `backward_out = ()` and `backward_in = ()` (state-writing, no signal passing)
- `BoundaryAction` — always has `forward_in = ()` (exogenous input, nothing feeds it from inside)
- `Policy` and `ControlAction` — can use all four slots

### 2.5 Key reconciliation: two type systems coexisting

The package has two complementary type systems:

1. **Token-based structural matching** (existing) — Port names auto-tokenize; `tokens_subset()` checks set containment. Used by the composition algebra and compiler for auto-wiring and verification checks G-001/G-005. This is lightweight, flexible, and doesn't require users to pre-define types.

2. **TypeDef with runtime constraints** (new, from deepdive) — Named types with `python_type` and `constraint` callable. Used by Spaces to validate actual data. This is strict, explicit, and catches value-level errors.

They operate at different levels. Token matching checks structural compatibility at the wiring level ("can these ports connect?"). TypeDef validation checks value correctness at the data level ("is this a valid probability?"). Both are needed.

---

## 3. Implementation plan

### Phase 0: Expand — Add specification layer (from deepdive)

#### 0.1 Create `gds/types/typedef.py` — Runtime-constrained types

From deepdive Section 4.1. Pydantic BaseModel with:
- `name: str`, `python_type: type`, `description: str`, `constraint: Callable | None`, `units: str | None`
- `.validate(value) -> bool` method
- Built-in types: `Probability`, `NonNegativeFloat`, `PositiveInt`, `TokenAmount`, `AgentID`, `Timestamp`

Note: Unlike deepdive's plain class, ours is a Pydantic model (consistent with rest of package). Constraint functions are not serializable — this is by design.

#### 0.2 Create `gds/spaces.py` — Typed product spaces

From deepdive Section 4.2. Pydantic BaseModel with:
- `name: str`, `schema: dict[str, TypeDef]`, `description: str`
- `.validate(data: dict) -> list[str]` — checks fields against schema
- `.is_compatible(other: Space) -> bool` — structural equality check
- Sentinels: `EMPTY` (no data flows), `TERMINAL` (state write, signal terminates)

#### 0.3 Create `gds/state.py` — Entity and state variables

From deepdive Section 4.4. Two Pydantic models:
- `StateVariable` — `name`, `typedef: TypeDef`, `description`, `symbol`; `.validate(value) -> bool`
- `Entity` — `name`, `variables: dict[str, StateVariable]`, `description`; `.validate_state(data) -> list[str]`

These model the GDS state space X as a product of entity states.

#### 0.4 Create `gds/blocks/roles.py` — GDS block roles

From deepdive Section 4.3, adapted to our Block/AtomicBlock hierarchy as Pydantic models:
- `BoundaryAction(AtomicBlock)` — exogenous input (GDS admissible inputs U). `kind = "boundary"`. Enforces `forward_in = ()`. Has `options: list[str]`.
- `ControlAction(AtomicBlock)` — endogenous control. `kind = "control"`. Has `options: list[str]`.
- `Policy(AtomicBlock)` — decision logic. `kind = "policy"`. Has `options: list[str]`.
- `Mechanism(AtomicBlock)` — state update (only thing that writes state). `kind = "mechanism"`. Has `updates: list[tuple[str, str]]` (entity_name, variable_name). Enforces `backward_in = ()`, `backward_out = ()`.

These subclass our existing `AtomicBlock`, inheriting composition operators and `flatten()`.

#### 0.5 Create `gds/spec.py` — GDS specification registry

From deepdive Section 4.6. The GDSSpec is the `{h, X}` pair:
- Registration methods: `register_type()`, `register_space()`, `register_entity()`, `register_block()`, `register_wiring()`, `register_parameter()` — all chainable, all assert uniqueness.
- `.validate() -> list[str]` — structural validation:
  - Space types are registered
  - Block spaces are registered
  - Wiring compatibility
  - Mechanism update targets exist
  - Parameter references valid

GDSSpec is focused: registration and structural validation only. Rendering, simulation, and export are separate concerns handled by downstream packages.

#### 0.6 Create `gds/verification/spec_checks.py` — Semantic verification

From deepdive Section 4.7. Functions that take a `GDSSpec` and return `list[Finding]`:
- `check_completeness()` — every entity variable is updated by at least one mechanism (no orphan state)
- `check_determinism()` — within each wiring, no two mechanisms update the same variable (write conflict detection)
- `check_reachability(from_block, to_block)` — can signals reach from A to B through wiring? (GDS attainability)
- `check_admissibility(wiring_name)` — all blocks in a wiring have their domain requirements satisfied
- `check_type_safety()` — every wire's space matches source codomain and target domain at the field level

#### 0.7 Create `gds/query.py` — Dependency analysis

From deepdive Section 4.8:
- `SpecQuery(spec)` with methods:
  - `param_to_blocks()` — which blocks use each parameter
  - `block_to_params()` — which parameters each block uses
  - `entity_update_map()` — entity → variable → list of mechanisms
  - `dependency_graph()` — block adjacency from wiring
  - `blocks_by_kind()` — group blocks by GDS role
  - `blocks_affecting(entity, variable)` — transitive impact analysis (generalizing the parameter crawling concept from MSML)

#### 0.8 Create `gds/serialize.py` — Spec serialization

From deepdive Section 4.9:
- `spec_to_dict(spec: GDSSpec) -> dict` — full spec to plain dict
- `spec_to_json(spec: GDSSpec, indent=2) -> str` — to JSON string

Note: constraint functions are not serializable. JSON is an interchange format, not the source of truth. This is by design and should be documented.

---

### Phase 1: Stabilize — Tests for everything

Tests live in `tests/` and import ONLY from `gds`. Two groups: tests for the existing composition algebra, and tests for the new specification layer.

#### 1.1 `tests/conftest.py` — Shared fixtures

Fixtures for both layers:
- **Composition fixtures**: `block_a`, `block_b`, `block_c`, `block_sensor`, `block_controller`, `block_plant`, `sample_system_ir`, `thermostat_system_ir`
- **Spec fixtures**: `typedef_probability`, `space_signal`, `entity_agent`, `sample_mechanism`, `sample_spec`

#### 1.2 `tests/test_types.py` (~25 tests)

Existing type system:
- `TestTokenize` — empty, single, comma-sep, plus-sep, mixed, whitespace, case normalization
- `TestTokensSubset` — exact match, subset of compound, whole-token-only rejection, vacuous truth
- `TestTokensOverlap` — shared token, disjoint, empty strings
- `TestPort` — `port()` factory, auto-tokenization, frozen, equality, hashable
- `TestInterface` — empty default, with ports, frozen, equality

New TypeDef:
- `TestTypeDef` — creation, validate passes/fails, constraint enforcement, units, equality, hash
- `TestBuiltInTypes` — Probability rejects >1 and <0, NonNegativeFloat rejects negatives, PositiveInt rejects 0

#### 1.3 `tests/test_spaces.py` (~15 tests)

- `TestSpace` — creation, validate with valid/invalid/missing/extra fields, is_compatible
- `TestSentinels` — EMPTY has empty schema, TERMINAL has empty schema
- `TestSpaceEquality` — by name, hashable

#### 1.4 `tests/test_state.py` (~12 tests)

- `TestStateVariable` — creation, validate passes/fails, typedef reference
- `TestEntity` — creation, validate_state with valid/missing/invalid data, variable lookup

#### 1.5 `tests/test_blocks.py` (~30 tests)

Existing composition:
- `TestAtomicBlock` — creation, flatten, interface
- `TestStackComposition` — `>>` operator, type mismatch error, explicit wiring bypass, flatten order, chaining, interface union
- `TestParallelComposition` — `|` operator, flatten, interface union
- `TestFeedbackLoop` — `.feedback()`, interface preserved, flatten
- `TestTemporalLoop` — `.loop()`, contravariant rejection, exit_condition
- `TestWiring` — creation, default direction, frozen

New block roles:
- `TestBoundaryAction` — creation, kind="boundary", forward_in enforced empty
- `TestPolicy` — creation, kind="policy", options preserved
- `TestMechanism` — creation, kind="mechanism", updates list, backward ports enforced empty
- `TestControlAction` — creation, kind="control", options preserved
- `TestRoleComposition` — boundary >> policy >> mechanism composes correctly

#### 1.6 `tests/test_ir.py` (~20 tests)

- `TestBlockIR`, `TestWiringIR`, `TestHierarchyNodeIR`, `TestSystemIR` — construction, defaults, JSON round-trip
- `TestIRDocument` — creation, round-trip
- `TestSaveLoadIR` — `save_ir`/`load_ir` with `tmp_path`

#### 1.7 `tests/test_compiler.py` (~25 tests)

- `TestCompileSystemBasic` — single block, two stacked, names preserved
- `TestAutoWiring` — matching tokens, direction, no auto-wire with explicit
- `TestExplicitWiring` — stack, feedback is_feedback, temporal is_temporal
- `TestDefaultBlockCompiler` — signature from interface
- `TestCustomBlockCompiler` — callback invoked
- `TestHierarchyExtraction` — leaf, sequential/parallel/feedback/temporal groups, chain flattening

#### 1.8 `tests/test_verification.py` (~25 tests)

Existing generic checks:
- `TestG001` through `TestG006` — each with pass/fail/skip cases

#### 1.9 `tests/test_spec.py` (~20 tests)

- `TestGDSSpecRegistration` — register type/space/entity/block/wiring/param; duplicate assertion
- `TestGDSSpecValidation` — unregistered space type, unregistered block space, invalid mechanism update, invalid param reference, wiring compatibility
- `TestGDSSpecChaining` — `spec.register_type(t).register_space(s)` chainable

#### 1.10 `tests/test_spec_checks.py` (~20 tests)

- `TestCompleteness` — orphan variable detected, all-updated passes
- `TestDeterminism` — write conflict detected, non-overlapping passes
- `TestReachability` — reachable returns True, unreachable returns False
- `TestTypeSafety` — schema mismatch detected, matching passes

#### 1.11 `tests/test_query.py` (~15 tests)

- `TestParamMapping` — param_to_blocks, block_to_params
- `TestEntityUpdateMap` — correct mechanism → entity → variable mapping
- `TestDependencyGraph` — correct adjacency from wiring
- `TestBlocksByKind` — groups by role correctly
- `TestBlocksAffecting` — transitive impact analysis

#### 1.12 Update `gds/__init__.py` — Top-level re-exports

Add `__version__ = "0.1.0"` and re-export all public symbols. The import surface should tell the GDS story:

```python
from gds import (
    # The composition algebra
    Block, AtomicBlock, Interface, Port, port,
    StackComposition, ParallelComposition, FeedbackLoop, TemporalLoop,
    Wiring, compile_system,

    # The type system
    TypeDef, Probability, NonNegativeFloat, PositiveInt, TokenAmount,
    tokenize, tokens_subset, tokens_overlap,

    # Typed spaces and state
    Space, EMPTY, TERMINAL,
    Entity, StateVariable,

    # GDS block roles (from MSML decomposition)
    BoundaryAction, Policy, Mechanism, ControlAction,

    # The specification object — {h, X}
    GDSSpec,

    # Verification and querying
    verify, Finding, Severity, VerificationReport,
    SpecQuery,

    # IR and serialization
    SystemIR, BlockIR, WiringIR, HierarchyNodeIR,
    IRDocument, save_ir, load_ir,
    spec_to_dict, spec_to_json,
)
```

---

### Phase 2: Package for PyPI

#### 2.1 Update `pyproject.toml`

```toml
[project]
name = "gds-framework"
version = "0.1.0"
description = "Generalized Dynamical Systems — typed compositional specifications for complex systems"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.12"
authors = [
    { name = "BlockScience" },
]
keywords = [
    "generalized-dynamical-systems", "compositional-systems",
    "block-diagram", "categorical-cybernetics",
    "dsl", "type-system", "verification",
    "msml", "cadcad",
    "system-specification", "mechanism-design",
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Mathematics",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
dependencies = ["pydantic>=2.10"]

[project.urls]
Homepage = "https://github.com/BlockScience/gds-framework"
Repository = "https://github.com/BlockScience/gds-framework"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["gds"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = ["pytest>=9.0"]
```

#### 2.2 Create `README.md`

Structure:
1. **Headline** — "Generalized Dynamical Systems — typed compositional specifications for complex systems"
2. **What is GDS?** — One paragraph connecting Roxin → Zargham/Shorish → block diagram representation
3. **What this package provides** — Bullet list: composition algebra, typed spaces, state model, block roles, verification ladder, query engine
4. **Install** — `pip install gds-framework`
5. **Quick start: Predator-Prey** — The example from deepdive Section 5
6. **Quick start: Thermostat** — Control systems example demonstrating bidirectional flow
7. **Core concepts table** — GDS Math → Software Concept → Python Class (from deepdive Section 1.4)
8. **Building domain DSLs** — How domain packages extend `gds` with their own block types and checks
9. **Intellectual lineage** — Section citing GDS theory, MSML, BDP-lib, categorical cybernetics
10. **License** — Apache-2.0

#### 2.3 Create `LICENSE` — Apache-2.0

---

## 4. Verification checklist

1. `uv run pytest tests/ -v` — all ~210 GDS tests pass
2. `uv build` — wheel builds without errors
3. `uv run python -c "import gds; print(gds.__version__)"` — prints `0.1.0`
4. `uv run python -c "from gds import GDSSpec, Entity, Mechanism, verify"` — spec layer imports work
5. `uv run python -c "from gds import Block, compile_system"` — composition algebra imports work
6. Predator-Prey example from README runs without errors

---

## 5. Files summary

### New files to create

| File | Purpose | Source |
|---|---|---|
| `gds/types/typedef.py` | TypeDef with runtime constraints + built-in types | Deepdive 4.1 |
| `gds/spaces.py` | Typed product spaces, EMPTY/TERMINAL sentinels | Deepdive 4.2 |
| `gds/state.py` | Entity, StateVariable | Deepdive 4.4 |
| `gds/blocks/roles.py` | BoundaryAction, Policy, Mechanism, ControlAction | Deepdive 4.3 |
| `gds/spec.py` | GDSSpec registry | Deepdive 4.6 |
| `gds/verification/spec_checks.py` | Completeness, determinism, reachability | Deepdive 4.7 |
| `gds/query.py` | SpecQuery — param crawling, dependency graph | Deepdive 4.8 |
| `gds/serialize.py` | spec_to_dict, spec_to_json | Deepdive 4.9 |
| `tests/__init__.py` | Empty (pytest discovery) | — |
| `tests/conftest.py` | Shared fixtures for both layers | — |
| `tests/test_types.py` | Tokens + Port + Interface + TypeDef | — |
| `tests/test_spaces.py` | Space validation | — |
| `tests/test_state.py` | Entity + StateVariable | — |
| `tests/test_blocks.py` | Composition operators + block roles | — |
| `tests/test_ir.py` | IR models + serialization | — |
| `tests/test_compiler.py` | Compiler + auto-wiring + hierarchy | — |
| `tests/test_verification.py` | G-001..G-006 structural checks | — |
| `tests/test_spec.py` | GDSSpec registration + validation | — |
| `tests/test_spec_checks.py` | Semantic verification checks | — |
| `tests/test_query.py` | SpecQuery methods | — |
| `LICENSE` | Apache-2.0 | — |

### Files to modify

| File | Change |
|---|---|
| `gds/__init__.py` | Add `__version__`, re-export all public symbols |
| `gds/types/__init__.py` | Add TypeDef and built-in types to `__all__` |
| `gds/blocks/__init__.py` | Add roles to `__all__` |
| `gds/verification/__init__.py` | Add spec_checks to `__all__` |
| `pyproject.toml` | Full PyPI metadata |
| `README.md` | Expand with full content |

### Unchanged (existing composition algebra)

| File | Status |
|---|---|
| `gds/blocks/base.py` | Unchanged |
| `gds/blocks/composition.py` | Unchanged |
| `gds/blocks/errors.py` | Unchanged |
| `gds/compiler/compile.py` | Unchanged |
| `gds/ir/models.py` | Unchanged |
| `gds/ir/serialization.py` | Unchanged |
| `gds/types/tokens.py` | Unchanged |
| `gds/types/interface.py` | Unchanged |
| `gds/verification/engine.py` | Unchanged |
| `gds/verification/generic_checks.py` | Unchanged |
| `gds/verification/findings.py` | Unchanged |

### Expected test count: ~210 new tests

| Test file | Approx. count |
|---|---|
| `test_types.py` | 25 |
| `test_spaces.py` | 15 |
| `test_state.py` | 12 |
| `test_blocks.py` | 30 |
| `test_ir.py` | 20 |
| `test_compiler.py` | 25 |
| `test_verification.py` | 25 |
| `test_spec.py` | 20 |
| `test_spec_checks.py` | 20 |
| `test_query.py` | 15 |
| **Total** | **~207** |
