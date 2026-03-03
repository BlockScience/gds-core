# Evolution of Trust

**Iterated Prisoner's Dilemma** — OGS game structure with tournament simulation and evolutionary dynamics.

Based on Nicky Case's [The Evolution of Trust](https://ncase.me/trust/). Demonstrates how a single OGS specification can serve as the source of truth for both structural analysis and computational simulation.

## OGS Decomposition

```
Players: Alice, Bob
Actions: {Cooperate, Defect}
Payoff Matrix: (R, T, S, P) = (2, 3, -1, 0)
Composition: (alice | bob) >> payoff .feedback([payoff -> decisions])
```

## Composition

```python
pipeline = (alice_decision | bob_decision) >> payoff_computation
system = pipeline.feedback([payoff -> decisions])
```

```mermaid
flowchart TD
    subgraph Simultaneous Decisions
        Alice[Alice Decision]
        Bob[Bob Decision]
    end
    Simultaneous Decisions --> Payoff[[Payoff Computation]]
    Payoff -.Alice Payoff.-> Alice
    Payoff -.Bob Payoff.-> Bob
```

## What You'll Learn

- Building a 2-player normal-form game from OGS primitives (`DecisionGame`, `CovariantFunction`)
- Feedback composition for iterated play (payoffs fed back to decision nodes)
- Non-zero-sum payoff matrices with negative values (Sucker payoff S = -1)
- **Interoperability pattern**: same OGS specification consumed by multiple tools (visualization, simulation, equilibrium analysis)
- Strategy protocol design for agent-based simulation on top of GDS specifications

## Key Concepts

### OGS Game Structure

| Block | OGS Type | Purpose |
|---|---|---|
| Alice Decision | DecisionGame | Chooses Cooperate or Defect based on observation |
| Bob Decision | DecisionGame | Symmetric to Alice |
| Payoff Computation | CovariantFunction | Maps action pairs to payoffs via the matrix |

### Payoff Matrix

|  | Bob: Cooperate | Bob: Defect |
|---|:---:|:---:|
| **Alice: Cooperate** | (2, 2) | (-1, 3) |
| **Alice: Defect** | (3, -1) | (0, 0) |

T > R > P > S and 2R > T + S (satisfies the Prisoner's Dilemma conditions).

### Simulation Stack

The tournament code builds three layers on top of the OGS specification:

1. **Strategies** — 8 implementations (Tit for Tat, Grim Trigger, Detective, Pavlov, etc.) following a common `Strategy` protocol
2. **Tournament** — `play_match()` for iterated rounds, `play_round_robin()` for all-pairs competition
3. **Evolutionary dynamics** — `run_evolution()` for generational population selection

Each layer consumes only `get_payoff()` from the specification — no GDS internals needed.

### Terminal Conditions

| Outcome | Actions | Payoffs | Character |
|---|---|---|---|
| Mutual Cooperation | (C, C) | (2, 2) | Pareto optimal |
| Mutual Defection | (D, D) | (0, 0) | Nash equilibrium |
| Alice Exploits | (D, C) | (3, -1) | Temptation vs Sucker |
| Bob Exploits | (C, D) | (-1, 3) | Sucker vs Temptation |

## Files

- [model.py](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/games/evolution_of_trust/model.py)
- [strategies.py](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/games/evolution_of_trust/strategies.py)
- [tournament.py](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/games/evolution_of_trust/tournament.py)
- [test_model.py](https://github.com/BlockScience/gds-core/blob/main/packages/gds-examples/games/evolution_of_trust/test_model.py)

## Related

- [Interoperability Guide](../../guides/interoperability.md) — detailed explanation of the specification-as-interoperability-layer pattern
- [Prisoner's Dilemma](prisoners-dilemma.md) — the base GDS framework version (without OGS or simulation)
