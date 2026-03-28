"""Serialization convenience functions — Graph to Turtle/JSON-LD/N-Triples.

Also provides high-level shortcuts that combine export + serialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_owl.export import (
    canonical_to_graph,
    report_to_graph,
    spec_to_graph,
    system_ir_to_graph,
)

if TYPE_CHECKING:
    from rdflib import Graph

    from gds.canonical import CanonicalGDS
    from gds.ir.models import SystemIR
    from gds.spec import GDSSpec
    from gds.verification.findings import VerificationReport


def to_turtle(graph: Graph) -> str:
    """Serialize an RDF graph to Turtle format."""
    return graph.serialize(format="turtle")


def to_jsonld(graph: Graph) -> str:
    """Serialize an RDF graph to JSON-LD format."""
    return graph.serialize(format="json-ld")


def to_ntriples(graph: Graph) -> str:
    """Serialize an RDF graph to N-Triples format."""
    return graph.serialize(format="nt")


# ── High-level convenience ───────────────────────────────────────────


def spec_to_turtle(spec: GDSSpec, **kwargs: Any) -> str:
    """Export a GDSSpec directly to Turtle string."""
    return to_turtle(spec_to_graph(spec, **kwargs))


def system_ir_to_turtle(system: SystemIR, **kwargs: Any) -> str:
    """Export a SystemIR directly to Turtle string."""
    return to_turtle(system_ir_to_graph(system, **kwargs))


def canonical_to_turtle(canonical: CanonicalGDS, **kwargs: Any) -> str:
    """Export a CanonicalGDS directly to Turtle string."""
    return to_turtle(canonical_to_graph(canonical, **kwargs))


def report_to_turtle(report: VerificationReport, **kwargs: Any) -> str:
    """Export a VerificationReport directly to Turtle string."""
    return to_turtle(report_to_graph(report, **kwargs))
