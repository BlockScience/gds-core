# Simulation

This guide shows the shortest path from a Python state update model to
simulation results with `gds-sim`.

Use this workflow when you already know how the state should update at each
timestep. If you are starting from a structural `GDSSpec`, read
[`gds-analysis`](../analysis/index.md) as the bridge from specification to
runtime.

## Install

```bash
uv add gds-sim
```

For pandas conversion support:

```bash
uv add "gds-sim[pandas]"
```

## Define the Model

A `gds-sim` model has three parts:

- `initial_state`: every state variable and its initial value
- `state_update_blocks`: ordered blocks that compute each timestep
- `params`: optional parameter values or parameter grids

```python
from gds_sim import Model, StateUpdateBlock


def growth_policy(state, params, **kw):
    return {"delta": state["population"] * params["growth_rate"]}


def update_population(state, params, *, signal=None, **kw):
    signal = signal or {}
    return "population", state["population"] + signal["delta"]


model = Model(
    initial_state={"population": 100.0},
    state_update_blocks=[
        StateUpdateBlock(
            policies={"growth": growth_policy},
            variables={"population": update_population},
        )
    ],
    params={"growth_rate": [0.01, 0.05]},
)
```

Policy functions read the current state and parameters, then return signal
values. State update functions return `(state_key, new_value)`.

## Run the Simulation

```python
from gds_sim import Simulation

sim = Simulation(model=model, timesteps=10, runs=2)
results = sim.run()
```

`timesteps` controls how many outer steps are executed. `runs` repeats the
simulation for Monte Carlo-style workflows.

## Inspect Results

```python
rows = results.to_list()
print(rows[:3])
```

Each row contains timestep metadata plus state variables:

| Column | Meaning |
|--------|---------|
| `timestep` | Outer simulation step |
| `substep` | State update block index inside the timestep |
| `run` | Run index |
| `subset` | Parameter subset index |
| state variables | One column per key in `initial_state` |

Convert to pandas when the optional dependency is installed:

```python
df = results.to_dataframe()
```

## Sweep Simple Parameters

`Model.params` expands lists into a cartesian product. This example evaluates
four parameter subsets:

```python
model = Model(
    initial_state={"x": 0},
    state_update_blocks=[StateUpdateBlock(variables={"x": update_x})],
    params={"rate": [1, 2], "bias": [0, 10]},
)
```

For KPI scoring, optimizer strategies, and sensitivity analysis, move from
plain `gds-sim` parameter grids to [PSUU](parameter-sweep.md).

## Next Steps

- Read the [`gds-sim` model guide](../sim/guide/model.md) for callable
  signatures and validation rules.
- Read the [`gds-sim` execution guide](../sim/guide/execution.md) for timesteps,
  runs, hooks, and experiments.
- Use [parameter sweeps](parameter-sweep.md) when you need KPIs or optimizer
  strategies.

