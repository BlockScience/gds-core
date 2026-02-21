# gds-games

[![PyPI](https://img.shields.io/pypi/v/gds-games)](https://pypi.org/project/gds-games/)
[![Python](https://img.shields.io/pypi/pyversions/gds-games)](https://pypi.org/project/gds-games/)
[![License](https://img.shields.io/github/license/BlockScience/gds-games)](https://github.com/BlockScience/gds-games/blob/main/LICENSE)

**Typed DSL for compositional game theory**, built on [gds-framework](https://blockscience.github.io/gds-framework).

## What is this?

`gds-games` extends the GDS framework with game-theoretic vocabulary — open games, strategic interactions, and compositional game patterns. It provides:

- **6 atomic game types** — DecisionGame, CovariantFunction, ContravariantFunction, DeletionGame, DuplicationGame, CounitGame
- **Pattern composition** — Sequential, Parallel, Feedback, and Corecursive composition operators
- **IR compilation** — Flatten game patterns into JSON-serializable intermediate representation
- **13 verification checks** — Type matching (T-001..T-006) and structural validation (S-001..S-007)
- **7 Markdown report templates** — System overview, verification summary, state machine, interface contracts, and more
- **6 Mermaid diagram generators** — Structural, hierarchy, flow topology, architecture views
- **CLI** — `ogs compile`, `ogs verify`, `ogs report`

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
# or: pip install gds-games
```

```python
from ogs.dsl.games import DecisionGame, CovariantFunction
from ogs.dsl.pattern import Pattern
from ogs import compile_to_ir, verify

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

## Credits

**Author:** [Rohan Mehta](https://github.com/rororowyourboat) — [BlockScience](https://block.science/)

**Theoretical foundation:** [Dr. Michael Zargham](https://github.com/mzargham) and [Dr. Jamsheed Shorish](https://github.com/jshorish)

**Lineage:** Part of the [cadCAD](https://github.com/cadCAD-org/cadCAD) ecosystem for Complex Adaptive Dynamics.
