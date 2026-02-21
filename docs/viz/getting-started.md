# Getting Started

## Installation

```bash
pip install gds-viz
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add gds-viz
```

## Requirements

- Python 3.12 or later
- [gds-framework](https://pypi.org/project/gds-framework/) >= 0.2.0 (installed automatically)

## Basic Usage

gds-viz takes GDS objects (`SystemIR`, `GDSSpec`, `CanonicalGDS`) and returns Mermaid markdown strings.

```python
from gds import compile_system, GDSSpec
from gds.canonical import project_canonical
from gds_viz import (
    system_to_mermaid,
    canonical_to_mermaid,
    spec_to_mermaid,
    params_to_mermaid,
    trace_to_mermaid,
)

# Build your model
spec = build_spec()       # your GDSSpec
system = build_system()   # your SystemIR
canonical = project_canonical(spec)

# Generate diagrams
print(system_to_mermaid(system))        # View 1: Structural
print(canonical_to_mermaid(canonical))  # View 2: Canonical GDS
print(spec_to_mermaid(spec))            # View 3: Architecture by role
print(params_to_mermaid(spec))          # View 5: Parameter influence
print(trace_to_mermaid(spec, "Room", "temperature"))  # View 6: Traceability
```

Output is Mermaid markdown — renders in GitHub, GitLab, VS Code, Obsidian, and [mermaid.live](https://mermaid.live).
