# gds-psuu

[![PyPI](https://img.shields.io/pypi/v/gds-psuu)](https://pypi.org/project/gds-psuu/)
[![Python](https://img.shields.io/pypi/pyversions/gds-psuu)](https://pypi.org/project/gds-psuu/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Parameter space search under uncertainty** — explore, evaluate, and optimize simulation parameters with Monte Carlo awareness.

Built on top of [gds-sim](../gds-sim/), `gds-psuu` provides a search engine for intelligently exploring simulation parameter spaces to optimize KPIs.

## Install

```bash
uv add gds-psuu
# or: pip install gds-psuu

# For Bayesian optimization (optional):
uv add "gds-psuu[bayesian]"
```

## Quick Start

```python
from gds_sim import Model, StateUpdateBlock
from gds_psuu import (
    KPI, Continuous, GridSearchOptimizer,
    ParameterSpace, Sweep, final_value, mean_agg,
)

# Define a gds-sim model
model = Model(
    initial_state={"population": 100.0},
    state_update_blocks=[
        StateUpdateBlock(
            policies={"growth": lambda s, p, **kw: {"delta": s["population"] * p["growth_rate"]}},
            variables={"population": lambda s, p, signal=None, **kw: ("population", s["population"] + signal["delta"])},
        )
    ],
)

# Define what to search and what to measure
sweep = Sweep(
    model=model,
    space=ParameterSpace(params={"growth_rate": Continuous(min_val=0.01, max_val=0.2)}),
    kpis=[KPI(name="avg_pop", metric=final_value("population"), aggregation=mean_agg)],
    optimizer=GridSearchOptimizer(n_steps=5),
    timesteps=10,
    runs=3,
)
results = sweep.run()

best = results.best("avg_pop")
print(f"Best growth_rate: {best.params['growth_rate']:.3f}")
```

## Features

### Composable KPIs

**Metric** (per-run scalar) + **Aggregation** (cross-run reducer) = **KPI**:

```python
from gds_psuu import (
    KPI, final_value, trajectory_mean, max_value, min_value,
    mean_agg, std_agg, percentile_agg, probability_above, probability_below,
)

# Mean of final population across Monte Carlo runs
KPI(name="avg_pop", metric=final_value("population"), aggregation=mean_agg)

# 95th percentile of trajectory means
KPI(name="p95", metric=trajectory_mean("x"), aggregation=percentile_agg(95))

# Probability that max value exceeds a threshold
KPI(name="risk", metric=max_value("x"), aggregation=probability_above(500.0))
```

Per-run distributions are tracked in `EvaluationResult.distributions` for downstream analysis.

### Parameter Spaces

Three dimension types with validation:

```python
from gds_psuu import Continuous, Integer, Discrete, ParameterSpace

space = ParameterSpace(params={
    "learning_rate": Continuous(min_val=0.001, max_val=0.1),
    "layers": Integer(min_val=1, max_val=5),
    "activation": Discrete(values=("relu", "tanh")),
})
```

### Parameter Constraints

Define feasible regions with linear or functional constraints:

```python
from gds_psuu import LinearConstraint, FunctionalConstraint

# x + y <= 1.0
LinearConstraint(coefficients={"x": 1.0, "y": 1.0}, bound=1.0)

# Custom constraint function
FunctionalConstraint(fn=lambda p: p["x"] ** 2 + p["y"] ** 2 <= 1.0)
```

Grid search filters infeasible points; random search uses rejection sampling.

### Search Strategies

| Optimizer | Strategy | When to use |
|-----------|----------|-------------|
| `GridSearchOptimizer(n_steps)` | Exhaustive grid | 1-2 dimensions, full coverage |
| `RandomSearchOptimizer(n_samples, seed)` | Uniform random | Higher dimensions, exploration |
| `BayesianOptimizer(n_calls, target_kpi)` | Gaussian process (optuna) | Expensive sims, optimization |

### Composable Objectives

Multi-KPI optimization:

```python
from gds_psuu import SingleKPI, WeightedSum

# Single KPI (maximize or minimize)
obj = SingleKPI(name="avg_pop", maximize=True)

# Weighted combination of multiple KPIs
obj = WeightedSum(weights={"profit": 1.0, "risk": -0.5})

results.best_by_objective(obj)
```

### Sensitivity Analysis

Screen parameter importance before running expensive sweeps:

```python
from gds_psuu import OATAnalyzer, MorrisAnalyzer

# One-at-a-time: vary each parameter independently
oat = OATAnalyzer(n_steps=5)
result = oat.analyze(evaluator, space)

# Morris method: elementary effects (mu_star = influence, sigma = nonlinearity)
morris = MorrisAnalyzer(r=10, levels=4)
result = morris.analyze(evaluator, space)

result.ranking("my_kpi")  # parameters sorted by importance
```

## Architecture

```
Parameter Point  ->  Simulation  ->  Results  ->  Metric  ->  Aggregation  ->  KPI
                                                                                 |
Optimizer.suggest()  -->  Evaluator.evaluate(params)  -->  Optimizer.observe(scores)
       ^                          |                              |
       |                   gds-sim Simulation                    |
       +------------------------ repeat --------------------------+
```

## Documentation

Full docs at [blockscience.github.io/gds-core](https://blockscience.github.io/gds-core/psuu/).

## License

Apache-2.0 — [BlockScience](https://block.science)
