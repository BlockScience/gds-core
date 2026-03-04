# GDS Ecosystem

**Typed compositional specifications for complex systems**, grounded in [Generalized Dynamical Systems](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc) theory (Zargham & Shorish, 2022).

GDS gives you a composition algebra for modeling complex systems — from epidemics and control loops to game theory and software architecture — with built-in verification, visualization, and a shared formal foundation.

## Where to Start

| | |
|---|---|
| **[Start Here](tutorials/getting-started.md)** | New to GDS? Follow the hands-on tutorial to build your first model in minutes. |
| **[Learning Path](examples/learning-path.md)** | Work through seven example models in recommended order, from simple to complex. |
| **[Choosing a DSL](guides/choosing-a-dsl.md)** | Compare all seven domain DSLs and pick the right one for your problem. |
| **[Rosetta Stone](guides/rosetta-stone.md)** | See the same problem modeled with stockflow, control, and game theory DSLs side by side. |

## Interactive Notebooks

Key guides include embedded [marimo](https://marimo.io) notebooks — run code, tweak parameters, and see results directly in the docs. No local setup required.

| Guide | What You'll Explore |
|-------|---------------------|
| **[Getting Started](guides/getting-started.md)** | Build a thermostat model in 5 progressive stages |
| **[Rosetta Stone](guides/rosetta-stone.md)** | Same problem modeled with three different DSLs |
| **[Verification](guides/verification.md)** | All 3 verification layers with deliberately broken models |
| **[Visualization](guides/visualization.md)** | 6 view types, 5 themes, cross-DSL rendering |
| **[Interoperability](guides/interoperability.md)** | Cross-DSL composition and data exchange |

## Packages

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
