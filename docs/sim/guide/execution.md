# Execution Guide

## Simulation

`Simulation` combines a `Model` with runtime settings.

```python
from gds_sim import Simulation

sim = Simulation(model=model, timesteps=100, runs=10)
results = sim.run()
```

For each parameter subset and run, `gds-sim` starts from a shallow copy of
`initial_state`.

## Timesteps and Substeps

The initial state is recorded at `timestep=0`, `substep=0`. Each timestep then
executes every `StateUpdateBlock` in order.

For a model with two blocks and `timesteps=3`, each run produces:

```text
(0, 0)
(1, 1), (1, 2)
(2, 1), (2, 2)
(3, 1), (3, 2)
```

The row count per run is:

```text
1 + timesteps * number_of_blocks
```

## Runs and Subsets

`runs` repeats every parameter subset. Use this for stochastic models or Monte
Carlo evaluation.

```python
sim = Simulation(model=model, timesteps=50, runs=20)
```

The output rows identify both dimensions:

- `run`: repeated run index
- `subset`: parameter combination index

## Hooks

Lifecycle hooks allow instrumentation and early stopping.

```python
from gds_sim import Hooks, Simulation


def before_run(state, params):
    state["seen"] = True


def after_step(state, timestep):
    return False if state["x"] >= 10 else None


def after_run(state, params):
    print(state)


sim = Simulation(
    model=model,
    timesteps=100,
    hooks=Hooks(
        before_run=before_run,
        after_step=after_step,
        after_run=after_run,
    ),
)
```

Returning `False` from `after_step` stops the current run after that timestep.

## Experiments and Parallelism

`Experiment` executes one or more simulations and merges their results.

```python
from gds_sim import Experiment, Simulation

experiment = Experiment(
    simulations=[
        Simulation(model=model_a, timesteps=10),
        Simulation(model=model_b, timesteps=10),
    ],
    processes=1,
)
results = experiment.run()
```

When `processes` is greater than `1`, independent `(subset, run)` jobs are
executed in a process pool and merged into one `Results` object.

