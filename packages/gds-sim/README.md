# gds-sim

High-performance simulation engine for the GDS ecosystem.

`gds-sim` is the standalone discrete-time runtime for GDS models. It has no
dependency on `gds-framework`: it executes plain Python policy functions and
state update functions over a dictionary state, then stores trajectories in a
compact columnar `Results` object.

## Install

```bash
uv add gds-sim
# or: pip install gds-sim
```

For DataFrame output:

```bash
uv add "gds-sim[pandas]"
```

## Quick Start

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

results = Simulation(model=model, timesteps=10, runs=2).run()
rows = results.to_list()

print(rows[-1])
```

Each result row includes metadata columns:

- `timestep`: outer simulation step
- `substep`: state update block index within the timestep
- `run`: Monte Carlo run index
- `subset`: parameter subset index

## Execution Model

`gds-sim` runs a cadCAD-like loop:

1. Start from `initial_state`
2. For each parameter subset and run, copy the initial state
3. At each timestep, execute each `StateUpdateBlock`
4. Policies produce a signal dictionary
5. State update functions return `(state_key, new_value)`
6. Append each substep state snapshot to `Results`

Parameter sweeps are built into `Model.params` as a cartesian product:

```python
model = Model(
    initial_state={"x": 0},
    state_update_blocks=[StateUpdateBlock(variables={"x": update_x})],
    params={"rate": [1, 2], "delay": [0, 5]},
)
# subset 0..3 covers all 2 x 2 combinations
```

## Hooks and Early Exit

```python
from gds_sim import Hooks


def stop_when_large(state, timestep):
    return False if state["population"] > 500 else None


sim = Simulation(
    model=model,
    timesteps=100,
    hooks=Hooks(after_step=stop_when_large),
)
```

Hooks are available before a run, after each step, and after a run. Returning
`False` from `after_step` stops that run early.

## Results

`Results` stores columns internally and converts on demand:

```python
rows = results.to_list()
df = results.to_dataframe()  # requires gds-sim[pandas]
```

`Experiment` can merge multiple simulations and run independent `(subset, run)`
pairs across processes:

```python
from gds_sim import Experiment

experiment = Experiment(simulations=[Simulation(model=model)], processes=2)
merged = experiment.run()
```

## Relationship to the GDS Ecosystem

- `gds-framework` defines structural specifications and verification.
- `gds-analysis` converts selected `GDSSpec` structures into `gds_sim.Model`.
- `gds_analysis.psuu` uses `gds-sim` as its runtime for parameter sweeps,
  KPI scoring, optimization, and sensitivity analysis.

## License

Apache-2.0 -- [Dynamical Systems Group](https://www.dynamicalsystemsgroup.com)
