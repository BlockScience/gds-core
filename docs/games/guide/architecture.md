# Architecture

## Layered Design

```
GDS Framework  ←  core engine (generic blocks, IR, verification)
    ↑
OGS (this pkg) ←  game-theory DSL extension
    ↑
Domain packages ←  applications using OGS patterns
```

**GDS (dependency):** Provides Block, Interface, Port, composition operators (`>>`, `|`, `.feedback()`, `.loop()`), compiler, token-based type matching, generic IR models, and generic verification (G-001..G-006).

**OGS (this package):** Adds the game-theoretic DSL on top:

- `OpenGame(Block)` — abstract base mapping `Signature(x,y,r,s)` to `Interface`
- 6 atomic game types with port-constraint validators
- `Pattern` — groups games + flows + metadata
- `compile_to_ir()` — flatten patterns into `PatternIR`
- `PatternIR.to_system_ir()` — project to GDS `SystemIR` for interop
- 13 verification checks (T-001..T-006, S-001..S-007)
- 7 Markdown report generators via Jinja2 templates
- 6 Mermaid diagram generators

## Compilation Pipeline

```
Pattern(games, flows)
  → compile_to_ir()
    → flatten games into AtomicBlocks
    → walk explicit flows + auto-wire sequential chains
    → extract hierarchy tree
    → flatten sequential chains in hierarchy
  → IRDocument(patterns=[PatternIR(...)], metadata=IRMetadata(...))
```

## IR Layering

Domain enums and metadata models are canonically defined in the DSL layer and re-exported by `ogs/ir/models.py`:

- Enums: `ogs.dsl.types` → `ogs.ir.models` (re-export)
- Hierarchy: `gds.ir.models.HierarchyNodeIR` → `ogs.ir.models.HierarchyNodeIR` (subclass with CORECURSIVE)
- Projection: `ogs.ir.models.PatternIR.to_system_ir()` → `gds.ir.models.SystemIR`
