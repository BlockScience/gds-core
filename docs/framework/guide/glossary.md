# Glossary

GDS terminology mapped to framework concepts.

| Term | Definition | In the framework |
|---|---|---|
| **State** (x) | The current configuration of the system — a point in the state space | A value held by `StateVariable`s inside an `Entity` |
| **State Space** (X) | All possible configurations; can be any data structure, not just ℝⁿ | Product of all `Entity` variables, each typed by `TypeDef` |
| **Input** (u) | An external or agent-chosen action that influences the next state | A signal flowing through `Port`s on a block's `Interface` |
| **Admissible Input Space** (U_x) | The set of inputs available *given* the current state x | Constraints encoded in `ControlAction` blocks |
| **Input Map** (g) | Selects an input u from the admissible set — may be a decision-maker or stochastic process | `BoundaryAction` (exogenous) or `Policy` (endogenous) |
| **State Update Map** (f) | Takes current state and chosen input, produces the next state: f(x, u) → x⁺ | `Mechanism` blocks — the only blocks that write to state |
| **State Transition Map** (h) | The composed pipeline h = f\|_x ∘ g — one full step of the system | The wiring produced by `>>` composition |
| **Trajectory** (x₀, x₁, ...) | A sequence of states produced by repeatedly applying h | Temporal iteration via `.loop()` |
| **Reachability** | Can the system reach state y from state x through some sequence of inputs? | `check_reachability()` in the verification engine |
| **Controllability** | Can the system be steered to a target state from any nearby initial condition? | Formal property checked at the spec level |
| **Configuration Space** | The subset of X where every point is reachable from some initial condition | Characterized by transitive closure over the wiring graph |

## Intellectual Lineage

- **GDS formalism** (Roxin 1960s; [Zargham & Shorish 2022](https://doi.org/10.57938/e8d456ea-d975-4111-ac41-052ce73cb0cc)) — state transitions composed over arbitrary data structures
- **MSML** (BlockScience) — block roles, parameter tracking, typed transmission channels
- **BDP-lib** (Block Diagram Protocol) — abstract/concrete separation, structural validation
- **Categorical cybernetics** (Ghani, Hedges et al.) — bidirectional composition with contravariant feedback
