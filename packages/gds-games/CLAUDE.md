# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gds-games` — typed DSL for compositional game theory, built on `gds-framework`. Published as `gds-games`, imported as `ogs`.

## Commands

```bash
uv sync                                    # Install deps
uv run pytest tests/ -v                    # Run all tests
uv run pytest tests/test_dsl.py -v         # Single test file
uv run pytest tests/test_dsl.py::TestDecisionGame::test_basic -v  # Single test
```

## Architecture

### Layered Architecture

```
GDS Framework  ←  core engine (generic blocks, IR, verification)
    ↑
OGS (this pkg) ←  game-theory DSL extension
    ↑
Domain packages ←  applications using OGS patterns
```

**GDS (dependency):** Provides Block, Interface, Port, composition operators (`>>`, `|`, `.feedback()`, `.loop()`), compiler (flatten → wire → hierarchy), token-based type matching, generic IR models (`BlockIR`, `WiringIR`, `SystemIR`, `HierarchyNodeIR`), and generic verification (G-001..G-006). Installed as a PyPI dependency.

**OGS (this package):** Adds the game-theoretic DSL on top:
- `OpenGame(Block)` — abstract base mapping Signature(x,y,r,s) to Interface(forward_in/out, backward_in/out)
- 6 atomic game types with port-constraint validators
- Domain enums in `ogs/dsl/types.py`: `GameType`, `FlowType`, `CompositionType`, `InputType`
- Metadata models in `ogs/dsl/pattern.py`: `TerminalCondition`, `ActionSpace`, `StateInitialization`
- `Pattern` — groups games + flows + metadata
- `compile_to_ir()` — flatten patterns into `PatternIR` (JSON-serializable)
- `PatternIR.to_system_ir()` — projects to GDS `SystemIR` for generic verification and tooling interop
- `HierarchyNodeIR` — extends GDS `HierarchyNodeIR` with `CORECURSIVE` composition type
- 13 verification checks (T-001..T-006 type, S-001..S-007 structural), plus optional GDS check delegation via `verify(pattern, include_gds_checks=True)`
- 7 Markdown report generators via Jinja2 templates
- 6 Mermaid diagram generators for visualization

### Package Layout

```
ogs/
├── __init__.py          # Public API: verify, generate_reports, save_ir, load_ir, IR models
├── cli.py               # Typer CLI: compile, verify, report
├── dsl/                 # Core domain DSL (canonical definitions)
│   ├── types.py         # Signature(Interface), domain enums (GameType, FlowType, CompositionType, InputType)
│   ├── errors.py        # DSLError, DSLTypeError, DSLCompositionError
│   ├── base.py          # OpenGame(Block) abstract base
│   ├── games.py         # 6 atomic game types
│   ├── composition.py   # Flow + Sequential, Parallel, Feedback, Corecursive
│   ├── pattern.py       # Pattern, PatternInput, TerminalCondition, ActionSpace, StateInit
│   ├── compile.py       # compile_to_ir() — DSL tree → PatternIR
│   └── library.py       # Reusable factories (reactive_decision_agent, etc.)
├── ir/                  # Intermediate representation (extends GDS IR)
│   ├── __init__.py      # Architecture docs, re-exports all IR types
│   ├── models.py        # OpenGameIR, FlowIR, PatternIR(.to_system_ir()), HierarchyNodeIR(GDS)
│   └── serialization.py # IRDocument, save_ir(), load_ir()
├── verification/        # 13 pluggable checks + optional GDS check delegation
│   ├── tokens.py        # Re-exports from gds.types.tokens
│   ├── findings.py      # VerificationReport with pattern_name alias
│   ├── engine.py        # verify(include_gds_checks=) + ALL_CHECKS registry
│   ├── type_checks.py   # T-001..T-006
│   ├── structural_checks.py  # S-001..S-007
│   └── diagnostic.py    # Mermaid diagnostic diagram
├── viz.py               # 6 Mermaid diagram generators (see below)
└── reports/             # Markdown report generation
    ├── mermaid.py       # Flowchart + sequence diagram generators
    ├── generator.py     # 6 generators + generate_reports()
    ├── domain_analysis.py  # Cross-domain flow detection, coupling metrics, interaction matrix
    └── templates/       # 7 Jinja2 .md.j2 templates
```

