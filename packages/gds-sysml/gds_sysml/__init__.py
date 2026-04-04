"""gds-sysml — SysML v2 bridge for gds-framework via OSLC RDF vocabulary."""

__version__ = "0.1.0"

from gds_sysml._namespace import GDS_SYSML, SYSML_OSLC
from gds_sysml.import_ import sysml_to_spec
from gds_sysml.model import (
    GDSAnnotation,
    SysMLAction,
    SysMLAttribute,
    SysMLConnection,
    SysMLModel,
    SysMLPart,
    SysMLPort,
)
from gds_sysml.parser.regex import parse_sysml
from gds_sysml.rdf import sysml_to_rdf

__all__ = [
    "GDS_SYSML",
    "SYSML_OSLC",
    "GDSAnnotation",
    "SysMLAction",
    "SysMLAttribute",
    "SysMLConnection",
    "SysMLModel",
    "SysMLPart",
    "SysMLPort",
    "parse_sysml",
    "sysml_to_rdf",
    "sysml_to_spec",
]
