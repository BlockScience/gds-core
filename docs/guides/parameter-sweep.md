# Parameter Sweep

This guide shows how to evaluate a simulation model across many parameter
points with PSUU.

PSUU is provided by `gds-analysis` under the `gds_analysis.psuu` import path. It
uses `gds-sim` models as executable inputs, then adds parameter spaces, KPIs,
optimizers, and sensitivity analysis.

## Install

```bash
uv add gds-analysis gds-sim
```

For Bayesian optimization support:

```bash
uv add "gds-analysis[psuu]"
```

## Start from a Simulation Model

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
)
```

## Define the Parameter Space

```python
from gds_analysis.psuu import Continuous, ParameterSpace

space = ParameterSpace(
    params={"growth_rate": Continuous(min_val=0.01, max_val=0.2)}
)
```

Use `Continuous`, `Integer`, and `Discrete` dimensions to describe the values
that an optimizer may test. Add constraints when only some combinations are
feasible.

## Define KPIs

A KPI combines a per-run metric with an aggregation across runs.

```python
from gds_analysis.psuu import KPI, final_value, mean_agg, std_agg

kpis = [
    KPI(
        name="avg_final_population",
        metric=final_value("population"),
        aggregation=mean_agg,
    ),
    KPI(
        name="uncertainty",
        metric=final_value("population"),
        aggregation=std_agg,
    ),
]
```

Use risk-style aggregations such as `probability_above()` or
`probability_below()` when the question is about threshold violations instead of
average performance.

## Run the Sweep

```python
from gds_analysis.psuu import GridSearchOptimizer, Sweep

sweep = Sweep(
    model=model,
    space=space,
    kpis=kpis,
    optimizer=GridSearchOptimizer(n_steps=5),
    timesteps=10,
    runs=3,
)

results = sweep.run()
best = results.best("avg_final_population")

print(best.params)
print(best.scores)
```

Use grid search for small spaces where coverage matters. Use random search for
larger spaces. Use Bayesian optimization when evaluations are expensive and one
KPI is the main target.

## Inspect Distributions

Metric-based KPIs keep the per-run distribution for each parameter point:

```python
for evaluation in results.evaluations:
    values = evaluation.distributions["avg_final_population"]
    print(evaluation.params, values)
```

This is useful when the average score hides high variance or tail risk.

## Add Sensitivity Analysis

Sensitivity analyzers reuse the same model and KPIs:

```python
from gds_analysis.psuu import Evaluator, OATAnalyzer

evaluator = Evaluator(base_model=model, kpis=kpis, timesteps=10, runs=3)
sensitivity = OATAnalyzer(n_levels=4).analyze(evaluator, space)

print(sensitivity.ranking("avg_final_population"))
```

## Next Steps

- Read [PSUU concepts](../psuu/guide/concepts.md) for the full hierarchy.
- Read [parameter spaces](../psuu/guide/spaces.md) for dimensions and
  constraints.
- Read [optimizers](../psuu/guide/optimizers.md) for grid, random, and Bayesian
  strategies.

