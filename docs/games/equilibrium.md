# Equilibrium Analysis

The `ogs.equilibrium` module computes Nash equilibria for two-player normal-form games using [Nashpy](https://nashpy.readthedocs.io/).

## Installation

```bash
uv add "gds-games[nash]"
```

The `[nash]` extra installs `nashpy` and `numpy`.

## Key Types and Functions

| Name | Purpose |
|------|---------|
| `extract_payoff_matrices(ir)` | Extract `(A, B)` payoff matrices from a two-player `PatternIR` |
| `compute_nash(ir, method)` | Compute Nash equilibria from a compiled `PatternIR` |
| `NashResult` | Container for equilibrium strategies with `support()` and `expected_payoffs()` |

## Solver Methods

| Method | Algorithm | Notes |
|--------|-----------|-------|
| `"support_enumeration"` (default) | Support enumeration | Exact, finds all Nash equilibria |
| `"vertex_enumeration"` | Vertex enumeration | Alternative exact enumeration |
| `"lemke_howson"` | Lemke-Howson pivoting | Fast, returns one equilibrium |

## Example: Prisoner's Dilemma

Define payoffs via `TerminalCondition` entries, then compute equilibria:

```python
from ogs.dsl.pattern import TerminalCondition

# Prisoner's Dilemma payoff structure
terminal_conditions = [
    TerminalCondition(
        name="CC",
        actions={"Player1": "Cooperate", "Player2": "Cooperate"},
        outcome="mutual_cooperation",
        payoffs={"Player1": 3.0, "Player2": 3.0},
    ),
    TerminalCondition(
        name="CD",
        actions={"Player1": "Cooperate", "Player2": "Defect"},
        outcome="sucker",
        payoffs={"Player1": 0.0, "Player2": 5.0},
    ),
    TerminalCondition(
        name="DC",
        actions={"Player1": "Defect", "Player2": "Cooperate"},
        outcome="temptation",
        payoffs={"Player1": 5.0, "Player2": 0.0},
    ),
    TerminalCondition(
        name="DD",
        actions={"Player1": "Defect", "Player2": "Defect"},
        outcome="mutual_defection",
        payoffs={"Player1": 1.0, "Player2": 1.0},
    ),
]
```

Extract matrices and solve:

```python
from ogs.equilibrium import extract_payoff_matrices, compute_nash

# Extract payoff matrices from a compiled PatternIR
matrices = extract_payoff_matrices(pattern_ir)
print(matrices.A)  # Player 1's payoff matrix
print(matrices.B)  # Player 2's payoff matrix

# Find Nash equilibria
equilibria = compute_nash(pattern_ir)
for ne in equilibria:
    print(f"Player 1: {dict(zip(ne.actions1, ne.sigma1))}")
    print(f"Player 2: {dict(zip(ne.actions2, ne.sigma2))}")
    print(f"Support: {ne.support()}")
    print(f"Expected payoffs: {ne.expected_payoffs(matrices)}")
```

## NashResult

Each `NashResult` contains:

- **`sigma1`** / **`sigma2`** -- mixed strategy vectors (numpy arrays)
- **`actions1`** / **`actions2`** -- action labels corresponding to each strategy index
- **`support()`** -- returns the set of actions played with positive probability for each player
- **`expected_payoffs(matrices)`** -- computes `(E[payoff1], E[payoff2])` under the equilibrium strategies

## Direct Matrix Input

You can also bypass IR extraction and supply payoff matrices directly:

```python
import numpy as np
from ogs.equilibrium import compute_nash_from_matrices

A = np.array([[3, 0], [5, 1]])  # Player 1 payoffs
B = np.array([[3, 5], [0, 1]])  # Player 2 payoffs

equilibria = compute_nash_from_matrices(A, B, method="support_enumeration")
```

## Limitations

- **2-player only** -- games with more than 2 action spaces raise `ValueError`
- **Complete information** -- all joint action profiles must have numeric payoffs
- **Normal form** -- extensive-form games must be converted to normal form first
- **Numerical precision** -- mixed strategy equilibria may have floating-point rounding

## Next Steps

- [Game Types](guide/game-types.md) -- all 6 atomic game types
- [Patterns & Composition](guide/patterns.md) -- composing complex multi-player games
- [Getting Started](getting-started.md) -- basic game definition workflow
