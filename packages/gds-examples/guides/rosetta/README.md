# Cross-Domain Rosetta Stone

Three views of the same resource pool problem, each compiled to a GDS canonical form.

## The Resource Pool Scenario

A shared resource pool (water reservoir, inventory, commons) that agents interact
with through supply, consumption, or extraction. The same real-world system is
modeled through three different DSL lenses.

## Views

| View | Module | DSL | Character |
|------|--------|-----|-----------|
| Stock-Flow | `stockflow_view.py` | `stockflow` | Dynamical -- accumulation via rates |
| Control | `control_view.py` | `gds_control` | Dynamical -- regulation toward setpoint |
| Game Theory | `game_view.py` | `ogs` | Strategic -- stateless extraction game |

## Canonical Spectrum

All three views compile to `GDSSpec` and project to the canonical `h = f . g`
decomposition. The comparison table (`comparison.py`) shows how they differ:

```
View            |X|  |U|  |g|  |f|  Form                 Character
-----------------------------------------------------------------------
Stock-Flow        1    2    3    1  h_theta = f_theta . g_theta  Dynamical
Control           1    1    2    1  h_theta = f_theta . g_theta  Dynamical
Game Theory       0    1    3    0  h = g                Strategic
```

Key insight: **the same GDS composition algebra underlies all three**, but each
DSL decomposes the problem differently:

- **Stock-Flow**: State `X` is the resource level, updated by net flow rates.
  Two exogenous parameters (supply rate, consumption rate) drive the dynamics.
- **Control**: State `X` is the resource level, regulated by a feedback controller
  that tracks an exogenous reference setpoint.
- **Game Theory**: No state -- pure strategic interaction. Two agents simultaneously
  choose extraction amounts; a payoff function determines the outcome.

## Running

```bash
# Run all tests
uv run --package gds-examples pytest packages/gds-examples/guides/rosetta/ -v

# Print the comparison table
uv run --package gds-examples python -m guides.rosetta.comparison
```

## Unified Transition Calculus

The GDS canonical form provides a unified notation for all three:

```
h_theta : X -> X    where h = f . g
```

- When `|f| > 0` and `|g| > 0`: **Dynamical** system (stock-flow, control)
- When `|f| = 0` and `|g| > 0`: **Strategic** system (game theory)
- When `|g| = 0` and `|f| > 0`: **Autonomous** system (no policy)

This is the "Rosetta Stone" -- the same mathematical structure expressed in
different domain languages, all grounded in GDS theory.
