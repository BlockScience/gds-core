# gds-interchange

Bidirectional format bridges for [gds-framework](https://github.com/BlockScience/gds-core) specifications.

## Subpackages

- `gds_interchange.owl` — OWL/Turtle, SHACL validation, and SPARQL queries

## Installation

```bash
pip install gds-interchange
pip install gds-interchange[shacl]  # SHACL validation support
```

## Usage

```python
from gds_interchange.owl import spec_to_turtle, build_core_ontology
```
