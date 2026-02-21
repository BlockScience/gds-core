# Quick Start

## Define Blocks

Every block has a **name**, an **interface** (typed ports), and a **role** that constrains its port layout.

```python
from gds import BoundaryAction, Policy, Mechanism, interface

sensor = BoundaryAction(
    name="Contact Process",
    interface=interface(forward_out=["Contact Signal"]),
)

policy = Policy(
    name="Infection Policy",
    interface=interface(
        forward_in=["Contact Signal"],
        forward_out=["Susceptible Delta", "Infected Delta", "Recovered Delta"],
    ),
)

update_s = Mechanism(
    name="Update Susceptible",
    interface=interface(forward_in=["Susceptible Delta"]),
    updates=[("Susceptible", "count")],
)
```

## Compose

Chain blocks with `>>` (sequential) and `|` (parallel). Types are checked at construction time.

```python
system = sensor >> policy >> (update_s | update_i | update_r)
```

## Compile & Verify

```python
from gds import compile_system, verify

ir = compile_system("SIR Epidemic", system)
report = verify(ir)
print(f"{report.checks_passed}/{report.checks_total} checks passed")
```

## Four Composition Operators

| Operator | Name | Direction | Use Case |
|---|---|---|---|
| `>>` | Sequential | Forward | Pipeline stages |
| `\|` | Parallel | Independent | Concurrent updates |
| `.feedback()` | Feedback | Backward (within timestep) | Cost signals, constraints |
| `.loop()` | Temporal | Forward (across timesteps) | Iteration, convergence |

## Next Steps

- [Architecture](../guide/architecture.md) — understand the two-layer design
- [Blocks & Roles](../guide/blocks.md) — role constraints and composition
- [Examples](https://blockscience.github.io/gds-examples) — six complete tutorial models
