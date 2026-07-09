# Getting Started

## Installation

```bash
uv add gds-analysis
# or: pip install gds-analysis
```

For Bayesian optimization (optional):

```bash
uv add "gds-analysis[psuu]"
# or: pip install "gds-analysis[psuu]"
```

For development (monorepo):

```bash
git clone https://github.com/DynamicalSystemsGroup/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Parameter Sweep

Define a `gds-sim` model, then sweep a parameter to find the best value:

```python
from gds_sim import Model, StateUpdateBlock
from gds_analysis.psuu import (
    KPI,
    Continuous,
    GridSearchOptimizer,
    ParameterSpace,
    Sweep,
    final_value,
    mean_agg,
)


# 1. Define a growth model
def growth_policy(state, params, **kw):
    return {"delta": state["population"] * params["growth_rate"]}


def update_pop(state, params, *, signal=None, **kw):
    return ("population", state["population"] + signal["delta"])


model = Model(
    initial_state={"population": 100.0},
    state_update_blocks=[
        StateUpdateBlock(
            policies={"growth": growth_policy},
            variables={"population": update_pop},
        )
    ],
)

# 2. Define what to search
space = ParameterSpace(
    params={"growth_rate": Continuous(min_val=0.01, max_val=0.2)}
)

# 3. Define what to measure
kpis = [
    KPI(
        name="avg_final_pop",
        metric=final_value("population"),    # per-run: final value
        aggregation=mean_agg,                # cross-run: mean
    ),
]

# 4. Run the sweep
sweep = Sweep(
    model=model,
    space=space,
    kpis=kpis,
    optimizer=GridSearchOptimizer(n_steps=5),
    timesteps=10,
    runs=3,  # 3 Monte Carlo runs per parameter point
)
results = sweep.run()

# 5. Inspect results
best = results.best("avg_final_pop")
print(f"Best growth_rate: {best.params['growth_rate']:.3f}")
print(f"Best avg final pop: {best.scores['avg_final_pop']:.1f}")
```

## Composable KPIs

The key design is the **Metric + Aggregation = KPI** pattern:

```python
from gds_analysis.psuu import (
    KPI,
    final_value,
    trajectory_mean,
    max_value,
    mean_agg,
    std_agg,
    percentile_agg,
    probability_above,
)

# Mean of final population across runs
avg_final = KPI(name="avg_pop", metric=final_value("population"), aggregation=mean_agg)

# Standard deviation of final population (measures uncertainty)
std_final = KPI(name="std_pop", metric=final_value("population"), aggregation=std_agg)

# 90th percentile of trajectory means
p90_mean = KPI(name="p90_mean", metric=trajectory_mean("population"), aggregation=percentile_agg(90))

# Probability that max population exceeds 500
risk = KPI(name="boom_risk", metric=max_value("population"), aggregation=probability_above(500.0))
```

**Metric** extracts a scalar from each run. **Aggregation** reduces the per-run values to a single score.

If no aggregation is specified, `mean_agg` is used by default:

```python
# These are equivalent:
KPI(name="avg_pop", metric=final_value("population"))
KPI(name="avg_pop", metric=final_value("population"), aggregation=mean_agg)
```

## Per-Run Distributions

Metric-based KPIs track the full distribution across Monte Carlo runs:

```python
results = sweep.run()

for ev in results.evaluations:
    dist = ev.distributions["avg_final_pop"]
    print(f"  params={ev.params}, per_run={dist}")
    # e.g. per_run=[265.3, 265.3, 265.3] for deterministic model
```

## Multiple Optimizers

```python
from gds_analysis.psuu import GridSearchOptimizer, RandomSearchOptimizer

# Exhaustive grid (good for 1-2 dimensions)
grid = GridSearchOptimizer(n_steps=10)  # 10 points per continuous dim

# Random sampling (good for higher dimensions)
rand = RandomSearchOptimizer(n_samples=50, seed=42)
```

For Bayesian optimization (requires `gds-analysis[psuu]`):

```python
from gds_analysis.psuu.optimizers.bayesian import BayesianOptimizer

bayes = BayesianOptimizer(n_trials=30, target_kpi="avg_final_pop", seed=42)
```

## Legacy KPI Support

The older `fn`-based KPI interface still works:

```python
from gds_analysis.psuu import KPI, final_state_mean

# Legacy style (backwards compatible)
kpi = KPI(name="pop", fn=lambda r: final_state_mean(r, "population"))
```

Legacy KPIs don't track per-run distributions -- use metric-based KPIs for full Monte Carlo awareness.

## Objectives

Use objectives when selecting the best evaluation from multiple KPI scores:

```python
from gds_analysis.psuu import SingleKPI, WeightedSum

best_growth = results.best_by_objective(SingleKPI(name="avg_final_pop"))
balanced = results.best_by_objective(
    WeightedSum(weights={"avg_final_pop": 1.0, "risk": -0.5})
)
```

## Sensitivity Analysis

Sensitivity analyzers run an `Evaluator` over structured parameter variations
before or after a full sweep:

```python
from gds_analysis.psuu import Evaluator, OATAnalyzer

evaluator = Evaluator(base_model=model, kpis=kpis, timesteps=10, runs=3)
sensitivity = OATAnalyzer(n_levels=4).analyze(evaluator, space)

print(sensitivity.ranking("avg_final_pop"))
```

## Next Steps

- [Concepts](guide/concepts.md) -- Metric, Aggregation, KPI, and the full conceptual hierarchy
- [Parameter Spaces](guide/spaces.md) -- dimensions, validation, and grid generation
- [Optimizers](guide/optimizers.md) -- grid, random, and Bayesian search strategies
- [API Reference](api/init.md) -- complete auto-generated API docs
