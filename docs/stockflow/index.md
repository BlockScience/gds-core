# gds-stockflow

[![PyPI](https://img.shields.io/pypi/v/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![Python](https://img.shields.io/pypi/pyversions/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Declarative stock-flow DSL over GDS semantics** — system dynamics with formal verification.

## What is this?

`gds-stockflow` extends the GDS framework with system dynamics vocabulary — stocks, flows, auxiliaries, and converters. It provides:

- **4 element types** — Stock, Flow, Auxiliary, Converter
- **Typed compilation** — Each element compiles to GDS role blocks, entities, and composition trees
- **5 verification checks** — Domain-specific structural validation (SF-001..SF-005)
- **Canonical decomposition** — Validated h = f &#x2218; g projection with state-dominant accumulation
- **Full GDS integration** — All downstream tooling works immediately (canonical projection, semantic checks, gds-viz)

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

## Credits

Built on [gds-framework](../framework/index.md) by [BlockScience](https://block.science).
