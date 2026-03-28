# CLAUDE.md -- gds-psuu

## Package Identity

`gds-psuu` provides parameter space search under uncertainty for the GDS ecosystem. Wraps Optuna for Bayesian optimization and supports grid/random search, sensitivity analysis (Morris, OAT), and KPI-based evaluation.

- **Import**: `import gds_psuu`
- **Dependencies**: `gds-sim>=0.1.0`, `pydantic>=2.10`, `pandas>=2.0`, `optuna>=4.0`

## Architecture

| Module | Purpose |
|--------|---------|
| `space.py` | `ParameterSpace`, `Continuous`, `Discrete`, `Integer` — search domain definition |
| `kpi.py` | `KPI` — key performance indicators (`final_state_mean`, `time_average`, etc.) |
| `metric.py` | `Metric`, `Aggregation` — trajectory metrics (`final_value`, `max_value`, `probability_above`) |
| `objective.py` | `Objective`, `SingleKPI`, `WeightedSum` — optimization targets |
| `evaluation.py` | `Evaluator` — runs simulation, computes KPIs, aggregates |
| `sweep.py` | `Sweep` — orchestrates parameter sweep + evaluation |
| `sensitivity.py` | `MorrisAnalyzer`, `OATAnalyzer` — sensitivity analysis |
| `optimizers/` | `GridSearchOptimizer`, `RandomSearchOptimizer`, `BayesianOptimizer` |
| `results.py` | `SweepResults`, `EvaluationSummary` — structured output |

### Pipeline

```
ParameterSpace → Sweep(model, space, kpis, objective) → sweep.run()
    → evaluates each param point via gds-sim
    → computes KPIs per trajectory
    → returns SweepResults with best_point, all_results
```

## Commands

```bash
uv run --package gds-psuu pytest packages/gds-psuu/tests -v
```