### Visualization (`ogs/viz.py`)

Six Mermaid diagram generators, all take `PatternIR` and return `str`:

- `structural_to_mermaid` — full game topology with all flows
- `architecture_by_role_to_mermaid` — grouped by GameType (decision, function, etc.)
- `architecture_by_domain_to_mermaid` — grouped by domain tag
- `hierarchy_to_mermaid` — composition tree (sequential/parallel/feedback nesting)
- `flow_topology_to_mermaid` — covariant flows only
- `terminal_conditions_to_mermaid` — state transition diagram
- `generate_all_views` → `dict[str, str]` — all 6 views at once

### Key Types

- `Signature(Interface)` — `@model_validator` maps `x/y/r/s` strings to `forward_in/forward_out/backward_in/backward_out` Port tuples
- `OpenGame(Block)` — adds `signature` property, operator overloads (`>>`, `|`), `.feedback()`, `.corecursive()`
- `Pattern` — container for games + flows + domain metadata, entry point for `compile_to_ir()`
- `PatternIR` / `OpenGameIR` / `FlowIR` — Pydantic models for the compiled IR
- `PatternIR.to_system_ir()` — projects OGS IR to GDS `SystemIR` for generic tooling interop
- `HierarchyNodeIR(gds.HierarchyNodeIR)` — extends GDS hierarchy with CORECURSIVE composition; `game_name` property aliases `block_name`

### IR Layering

Domain enums and metadata models are canonically defined in the DSL layer and re-exported by `ogs/ir/models.py` for backwards compatibility:

- Enums: `ogs.dsl.types` → `ogs.ir.models` (re-export)
- Metadata: `ogs.dsl.pattern.TerminalCondition` → `ogs.ir.models.TerminalConditionIR` (alias)
- Hierarchy: `gds.ir.models.HierarchyNodeIR` → `ogs.ir.models.HierarchyNodeIR` (subclass)
- Projection: `ogs.ir.models.PatternIR.to_system_ir()` → `gds.ir.models.SystemIR`

### Compilation Pipeline

```
Pattern(games, flows)
  → compile_to_ir()
    → flatten games into AtomicBlocks
    → walk explicit flows + auto-wire sequential chains
    → extract hierarchy tree
    → flatten sequential chains in hierarchy
  → IRDocument(patterns=[PatternIR(...)], metadata=IRMetadata(...))
```

## Conventions

- All models are **Pydantic v2 BaseModel** — not dataclasses
- `@model_validator(mode="after")` returning `Self` for construction-time validation
- **Absolute imports only** — `from ogs.dsl.types import Signature`, never relative
- **String enums** (`str, Enum`) for JSON serialization (GameType, FlowType, CompositionType)
- Custom exceptions inherit from `DSLError` base (which wraps `GDSError`)
- `Field(default_factory=list)` for mutable defaults
- Token-based type matching via `gds.types.tokens` — ports auto-tokenize on `+`
- Verification checks are `Callable[[IRDocument], list[Finding]]` — pluggable via `ALL_CHECKS`
- Jinja2 templates use `trim_blocks=True` and `lstrip_blocks=True` — avoid `-%}` that strips blank lines markdown needs between block elements

## Key GDS Imports

- `gds.blocks.base.Block`, `gds.blocks.base.AtomicBlock` — base classes
- `gds.types.ports.Port`, `gds.types.interfaces.Interface` — type system
- `gds.types.tokens.tokenize`, `tokens_overlap`, `tokens_subset` — matching
- `gds.ir.models.FlowDirection`, `gds.ir.models.SystemIR`, `gds.ir.models.HierarchyNodeIR` — IR types
- `gds.ir.models.BlockIR`, `gds.ir.models.WiringIR` — used by `PatternIR.to_system_ir()`
- `gds.verification.findings.Finding`, `Severity` — verification output
- `gds.verification.engine.ALL_CHECKS` — GDS generic checks (used by `verify(include_gds_checks=True)`)
