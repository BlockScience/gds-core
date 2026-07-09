# Results Guide

## Result Shape

`Results` stores simulation output as a dict of columns. Each appended row
contains metadata and one value for each state variable.

| Column | Meaning |
|---|---|
| `timestep` | Outer simulation step |
| `substep` | State update block index |
| `run` | Monte Carlo run index |
| `subset` | Parameter subset index |
| state keys | Values from the model state |

```python
rows = results.to_list()
print(rows[0])
```

## Columnar Storage

The engine preallocates result capacity when it can compute the expected row
count:

```text
(1 + timesteps * number_of_blocks) * runs * parameter_subsets
```

Early exit can produce fewer rows than the preallocated capacity. Conversion
methods trim unused slots automatically.

## Convert to Lists

```python
rows = results.to_list()
```

This returns a cadCAD-compatible list of row dictionaries.

## Convert to pandas

```python
df = results.to_dataframe()
```

`to_dataframe()` requires pandas:

```bash
uv add "gds-sim[pandas]"
```

## Merge Results

`Experiment.run()` uses `Results.merge()` internally, but it can also be called
directly:

```python
from gds_sim import Results

merged = Results.merge([results_a, results_b])
```

Merging preserves row order within each input result object.

