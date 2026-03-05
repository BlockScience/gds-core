# gds-psuu

[![PyPI](https://img.shields.io/pypi/v/gds-psuu)](https://pypi.org/project/gds-psuu/)
[![Python](https://img.shields.io/pypi/pyversions/gds-psuu)](https://pypi.org/project/gds-psuu/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Parameter space search under uncertainty** -- explore, evaluate, and optimize simulation parameters with Monte Carlo awareness.

## What is this?

`gds-psuu` bridges `gds-sim` simulations with systematic parameter exploration. It provides:

- **Parameter spaces** -- `Continuous`, `Integer`, and `Discrete` dimensions with validation
- **Composable KPIs** -- `Metric` (per-run scalar) + `Aggregation` (cross-run reducer) = `KPI`
- **3 search strategies** -- Grid, Random, and Bayesian (optuna) optimizers
- **Monte Carlo awareness** -- per-run distributions tracked alongside aggregated scores
- **Zero mandatory dependencies** beyond `gds-sim` and `pydantic`

## Architecture

```
gds-sim (pip install gds-sim)
|
|  Simulation engine: Model, StateUpdateBlock,
|  Simulation, Results (columnar storage).
|
+-- gds-psuu (pip install gds-psuu)
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

## Quick Start

```bash
uv add gds-psuu
# or: pip install gds-psuu
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on gds-sim by [BlockScience](https://block.science).
