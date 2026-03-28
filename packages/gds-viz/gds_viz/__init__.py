"""Visualization utilities for GDS specifications."""

__version__ = "0.1.2"

from gds_viz._styles import MermaidTheme
from gds_viz.architecture import spec_to_mermaid
from gds_viz.canonical import canonical_to_mermaid
from gds_viz.mermaid import block_to_mermaid, system_to_mermaid
from gds_viz.traceability import params_to_mermaid, trace_to_mermaid

__all__ = [
    "MermaidTheme",
    "block_to_mermaid",
    "canonical_to_mermaid",
    "params_to_mermaid",
    "spec_to_mermaid",
    "system_to_mermaid",
    "trace_to_mermaid",
]


def __getattr__(name: str) -> object:
    """Lazy import for optional phase portrait module."""
    if name == "phase_portrait":
        from gds_viz.phase import phase_portrait

        return phase_portrait
    raise AttributeError(f"module 'gds_viz' has no attribute {name!r}")
