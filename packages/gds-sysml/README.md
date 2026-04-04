# gds-sysml

SysML v2 bridge for gds-framework via OSLC RDF vocabulary.

## Installation

```bash
uv add gds-sysml
```

## Usage

```python
from gds_sysml import sysml_to_spec

spec = sysml_to_spec("path/to/model.sysml")
print(spec.name)
print(list(spec.blocks.keys()))
```
