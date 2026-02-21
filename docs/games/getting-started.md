# Getting Started

## Installation

```bash
pip install gds-games
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add gds-games
```

## Requirements

- Python 3.12 or later
- [gds-framework](https://pypi.org/project/gds-framework/) >= 0.1 (installed automatically)
- [pydantic](https://docs.pydantic.dev/) >= 2.10
- [typer](https://typer.tiangolo.com/) >= 0.15 (for CLI)
- [jinja2](https://jinja.palletsprojects.com/) >= 3.1 (for reports)

## Import

The package is installed as `gds-games` but imported as `ogs`:

```python
import ogs
from ogs.dsl.games import DecisionGame
from ogs import compile_to_ir, verify
```

## Basic Workflow

```python
from ogs.dsl.games import DecisionGame, CovariantFunction
from ogs.dsl.pattern import Pattern
from ogs import compile_to_ir, verify, generate_reports, save_ir

# 1. Define atomic games
sensor = CovariantFunction(name="Sensor", x="observation", y="signal")
agent = DecisionGame(name="Agent", x="signal", y="action", r="reward", s="experience")

# 2. Compose
game = sensor >> agent

# 3. Wrap in a Pattern
pattern = Pattern(name="Simple Decision", game=game)

# 4. Compile to IR
ir = compile_to_ir(pattern)

# 5. Verify
report = verify(ir)

# 6. Generate reports
reports = generate_reports(ir)

# 7. Save IR to JSON
save_ir(ir, "simple_decision.json")
```

## CLI

```bash
# Compile a pattern to IR
ogs compile pattern.json -o output.json

# Run verification
ogs verify output.json

# Generate reports
ogs report output.json -o reports/
```
