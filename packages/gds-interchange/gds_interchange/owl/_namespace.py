"""OWL namespace constants and prefix bindings for the GDS ontology."""

from rdflib import Namespace

# Base namespace
GDS = Namespace("https://gds.dynamicalsystemsgroup.com/ontology/")

# Sub-namespaces
GDS_CORE = Namespace("https://gds.dynamicalsystemsgroup.com/ontology/core/")
GDS_IR = Namespace("https://gds.dynamicalsystemsgroup.com/ontology/ir/")
GDS_VERIF = Namespace("https://gds.dynamicalsystemsgroup.com/ontology/verification/")

# Standard prefix bindings for Turtle output
PREFIXES: dict[str, Namespace] = {
    "gds": GDS,
    "gds-core": GDS_CORE,
    "gds-ir": GDS_IR,
    "gds-verif": GDS_VERIF,
}

# Default base URI for instance data
DEFAULT_BASE_URI = "https://gds.dynamicalsystemsgroup.com/instance/"
