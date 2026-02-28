# GDS Ecosystem

**Typed compositional specifications for complex systems**, grounded in [Generalized Dynamical Systems](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) theory (Zargham & Shorish, 2022).

## Installation

Install individual packages from PyPI as needed:

```bash
pip install gds-framework    # Core library
pip install gds-viz          # Visualization
pip install gds-stockflow    # Stock-flow DSL
pip install gds-control      # Control systems DSL
pip install gds-games        # Game theory DSL
pip install gds-software     # Software architecture DSL
pip install gds-business     # Business dynamics DSL
pip install gds-examples     # Tutorial models
```

!!! note "PyPI names differ from import names"
    Each package's PyPI name (what you `pip install`) differs from its Python import name.
    Use the table below as a reference.

| PyPI Package | Import Name | Description |
|---|---|---|
| `gds-framework` | `gds` | Core engine — blocks, composition algebra, compiler, verification |
| `gds-viz` | `gds_viz` | Mermaid diagram renderers for GDS specifications |
| `gds-stockflow` | `stockflow` | Declarative stock-flow DSL over GDS semantics |
| `gds-control` | `gds_control` | State-space control DSL over GDS semantics |
| `gds-games` | `ogs` | Typed DSL for compositional game theory (Open Games) |
| `gds-software` | `gds_software` | Software architecture DSL (DFD, state machine, C4, ERD, etc.) |
| `gds-business` | `gds_business` | Business dynamics DSL (CLD, supply chain, value stream map) |
| `gds-examples` | — | Tutorial models demonstrating framework features |

### For developers

To work on the monorepo with all packages linked locally:

```bash
git clone https://github.com/BlockScience/gds-core.git
cd gds-core
uv sync --all-packages
```

## Quick Start

```python
from gds import (
    BoundaryAction, Policy, Mechanism,
    GDSSpec, compile_system, verify,
    typedef, entity, state_var, space, interface,
)
```

## Packages

| Package | Docs |
|---------|------|
| **[gds-framework](framework/index.md)** | Core engine — blocks, composition algebra, compiler, verification |
| **[gds-viz](viz/index.md)** | Mermaid diagram renderers for GDS specifications |
| **gds-stockflow** | Declarative stock-flow DSL over GDS semantics |
| **gds-control** | State-space control DSL over GDS semantics |
| **[gds-games](games/index.md)** | Typed DSL for compositional game theory (Open Games) |
| **gds-software** | Software architecture DSL — DFD, state machine, component, C4, ERD, dependency |
| **[gds-business](business/index.md)** | Business dynamics DSL — CLD, supply chain, value stream map |
| **[gds-examples](examples/index.md)** | Six tutorial models demonstrating every framework feature |

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
gds-stockflow  ←  stock-flow DSL (depends on gds-framework)
gds-control    ←  control systems DSL (depends on gds-framework)
gds-software   ←  software architecture DSL (depends on gds-framework)
gds-business   ←  business dynamics DSL (depends on gds-framework)
    ↑
gds-examples   ←  tutorials (depends on gds-framework + gds-viz)
```

## License

Apache-2.0 — [BlockScience](https://block.science)
