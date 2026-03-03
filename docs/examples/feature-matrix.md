# Feature Coverage Matrix

| Feature | SIR | Thermostat | Lotka-V | Prisoner's D | Insurance | Crosswalk | Evol. of Trust |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| BoundaryAction | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Policy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Mechanism | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| ControlAction | | ✓ | | | ✓ | ✓ | |
| `>>` (sequential) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `\|` (parallel) | ✓ | | ✓ | ✓ | | | |
| `.feedback()` | | ✓ | | | | | |
| `.loop()` | | | ✓ | ✓ | | | |
| CONTRAVARIANT wiring | | ✓ | | | | | |
| Temporal wiring | | | ✓ | ✓ | | | |
| Multi-variable Entity | | ✓ | | ✓ | ✓ | | |
| Multiple entities | ✓ | | ✓ | ✓ | ✓ | | |
| Parameters (Θ) | ✓ | ✓ | ✓ | | ✓ | ✓ | |
| OGS DSL | | | | | | | ✓ |
| OGS Feedback | | | | | | | ✓ |
| Simulation layer | | | | | | | ✓ |

## Complexity Progression

| Example | Roles Used | Operators | Key Teaching Point |
|---------|-----------|-----------|-------------------|
| SIR Epidemic | BA, P, M | `>>`, `\|` | Fundamentals, 3-role pipeline |
| Insurance | BA, P, CA, M | `>>` | ControlAction, complete 4-role taxonomy |
| Thermostat | BA, P, CA, M | `>>`, `.feedback()` | CONTRAVARIANT backward flow |
| Lotka-Volterra | BA, P, M | `>>`, `\|`, `.loop()` | COVARIANT temporal loops |
| Prisoner's Dilemma | BA, P, M | `\|`, `>>`, `.loop()` | Nested parallel, multi-entity |
| Crosswalk | BA, P, CA, M | `>>` | Mechanism design, governance |
| Evolution of Trust | OGS games | OGS feedback | Iterated PD, strategies, simulation |

**Roles:** BA = BoundaryAction, P = Policy, CA = ControlAction, M = Mechanism

!!! note "OGS examples"
    The Evolution of Trust uses the gds-games (OGS) DSL rather than gds-framework roles directly. OGS games (DecisionGame, CovariantFunction) compile to GDS blocks via the canonical bridge.
