"""End-to-end SysML v2 → GDSSpec import pipeline.

Pipeline:  .sysml text → parse_sysml() → SysMLModel → sysml_to_rdf() → RDF Graph
           → gds_owl.graph_to_spec() → GDSSpec

This module provides the high-level ``sysml_to_spec()`` entry point that
orchestrates the full pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds_owl.import_ import graph_to_spec
from gds_sysml.model import SysMLModel
from gds_sysml.parser.regex import parse_sysml
from gds_sysml.rdf import sysml_to_rdf

if TYPE_CHECKING:
    from pathlib import Path

    from gds.spec import GDSSpec


def sysml_to_spec(
    source: str | Path | SysMLModel,
    *,
    base_uri: str = "https://gds.block.science/instance/",
) -> GDSSpec:
    """Import a SysML v2 model as a GDSSpec.

    Orchestrates the full pipeline: parse → RDF → GDSSpec.

    Args:
        source: One of:
            - A ``str`` containing SysML v2 textual notation
            - A ``Path`` to a ``.sysml`` file
            - A pre-parsed ``SysMLModel``
        base_uri: Base URI for RDF instance data.

    Returns:
        A fully populated GDSSpec reconstructed from the SysML model.

    Example::

        from gds_sysml import sysml_to_spec

        spec = sysml_to_spec("path/to/model.sysml")
        print(spec.name)
        print(list(spec.blocks.keys()))
    """
    model = source if isinstance(source, SysMLModel) else parse_sysml(source)
    graph = sysml_to_rdf(model, base_uri=base_uri)
    return graph_to_spec(graph)
