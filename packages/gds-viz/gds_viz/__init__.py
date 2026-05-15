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


_PHASE_EXPORTS = {"phase_portrait"}

_FREQUENCY_EXPORTS = {"bode_plot", "nyquist_plot", "nichols_plot", "root_locus_plot"}

_RESPONSE_EXPORTS = {"step_response_plot", "impulse_response_plot", "compare_responses"}


def __getattr__(name: str) -> object:
    """Lazy import for optional visualization modules."""
    if name in _PHASE_EXPORTS:
        from gds_viz.phase import phase_portrait

        return phase_portrait

    if name in _FREQUENCY_EXPORTS:
        from gds_viz import frequency

        return getattr(frequency, name)

    if name in _RESPONSE_EXPORTS:
        from gds_viz import response

        return getattr(response, name)

    raise AttributeError(f"module 'gds_viz' has no attribute {name!r}")
