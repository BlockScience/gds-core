# Feature Coverage Matrix

| Feature | SIR | Thermostat | Lotka-V | Prisoner's D | Insurance | Crosswalk |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| BoundaryAction | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Policy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Mechanism | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ControlAction | | ✓ | | | ✓ | ✓ |
| `>>` (sequential) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `\|` (parallel) | ✓ | | ✓ | ✓ | | |
| `.feedback()` | | ✓ | | | | |
| `.loop()` | | | ✓ | ✓ | | |
| CONTRAVARIANT wiring | | ✓ | | | | |
| Temporal wiring | | | ✓ | ✓ | | |
| Multi-variable Entity | | ✓ | | ✓ | ✓ | |
| Multiple entities | ✓ | | ✓ | ✓ | ✓ | |
| Parameters (Θ) | ✓ | ✓ | ✓ | | ✓ | ✓ |

## Complexity Progression

| Example | Roles Used | Operators | Key Teaching Point |
|---------|-----------|-----------|-------------------|
| SIR Epidemic | BA, P, M | `>>`, `\|` | Fundamentals, 3-role pipeline |
| Insurance | BA, P, CA, M | `>>` | ControlAction, complete 4-role taxonomy |
| Thermostat | BA, P, CA, M | `>>`, `.feedback()` | CONTRAVARIANT backward flow |
| Lotka-Volterra | BA, P, M | `>>`, `\|`, `.loop()` | COVARIANT temporal loops |
| Prisoner's Dilemma | BA, P, M | `\|`, `>>`, `.loop()` | Nested parallel, multi-entity |
| Crosswalk | BA, P, CA, M | `>>` | Mechanism design, governance |

**Roles:** BA = BoundaryAction, P = Policy, CA = ControlAction, M = Mechanism
