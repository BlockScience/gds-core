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

Install just what you need: `uv add gds-core[control,continuous]`

### Structural Specification

| Package | Import | Description |
|---|---|---|
| [`gds-framework`](framework/index.md) | `gds` | Core engine -- composition algebra, compiler, verification |
| [`gds-viz`](viz/index.md) | `gds_viz` | Mermaid diagrams + [phase portraits](viz/index.md) `[phase]` |
| [`gds-owl`](owl/index.md) | `gds_owl` | OWL/SHACL/SPARQL export for formal representability |

### Domain DSLs

| Package | Import | Description |
|---|---|---|
| [`gds-stockflow`](stockflow/index.md) | `stockflow` | Declarative stock-flow DSL |
| [`gds-control`](control/index.md) | `gds_control` | State-space control DSL |
| [`gds-games`](games/index.md) | `ogs` | Compositional game theory + [Nash equilibrium](games/equilibrium.md) `[nash]` |
| [`gds-software`](software/index.md) | `gds_software` | Software architecture DSL (DFD, SM, C4, ERD) |
| [`gds-business`](business/index.md) | `gds_business` | Business dynamics DSL (CLD, SCN, VSM) |
| [`gds-symbolic`](symbolic/index.md) | `gds_symbolic` | SymPy bridge for control models `[sympy]` |

### Simulation & Analysis

| Package | Import | Description |
|---|---|---|
| [`gds-sim`](https://pypi.org/project/gds-sim/) | `gds_sim` | Discrete-time simulation engine (standalone) |
| [`gds-continuous`](continuous/index.md) | `gds_continuous` | Continuous-time ODE engine `[scipy]` |
| [`gds-analysis`](analysis/index.md) | `gds_analysis` | GDSSpec-to-gds-sim bridge, reachability |
| [`gds-psuu`](psuu/index.md) | `gds_psuu` | Parameter sweep + Optuna optimization |

### Tutorials

| Package | Description |
|---|---|
| `gds-examples` | [Tutorial models](examples/learning-path.md) + [Homicidal Chauffeur](continuous/getting-started.md) notebook |

## Architecture

```
gds-framework  ←  core engine (pydantic only)
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
    ├── gds-analysis   ←  spec→sim bridge, reachability
    └── gds-psuu       ←  parameter sweep + Optuna

gds-continuous     ←  continuous-time ODE engine (standalone) [scipy]
```

## License

Apache-2.0 — [BlockScience](https://block.science)
