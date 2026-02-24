# gds-stockflow

[![PyPI](https://img.shields.io/pypi/v/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![Python](https://img.shields.io/pypi/pyversions/gds-stockflow)](https://pypi.org/project/gds-stockflow/)
[![License](https://img.shields.io/github/license/BlockScience/gds-stockflow)](LICENSE)

Declarative stock-flow DSL over GDS semantics — system dynamics with formal guarantees.

## Table of Contents

- [Quick Start](#quick-start)
- [What is this?](#what-is-this)
- [Architecture](#architecture)
- [Elements](#elements)
- [Semantic Type System](#semantic-type-system)
- [Verification](#verification)
- [Examples](#examples)
- [Status](#status)
- [Credits & Attribution](#credits--attribution)

## Quick Start

```bash
pip install gds-stockflow
```

```python
from stockflow import (
    Stock, Flow, Auxiliary, Converter,
    StockFlowModel, compile_model, compile_to_system, verify,
)

# Declare a simple population model
model = StockFlowModel(
    name="Population",
    stocks=[Stock(name="Population", initial=1000.0)],
    flows=[
        Flow(name="Births", target="Population"),
        Flow(name="Deaths", source="Population"),
    ],
    auxiliaries=[
        Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"]),
        Auxiliary(name="Death Rate", inputs=["Population"]),
    ],
    converters=[Converter(name="Fertility")],
)

# Compile to GDS — produces a real GDSSpec with role blocks, entities, wirings
spec = compile_model(model)
ir = compile_to_system(model)
print(f"{len(ir.blocks)} blocks, {len(ir.wirings)} wirings")

# Verify — domain checks + optional GDS structural checks
report = verify(model, include_gds_checks=True)
print(f"{report.checks_passed}/{report.checks_total} checks passed")
```

## What is this?

`gds-stockflow` is a **domain DSL** that compiles stock-flow diagrams to [GDS](https://github.com/BlockScience/gds-core) specifications. You declare stocks, flows, auxiliaries, and converters as plain data models — the compiler handles the mapping to GDS role blocks, entities, composition trees, and wirings.

```
Your declaration                    What the compiler produces
────────────────                    ─────────────────────────
Stock("Population")          →     Mechanism + Entity (state update f + state X)
Flow("Births", target=...)   →     Policy (rate computation g)
Auxiliary("Birth Rate")      →     Policy (decision logic g)
Converter("Fertility")       →     BoundaryAction (exogenous input U)
StockFlowModel(...)          →     GDSSpec + SystemIR (full GDS specification)
```

Once compiled, all downstream GDS tooling works immediately — canonical projection (`h = f ∘ g`), semantic checks, SpecQuery dependency analysis, JSON serialization, and [gds-viz](https://github.com/BlockScience/gds-core/tree/main/packages/gds-viz) diagram generation.

## Architecture

### DSL over GDS

```
StockFlowModel (user-facing declarations)
       │
       ▼  compile_model()
GDSSpec (entities, blocks, wirings, parameters)
       │
       ▼  compile_to_system()
SystemIR (flat IR for verification + visualization)
```

No parallel IR stack. The compiler produces a real `GDSSpec` with real GDS role blocks. This means stock-flow models are first-class GDS citizens — they compose with other GDS models, share the same verification engine, and render with the same visualization tools.

### Composition Tree

The compiler builds a tiered composition tree:

```
(converters |) >> (auxiliaries |) >> (flows |) >> (stock mechanisms |)
    .loop([stock forward_out → auxiliary forward_in])
```

- **Within each tier:** parallel composition (`|`) — independent elements run side-by-side
- **Across tiers:** sequential composition (`>>`) — converters feed auxiliaries, auxiliaries feed flows, flows feed stock mechanisms
- **Temporal recurrence:** `.loop()` — stock levels at timestep *t* feed back to auxiliaries at timestep *t+1*

## Elements

Four declaration types, each mapping to a specific GDS role:

### Stock

```python
Stock(name="Population", initial=1000.0, non_negative=True)
```

**GDS mapping:** `Mechanism` (state update *f*) + `Entity` (state *X*)

A stock accumulates value over time. Each stock becomes a GDS entity with a `level` state variable, and a mechanism block that applies incoming flow rates. Stocks emit a `Level` port for temporal feedback.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Stock name (becomes entity name) |
| `initial` | float \| None | None | Initial level |
| `units` | str | "" | Unit label |
| `non_negative` | bool | True | Constrain level ≥ 0 |

### Flow

```python
Flow(name="Births", target="Population")
Flow(name="Deaths", source="Population")
Flow(name="Migration", source="CityA", target="CityB")
```

**GDS mapping:** `Policy` (rate computation *g*)

A flow transfers value between stocks (or from/to "clouds" — external sources/sinks). Flows with only a `target` are inflows; flows with only a `source` are outflows; flows with both transfer between stocks.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Flow name |
| `source` | str | "" | Source stock (empty = cloud inflow) |
| `target` | str | "" | Target stock (empty = cloud outflow) |

### Auxiliary

```python
Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"])
```

**GDS mapping:** `Policy` (decision logic *g*)

An auxiliary computes intermediate values from stocks, converters, or other auxiliaries. Auxiliaries form an acyclic dependency graph — the compiler validates this at construction time.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Auxiliary name |
| `inputs` | list[str] | [] | Names of stocks, converters, or auxiliaries this depends on |

### Converter

```python
Converter(name="Fertility", units="births/person/year")
```

**GDS mapping:** `BoundaryAction` (exogenous input *U*)

A converter represents an exogenous constant or parameter — a value that enters the system from outside. Converters have no internal inputs.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Converter name |
| `units` | str | "" | Unit label |

## Semantic Type System

Three distinct semantic spaces, all `float`-backed but structurally separate — this prevents accidentally wiring a rate where a level is expected:

| Type | Space | Used By | Constraint |
|------|-------|---------|------------|
| `LevelType` | `LevelSpace` | Stocks | ≥ 0 (by default) |
| `UnconstrainedLevelType` | `UnconstrainedLevelSpace` | Stocks with `non_negative=False` | None |
| `RateType` | `RateSpace` | Flows | None (rates can be negative) |
| `SignalType` | `SignalSpace` | Auxiliaries, Converters | None |

## Verification

Five domain-specific checks validate the stock-flow model structure before compilation:

| ID | Name | Severity | What It Checks |
|----|------|----------|---------------|
| SF-001 | Orphan stocks | WARNING | Every stock has ≥ 1 connected flow |
| SF-002 | Flow-stock validity | ERROR | Flow source/target reference declared stocks |
| SF-003 | Auxiliary acyclicity | ERROR | No cycles in auxiliary dependency graph |
| SF-004 | Converter connectivity | WARNING | Every converter referenced by ≥ 1 auxiliary |
| SF-005 | Flow completeness | ERROR | Every flow has at least one of source or target |

```python
from stockflow import verify

# Domain checks only
report = verify(model)

# Domain checks + GDS structural checks (G-001..G-006)
report = verify(model, include_gds_checks=True)
```

## Examples

Two tutorial examples in [`gds-examples`](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples) demonstrate stock-flow modeling using the GDS framework primitives:

| Example | Domain | What It Teaches |
|---------|--------|-----------------|
| [SIR Epidemic](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples/stockflow/sir_epidemic) | Epidemiology | 3-compartment accumulation, sequential + parallel composition |
| [Lotka-Volterra](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples/stockflow/lotka_volterra) | Population dynamics | Temporal loops (`.loop()`), predator-prey rate equations |

## Status

**v0.1.0 — Alpha.** Complete DSL with 5 verification checks and full GDS compilation. 215 tests.

## License

Apache-2.0

---
Built with [Claude Code](https://claude.ai/code). All code is test-driven and human-reviewed.

## Credits & Attribution

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/BlockScience/MSML) and [bdp-lib](https://github.com/BlockScience/bdp-lib).

**Contributors:**
* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (BlockScience).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (BlockScience).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.
