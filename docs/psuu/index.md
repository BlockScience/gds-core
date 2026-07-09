# PSUU

[![PyPI](https://img.shields.io/pypi/v/gds-analysis)](https://pypi.org/project/gds-analysis/)
[![Python](https://img.shields.io/pypi/pyversions/gds-analysis)](https://pypi.org/project/gds-analysis/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](https://github.com/DynamicalSystemsGroup/gds-core/blob/main/LICENSE)

**Parameter space search under uncertainty** -- explore, evaluate, and optimize simulation parameters with Monte Carlo awareness.

## Package Identity

| Distribution | Import | Role |
|---|---|---|
| `gds-analysis` | `gds_analysis.psuu` | Canonical PSUU implementation |
| `gds-psuu` | `gds_psuu` | Deprecated compatibility import path |

## What is this?

`gds_analysis.psuu` bridges `gds-sim` simulations with systematic parameter exploration. It provides:

- **Parameter spaces** -- `Continuous`, `Integer`, and `Discrete` dimensions with validation
- **Feasibility constraints** -- linear and functional constraints over parameter points
- **Composable KPIs** -- `Metric` (per-run scalar) + `Aggregation` (cross-run reducer) = `KPI`
- **3 search strategies** -- Grid, Random, and Bayesian/Optuna optimizers
- **Monte Carlo awareness** -- per-run distributions tracked alongside aggregated scores
- **Objectives and sensitivity** -- multi-KPI scoring, OAT, and Morris screening
- **Schema compatibility checks** -- validate sweep spaces against GDS parameter schemas

!!! note "Package naming"
    The canonical import path is `gds_analysis.psuu`. The `gds-psuu` distribution
    remains as a compatibility package and re-exports this API via `gds_psuu`,
    but that import path emits a deprecation warning.

## When to Use It

Use PSUU when you have a simulation model and need to evaluate many parameter
points, score KPI outcomes, optimize objectives, or run sensitivity analysis.
Use `gds-sim` first when you only need to execute one model trajectory.

## Architecture

```
gds-sim (pip install gds-sim)
|
|  Simulation engine: Model, StateUpdateBlock,
|  Simulation, Results (columnar storage).
|
+-- gds-analysis.psuu (pip install gds-analysis)
    |
    |  Parameter search: ParameterSpace, Metric, Aggregation,
    |  KPI, Evaluator, Sweep, Optimizer.
    |
    +-- Your application
        |
        |  Concrete models, parameter studies,
        |  sensitivity analysis, optimization.
```

## Conceptual Hierarchy

The package follows a clear hierarchy from parameters to optimization:

```
Parameter Point          {"growth_rate": 0.05}
    |
    v
Simulation              Model + timesteps + N runs
    |
    v
Results                 Columnar data (timestep, substep, run, state vars)
    |
    v
Metric (per-run)        final_value("pop") -> scalar per run
    |
    v
Aggregation (cross-run) mean_agg, std_agg, probability_above(...)
    |
    v
KPI (composed)          KPI(metric=..., aggregation=...) -> single score
    |
    v
Sweep                   Optimizer drives suggest/evaluate/observe loop
    |
    v
SweepResults            All evaluations + best() selection
```

## How the Sweep Loop Works

```
Optimizer.suggest()  -->  Evaluator.evaluate(params)  -->  Optimizer.observe(scores)
       ^                          |                              |
       |                   gds-sim Simulation                    |
       +------------------------ repeat --------------------------+
```

1. The **Optimizer** suggests a parameter point
2. The **Evaluator** injects params into a `gds-sim` Model, runs N Monte Carlo simulations
3. Each **KPI** extracts a per-run **Metric**, then **Aggregates** across runs into a single score
4. The **Optimizer** observes the scores and decides what to try next

## Relationship to the Ecosystem

PSUU is the parameter-search layer of `gds-analysis`. It uses `gds-sim` as the
runtime for evaluations and can validate parameter spaces against GDS parameter
schemas when those schemas are available.

## Quick Start

```bash
uv add gds-analysis
# or: pip install gds-analysis
```

See [Getting Started](getting-started.md) for a full walkthrough.

For a task-focused workflow, see the
[Parameter Sweep how-to](../guides/parameter-sweep.md).

## Credits

Built on gds-sim by [DynamicalSystemsGroup](https://dynamicalsystemsgroup.com).
