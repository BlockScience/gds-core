# Game Types

## Signature

Every game has a `Signature` — a mapping from game-theoretic ports `(x, y, r, s)` to GDS interface ports:

| Game port | Direction | GDS port | Meaning |
|---|---|---|---|
| `x` | forward_in | Input | Observation / state |
| `y` | forward_out | Output | Action / decision |
| `r` | backward_in | Utility | Reward / payoff |
| `s` | backward_out | Coutility | Experience / cost |

## Six Atomic Game Types

### DecisionGame

A strategic agent that observes state, chooses an action, receives utility, and emits coutility.

```python
from ogs.dsl.games import DecisionGame

agent = DecisionGame(name="Agent", x="signal", y="action", r="reward", s="experience")
```

Has all four ports: x, y, r, s.

### CovariantFunction

A forward-only transformation — no backward ports.

```python
from ogs.dsl.games import CovariantFunction

sensor = CovariantFunction(name="Sensor", x="observation", y="signal")
```

Has x and y only.

### ContravariantFunction

A backward-only transformation — no forward ports.

```python
from ogs.dsl.games import ContravariantFunction

cost = ContravariantFunction(name="Cost", r="total_cost", s="unit_cost")
```

Has r and s only.

### DeletionGame

Discards a forward signal — has x but no y.

```python
from ogs.dsl.games import DeletionGame

sink = DeletionGame(name="Sink", x="unused_signal")
```

### DuplicationGame

Copies a forward signal — has x and produces two copies.

```python
from ogs.dsl.games import DuplicationGame

split = DuplicationGame(name="Split", x="signal", y="signal+signal")
```

### CounitGame

Terminal evaluation — has r but no s.

```python
from ogs.dsl.games import CounitGame

evaluate = CounitGame(name="Evaluate", r="final_utility")
```
