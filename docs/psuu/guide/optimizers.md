# Optimizers

All optimizers implement the same `Optimizer` interface: `setup()`, `suggest()`, `observe()`, `is_exhausted()`. The `Sweep` class drives this loop automatically.

## GridSearchOptimizer

Exhaustive evaluation of every point in a regular grid.

```python
from gds_analysis.psuu import GridSearchOptimizer

optimizer = GridSearchOptimizer(n_steps=10)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_steps` | `int` | `5` | Points per continuous dimension |

**Behavior:** Generates the full cartesian product via `ParameterSpace.grid_points()`, then evaluates each point exactly once. Does not adapt based on observed scores.

**When to use:** Small parameter spaces (1-2 dimensions), need complete coverage, want reproducible results.

**Total evaluations:** `n_steps^(n_continuous) * product(integer_ranges) * product(discrete_sizes)`

---

## RandomSearchOptimizer

Uniform random sampling across the parameter space.

```python
from gds_analysis.psuu import RandomSearchOptimizer

optimizer = RandomSearchOptimizer(n_samples=50, seed=42)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_samples` | `int` | `20` | Total parameter points to sample |
| `seed` | `int \| None` | `None` | Random seed for reproducibility |

**Behavior:** Samples each dimension independently -- `uniform(min, max)` for Continuous, `randint(min, max)` for Integer, `choice(values)` for Discrete. Does not adapt based on observed scores.

**When to use:** Higher-dimensional spaces where grid search is infeasible, initial exploration before Bayesian optimization.

---

## BayesianOptimizer

Gaussian process surrogate model that learns from past evaluations.

!!! note "Optional dependency"
    Requires `scikit-optimize`. Install with: `uv add "gds-psuu[bayesian]"`

```python
from gds_analysis.psuu.optimizers.bayesian import BayesianOptimizer

optimizer = BayesianOptimizer(
    n_calls=30,
    target_kpi="avg_final_pop",
    maximize=True,
    seed=42,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_calls` | `int` | `20` | Total evaluations (initial + optimization) |
| `target_kpi` | `str \| None` | `None` | KPI to optimize (defaults to first) |
| `maximize` | `bool` | `True` | Maximize (True) or minimize (False) |
| `seed` | `int \| None` | `None` | Random seed |

**Behavior:** Starts with random exploration (`min(5, n_calls)` initial points), then uses a Gaussian process surrogate to balance exploration and exploitation. Optimizes a single target KPI.

**When to use:** Expensive simulations where you want to find the optimum with fewer evaluations. Works best with continuous parameters.

---

## Custom Optimizers

Subclass `Optimizer` to implement your own search strategy:

```python
from gds_analysis.psuu.optimizers.base import Optimizer
from gds_analysis.psuu.space import ParameterSpace
from gds_analysis.psuu.types import KPIScores, ParamPoint


class MyOptimizer(Optimizer):
    def setup(self, space: ParameterSpace, kpi_names: list[str]) -> None:
        # Initialize search state
        ...

    def suggest(self) -> ParamPoint:
        # Return next parameter point to evaluate
        ...

    def observe(self, params: ParamPoint, scores: KPIScores) -> None:
        # Learn from evaluation results
        ...

    def is_exhausted(self) -> bool:
        # Return True when search is complete
        ...
```
