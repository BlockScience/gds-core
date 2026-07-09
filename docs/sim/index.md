# gds-sim

[![PyPI](https://img.shields.io/pypi/v/gds-sim)](https://pypi.org/project/gds-sim/)
[![Python](https://img.shields.io/pypi/pyversions/gds-sim)](https://pypi.org/project/gds-sim/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](https://github.com/DynamicalSystemsGroup/gds-core/blob/main/LICENSE)

**Standalone discrete-time simulation runtime for GDS models.**

## What is this?

`gds-sim` is the runtime layer beneath GDS analysis workflows. It executes
policy functions and state update functions over a plain Python dictionary
state, then records trajectories in a columnar `Results` object.

It is deliberately independent from `gds-framework`: use it directly for fast
experiments, or use `gds-analysis` when you want to bridge a verified `GDSSpec`
into executable behavior.

## Key Capabilities

- **Discrete timestep execution** -- run ordered state update blocks over time
- **cadCAD-style model shape** -- policies produce signals, SUFs update state
- **Parameter subsets** -- cartesian expansion of `Model.params`
- **Monte Carlo runs** -- repeat each parameter subset with run metadata
- **Lifecycle hooks** -- before-run, after-step, after-run, and early exit
- **Columnar results** -- efficient storage with `to_list()` and optional pandas
- **Parallel experiments** -- process-level execution for independent runs

## Architecture

```text
Model
  initial_state
  state_update_blocks
  params
        |
        v
Simulation
  timesteps, runs, hooks
        |
        v
Results
  timestep, substep, run, subset, state variables
```

`gds-sim` is also the execution engine used by `gds_analysis.psuu`:

```text
ParameterSpace -> Sweep -> Evaluator -> gds-sim Simulation -> KPI scores
```

## Install

```bash
uv add gds-sim
# or: pip install gds-sim
```

For pandas conversion:

```bash
uv add "gds-sim[pandas]"
```

See [Getting Started](getting-started.md) for a complete walkthrough.

