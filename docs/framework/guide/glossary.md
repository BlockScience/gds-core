# Glossary

GDS terminology mapped to framework concepts.

| Term | Definition | In the framework |
|---|---|---|
| **State** (x) | The current configuration of the system — a point in the state space | A value held by `StateVariable`s inside an `Entity` |
| **State Space** (X) | All possible configurations; can be any data structure, not just ℝⁿ | Product of all `Entity` variables, each typed by `TypeDef` |
| **Exogenous Signal** (z) | An external signal entering the system from outside | `BoundaryAction` outputs flowing through `Port`s. Paper uses u for the selected action; codebase uses z for exogenous signals to avoid conflation. |
| **Decision** (d) | The output of the policy mapping d = g(x, z) | `Policy` forward_out ports. Corresponds to the paper's selected action u ∈ U_x. |
| **Admissible Input Space** (U_x) | The set of inputs available *given* the current state x (paper Def 2.5) | Structural skeleton via `AdmissibleInputConstraint`; behavioral constraint requires runtime |
| **Input Map** (g) | Maps state and exogenous signals to a decision: g(x, z) → d | `Policy` blocks (endogenous decision logic) |
| **State Update Map** (f) | Takes current state and decision, produces the next state: f(x, d) → x⁺ | `Mechanism` blocks — the only blocks that write to state |
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
