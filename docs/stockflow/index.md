# gds-stockflow

[![PyPI](https://img.shields.io/pypi/v/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![Python](https://img.shields.io/pypi/pyversions/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](https://github.com/DynamicalSystemsGroup/gds-core/blob/main/LICENSE)

**Declarative stock-flow DSL over GDS semantics** — system dynamics with formal verification.

## Package Identity

| Distribution | Import | Role |
|---|---|---|
| `gds-stockflow` | `gds_domains.stockflow` | Stock-flow DSL over GDS semantics |
| `gds-domains` | `gds_domains.stockflow` | Consolidated domain package distribution |

## What is this?

`gds-stockflow` extends the GDS framework with system dynamics vocabulary — stocks, flows, auxiliaries, and converters. It provides:

- **4 element types** — Stock, Flow, Auxiliary, Converter
- **Typed compilation** — Each element compiles to GDS role blocks, entities, and composition trees
- **5 verification checks** — Domain-specific structural validation (SF-001..SF-005)
- **Canonical decomposition** — Validated h = f &#x2218; g projection with state-dominant accumulation
- **Full GDS integration** — All downstream tooling works immediately (canonical projection, semantic checks, gds-viz)

## When to Use It

Use `gds-stockflow` when your model is naturally expressed as stocks, flows,
auxiliaries, and converters. Use `gds-sim` or `gds-analysis` when you need to
execute or analyze trajectories after the structure is defined.

## Architecture

```
gds-framework (pip install gds-framework)
|
|  Domain-neutral composition algebra, typed spaces,
|  state model, verification engine, flat IR compiler.
|
+-- gds-stockflow (pip install gds-domains)
    |
    |  Stock-flow DSL: Stock, Flow, Auxiliary, Converter elements,
    |  compile_model(), domain verification, verify() dispatch.
    |
    +-- Your application
        |
        |  Concrete stock-flow models, analysis notebooks,
        |  verification runners.
```

## GDS Mapping

```
Your declaration                    What the compiler produces
----------------                    -------------------------
Stock("Population")          ->     Mechanism + Entity (state update f + state X)
Flow("Births", target=...)   ->     Policy (rate computation g)
Auxiliary("Birth Rate")      ->     Policy (decision logic g)
Converter("Fertility")       ->     BoundaryAction (exogenous input U)
StockFlowModel(...)          ->     GDSSpec + SystemIR (full GDS specification)
```

## Composition Tree

The compiler builds a tiered composition tree:

```
(converters |) >> (auxiliaries |) >> (flows |) >> (stock mechanisms |)
    .loop([stock forward_out -> auxiliary forward_in])
```

- **Within each tier:** parallel composition (`|`) -- independent elements run side-by-side
- **Across tiers:** sequential composition (`>>`) -- converters feed auxiliaries, auxiliaries feed flows, flows feed stock mechanisms
- **Temporal recurrence:** `.loop()` -- stock levels at timestep *t* feed back to auxiliaries at timestep *t+1*

## Canonical Form

Stock-flow models produce the full dynamical form:

| |X| | |f| | Form | Character |
|-----|-----|------|-----------|
| n | n | h = f &#x2218; g | State-dominant accumulation |

Stocks carry state (X), mechanisms provide f, and all other elements contribute to g.

## Quick Start

```bash
uv add gds-stockflow
# or: pip install gds-domains
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Relationship to the Ecosystem

`gds-stockflow` is a domain DSL. It compiles stock-flow declarations into
`gds-framework` specifications, which can then be verified, visualized with
`gds-viz`, and connected to simulation workflows through `gds-analysis`.

## Credits

Built on [gds-framework](../framework/index.md) by [DynamicalSystemsGroup](https://dynamicalsystemsgroup.com).
