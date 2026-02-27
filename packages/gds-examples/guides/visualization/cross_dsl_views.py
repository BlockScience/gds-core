"""Cross-DSL visualization demo.

Shows that the same gds-viz API works identically across different DSLs
and hand-built models. The viz layer operates on GDSSpec and SystemIR --
both are DSL-neutral IR types produced by every GDS compilation path.

This demo generates views from two different domains:
    1. SIR Epidemic   -- hand-built with gds-framework primitives
    2. Double Integrator -- built via the gds-control DSL

The key insight: regardless of how a model is built (raw GDS blocks,
stockflow DSL, control DSL, or games DSL), the viz API sees the same
GDSSpec and SystemIR structures. Every view function works unchanged.

Usage (interactive notebook):
    uv run marimo edit packages/gds-examples/guides/visualization/notebook.py

Usage (tests):
    uv run --package gds-examples pytest packages/gds-examples/guides/visualization/ -v

Note: This module is designed to be imported by the test suite and marimo
notebook, which handle sys.path setup via conftest.py. Running as a
standalone script requires stockflow/ and control/ on sys.path.
"""

from gds.canonical import project_canonical
from gds_viz import (
    canonical_to_mermaid,
    params_to_mermaid,
    spec_to_mermaid,
    system_to_mermaid,
    trace_to_mermaid,
)


def sir_views() -> dict[str, str]:
    """Generate views for the SIR Epidemic model (hand-built GDS).

    The SIR model is built directly with gds-framework primitives:
    TypeDef, Entity, Space, BoundaryAction, Policy, Mechanism.
    No DSL compiler is involved -- blocks and wirings are explicit.
    """
    from sir_epidemic.model import build_spec, build_system

    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    return {
        "structural": system_to_mermaid(system),
        "canonical": canonical_to_mermaid(canonical),
        "architecture_by_role": spec_to_mermaid(spec),
        "parameter_influence": params_to_mermaid(spec),
        "traceability": trace_to_mermaid(spec, "Susceptible", "count"),
    }


def double_integrator_views() -> dict[str, str]:
    """Generate views for the Double Integrator (gds-control DSL).

    The Double Integrator is built using the gds-control DSL:
    State, Input, Sensor, Controller declarations are compiled to
    GDSSpec and SystemIR by compile_model() and compile_to_system().
    The viz API works identically on the compiled output.
    """
    from double_integrator.model import build_spec, build_system

    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    return {
        "structural": system_to_mermaid(system),
        "canonical": canonical_to_mermaid(canonical),
        "architecture_by_role": spec_to_mermaid(spec),
        "parameter_influence": params_to_mermaid(spec),
        "traceability": trace_to_mermaid(spec, "position", "value"),
    }


def generate_cross_dsl_views() -> dict[str, dict[str, str]]:
    """Generate views from both domains for comparison.

    Returns:
        Dict mapping domain name to view dict.
    """
    return {
        "sir_epidemic": sir_views(),
        "double_integrator": double_integrator_views(),
    }


def main() -> None:
    """Print side-by-side views from both domains."""
    all_views = generate_cross_dsl_views()

    view_labels = {
        "structural": "Structural (SystemIR)",
        "canonical": "Canonical GDS (CanonicalGDS)",
        "architecture_by_role": "Architecture by Role (GDSSpec)",
        "parameter_influence": "Parameter Influence (GDSSpec)",
        "traceability": "Traceability (GDSSpec)",
    }

    for view_key, label in view_labels.items():
        print(f"\n{'=' * 60}")
        print(f"  {label}")
        print(f"{'=' * 60}")

        for domain, views in all_views.items():
            print(f"\n--- {domain} ---\n")
            print(f"```mermaid\n{views[view_key]}\n```")


if __name__ == "__main__":
    main()
