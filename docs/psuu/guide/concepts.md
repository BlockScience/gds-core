# Concepts

This page explains the core abstractions in `gds-psuu` and how they compose.

## The Hierarchy

```
Parameter Point  ->  Simulation  ->  Results  ->  Metric  ->  Aggregation  ->  KPI
```

Each layer transforms data from the previous one. The sweep loop orchestrates the full pipeline across many parameter points.

---

## Parameter Space

A `ParameterSpace` defines what to search. Each dimension has a name and a type:

| Dimension | Description | Grid behavior |
|-----------|-------------|---------------|
| `Continuous(min_val, max_val)` | Real-valued range | `n_steps` evenly spaced points |
| `Integer(min_val, max_val)` | Integer range (inclusive) | All integers in range |
| `Discrete(values=(...))` | Explicit set of values | All values |

```python
from gds_analysis.psuu import Continuous, Integer, Discrete, ParameterSpace

space = ParameterSpace(params={
    "learning_rate": Continuous(min_val=0.001, max_val=0.1),
    "hidden_layers": Integer(min_val=1, max_val=5),
    "activation": Discrete(values=("relu", "tanh", "sigmoid")),
})
```

Validation enforces `min_val < max_val` and at least one parameter.

---

## Metric

A `Metric` extracts a **single scalar from one simulation run**. It receives the full `Results` object and a run ID.

```python
from gds_analysis.psuu import Metric

# Built-in factories
from gds_analysis.psuu import final_value, trajectory_mean, max_value, min_value

final_value("population")      # value at last timestep
trajectory_mean("population")  # mean over all timesteps
max_value("population")        # maximum over all timesteps
min_value("population")        # minimum over all timesteps
```

Custom metrics:

```python
Metric(
    name="range",
    fn=lambda results, run: (
        max_value("x").fn(results, run) - min_value("x").fn(results, run)
    ),
)
```

The `MetricFn` signature is `(Results, int) -> float` where the int is the run ID.

---

## Aggregation

An `Aggregation` reduces a **list of per-run values into a single scalar**. It operates on `list[float]` and returns `float`.

```python
from gds_analysis.psuu import mean_agg, std_agg, percentile_agg, probability_above, probability_below

mean_agg                    # arithmetic mean
std_agg                     # sample standard deviation
percentile_agg(50)          # median (50th percentile)
percentile_agg(95)          # 95th percentile
probability_above(100.0)    # fraction of runs > 100
probability_below(0.0)      # fraction of runs < 0 (risk measure)
```

Custom aggregations:

```python
from gds_analysis.psuu import Aggregation

cv_agg = Aggregation(
    name="cv",
    fn=lambda vals: (
        (sum((x - sum(vals)/len(vals))**2 for x in vals) / (len(vals)-1))**0.5
        / (sum(vals)/len(vals))
        if len(vals) > 1 and sum(vals) != 0 else 0.0
    ),
)
```

---

## KPI

A `KPI` composes a Metric and an Aggregation into a named score:

```python
from gds_analysis.psuu import KPI, final_value, std_agg

kpi = KPI(
    name="uncertainty",
    metric=final_value("population"),  # per-run: final value
    aggregation=std_agg,               # cross-run: standard deviation
)
```

If `aggregation` is omitted, `mean_agg` is used by default.

### Per-run access

Metric-based KPIs expose the full distribution:

```python
results = simulation_results  # from gds-sim
per_run_values = kpi.per_run(results)  # [val_run1, val_run2, ...]
aggregated = kpi.compute(results)       # single float
```

### Legacy KPIs

The older `fn`-based interface operates on the full `Results` at once:

```python
from gds_analysis.psuu import KPI, final_state_mean

kpi = KPI(name="pop", fn=lambda r: final_state_mean(r, "population"))
```

Legacy KPIs cannot use `per_run()` and don't produce distributions. Prefer metric-based KPIs for new code.

---

## Evaluator

The `Evaluator` bridges parameter points to scored KPIs:

1. Takes a parameter point `{"growth_rate": 0.05}`
2. Injects params into the `gds-sim` Model
3. Runs N Monte Carlo simulations
4. Computes each KPI on the results
5. Returns `EvaluationResult` with scores and distributions

```python
from gds_analysis.psuu import Evaluator

evaluator = Evaluator(
    base_model=model,
    kpis=[kpi1, kpi2],
    timesteps=100,
    runs=10,
)
result = evaluator.evaluate({"growth_rate": 0.05})
# result.scores == {"kpi1_name": 42.0, "kpi2_name": 3.14}
# result.distributions == {"kpi1_name": [per-run values...]}
```

---

## Optimizer

An `Optimizer` implements the suggest/observe loop:

| Optimizer | Strategy | When to use |
|-----------|----------|-------------|
| `GridSearchOptimizer(n_steps)` | Exhaustive cartesian product | 1-2 dimensions, need full coverage |
| `RandomSearchOptimizer(n_samples, seed)` | Uniform random sampling | Higher dimensions, exploration |
| `BayesianOptimizer(n_calls, target_kpi)` | Gaussian process surrogate | Expensive evaluations, optimization |

All optimizers implement the same interface:

```python
optimizer.setup(space, kpi_names)
while not optimizer.is_exhausted():
    params = optimizer.suggest()
    # ... evaluate ...
    optimizer.observe(params, scores)
```

---

## Sweep

`Sweep` is the top-level orchestrator that connects everything:

```python
from gds_analysis.psuu import Sweep

sweep = Sweep(
    model=model,
    space=space,
    kpis=kpis,
    optimizer=optimizer,
    timesteps=100,
    runs=10,
)
results = sweep.run()
```

### SweepResults

```python
results.evaluations       # list[EvaluationResult] -- all evaluations
results.summaries         # list[EvaluationSummary] -- params + scores only
results.best("kpi_name")  # best evaluation for a KPI
results.to_dataframe()    # pandas DataFrame (requires pandas)
```
