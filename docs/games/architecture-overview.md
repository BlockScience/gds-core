# GDS Ecosystem Architecture

## The Three Layers

```
+------------------------------------------------------------------+
|                        CLIENT LAYER                               |
|  (Your application — the delivery layer)                           |
|                                                                   |
|  - Concrete pattern definitions (specifications)                  |
|  - Analysis notebooks and visualization                           |
|  - Runs verification, generates reports                           |
|  - Can fork DSL packages for custom needs                         |
+------------------------------------------------------------------+
         |  depends on gds-games  (which pulls in gds-framework)
         v
+------------------------------------------------------------------+
|                        DSL LAYER                                  |
|  (gds-games — game theory DSL)                              |
|  (future: msml-spec, cadcad-spec, etc.)                           |
|                                                                   |
|  - Domain-specific types and game vocabulary                      |
|  - Composition patterns, compilation to IR                        |
|  - Domain-specific verification checks                            |
|  - Mermaid visualization, Markdown reports                        |
|  - Projection back to GDS IR for generic tooling                  |
+------------------------------------------------------------------+
         |  depends on gds-framework
         v
+------------------------------------------------------------------+
|                      FRAMEWORK LAYER                              |
|  (gds-framework — the core engine)                                |
|                                                                   |
|  - Generic composition algebra (Block, >>, |, .feedback, .loop)   |
|  - Bidirectional type system (Port, Interface, tokens)            |
|  - IR data models (BlockIR, WiringIR, SystemIR, HierarchyNodeIR) |
|  - Compiler (flatten, wire, hierarchy extraction)                 |
|  - Generic verification checks (G-001 through G-006)             |
+------------------------------------------------------------------+
```

## Ownership and Delivery

All three packages are **developed by BlockScience**. During delivery:

- **GDS Framework** and **DSL packages** (like OGS) are made public and pip-installable
- **Client repos** are delivered to the client team who can:
  - Use DSL packages as-is
  - Fork a DSL to customize game types, checks, or reports
  - Build entirely new DSL packages on top of GDS

```
              BlockScience develops
              ┌─────────────────────────────────┐
              │  gds-framework     (open source) │
              │  gds-games   (open source) │
              │  client-app        (private)      │
              └─────────────────────────────────┘
                              │
                    delivery  │
                              v
              ┌─────────────────────────────────┐
              │  Client team receives:           │
              │                                  │
              │  pip install gds-games     │
              │  + their own repo with patterns  │
              │    notebooks, and analysis        │
              │                                  │
              │  Can fork OGS if needed.         │
              │  GDS stays stable underneath.    │
              └─────────────────────────────────┘
```

---

## What Each Layer Owns

### GDS Framework — `gds-framework`

The **core engine**. Domain-agnostic. Knows nothing about games, agents, or negotiation.

| Owns | Details |
|------|---------|
| **Composition algebra** | `Block`, `AtomicBlock`, `StackComposition`, `ParallelComposition`, `FeedbackLoop`, `TemporalLoop` |
| **Type system** | `Port`, `Interface`, token-based matching (`tokenize`, `tokens_overlap`, `tokens_subset`) |
| **IR models** | `BlockIR`, `WiringIR`, `HierarchyNodeIR`, `SystemIR` — the canonical flat representation |
| **Compiler** | `compile_system()` — flatten blocks, extract wirings, build hierarchy tree |
| **Generic verification** | 6 checks (G-001..G-006): type matching, completeness, direction consistency, dangling wires, acyclicity |
| **Specification layer** | `TypeDef`, `Space`, `Entity`, `GDSSpec`, `ParameterSchema`, `CanonicalGDS` |
| **Mixins** | `Tagged` — inert annotation tags for domain grouping |

**Does not own:** Any domain vocabulary. No game types, no flow semantics, no patterns.

### DSL Packages — e.g. `gds-games`

**Domain extensions** built on top of GDS. Each DSL is an independent package.

