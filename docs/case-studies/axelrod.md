# Axelrod Tournament

**One model, many views** — an interactive exploration of Axelrod's iterated Prisoner's Dilemma tournament, built on the GDS ecosystem.

[:octicons-link-external-16: Live Site](https://blockscience.github.io/gds-axelrod/) &nbsp; [:octicons-mark-github-16: Source](https://github.com/BlockScience/gds-axelrod)

---

## Overview

[gds-axelrod](https://github.com/BlockScience/gds-axelrod) demonstrates how a single OGS game specification can be projected through six distinct analytical lenses — from narrative storytelling to formal mathematical decomposition to interactive parameter exploration — without simplification or compromise.

The project is a concrete realization of the **specification-as-interoperability-layer** pattern described in the [Interoperability Guide](../guides/interoperability.md): one compositional model serves as the single source of truth, and multiple independent tools consume it for different purposes.

## Architecture

The project splits into two tiers:

```
Pipeline (Python)                    Site (Vite/JavaScript)
┌──────────────────────┐            ┌──────────────────────────┐
│  OGS game definition │──export──→ │  Canvas Petri dish viz   │
│  gds-sim population  │  (JSON)    │  Mermaid diagrams        │
│  gds-psuu sweeps     │            │  Narrative chapters      │
│  Nash/dominance calc  │            │  Pyodide PSUU sandbox   │
└──────────────────────┘            └──────────────────────────┘
```

**Pipeline**: Python data generation using `gds-games`, `gds-sim`, `gds-psuu`, and `gds-viz`. Produces JSON artifacts consumed by the frontend.

**Site**: Vite-based JavaScript frontend with Canvas rendering, responsive chapter navigation, and browser-side Python execution via Pyodide.

## Six Showcase Views

Each page presents the same underlying Prisoner's Dilemma model through a different analytical lens:

| View | What It Shows | GDS Package |
|------|---------------|-------------|
| **Story** | Narrative chapters with interactive sandbox simulation | Strategy definitions from OGS |
| **Formal Structure** | Canonical `h = f . g` decomposition | `GDSSpec` + `project_canonical()` |
| **Visualizations** | Mermaid diagrams across 6 view types | `gds-viz` on `SystemIR` |
| **Simulation** | Population trajectory tracking over generations | `gds-sim` |
| **Nash Analysis** | Equilibria and dominance calculations | `PatternIR` from `gds-games` |
| **PSUU** | Interactive parameter space exploration | `gds-psuu` via Pyodide |

## GDS Ecosystem Integration

gds-axelrod exercises four GDS packages together, demonstrating the composability of the ecosystem:

- **gds-domains** (`gds_domains.games`) — defines the game as an OGS pattern, compiles to `PatternIR` and `GDSSpec`
- **gds-viz** (`gds_viz`) — renders Mermaid diagrams from the compiled `SystemIR`
- **gds-sim** (`gds_sim`) — runs population dynamics simulation over iterated tournament rounds
- **gds-analysis** (`gds_analysis.psuu`) — parameter sweeps compiled to WebAssembly via Pyodide for in-browser execution

## Key Patterns Demonstrated

### Specification as Single Source of Truth

The OGS game definition is written once. Every view — visualization, simulation, equilibrium analysis, parameter exploration — derives from the same specification. No view has a private copy of the model.

### Thin Projections

Each analytical tool is a thin projection over the specification:

- `PatternIR` → Nash equilibria via Nashpy
- `PatternIR` → payoff matrix → tournament simulation
- `SystemIR` → Mermaid diagrams via gds-viz
- `GDSSpec` → canonical decomposition

### Browser-Side Computation

The PSUU page compiles Python (gds-sim + gds-psuu) to WebAssembly via Pyodide, enabling interactive parameter exploration without a backend server.

## Related

- [Interoperability Guide](../guides/interoperability.md) — the specification-as-interoperability-layer pattern
- [Evolution of Trust](../examples/examples/evolution-of-trust.md) — the in-repo tutorial model that gds-axelrod builds upon
- [Prisoner's Dilemma](../examples/examples/prisoners-dilemma.md) — the base GDS framework version
- [View Stratification](../guides/view-stratification.md) — the theoretical basis for "one model, many views"
