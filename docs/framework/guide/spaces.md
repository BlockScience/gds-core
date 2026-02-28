# Spaces

Spaces define the signal domains that flow between blocks. They describe what kind of data travels through ports in a composition.

## Creating Spaces

A `Space` wraps a set of named dimensions, each backed by a `TypeDef`:

```python
from gds import space, typedef

Temperature = typedef("Temperature", float)
Humidity = typedef("Humidity", float, constraint=lambda x: 0.0 <= x <= 1.0)

env_space = space("Environment", temperature=Temperature, humidity=Humidity)
```

## Built-in Spaces

Two sentinel spaces are provided for common patterns:

| Space | Purpose |
|---|---|
| `EMPTY` | No signals — used for unused port groups (e.g. backward ports on a `Mechanism`) |
| `TERMINAL` | Terminal signal — marks the end of a signal chain |

```python
from gds import EMPTY, TERMINAL
```

## Spaces in Blocks

Spaces connect to blocks through interfaces. Each block has four port groups, and spaces define the data flowing through them:

```python
from gds import Policy, interface, space, typedef

Command = typedef("Command", float)
Signal = typedef("Signal", float)

cmd_space = space("Command Space", command=Command)
sig_space = space("Signal Space", signal=Signal)

controller = Policy(
    name="Controller",
    interface=interface(
        forward_in=["Signal"],
        forward_out=["Command"],
    ),
)
```

## Registering Spaces

Spaces are registered with `GDSSpec` for semantic validation:

```python
from gds import GDSSpec

spec = GDSSpec(name="My System")
spec.collect(env_space, cmd_space)  # type-dispatched registration
```

## See Also

- [Type System](types.md) — TypeDefs that back space dimensions
- [State & Entities](state.md) — state variables that use TypeDefs
- [Blocks & Roles](blocks.md) — how spaces connect to block interfaces
- [API Reference](../api/spaces.md) — `gds.spaces` module
