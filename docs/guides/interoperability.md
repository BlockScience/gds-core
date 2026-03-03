# Interoperability: From Specification to Computation

> GDS specifications are not just documentation — they are structured representations that project cleanly onto domain-specific computation. This guide demonstrates two concrete projections: **Nash equilibrium computation** (game theory) and **iterated tournament simulation** (evolutionary dynamics), both built on the same OGS game structure without modifying the framework.

---

## The Thesis

A GDS specification captures the **structural skeleton** of a system: blocks, roles, interfaces, composition, and wiring. By design, the framework provides no execution semantics — blocks describe *what* a system is, not *how* it runs.

This is a feature, not a limitation. It means the same specification can be consumed by multiple independent tools:

```
                    ┌─ Nash equilibrium solver (Nashpy)
OGS Pattern ─┬─ PatternIR ─┤
              │             └─ Mermaid visualization (ogs.viz)
              │
              └─ get_payoff() ─┬─ Iterated match simulator
                               ├─ Round-robin tournament
                               └─ Evolutionary dynamics engine
```

The specification is the **single source of truth**. The computations are **thin projections** that extract what they need and add domain-specific logic on top.

---

## Case Study: Prisoner's Dilemma

The Prisoner's Dilemma is formalized as an OGS composition:

```
(Alice Decision | Bob Decision) >> Payoff Computation
    .feedback([payoff -> decisions])
```

This encodes:

- **Two players** as `DecisionGame` blocks with (X, Y, R, S) port signatures
- **Payoff computation** as a `CovariantFunction` that maps action pairs to payoffs
- **Feedback** carrying payoffs back to decision nodes for iterated play
- **Terminal conditions** declaring all four action profiles and their payoffs
- **Action spaces** enumerating each player's available moves

The specification exists in two concrete instantiations:

| Variant | Payoffs (R, T, S, P) | Purpose |
|---|---|---|
| `prisoners_dilemma_nash` | (3, 5, 0, 1) | Standard PD — Nash equilibrium analysis |
| `evolution_of_trust` | (2, 3, -1, 0) | Nicky Case variant — iterated simulation |

Both share the identical OGS composition tree. Only the payoff parameters differ.

---

## Projection 1: Nash Equilibrium Computation

**Source:** `packages/gds-examples/games/prisoners_dilemma_nash/model.py`

