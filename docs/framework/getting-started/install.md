# Installation

## From PyPI

```bash
pip install gds-framework
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add gds-framework
```

## Requirements

- Python 3.12 or later
- [pydantic](https://docs.pydantic.dev/) >= 2.10 (installed automatically)

## Import

The package is installed as `gds-framework` but imported as `gds`:

```python
import gds
print(gds.__version__)
```

## Development Setup

```bash
git clone https://github.com/BlockScience/gds-framework.git
cd gds-framework
uv sync
uv run pytest tests/ -v
```
