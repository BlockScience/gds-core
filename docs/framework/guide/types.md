# Type System

gds-framework has two type systems that coexist at different levels.

## Token-Based Types

Lightweight structural matching at composition/wiring time. Port names auto-tokenize; `tokens_subset()` and `tokens_overlap()` check set containment.

```python
from gds import port, tokenize, tokens_overlap

p1 = port("Contact Signal")   # tokens: {"contact", "signal"}
p2 = port("Signal Strength")  # tokens: {"signal", "strength"}

tokens_overlap(p1.tokens, p2.tokens)  # True — "signal" in common
```

Used by composition validators, auto-wiring, and G-001/G-005 checks.

## TypeDef-Based Types

Rich runtime validation at the data level. TypeDef wraps a Python type + optional constraint predicate.

```python
from gds import typedef

Count = typedef("Count", int,
    constraint=lambda x: x >= 0,
    description="Non-negative count")

Count.check_value(5)    # True
Count.check_value(-1)   # False
```

Used by Spaces and Entities to validate actual data values.

### Built-in TypeDefs

| TypeDef | Python type | Constraint |
|---|---|---|
| `PositiveInt` | `int` | x > 0 |
| `NonNegativeFloat` | `float` | x >= 0 |
| `Probability` | `float` | 0 <= x <= 1 |
| `Timestamp` | `float` | x >= 0 |
| `TokenAmount` | `float` | x >= 0 |
| `AgentID` | `str` | non-empty |

## Interfaces & Ports

Every block has an `Interface` with four port groups:

```python
from gds import interface

iface = interface(
    forward_in=["Temperature"],
    forward_out=["Heater Command"],
    backward_in=["Energy Cost"],
    backward_out=[],
)
```

- **forward_in** / **forward_out** — covariant data flow
- **backward_in** / **backward_out** — contravariant flow (feedback, cost signals)
