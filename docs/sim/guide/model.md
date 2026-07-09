# Model Guide

## Model

A `Model` declares the state variables, update blocks, and optional parameter
grid for a simulation.

```python
from gds_sim import Model, StateUpdateBlock

model = Model(
    initial_state={"x": 0.0},
    state_update_blocks=[StateUpdateBlock(variables={"x": update_x})],
    params={"rate": [0.1, 0.2]},
)
```

`initial_state` defines the complete state key set. Every variable updated by a
state update function must already exist in `initial_state`; missing keys are
rejected during model validation.

## StateUpdateBlock

A block has two parts:

| Field | Purpose |
|---|---|
| `policies` | Functions that read state and parameters, then emit signals |
| `variables` | Functions that update one state variable each |

```python
def policy(state, params, **kw):
    return {"delta": params["rate"]}


def update_x(state, params, *, signal=None, **kw):
    signal = signal or {}
    return "x", state["x"] + signal["delta"]


block = StateUpdateBlock(
    policies={"p": policy},
    variables={"x": update_x},
)
```

Policy outputs are merged with `dict.update()`. If multiple policies emit the
same signal key, the later policy value wins.

## Function Signatures

Native `gds-sim` functions receive current state, current parameter subset, and
keyword metadata:

```python
policy(state, params, timestep=t, substep=s) -> dict
state_update(state, params, signal=signal, timestep=t, substep=s) -> tuple[str, Any]
```

State update functions return the state key and its new value. The engine
creates a shallow copy of the state for each block and writes returned values
into that new state.

## cadCAD Compatibility

`gds-sim` also accepts cadCAD-style callables. Signature detection happens once
when the model is created.

```python
def cadcad_policy(params, substep, state_history, previous_state):
    return {"delta": params["rate"]}


def cadcad_suf(params, substep, state_history, previous_state, policy_input):
    return "x", previous_state["x"] + policy_input["delta"]
```

These are adapted to the native runtime signature before the hot loop starts.

## Parameters

`Model.params` maps each parameter name to a list of values. The model expands
those lists into cartesian-product subsets.

```python
Model(
    initial_state={"x": 0},
    state_update_blocks=[StateUpdateBlock(variables={"x": update_x})],
    params={"a": [1, 2], "b": [10, 20]},
)
```

The simulation records the active combination as the `subset` metadata column.

