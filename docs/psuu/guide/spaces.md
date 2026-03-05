# Parameter Spaces

## Dimension Types

### Continuous

A real-valued range with inclusive bounds.

```python
from gds_psuu import Continuous

dim = Continuous(min_val=0.0, max_val=1.0)
```

| Field | Type | Description |
|-------|------|-------------|
| `min_val` | `float` | Lower bound (inclusive) |
| `max_val` | `float` | Upper bound (inclusive) |

Validation: `min_val < max_val`, both must be finite.

Grid behavior: `n_steps` evenly spaced points from `min_val` to `max_val`.

---

### Integer

An integer range with inclusive bounds.

```python
from gds_psuu import Integer

dim = Integer(min_val=1, max_val=10)
```

| Field | Type | Description |
|-------|------|-------------|
| `min_val` | `int` | Lower bound (inclusive) |
| `max_val` | `int` | Upper bound (inclusive) |

Validation: `min_val < max_val`.

Grid behavior: all integers from `min_val` to `max_val` (ignores `n_steps`).

---

### Discrete

An explicit set of allowed values (any hashable type).

```python
from gds_psuu import Discrete

dim = Discrete(values=("adam", "sgd", "rmsprop"))
```

| Field | Type | Description |
|-------|------|-------------|
| `values` | `tuple[Any, ...]` | Allowed values |

Validation: at least 1 value.

Grid behavior: all values (ignores `n_steps`).

---

## ParameterSpace

Combines dimensions into a named parameter space:

```python
from gds_psuu import Continuous, Integer, Discrete, ParameterSpace

space = ParameterSpace(params={
    "learning_rate": Continuous(min_val=0.001, max_val=0.1),
    "batch_size": Integer(min_val=16, max_val=128),
    "optimizer": Discrete(values=("adam", "sgd")),
})
```

### Grid Generation

```python
points = space.grid_points(n_steps=5)
# Returns list of dicts, e.g.:
# [
#     {"learning_rate": 0.001, "batch_size": 16, "optimizer": "adam"},
#     {"learning_rate": 0.001, "batch_size": 16, "optimizer": "sgd"},
#     ...
# ]
```

The total number of grid points is the cartesian product:
`n_steps * (max_int - min_int + 1) * len(discrete_values)`

For the example above: `5 * 113 * 2 = 1130` points.

### Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `dimension_names` | `list[str]` | Ordered list of parameter names |
