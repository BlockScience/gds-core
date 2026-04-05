# Parameter Spaces

## Dimension Types

### Continuous

A real-valued range with inclusive bounds.

```python
from gds_analysis.psuu import Continuous

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
from gds_analysis.psuu import Integer

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
from gds_analysis.psuu import Discrete

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
from gds_analysis.psuu import Continuous, Integer, Discrete, ParameterSpace

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

---

## Connecting to GDS Parameter Schema

When your system has a `GDSSpec` with a `ParameterSchema` (the declared parameter space, theta), you can connect it to the sweep so that the optimizer never silently explores values outside declared bounds or type constraints.

### Creating a ParameterSpace from a Schema

`ParameterSpace.from_parameter_schema()` automatically creates dimensions from the declared `ParameterDef` entries:

- `float` with bounds becomes `Continuous`
- `int` with bounds becomes `Integer`
- Parameters without bounds raise `ValueError` (bounds are required for sweep)
- Unsupported types raise `TypeError`

```python
from gds import GDSSpec, typedef, ParameterDef
from gds_analysis.psuu import ParameterSpace

spec = GDSSpec(name="my_system")
rate_type = typedef("Rate", float, constraint=lambda x: 0.0 <= x <= 1.0)
spec.register_parameter(ParameterDef(name="growth_rate", typedef=rate_type, bounds=(0.01, 0.5)))

space = ParameterSpace.from_parameter_schema(spec.parameter_schema)
# space.params == {"growth_rate": Continuous(min_val=0.01, max_val=0.5)}
```

### Validating an Existing Space

If you build your `ParameterSpace` manually, you can validate it against the schema:

```python
from gds_analysis.psuu import Continuous, ParameterSpace

space = ParameterSpace(params={
    "growth_rate": Continuous(min_val=-1.0, max_val=2.0),  # exceeds bounds
})

violations = space.validate_against_schema(spec.parameter_schema)
for v in violations:
    print(f"[{v.violation_type}] {v.param}: {v.message}")
```

Violation types:

| Type | Meaning |
|------|---------|
| `missing_from_schema` | Parameter is swept but not declared in the schema |
| `out_of_bounds` | Sweep range exceeds declared bounds or fails typedef constraint |
| `type_mismatch` | Dimension type does not match declared Python type |

### PSUU-001 Check

The `check_parameter_space_compatibility()` function wraps validation into the GDS `Finding` pattern:

```python
from gds_analysis.psuu import check_parameter_space_compatibility

findings = check_parameter_space_compatibility(space, spec.parameter_schema)
for f in findings:
    print(f"[{f.check_id}] {f.severity}: {f.message}")
```

### Sweep Integration

Pass `parameter_schema` to `Sweep` for automatic validation before the optimizer loop starts. If any `ERROR`-level violations are found, `run()` raises `ValueError`:

```python
from gds_analysis.psuu import Sweep

sweep = Sweep(
    model=sim_model,
    space=space,
    kpis=kpis,
    optimizer=optimizer,
    parameter_schema=spec.parameter_schema,  # optional validation
)
sweep.run()  # raises ValueError if space violates schema
```

!!! note
    The `parameter_schema` field is optional. If omitted, no validation is performed and the sweep runs as before. Install `gds-framework` (or use the `validation` extra: `pip install gds-analysis[psuu][validation]`) to use these features.
