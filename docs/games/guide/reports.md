# Reports

gds-games includes 7 Markdown report generators powered by Jinja2 templates.

## Generating Reports

```python
from ogs import compile_to_ir, generate_reports

ir = compile_to_ir(pattern)
reports = generate_reports(ir)

for name, content in reports.items():
    print(f"--- {name} ---")
    print(content)
```

## Report Types

| Report | Description |
|---|---|
| System Overview | High-level summary of games, flows, and composition |
| Verification Summary | Check results with pass/fail status |
| State Machine | Terminal conditions and state transitions |
| Interface Contracts | Port signatures for each game |
| Domain Analysis | Cross-domain flow detection and coupling metrics |
| Hierarchy | Composition tree structure |
| Flow Topology | Covariant flow graph |

## Templates

Reports are generated from Jinja2 templates in `ogs/reports/templates/`. Each template receives the full `IRDocument` as context.

## CLI

```bash
ogs report compiled.json -o reports/
```

Generates all reports to the specified directory.