A DSL package:
- **Subclasses** `AtomicBlock` → domain-specific block types
- **Defines** domain enums (game types, flow types, etc.)
- **Extends** GDS IR with domain fields (OGS adds `game_type`, `constraints`, `tags`)
- **Compiles** DSL constructs → domain IR
- **Projects** domain IR → GDS `SystemIR` (enabling GDS generic checks)
- **Adds** domain-specific verification, visualization, and reports

**What OGS specifically owns:**

```
ogs/dsl/types.py      →  Domain enums: GameType, FlowType, CompositionType, InputType
ogs/dsl/base.py       →  OpenGame(Block) — abstract base with Signature(x,y,r,s)
ogs/dsl/games.py      →  6 atomic game types (Decision, CovariantFunction, etc.)
ogs/dsl/composition.py→  Flow, SequentialComposition, ParallelComposition, etc.
ogs/dsl/pattern.py    →  Pattern container + metadata models (TerminalCondition, etc.)
ogs/dsl/compile.py    →  compile_to_ir() — DSL tree → PatternIR
ogs/dsl/library.py    →  Reusable factories (reactive_decision_agent, etc.)
ogs/ir/models.py      →  OpenGameIR, FlowIR, PatternIR (with .to_system_ir())
                          HierarchyNodeIR (extends GDS HierarchyNodeIR)
ogs/verification/     →  13 domain checks (T-001..T-006, S-001..S-007)
ogs/viz.py            →  6 Mermaid diagram generators
ogs/reports/          →  7 Markdown report templates via Jinja2
ogs/cli.py            →  CLI: ogs compile, ogs verify, ogs report
```

**Does not own:** Concrete pattern definitions, analysis notebooks, application logic.

### Client Application

**Application layer**. Defines concrete specifications and runs analysis.

| Owns | Details |
|------|---------|
| **Pattern definitions** | Concrete game compositions (reactive_decision, bilateral_negotiation, multi_party_agreement, etc.) |
| **Notebooks** | Interactive marimo notebooks for stakeholders (system_specification, pattern_explorer, msml_components) |
| **Analysis scripts** | Verification runners, report generators, comparison tools |
| **Configuration** | Which patterns to verify, report output locations, etc. |

**Does not own:** The DSL itself, the framework, verification logic, or report templates.

---

## Where IR Fits

IR (Intermediate Representation) is the **contract between layers**.

```
  DSL Layer                          Framework Layer
  (domain-specific)                  (generic)

  ┌─────────────────────┐           ┌──────────────────────┐
  │  PatternIR           │           │  SystemIR             │
  │    games: OpenGameIR │ ────────> │    blocks: BlockIR    │
  │    flows: FlowIR     │  project  │    wirings: WiringIR  │
  │    + terminal conds  │           │    hierarchy          │
  │    + action spaces   │           │                       │
  │    + hierarchy (OGS) │           │                       │
  └─────────────────────┘           └──────────────────────┘
          ^                                   │
          │ compile_to_ir()                   │ GDS generic checks
          │                                   │ (G-001..G-006)
  ┌───────┴─────────────┐                    v
  │  Pattern             │           ┌──────────────────────┐
  │    game: OpenGame    │           │  VerificationReport   │
  │    inputs            │           └──────────────────────┘
  │    metadata          │
  └─────────────────────┘
```

**GDS owns** the IR concept — `BlockIR`, `WiringIR`, `SystemIR`, `HierarchyNodeIR`.

**DSL packages extend** with domain fields:
- `OpenGameIR` adds `game_type`, `constraints`, `tags` (not in `BlockIR`)
- `FlowIR` adds `flow_type`, `is_corecursive` (not in `WiringIR`)
- OGS `HierarchyNodeIR` subclasses GDS's, adding `CORECURSIVE` composition type

