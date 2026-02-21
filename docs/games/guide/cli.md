# CLI

gds-games provides the `ogs` command-line interface built with [Typer](https://typer.tiangolo.com/).

## Commands

### `ogs compile`

Compile a pattern definition to IR.

```bash
ogs compile pattern.json -o output.json
```

### `ogs verify`

Run verification checks on compiled IR.

```bash
ogs verify output.json
```

Options:

- `--include-gds-checks` — also run generic GDS verification checks (G-001..G-006)

### `ogs report`

Generate Markdown reports from compiled IR.

```bash
ogs report output.json -o reports/
```

Generates all 7 report templates to the specified output directory.