The Nash equilibrium solver extracts payoff matrices from `PatternIR` metadata and delegates to [Nashpy](https://nashpy.readthedocs.io/) for equilibrium computation.

### What the specification provides

The OGS Pattern declares `action_spaces` and `terminal_conditions` as structured metadata:

```python
action_spaces=[
    ActionSpace(game="Alice Decision", actions=["Cooperate", "Defect"]),
    ActionSpace(game="Bob Decision", actions=["Cooperate", "Defect"]),
]
terminal_conditions=[
    TerminalCondition(
        name="Mutual Cooperation",
        actions={"Alice Decision": "Cooperate", "Bob Decision": "Cooperate"},
        payoff_description="R=3 each",
    ),
    # ... 3 more conditions
]
```

### What the projection adds

A thin extraction layer (`build_payoff_matrices`) parses terminal conditions into numpy arrays, then Nashpy computes equilibria via support enumeration:

```python
def build_payoff_matrices(ir: PatternIR):
    # Extract from PatternIR metadata → numpy arrays
    ...

def compute_nash_equilibria(ir: PatternIR):
    alice_payoffs, bob_payoffs = build_payoff_matrices(ir)
    game = nashpy.Game(alice_payoffs, bob_payoffs)
    return list(game.support_enumeration())
```

### What the projection verifies

Cross-references computed equilibria against hand-annotated terminal conditions — the specification declares which outcomes are Nash equilibria, and the solver confirms or refutes them:

```python
verification = verify_terminal_conditions(ir, equilibria)
# → matches: [Mutual Defection (confirmed)]
# → mismatches: [] (none — declared NE matches computed NE)
```

Additional analyses extracted from the same specification:

- **Dominant strategies** — Defect strictly dominates for both players
- **Pareto optimality** — Mutual Cooperation is Pareto optimal but not a NE
- **The dilemma** — the unique NE is not Pareto optimal

!!! note "No framework changes required"
    The Nash solver is 100 lines of pure Python + Nashpy. It reads from `PatternIR` metadata using the existing API. No modifications to gds-framework, gds-games, or any IR layer were needed.

---

## Projection 2: Iterated Tournament Simulation

**Source:** `packages/gds-examples/games/evolution_of_trust/`

The tournament simulator uses the same game structure but projects it differently — instead of computing equilibria, it *plays the game* repeatedly with concrete strategies.

### What the specification provides

The payoff matrix parameters (R=2, T=3, S=-1, P=0) and the game structure define the rules. A direct lookup function is derived from the specification:

```python
def get_payoff(action_a: str, action_b: str) -> tuple[int, int]:
    """Direct payoff lookup from action pair."""
    return {
        ("Cooperate", "Cooperate"): (R, R),
        ("Cooperate", "Defect"): (S, T),
        ("Defect", "Cooperate"): (T, S),
        ("Defect", "Defect"): (P, P),
    }[(action_a, action_b)]
```

### What the projection adds

Three layers of simulation logic, each consuming only `get_payoff()`:

**Layer 1 — Strategies.** Eight strategy implementations as a `Strategy` protocol: `choose(history, round_num) → action`. These are pure Python — no GDS dependency:

| Strategy | Logic | Character |
|---|---|---|
| Always Cooperate | Always C | Naive cooperator |
| Always Defect | Always D | Pure exploiter |
| Tit for Tat | Copy opponent's last move | Retaliatory but forgiving |
| Grim Trigger | C until betrayed, then D forever | Unforgiving |
| Detective | Probe C,D,C,C then exploit or TfT | Strategic prober |
| Tit for Two Tats | C unless opponent D'd twice in a row | Extra forgiving |
| Pavlov | Win-stay, lose-shift | Adaptive |
| Random | 50/50 coin flip | Baseline noise |

**Layer 2 — Tournament.** `play_match()` runs iterated rounds between two strategies. `play_round_robin()` runs all-pairs competition. Both use `get_payoff()` as the sole interface to the game specification.

**Layer 3 — Evolutionary dynamics.** `run_evolution()` runs generational selection: each generation plays a tournament, the worst performer loses a member, the best gains one. Population dynamics emerge from repeated tournament play.

### The simulation stack

```
┌──────────────────────────────────────────────┐
│            Evolutionary dynamics              │
│  run_evolution(populations, generations, ...) │
├──────────────────────────────────────────────┤
│          Round-robin tournament               │
│  play_round_robin(strategies, rounds, noise)  │
├──────────────────────────────────────────────┤
│            Iterated match                     │
│  play_match(strategy_a, strategy_b, rounds)   │
├──────────────────────────────────────────────┤
│          Payoff lookup                        │
│  get_payoff(action_a, action_b) → (int, int)  │
├──────────────────────────────────────────────┤
│   OGS specification (R=2, T=3, S=-1, P=0)    │
│   build_game() → build_pattern() → build_ir() │
└──────────────────────────────────────────────┘
```

Each layer is independently testable. The simulation code knows nothing about OGS composition trees, PatternIR, or GDS blocks — it only knows payoff values.

!!! note "Thin runner, not a general simulator"
    This is **not** a GDS execution engine. It is a domain-specific simulation that uses the GDS specification as its source of truth for game rules. The strategies, match logic, and evolutionary dynamics are all hand-written Python specific to the iterated PD. A general `gds-sim` would require solving the much harder problem of executing arbitrary GDS specifications — see [Research Boundaries](research-boundaries.md#research-question-2-what-does-a-timestep-mean-across-dsls).

---

## The Pattern: Specification as Interoperability Layer

Both projections follow the same architectural pattern:

```
1. Build OGS specification     →  Pattern + PatternIR
2. Extract domain-relevant     →  Payoff matrices (Nash)
   data from the specification    or payoff lookup (simulation)
3. Add domain-specific logic   →  Nashpy solver / Strategy protocol
4. Produce domain-specific     →  Equilibria / Tournament results /
   results                        Evolutionary trajectories
```

The specification serves as the **interoperability contract** between different analytical tools. Each tool consumes the subset it needs:

| Consumer | What it reads from the specification | What it adds |
|---|---|---|
| Nash solver | Action spaces, terminal conditions, payoff descriptions | Support enumeration, dominance analysis, Pareto optimality |
| Tournament | Payoff parameters (R, T, S, P) | Strategy implementations, match replay, noise model |
| Evolutionary engine | Payoff parameters | Population dynamics, generational selection |
| Mermaid visualizer | Game tree structure, flows, feedback | Diagram rendering |
| OGS reports | Full PatternIR (games, flows, metadata) | Jinja2 text reports |

No consumer modifies the specification. No consumer needs to understand the full OGS type system. Each extracts a projection and operates in its own domain vocabulary.

---

## Why This Matters

### For game theorists

GDS provides a **compositional specification language** for games that separates structure from analysis. The same game structure supports both closed-form equilibrium computation and agent-based simulation without duplication. New analytical tools (e.g., correlated equilibria, mechanism design verifiers) can be added as additional projections without modifying the game definition.

### For simulation engineers

GDS specifications serve as **machine-readable game rules** that simulation engines can consume. The specification defines the action spaces, payoff structure, and composition topology. The simulator provides strategies, scheduling, and dynamics. The boundary is clean: the specification says *what the game is*, the simulator says *how it plays out*.

### For software teams

The OGS composition tree is a **formal architecture diagram** that happens to be executable by analytical tools. The same `(Alice | Bob) >> Payoff .feedback(...)` description generates Mermaid diagrams for documentation, payoff matrices for game theorists, and payoff lookup functions for simulators. One source, multiple views.

### For the GDS ecosystem

This validates GDS as an **interoperability substrate**, not just a modeling framework. The canonical form `h = f ∘ g` with varying dimensionality of X absorbs game-theoretic (stateless), control-theoretic (stateful), and stock-flow (state-dominant) formalisms. Each domain projects what it needs from the shared representation without architectural changes.

---

## Running the Examples

### Nash equilibrium analysis

```bash
# Install dependencies
uv sync --all-packages --extra nash

# Run tests (22 tests)
uv run --package gds-examples pytest \
    packages/gds-examples/games/prisoners_dilemma_nash/ -v

# Interactive notebook
cd packages/gds-examples && \
    uv run marimo run guides/nash_equilibrium/notebook.py
```

### Evolution of Trust simulation

```bash
# Run tests (71 tests)
uv run --package gds-examples pytest \
    packages/gds-examples/games/evolution_of_trust/ -v

# Interactive notebook (with plotly charts)
cd packages/gds-examples && \
    uv run marimo run guides/evolution_of_trust/notebook.py
```

### Source files

| File | Purpose |
|---|---|
| `games/prisoners_dilemma_nash/model.py` | OGS structure + Nash solver + verification |
| `games/evolution_of_trust/model.py` | OGS structure with Nicky Case payoffs |
| `games/evolution_of_trust/strategies.py` | 8 strategy implementations |
| `games/evolution_of_trust/tournament.py` | Match, tournament, evolutionary dynamics |
| `guides/nash_equilibrium/notebook.py` | Interactive Nash analysis notebook |
| `guides/evolution_of_trust/notebook.py` | Interactive simulation notebook |

All paths relative to `packages/gds-examples/`.

---

## Connection to Research Boundaries

This work provides concrete evidence for two open questions in [Research Boundaries](research-boundaries.md):

**RQ2 (Timestep semantics):** The tournament simulator implements a specific execution model — synchronous iterated play with optional noise — on top of a structural specification that encodes no execution semantics. This is exactly the pattern anticipated in RQ2: "Each DSL defines its own execution contract if/when it adds simulation."

**RQ3 (OGS as degenerate dynamical system):** Both projections confirm that OGS games are pure policy (`h = g`, `f = ∅`). The Nash solver computes equilibria over the policy layer. The simulator plays strategies through the policy layer. Neither requires a state transition mechanism. The "iterated" aspect of the tournament is handled entirely by the simulation harness, not by GDS temporal loops.

**RQ4 (Cross-lens analysis):** The two projections operate on different analytical lenses — equilibrium (static, game-theoretic) vs. tournament dynamics (iterated, evolutionary). The specification supports both simultaneously. Whether the Nash equilibrium (Defect, Defect) is also an evolutionary stable strategy is answerable by running both tools on the same specification — a concrete instance of the cross-lens analysis envisioned in RQ4.
