"""OSLC SysML v2 and GDS-SysML namespace constants."""

from rdflib import Namespace

# OSLC SysML v2 vocabulary (normative, published by OMG/OSLC)
SYSML_OSLC = Namespace("https://www.omg.org/spec/SysML/2.0/")

# GDS-SysML bridge namespace (for bridge-specific predicates)
GDS_SYSML = Namespace("https://gds.block.science/ontology/sysml/")

# Standard prefix bindings
PREFIXES: dict[str, Namespace] = {
    "sysml": SYSML_OSLC,
    "gds-sysml": GDS_SYSML,
}
