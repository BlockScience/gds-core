"""OWL namespace constants and prefix bindings for the GDS ontology."""

from rdflib import Namespace

# Base namespace
GDS = Namespace("https://gds.block.science/ontology/")

# Sub-namespaces
GDS_CORE = Namespace("https://gds.block.science/ontology/core/")
GDS_IR = Namespace("https://gds.block.science/ontology/ir/")
GDS_VERIF = Namespace("https://gds.block.science/ontology/verification/")

# Standard prefix bindings for Turtle output
PREFIXES: dict[str, Namespace] = {
    "gds": GDS,
    "gds-core": GDS_CORE,
    "gds-ir": GDS_IR,
    "gds-verif": GDS_VERIF,
}

# Default base URI for instance data
DEFAULT_BASE_URI = "https://gds.block.science/instance/"