**DSL packages project back** via `to_system_ir()`:
- Maps `OpenGameIR` → `BlockIR`
- Maps `FlowIR` → `WiringIR`
- Maps `CORECURSIVE` → GDS `TEMPORAL`
- Enables GDS generic verification on any DSL's output

---

## Repo Structure After Separation

### Repo structure

```
BlockScience/gds-framework             ← public, on PyPI as gds-framework
BlockScience/gds-games            ← public, on PyPI as gds-games
                                         pure library: ogs/, tests/
                                         depends on gds-framework (PyPI)
client-app/                            ← private, delivered to client
                                         depends on gds-games (PyPI)
```

### Target: GDS Framework repo

```
gds-framework/
├── gds/                    # the package
├── tests/
├── docs/
├── pyproject.toml          # dependencies: pydantic>=2.10
└── README.md               # "pip install gds-framework"
```

### Target: Open Games Spec repo

```
gds-games/
├── ogs/                    # the package (dsl, ir, verification, viz, reports)
├── tests/                  # DSL unit tests + IR tests + verification tests
├── docs/
├── pyproject.toml          # dependencies: gds-framework>=0.1, pydantic, typer, jinja2
└── README.md               # "pip install gds-games"
```

No `examples/`, no `notebooks/` — those belong to the client.

### Target: Client application repo

```
client-app/
├── patterns/                       # the specifications
│   ├── reactive_decision.py        # Pattern definitions using OGS DSL
│   ├── bilateral_negotiation.py
│   └── multi_party_agreement.py
├── notebooks/                      # interactive analysis
├── reports/                        # generated output (gitignored)
├── tests/
│   └── test_patterns.py            # verify patterns compile + pass checks
├── pyproject.toml                  # dependencies: gds-games>=0.1
└── README.md
```

---

## Separation Steps

### Step 1: Publish GDS to PyPI

```bash
# In gds-framework repo
git tag v0.1.0
uv build                           # wheel already exists in dist/
uv publish                          # or: twine upload dist/*
```

Prerequisite: make the repo public (or use private PyPI index).

### Step 2: Decouple OGS from submodule

```bash
# In gds-games repo
git submodule deinit gds-framework
git rm gds-framework
rm -rf .gitmodules
```

Update `pyproject.toml`:
```toml
# Remove this:
[tool.uv.sources]
gds-framework = { path = "gds-framework", editable = true }

# The dependency line stays:
dependencies = ["gds-framework>=0.1", ...]
```

### Step 3: Move examples + notebooks to client repo

```bash
# Create client repo
mkdir -p client-app/{patterns,notebooks,tests}
mv gds-games/examples/*.py client-app/patterns/
mv gds-games/notebooks/*.py client-app/notebooks/
```

### Step 4: Publish OGS to PyPI

```bash
# In gds-games repo
git tag v0.1.0
uv build && uv publish
```

### Step 5: Verify client app works

```bash
# In client repo
uv init && uv add gds-games
uv run python patterns/reactive_decision.py     # should work
```

---

## Forkability

DSL packages are designed to be forkable by clients:

```
Option A: Use OGS as-is (recommended)
  pip install gds-games

Option B: Fork and extend
  1. Fork gds-games
  2. Add custom game types, checks, or reports
  3. Keep as private package or publish as your-games-spec
  4. Still depends on gds-framework (unchanged)

Option C: Build a new DSL from scratch
  1. pip install gds-framework
  2. Subclass AtomicBlock for your domain
  3. Build your own compiler, verification, reports
  4. GDS generic checks work automatically via SystemIR projection
```

The key guarantee: **GDS is stable infrastructure.** DSL packages can diverge, fork, or be replaced without affecting the core framework or each other.

---

## Package Summary

| Package | PyPI | Import | Layer | Visibility |
|---------|------|--------|-------|------------|
| GDS Framework | `gds-framework` | `gds` | Framework | Public (open source) |
| GDS Games | `gds-games` | `ogs` | DSL | Public (open source) |
| Client App | — | — | Client | Private (delivered to client) |
