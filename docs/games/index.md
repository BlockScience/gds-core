# gds-games

[![PyPI](https://img.shields.io/pypi/v/gds-games)](https://pypi.org/project/gds-games/)
[![Python](https://img.shields.io/pypi/pyversions/gds-games)](https://pypi.org/project/gds-games/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-games)](https://github.com/DynamicalSystemsGroup/gds-games/blob/main/LICENSE)

**Typed DSL for compositional game theory**, built on [gds-framework](../framework/index.md).

## Package Identity

| Distribution | Import | Role |
|---|---|---|
| `gds-games` | `gds_domains.games` | Compositional game theory and open-game patterns |
| `gds-domains[games]` | `gds_domains.games` | Consolidated domain package extra |

## What is this?

`gds-games` extends the GDS framework with game-theoretic vocabulary — open games, strategic interactions, and compositional game patterns. It provides:

- **6 atomic game types** — DecisionGame, CovariantFunction, ContravariantFunction, DeletionGame, DuplicationGame, CounitGame
- **Pattern composition** — Sequential, Parallel, Feedback, and Corecursive composition operators
- **IR compilation** — Flatten game patterns into JSON-serializable intermediate representation
- **13 verification checks** — Type matching (T-001..T-006) and structural validation (S-001..S-007)
- **7 Markdown report templates** — System overview, verification summary, state machine, interface contracts, and more
- **6 Mermaid diagram generators** — Structural, hierarchy, flow topology, architecture views
- **CLI** — `ogs compile`, `ogs verify`, `ogs report`

## When to Use It

Use `gds-games` when your model is a strategic interaction, compositional game,
or open-game pattern. Use other domain DSLs for physical state dynamics,
software architecture, or business process models.

## Architecture

```
gds-framework (pip install gds-framework)
│
│  Domain-neutral composition algebra, typed spaces,
│  state model, verification engine, flat IR compiler.
│
└── gds-games (pip install gds-domains[games])
    │
    │  Game-theoretic DSL: OpenGame types, Pattern composition,
    │  compile_to_ir(), domain verification, reports, visualization.
    │
    └── Your application
        │
        │  Concrete pattern definitions, analysis notebooks,
        │  verification runners.
```

## Quick Start

```bash
uv add gds-games
# or: pip install gds-domains[games]
```

```python
from gds_domains.games.dsl.games import DecisionGame, CovariantFunction
from gds_domains.games.dsl.pattern import Pattern
from gds_domains.games import compile_to_ir, verify

# Define atomic games with typed signatures
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

## Relationship to the Ecosystem

`gds-games` is a domain DSL. It provides game-theoretic model vocabulary,
verification, reports, and diagrams while preserving compatibility with the GDS
composition and verification stack.

## Credits

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [DynamicalSystemsGroup](https://dynamicalsystemsgroup.com/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish)

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.
