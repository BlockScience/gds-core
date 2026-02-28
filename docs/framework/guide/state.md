# State & Entities

Entities and state variables define the mutable state that a GDS system evolves over time. They live in Layer 1 (the specification framework) and are validated by TypeDefs at runtime.

## Entities

An `Entity` groups related state variables into a named container. Each entity represents a distinct stateful component of the system.

```python
from gds import entity, state_var, typedef

Count = typedef("Count", int, constraint=lambda x: x >= 0)
Rate = typedef("Rate", float, constraint=lambda x: 0.0 <= x <= 1.0)

population = entity(
    "Population",
    susceptible=state_var(Count, symbol="S"),
    infected=state_var(Count, symbol="I"),
    recovered=state_var(Count, symbol="R"),
)
```

### State Variables

Each `StateVariable` has:

- **type_def** — a `TypeDef` that validates values at runtime
- **symbol** — a short mathematical symbol (e.g. `"S"`, `"I"`, `"R"`)
- **description** — optional human-readable description

```python
from gds import state_var, typedef

Temperature = typedef("Temperature", float)
temp = state_var(Temperature, symbol="T", description="Current temperature in Celsius")
```

## Registering Entities

Entities are registered with `GDSSpec` either explicitly or via `collect()`:

```python
from gds import GDSSpec, entity, state_var, typedef

spec = GDSSpec(name="SIR Model")

Count = typedef("Count", int, constraint=lambda x: x >= 0)
population = entity("Population", s=state_var(Count, symbol="S"))

# Explicit registration
spec.register_entity(population)

# Or via collect()
spec.collect(population)
```

## Role in Canonical Form

Entities define the state space **X** in the canonical decomposition `h = f . g`. The dimension of X (number of state variables across all entities) determines the character of the system:

| |X| | Canonical Form | Character |
|---|---|---|
| 0 | h = g | Stateless (pure policy) |
| n > 0 | h = f . g | Full dynamical system |

## See Also

- [Type System](types.md) — TypeDefs used by state variables
- [Spaces](spaces.md) — signal spaces that connect blocks
- [Specification](spec.md) — registering entities with GDSSpec
- [API Reference](../api/state.md) — `gds.state` module
