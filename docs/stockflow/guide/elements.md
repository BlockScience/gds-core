# Elements & GDS Mapping

`gds-stockflow` provides four element types, each mapping to a specific GDS role.

## Stock

Stocks accumulate value over time. Each stock becomes a GDS entity with a `level` state variable, and a mechanism block that applies incoming flow rates.

```python
Stock(name="Population", initial=1000.0, non_negative=True)
```

**GDS mapping:** `Mechanism` (state update *f*) + `Entity` (state *X*)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Stock name (becomes entity name) |
| `initial` | float \| None | None | Initial level |
| `units` | str | "" | Unit label |
| `non_negative` | bool | True | Constrain level >= 0 |

### Port Convention

- Output: `"{Name} Level"` (temporal feedback to auxiliaries)
- Input: `"{FlowName} Rate"` (incoming flow rates)

---

## Flow

Flows transfer value between stocks (or from/to "clouds" -- external sources/sinks).

```python
Flow(name="Births", target="Population")        # inflow from cloud
Flow(name="Deaths", source="Population")         # outflow to cloud
Flow(name="Migration", source="A", target="B")   # transfer between stocks
```

**GDS mapping:** `Policy` (rate computation *g*)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Flow name |
| `source` | str | "" | Source stock (empty = cloud inflow) |
| `target` | str | "" | Target stock (empty = cloud outflow) |

### Port Convention

- Output: `"{Name} Rate"`

---

## Auxiliary

Auxiliaries compute intermediate values from stocks, converters, or other auxiliaries. They form an acyclic dependency graph -- the compiler validates this at construction time.

```python
Auxiliary(name="Birth Rate", inputs=["Population", "Fertility"])
```

**GDS mapping:** `Policy` (decision logic *g*)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Auxiliary name |
| `inputs` | list[str] | [] | Names of stocks, converters, or auxiliaries this depends on |

### Port Convention

- Input: `"{InputName} Level"` or `"{InputName} Signal"`
- Output: `"{Name} Signal"`

---

## Converter

Converters represent exogenous constants or parameters -- values that enter the system from outside. Converters have no internal inputs.

```python
Converter(name="Fertility", units="births/person/year")
```

**GDS mapping:** `BoundaryAction` (exogenous input *U*)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | required | Converter name |
| `units` | str | "" | Unit label |

### Port Convention

- Output: `"{Name} Signal"`

---

## Semantic Type System

Three distinct semantic spaces, all `float`-backed but structurally separate -- this prevents accidentally wiring a rate where a level is expected:

| Type | Space | Used By | Constraint |
|------|-------|---------|------------|
| `LevelType` | `LevelSpace` | Stocks | >= 0 (by default) |
| `UnconstrainedLevelType` | `UnconstrainedLevelSpace` | Stocks with `non_negative=False` | None |
| `RateType` | `RateSpace` | Flows | None (rates can be negative) |
| `SignalType` | `SignalSpace` | Auxiliaries, Converters | None |

## Composition Structure

The compiler builds a tiered composition tree:

```
(converters |) >> (auxiliaries |) >> (flows |) >> (stock mechanisms |)
    .loop([stock forward_out -> auxiliary forward_in])
```

This maps to the GDS canonical form `h = f . g` where stocks carry state (X), mechanisms provide f, and all other elements contribute to g.
