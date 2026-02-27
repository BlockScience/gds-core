# GDS Ecosystem

**Typed compositional specifications for complex systems**, grounded in [Generalized Dynamical Systems](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) theory (Zargham & Shorish, 2022).

## Packages

| Package | PyPI | Description |
|---------|------|-------------|
| **[gds-framework](framework/index.md)** | `pip install gds-framework` | Core engine — blocks, composition algebra, compiler, verification |
| **[gds-viz](viz/index.md)** | `pip install gds-viz` | Mermaid diagram renderers for GDS specifications |
| **[gds-games](games/index.md)** | `pip install gds-games` | Typed DSL for compositional game theory (Open Games) |
| **[gds-examples](examples/index.md)** | `pip install gds-examples` | Six tutorial models demonstrating every framework feature |

## Quick Start

```bash
pip install gds-framework
```

```python
from gds import (
    BoundaryAction, Policy, Mechanism,
    GDSSpec, compile_system, verify,
    typedef, entity, state_var, space, interface,
)
```

## Guides

Interactive tutorials with code, diagrams, and runnable marimo notebooks:

| Guide | What You'll Learn |
|-------|-------------------|
| **[Getting Started](guides/getting-started.md)** | Build a thermostat model in 5 progressive stages — from raw blocks to DSL to verification |
| **[Rosetta Stone](guides/rosetta-stone.md)** | Same resource-pool problem modeled with stockflow, control, and game theory DSLs |
| **[Verification](guides/verification.md)** | All 3 verification layers demonstrated with deliberately broken models |
| **[Visualization](guides/visualization.md)** | 6 view types, 5 themes, and cross-DSL rendering with gds-viz |

## Architecture

```
gds-framework  ←  core engine (no GDS dependencies)
    ↑
gds-viz        ←  visualization (depends on gds-framework)
gds-games      ←  game theory DSL (depends on gds-framework)
    ↑
gds-examples   ←  tutorials (depends on gds-framework + gds-viz)
```

## License

Apache-2.0 — [BlockScience](https://block.science)
