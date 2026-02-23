# Contributing

## Setup

```bash
uv sync --all-packages
```

## Tests

```bash
# Per-package (preferred — avoids module name collisions)
uv run --package gds-framework pytest packages/gds-framework/tests -v
uv run --package gds-games pytest packages/gds-games/tests -v

# Lint
uv run ruff check packages/
uv run ruff format --check packages/
```

## Versioning

Each package's `__init__.py` owns its version via `__version__`. The `pyproject.toml` reads it dynamically — never edit the version there.

To bump a version, edit `__version__` in the package's `__init__.py`.

When a package starts using a new `gds-framework` API, bump the `gds-framework>=` lower bound in that package's `pyproject.toml` in the same change.

## Releases

Packages are published independently via tag-based CI. Tag format: `<package>/v<version>` (e.g., `gds-framework/v0.2.3`).
