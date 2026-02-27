# Build Your First Model

A progressive tutorial that walks through the GDS framework using a
thermostat/heater system as the running example. Each stage builds on the
previous one, introducing new concepts incrementally.

## Prerequisites

- Python 3.12+
- `gds-framework`, `gds-viz`, and `gds-control` installed
  (`uv sync --all-packages` from the repo root)

## Learning Path

| Stage | File | Concepts |
|-------|------|----------|
| 1 | `stage1_minimal.py` | Entity, BoundaryAction, Mechanism, `>>` composition, GDSSpec |
| 2 | `stage2_feedback.py` | Policy, `.loop()` temporal composition, parameters |
| 3 | `stage3_dsl.py` | gds-control DSL: ControlModel, compile_model, compile_to_system |
| 4 | `stage4_verify_viz.py` | Generic checks (G-001..G-006), semantic checks, Mermaid visualization |
| 5 | `stage5_query.py` | SpecQuery API: parameter influence, entity updates, causal chains |

## Running

Run any stage directly to see its output:

```bash
uv run python -m guides.getting_started.stage1_minimal
```

Run the test suite:

```bash
uv run --package gds-examples pytest packages/gds-examples/guides/getting_started/ -v
```
