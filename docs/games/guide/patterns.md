# Patterns & Composition

## Pattern

A `Pattern` groups games, flows, and metadata into a compilable unit.

```python
from ogs.dsl.pattern import Pattern

pattern = Pattern(
    name="Simple Decision",
    game=sensor >> agent,
    description="A sensor feeds an agent",
)
```

## Composition Operators

### Sequential (`>>`)

```python
pipeline = sensor >> agent >> evaluator
```

Auto-wires by token overlap between y (output) and x (input) ports.

### Parallel (`|`)

```python
agents = alice | bob
```

Independent games — no auto-wiring.

### Feedback (`.feedback()`)

```python
game = (sensor >> agent).feedback(wirings)
```

Within-timestep backward flow. Requires CONTRAVARIANT wirings.

### Corecursive (`.corecursive()`)

```python
game = (sensor >> agent).corecursive(wirings)
```

Extends GDS with a CORECURSIVE composition type — cross-timestep feedback specific to game-theoretic patterns.

## Flow Types

| Flow | Direction | Use Case |
|---|---|---|
| SEQUENTIAL | Forward | Pipeline stages |
| PARALLEL | Independent | Concurrent agents |
| FEEDBACK | Backward | Utility signals |
| CORECURSIVE | Cross-timestep | Iterated games |

## Pattern Metadata

Patterns can include domain-specific metadata:

```python
from ogs.dsl.pattern import TerminalCondition, ActionSpace, StateInitialization

pattern = Pattern(
    name="Iterated PD",
    game=game,
    terminal_conditions=[
        TerminalCondition(name="max_rounds", description="Stop after N rounds"),
    ],
    action_spaces=[
        ActionSpace(name="cooperate_defect", values=["C", "D"]),
    ],
)
```
