# Building New Models

A step-by-step guide to creating GDS models.

## File Structure

```
examples/
└── my_model/
    ├── __init__.py          # empty
    ├── model.py             # types, entities, spaces, blocks, build_spec(), build_system()
    ├── test_model.py        # tests for all layers
    └── generate_views.py    # visualization script
```

## Step-by-Step

### 1. Define Types (TypeDef)

Define value constraints before anything that references them.

```python
from gds import typedef

Count = typedef("Count", int,
    constraint=lambda x: x >= 0,
    description="Non-negative count")
```

### 2. Define Entities (state space X)

What persists across timesteps.

```python
from gds import entity, state_var

agent = entity("Agent",
    wealth=state_var(Currency, symbol="W"))
```

### 3. Define Spaces (communication channels)

Transient signals within a timestep — NOT state.

```python
from gds import space

signal = space("TransferSignal",
    amount=Currency, recipient=AgentID)
```

### 4. Define Blocks (with roles)

```python
from gds import BoundaryAction, Policy, Mechanism, interface

sensor = BoundaryAction(
    name="Sensor",
    interface=interface(forward_out=["Signal"]),
)

controller = Policy(
    name="Controller",
    interface=interface(
        forward_in=["Signal"],
        forward_out=["Command"],
    ),
    params_used=["gain"],
)

update = Mechanism(
    name="Update State",
    interface=interface(forward_in=["Command"]),
    updates=[("Agent", "wealth")],
)
```

### 5. Register in GDSSpec

```python
from gds import GDSSpec

def build_spec() -> GDSSpec:
    spec = GDSSpec(name="My Model", description="...")
    spec.collect(Currency, signal, agent, sensor, controller, update)
    spec.register_parameter("gain", GainType)
    return spec
```

### 6. Compose and Compile

```python
from gds import compile_system

def build_system():
    pipeline = sensor >> controller >> update
    return compile_system("My Model", pipeline)
```

## Design Decisions

| Decision | Guidance |
|---|---|
| State vs Signal | State persists (Entity). Signals are transient (Space). |
| Parameter vs Input | Parameters fixed per run (Θ). Inputs vary per step (BoundaryAction). |
| Which operator | Linear → `>>`. Independent → `\|`. Backward → `.feedback()`. Iteration → `.loop()`. |
| ControlAction vs Policy | Policy = decision logic (g). ControlAction = admissibility constraint (d). |

## Role Constraints

| Role | forward_in | forward_out | backward_in | backward_out |
|---|:---:|:---:|:---:|:---:|
| BoundaryAction | MUST be `()` | any | any | any |
| Policy | any | any | any | any |
| ControlAction | any | any | any | any |
| Mechanism | any | any | MUST be `()` | MUST be `()` |
