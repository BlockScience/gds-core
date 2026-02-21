# CLAUDE.md

This file provides guidance to Claude Code when working in this monorepo.

## Project

`gds-core` — monorepo for the Generalized Dynamical Systems ecosystem. Contains four packages managed as a uv workspace.

## Packages

| Package | Import | Location |
|---------|--------|----------|
| gds-framework | `gds` | `packages/gds-framework/` |
| gds-viz | `gds_viz` | `packages/gds-viz/` |
| gds-games | `ogs` | `packages/gds-games/` |
| gds-examples | — | `packages/gds-examples/` |

## Commands

```bash
# Install all packages (workspace-linked)
uv sync --all-packages

# Run tests per-package
uv run --package gds-framework pytest packages/gds-framework/tests -v
uv run --package gds-viz pytest packages/gds-viz/tests -v
uv run --package gds-games pytest packages/gds-games/tests -v
uv run --package gds-examples pytest packages/gds-examples -v

# Run all tests
uv run --package gds-framework pytest packages/gds-framework/tests packages/gds-viz/tests packages/gds-games/tests packages/gds-examples -v

# Lint & format
uv run ruff check packages/
uv run ruff format --check packages/

# Build a specific package
uv build --package gds-framework

# Docs
uv sync --all-packages --group docs
uv run mkdocs build --strict
uv run mkdocs serve
```

## Architecture

This is a **uv workspace** monorepo. The root `pyproject.toml` declares `packages/*` as workspace members. Each package has its own `pyproject.toml` with package-specific dependencies and build config. Shared tooling (ruff, docs) is configured at the root.

### Dependency Graph

```
gds-framework  ←  core engine (no GDS dependencies)
    ↑
gds-viz        ←  visualization (depends on gds-framework)
gds-games      ←  game theory DSL (depends on gds-framework)
    ↑
gds-examples   ←  tutorials (depends on gds-framework + gds-viz)
```

### Key Conventions

- All data models are Pydantic v2 BaseModel
- Absolute imports only (never relative)
- Ruff config inherited from root (line-length 88)
- Each package published independently to PyPI via tag-based workflow (`gds-framework/v0.3.1`)
- Per-package CLAUDE.md files contain package-specific architecture details
