# gds-owl

OWL/Turtle, SHACL, and SPARQL for [gds-framework](https://github.com/BlockScience/gds-core) specifications.

Exports GDS models (GDSSpec, SystemIR, CanonicalGDS, VerificationReport) to RDF/OWL and provides bidirectional round-trip with Pydantic models.

## Install

```bash
pip install gds-owl

# With SHACL validation support
pip install gds-owl[shacl]
```

## Quick Start

```python
import gds
from gds_owl import spec_to_turtle, build_core_ontology

# Export a GDSSpec to Turtle
ttl = spec_to_turtle(my_spec)

# Get the GDS ontology (TBox)
ontology = build_core_ontology()
```
