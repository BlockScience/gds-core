# Specification

## GDSSpec

`GDSSpec` is the central registry that holds all components of a model: types, spaces, entities, blocks, parameters, and wirings.

```python
from gds import GDSSpec, typedef, entity, state_var, space, BoundaryAction, interface

spec = GDSSpec(name="My Model", description="A simple model")

# Register types
Count = typedef("Count", int, constraint=lambda x: x >= 0)
spec.register_type(Count)

# Register entities
agent = entity("Agent", wealth=state_var(Count, symbol="W"))
spec.register_entity(agent)

# Register blocks, spaces, parameters...
```

### Using `collect()`

The `collect()` method type-dispatches objects to the right `register_*()` call:

```python
spec.collect(
    Count, RateType,     # TypeDefs
    signal,              # Spaces
    agent,               # Entities
    sensor, controller,  # Blocks
)
```

### SpecWiring

Explicit wiring declarations at the specification level:

```python
from gds import SpecWiring, Wire

spec.register_wiring(
    SpecWiring(
        name="Main Pipeline",
        block_names=["Sensor", "Controller"],
        wires=[
            Wire(source="Sensor", target="Controller", space="TemperatureSpace"),
        ],
    )
)
```

## Entities & State

Entities define the state space X — what persists across timesteps.

```python
from gds import entity, state_var, typedef

Temperature = typedef("Temperature", float)
Energy = typedef("Energy", float, constraint=lambda x: x >= 0)

room = entity("Room",
    temperature=state_var(Temperature, symbol="T"),
    energy_consumed=state_var(Energy, symbol="E"),
)
```

## Spaces

Spaces define typed communication channels — transient signals within a timestep.

```python
from gds import space

temp_space = space("TemperatureSpace", measured_temp=Temperature)
```

## Parameters

Parameters define the configuration space Θ — values fixed for a simulation run.

```python
spec.register_parameter("Kp", typedef("GainType", float))
spec.register_parameter("Ki", typedef("GainType", float))
```

Blocks reference parameters via `params_used`:

```python
controller = Policy(
    name="PID Controller",
    interface=interface(forward_in=["Temperature"], forward_out=["Command"]),
    params_used=["Kp", "Ki"],
)
```
