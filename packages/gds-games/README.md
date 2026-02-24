# gds-games

[![PyPI](https://img.shields.io/pypi/v/gds-games)](https://pypi.org/project/gds-games/)
[![Python](https://img.shields.io/pypi/pyversions/gds-games)](https://pypi.org/project/gds-games/)
[![License](https://img.shields.io/github/license/BlockScience/gds-games)](LICENSE)

Typed DSL for compositional game theory, built on [gds-framework](https://github.com/BlockScience/gds-core/tree/main/packages/gds-framework).

## Table of Contents

- [Quick Start](#quick-start)
- [What is this?](#what-is-this)
- [Architecture](#architecture)
- [Game Types](#game-types)
- [Composition](#composition)
- [Multi-Agent Helpers](#multi-agent-helpers)
- [Pattern Registry](#pattern-registry)
- [IR Layers](#ir-layers)
- [Verification](#verification)
- [CLI](#cli)
- [Examples](#examples)
- [Status](#status)
- [Credits & Attribution](#credits--attribution)

## Quick Start

```bash
pip install gds-games
```

```python
from ogs.dsl.games import DecisionGame, CovariantFunction
from ogs.dsl.pattern import Pattern
from ogs import compile_to_ir, verify

# Define atomic games with typed signatures (x=input, y=output, r=utility, s=coutility)
sensor = CovariantFunction(name="Sensor", x="observation", y="signal")
agent = DecisionGame(name="Agent", x="signal", y="action", r="reward", s="experience")

# Compose sequentially (auto-wires by token matching)
game = sensor >> agent

# Wrap in a Pattern and compile to IR
pattern = Pattern(name="Simple Decision", game=game)
ir = compile_to_ir(pattern)

# Run verification checks
report = verify(ir)
print(f"{report.checks_passed}/{report.checks_total} checks passed")
```

## What is this?

`gds-games` extends the GDS framework with game-theoretic vocabulary from **compositional game theory** (Ghani, Hedges et al.). It provides:

- **6 atomic game types** with port-constraint validators
- **Pattern composition** — sequential, parallel, feedback, and corecursive operators
- **Multi-agent helpers** — `parallel()`, `multi_agent_composition()`, `reactive_decision_agent()` with configurable flags
- **Pattern registry** — `discover_patterns()` auto-discovers patterns from a directory; `Pattern.specialize()` derives named variants
- **Dual IR** — `PatternIR` for game-theoretic analysis + projection to GDS `SystemIR`
- **13 verification checks** — type matching (T-001..T-006) and structural validation (S-001..S-007)
- **Canonical bridge** — `compile_pattern_to_spec()` maps games to `GDSSpec` for `h = f ∘ g` projection
- **7 Markdown report templates** via Jinja2
- **6 Mermaid diagram generators** for visualization
- **CLI** — `ogs compile`, `ogs verify`, `ogs report`

### Information Flow Model

Every open game has four directed information channels:

```
X → 𝒢 → Y        (covariant / forward)
R ← 𝒢 ← S        (contravariant / feedback)
```

| Channel | Name | Direction | Description |
|---------|------|-----------|-------------|
| **X** | Observations | forward in | What the game observes |
| **Y** | Choices | forward out | What the game decides |
| **R** | Utilities | backward in | Outcomes the game receives |
| **S** | Coutilities | backward out | Valuations the game transmits upstream |

This bidirectional structure is the foundation of compositional game theory — games compose by wiring outputs to inputs, both forward and backward.

## Architecture

```
gds-framework (pip install gds-framework)
│
│  Domain-neutral composition algebra, typed spaces,
│  state model, verification engine, flat IR compiler.
│
└── gds-games (pip install gds-games)
    │
    │  Game-theoretic DSL: OpenGame types, Pattern composition,
    │  PatternIR, GDS canonical bridge, verification, reports, CLI.
    │
    └── Your application
        │
        │  Concrete game patterns, analysis notebooks,
        │  verification runners.
```

### Two Compilation Paths

```
Pattern (game tree + flows + metadata)
       │
       ├─── compile_to_ir() ──→ PatternIR (game-theoretic analysis, reports, viz)
       │                              │
       │                              └─── .to_system_ir() ──→ SystemIR (GDS generic checks)
       │
       └─── compile_pattern_to_spec() ──→ GDSSpec (canonical projection h = f ∘ g)
```

- **PatternIR** preserves game-theoretic structure — game types, flow types, corecursive composition. Used for reports and domain visualization.
- **GDSSpec** maps all games to `Policy` and inputs to `BoundaryAction`. Canonical projection yields `g = all games, f = ∅, X = ∅` — the system is pure policy (`h = g`), which is semantically correct for games that compute equilibria, not state updates.

## Game Types

Six atomic game types, each enforcing structural constraints on its signature:

### DecisionGame

A strategic decision — a player who observes context and chooses an action.

```python
DecisionGame(name="Player", x="state", y="action", r="payoff", s="experience")
```

Has all four channels: X, Y, R, S. The core building block for strategic interactions.

### CovariantFunction

A pure forward transformation: X → Y. No utility or coutility.

```python
CovariantFunction(name="Sensor", x="raw data", y="processed signal")
```

**Constraint:** R and S must be empty. The simplest game type — pure functional transformation without feedback.

### ContravariantFunction

A pure backward transformation: R → S. No observations or choices.

```python
ContravariantFunction(name="Evaluator", r="outcome", s="valuation")
```

**Constraint:** X and Y must be empty. The dual of CovariantFunction.

### DeletionGame

Discards an input channel: X → {}. Information is intentionally lost.

```python
DeletionGame(name="Filter", x="noise signal")
```

**Constraint:** Y must be empty. Represents intentional information filtering.

### DuplicationGame

Copies an input to multiple outputs: X → X × X. Information is broadcast.

```python
DuplicationGame(name="Broadcast", x="signal", y=("copy A", "copy B"))
```

**Constraint:** Y must have 2+ ports. Represents information broadcasting to multiple consumers.

### CounitGame

Future-conditioned observation: X → {}, with S = X. Technical game for temporal conditioning.

```python
CounitGame(name="Future Context", x="future observation", s="context for present")
```

**Constraint:** Y and R must be empty. Makes future observations available as coutility for upstream games.

## Composition

Games compose using the same operators as GDS blocks, plus one additional:

| Operator | Syntax | Description |
|----------|--------|-------------|
| Sequential | `a >> b` | Chain forward: Y of `a` feeds X of `b` |
| Parallel | `a \| b` | Side-by-side: independent games |
| Feedback | `a.feedback(wirings)` | Backward within timestep (CONTRAVARIANT) |
| Corecursive | `a.corecursive(wirings)` | Forward across timesteps (extends GDS `.loop()`) |

```python
# Sequential: sensor feeds into agent
pipeline = sensor >> agent

# Parallel: two independent agents
pair = alice | bob

# Combined: observe, then both agents decide
system = observation >> (alice | bob) >> payoff
```

### FeedbackFlow

A convenience subclass of `Flow` that defaults to `CONTRAVARIANT` direction — avoids repeating `direction=FlowDirection.CONTRAVARIANT` on every feedback wiring:

```python
from ogs.dsl.composition import FeedbackFlow

FeedbackFlow(source_game="Outcome", source_port="Outcome",
             target_game="Reactive Decision", target_port="Outcome")
# equivalent to: Flow(..., direction=FlowDirection.CONTRAVARIANT)
```

### Object References in Flows

`Flow` and `FeedbackFlow` accept `OpenGame` instances for `source_game`/`target_game` — they are coerced to name strings at construction time:

```python
out = outcome()
rd = reactive_decision()

# Pass game objects instead of strings
FeedbackFlow(source_game=out, source_port="Outcome",
             target_game=rd, target_port="Outcome")
```

## Multi-Agent Helpers

### reactive_decision_agent()

Builds a configurable single-agent decision loop from atomic games. Two boolean flags control which components are included:

```python
from ogs.dsl.library import reactive_decision_agent

# Full 5-game loop with feedback (default)
agent = reactive_decision_agent("Agent 1")

# Open-loop chain without feedback — for multi-agent patterns
agent = reactive_decision_agent("Agent 1", include_outcome=False, include_feedback=False)
```

| `include_outcome` | `include_feedback` | Returns | Games |
|---|---|---|---|
| `True` (default) | `True` (default) | `FeedbackLoop` | CB → Hist → Pol → RD → Out + 3 feedback flows |
| `False` | `True` | `FeedbackLoop` | CB → Hist → Pol → RD + 2 feedback flows |
| `True` | `False` | `SequentialComposition` | CB → Hist → Pol → RD → Out (open chain) |
| `False` | `False` | `SequentialComposition` | CB → Hist → Pol → RD (open chain) |

### parallel()

Compose a dynamic list of games in parallel — enables N-agent patterns without manually enumerating the `|` chain:

```python
from ogs.dsl.library import parallel

agents = [reactive_decision_agent(f"Agent {i}", include_outcome=False, include_feedback=False)
          for i in range(1, 4)]
agents_parallel = parallel(agents)
```

Also available as `ParallelComposition.from_list(games)`.

### multi_agent_composition()

Composes N open-loop agents in parallel, wires them into a shared router, and auto-generates all N × K contravariant feedback flows:

```python
from ogs.dsl.library import multi_agent_composition

agent1 = reactive_decision_agent("Agent 1", include_outcome=False, include_feedback=False)
agent2 = reactive_decision_agent("Agent 2", include_outcome=False, include_feedback=False)

game = multi_agent_composition(
    agents=[agent1, agent2],
    router=my_decision_router(),
    feedback_port_map={
        "outcome":    ("Outcome",        "Outcome"),
        "experience": ("Experience",     "Experience"),
        "history":    ("History Update", "History Update"),
    },
)
# Returns FeedbackLoop with 2 × 3 = 6 contravariant feedback flows
```

The three-step structure: (1) parallel composition of agents, (2) sequential into router, (3) feedback loop with auto-generated flows.

## Pattern Registry

### Pattern.specialize()

Derive a named pattern variant from a base, inheriting the game tree and overriding only metadata:

```python
base = Pattern(name="Base", game=game_tree, inputs=[...])

variant = base.specialize(
    name="Resource Exchange",
    terminal_conditions=[TerminalCondition(name="Agreement", ...)],
    action_spaces=[ActionSpace(game="Agent 1 Reactive Decision", actions=["accept", "reject"])],
    # inputs inherited from base automatically
)
```

The game tree is shared (not deep-copied). All other fields (`inputs`, `terminal_conditions`, `action_spaces`, `initializations`, `composition_type`, `source`) inherit from the base unless explicitly overridden.

### discover_patterns()

Auto-discover all `Pattern` objects from Python files in a directory:

```python
from ogs.registry import discover_patterns

# Scan directory for modules with a `pattern` attribute
all_patterns = discover_patterns("./patterns")

for name, pattern in all_patterns.items():
    ir = compile_to_ir(pattern)
    report = verify(ir)
```

Skips `__init__.py` and `_`-prefixed files. Silently skips modules that fail to import. Returns an ordered dict mapping module stem name to `Pattern` object.

Works well with pytest parametrize for batch verification:

```python
ALL_PATTERNS = discover_patterns(PATTERNS_DIR)

@pytest.mark.parametrize("name,pattern", ALL_PATTERNS.items())
def test_compile_all(name, pattern):
    ir = compile_to_ir(pattern)
    report = verify(ir)
    assert report.passed
```

## IR Layers

### PatternIR (domain-specific)

Preserves game-theoretic structure for analysis and visualization:

- `OpenGameIR` — game name, type, signature, logic, tags
- `FlowIR` — source/target game+port, flow type, direction
- `HierarchyNodeIR` — composition tree including `CORECURSIVE` type
- `PatternIR` — top-level container with `.to_system_ir()` projection

### SystemIR (GDS-generic)

Flat IR compatible with all GDS tooling. Obtained via `PatternIR.to_system_ir()`. Used for GDS generic verification (G-001..G-006) and cross-domain interop.

### Serialization

```python
from ogs import save_ir, load_ir

save_ir(ir_document, "game.json")
loaded = load_ir("game.json")
```

## Verification

13 domain-specific checks in two categories:

### Type Checks (T-001..T-006)

| ID | Name | What It Checks |
|----|------|---------------|
| T-001 | Sequential type match | Y tokens of left overlap X tokens of right in `>>` |
| T-002 | Feedback type match | Source and target ports share tokens in feedback |
| T-003 | Corecursive type match | Source and target ports share tokens across time |
| T-004 | Input type match | Pattern inputs wire to valid game ports |
| T-005 | Port uniqueness | No port appears in multiple flows as a target |
| T-006 | Signature completeness | Every game port is either wired or is an external boundary |

### Structural Checks (S-001..S-007)

| ID | Name | What It Checks |
|----|------|---------------|
| S-001 | Game reachability | Every game is reachable from an input or boundary |
| S-002 | No isolated games | No games disconnected from all flows |
| S-003 | Hierarchy consistency | Composition tree matches flat game list |
| S-004 | Flow completeness | Every flow has valid source and target |
| S-005 | Acyclicity | No cycles in forward flow graph (within timestep) |
| S-006 | Terminal reachability | Every game can reach a terminal or feedback sink |
| S-007 | Composition balance | Parallel branches have compatible interfaces |

```python
from ogs import verify

# Domain checks only
report = verify(ir_document)

# Domain checks + GDS structural checks (G-001..G-006)
report = verify(ir_document, include_gds_checks=True)
```

## CLI

```bash
# Compile a pattern to IR (JSON)
ogs compile pattern.py -o output.json

# Run verification
ogs verify output.json

# Generate Markdown reports
ogs report output.json -o reports/
```

## Examples

Three tutorial examples in [`gds-examples`](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples) demonstrate game-theoretic modeling using the GDS framework primitives:

| Example | Domain | What It Teaches |
|---------|--------|-----------------|
| [Prisoner's Dilemma](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples/games/prisoners_dilemma) | Game theory | Nested parallel composition, multi-entity state, temporal loops |
| [Insurance Contract](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples/games/insurance) | Finance | Complete 4-role taxonomy (ControlAction), pure sequential pipeline |
| [Crosswalk Problem](https://github.com/BlockScience/gds-core/tree/main/packages/gds-examples/games/crosswalk) | Mechanism design | Discrete Markov transitions, governance parameters |

## Status

**v0.3.0 — Alpha.** Full DSL with 6 game types, 13 verification checks, 7 report templates, 6 diagram generators, canonical GDS bridge, CLI, multi-agent composition helpers, and pattern registry. 303 tests.

## License

Apache-2.0

---
Built with [Claude Code](https://claude.ai/code). All code is test-driven and human-reviewed.

## Credits & Attribution

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish) — [Generalized Dynamical Systems, Part I: Foundations](https://blog.block.science/generalized-dynamical-systems-part-i-foundations-2/) (2021).

**Game-theoretic foundation:** [Ghani, Hedges, Winschel, Zahn](https://arxiv.org/abs/1603.04641) — Compositional Game Theory (2018). Bidirectional composition with contravariant feedback channels.

**Architectural inspiration:** [Sean McOwen](https://github.com/SeanMcOwen) — [MSML](https://github.com/BlockScience/MSML) and [bdp-lib](https://github.com/BlockScience/bdp-lib).

**Contributors:**
* [Michael Zargham](https://github.com/mzargham) — Project direction, GDS theory guidance, and technical review (BlockScience).
* [Peter Hacker](https://github.com/phacker3) — Code auditing and review (BlockScience).

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.
