# CLAUDE.md -- gds-sim

## Package Identity

`gds-sim` is a high-performance discrete-time simulation engine for the GDS ecosystem. Standalone (pydantic-only dependency, no gds-framework import). cadCAD-compatible function signatures.

- **Import**: `import gds_sim`
- **Dependencies**: `pydantic>=2.10`
- **Optional**: `[pandas]` for DataFrame conversion

## Architecture

| Module | Purpose |
|--------|---------|
| `types.py` | `State`, `Signal`, `Params`, `PolicyFn`, `SUFn`, `StateUpdateBlock`, `Hooks` |
| `model.py` | `Model` (initial state + blocks + params), `Simulation`, `Experiment` |
| `engine.py` | Hot-path execution loop — no deepcopy, no wrapping at runtime |
| `results.py` | `Results` — columnar dict-of-lists with pre-allocation |
| `compat.py` | cadCAD signature auto-detection (4-arg policy, 5-arg SUF → wrapped) |
| `parallel.py` | `ProcessPoolExecutor` for multi-subset/multi-run parallelism (fork) |

### Execution model

```
for each (subset, run):
    state = dict(initial_state)
    for t in range(1, timesteps + 1):
        for block in blocks:
            signal = execute_policies(block, state, params)  # all read same state
            state = execute_sufs(block, state, signal)       # simultaneous within block
```

- **Simultaneous within block**: All SUFs in one block read the pre-block state
- **Sequential across blocks**: Each block sees the state from the previous block
- **Shallow copy only**: `dict(state)` per block (~10ns), no deepcopy

### Results pre-allocation

`Results.preallocate(sim)` computes exact row count: `(1 + timesteps * n_blocks) * runs * n_subsets`. Columnar storage avoids per-row dict overhead.

## Commands

```bash
uv run --package gds-sim pytest packages/gds-sim/tests -v
```
