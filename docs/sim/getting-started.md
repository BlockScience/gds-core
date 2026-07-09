# Getting Started

## Installation

```bash
uv add gds-sim
# or: pip install gds-sim
```

For development in this repository:

```bash
git clone https://github.com/DynamicalSystemsGroup/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Simulation

```python
from gds_sim import Model, Simulation, StateUpdateBlock


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

sim = Simulation(model=model, timesteps=10, runs=2)
results = sim.run()
```

## Inspecting Results

```python
rows = results.to_list()

for row in rows[:3]:
    print(row)
```

Every row contains:

| Column | Meaning |
|---|---|
| `timestep` | Outer simulation step |
| `substep` | State update block index inside the timestep |
| `run` | Monte Carlo run index |
| `subset` | Parameter subset index |
| state variables | One column per key in `initial_state` |

For pandas:

```python
df = results.to_dataframe()  # requires gds-sim[pandas]
```

## Parameter Sweeps

`Model.params` is expanded as a cartesian product. The example above evaluates
two subsets, one for each `growth_rate`.

```python
model = Model(
    initial_state={"x": 0},
    state_update_blocks=[StateUpdateBlock(variables={"x": update_x})],
    params={"rate": [1, 2], "bias": [0, 10]},
)
```

This creates four subsets: `(1, 0)`, `(1, 10)`, `(2, 0)`, and `(2, 10)`.

## Next Steps

- [Model Guide](guide/model.md) -- policy and state update function contracts
- [Execution Guide](guide/execution.md) -- timesteps, hooks, runs, experiments
- [Results Guide](guide/results.md) -- output shape and conversions
- [PSUU](../psuu/index.md) -- parameter search and KPI optimization over simulations

