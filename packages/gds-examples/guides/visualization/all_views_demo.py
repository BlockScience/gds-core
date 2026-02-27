"""All 6 GDS visualization views from a single model.

Demonstrates every gds-viz view type using the SIR Epidemic model as the
base. Each view provides a different perspective on the same system:

1. Structural      -- compiled block graph from SystemIR
2. Canonical GDS   -- mathematical h = f . g decomposition
3. Architecture by Role   -- blocks grouped by GDS role
4. Architecture by Domain -- blocks grouped by domain tag
5. Parameter Influence    -- Theta -> blocks -> entities causal map
6. Traceability           -- backwards trace from one state variable

All views produce Mermaid markdown that renders in GitHub, GitLab,
VS Code, Obsidian, and mermaid.live.

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


def _sir_spec():
    from sir_epidemic.model import build_spec

    return build_spec()


def _sir_system():
    from sir_epidemic.model import build_system

    return build_system()


def view_1_structural() -> str:
    """View 1: Structural -- compiled block graph from SystemIR.

    When to use:
        - Understand the compiled topology the GDS compiler produces
        - Debug composition operator behavior (>>, |, .loop(), .feedback())
        - Verify wiring directions (solid = forward, dashed = temporal,
          thick = feedback)

    Input: SystemIR (from compile_system or DSL compile_to_system)

    Shape conventions:
        - Stadium ([...]) = BoundaryAction (exogenous input, no forward_in)
        - Double-bracket [[...]] = terminal Mechanism (state sink, no forward_out)
        - Rectangle [...] = Policy or other block with both inputs and outputs

    Arrow conventions:
        - Solid arrow --> = covariant forward flow
        - Dashed arrow -.-> = temporal loop (cross-timestep)
        - Thick arrow ==> = feedback (within-timestep, contravariant)
        - Backward arrow <-- = contravariant flow
    """
    return system_to_mermaid(_sir_system())


def view_2_canonical() -> str:
    """View 2: Canonical GDS -- mathematical decomposition h = f . g.

    When to use:
        - Map a model to the formal GDS decomposition X_t -> U -> g -> f -> X_{t+1}
        - Verify the mathematical structure (which blocks are g vs f)
        - Review parameter space Theta and its connections to g and f
        - Compare models at the abstract level (ignoring block names)

    Input: CanonicalGDS (from project_canonical(spec))

    Layout: Left-to-right (flowchart LR) showing the data flow:
        X_t (state) -> U (boundary) -> g (policy) -> f (mechanism) -> X_{t+1}
        Theta (parameters) feeds into g and f via dashed arrows
    """
    canonical = project_canonical(_sir_spec())
    return canonical_to_mermaid(canonical)


def view_3_architecture_by_role() -> str:
    """View 3: Architecture by Role -- blocks grouped by GDS role.

    When to use:
        - Review whether the role decomposition is clean and complete
        - Verify each layer has the expected blocks
        - See entity cylinders and which mechanisms update them
        - Understand the layered structure: boundary -> policy -> mechanism

    Input: GDSSpec (the central specification registry)

    The default grouping (group_by=None) organizes blocks into subgraphs
    by their GDS role: Boundary (U), Policy (g), Mechanism (f), Control.
    Entity cylinders show state variables with mathematical symbols.
    """
    return spec_to_mermaid(_sir_spec())


def view_4_architecture_by_domain() -> str:
    """View 4: Architecture by Domain -- blocks grouped by domain tag.

    When to use:
        - See organizational ownership of blocks
        - Understand which subsystem or team owns which blocks
        - Review domain boundaries in multi-agent or multi-subsystem models

    Input: GDSSpec with blocks that have domain tags

    Uses group_by="domain" to organize blocks by their domain tag value
    instead of by GDS role. Blocks without the tag go into "Ungrouped".
    """
    return spec_to_mermaid(_sir_spec(), group_by="domain")


def view_5_parameter_influence() -> str:
    """View 5: Parameter Influence -- Theta -> blocks -> entities causal map.

    When to use:
        - Plan sensitivity analysis: "if I change parameter X, what is affected?"
        - Audit parameter usage: which blocks reference which parameters
        - Trace the full causal chain from configuration to state

    Input: GDSSpec with registered parameters

    Shows parameter hexagons, the blocks they feed, and the entities those
    blocks transitively update. Only includes blocks that reference at
    least one parameter. If a model has no parameters, shows a placeholder.
    """
    return params_to_mermaid(_sir_spec())


def view_6_traceability() -> str:
    """View 6: Traceability -- backwards trace from one state variable.

    When to use:
        - Debug unexpected behavior: "what could cause this variable to change?"
        - Audit the causal chain from parameters to a specific outcome
        - Plan targeted tests: which blocks and params to exercise

    Input: GDSSpec + entity name + variable name

    Traces Susceptible.count (S) backwards through the block graph to find
    all blocks and parameters that can influence it. Direct mechanisms get
    thick arrows (==>), transitive dependencies get normal arrows (-->),
    and parameter connections get dashed arrows (-.->).
    """
    return trace_to_mermaid(_sir_spec(), "Susceptible", "count")


def generate_all_views() -> dict[str, str]:
    """Generate all 6 views and return as a name -> mermaid dict."""
    return {
        "structural": view_1_structural(),
        "canonical": view_2_canonical(),
        "architecture_by_role": view_3_architecture_by_role(),
        "architecture_by_domain": view_4_architecture_by_domain(),
        "parameter_influence": view_5_parameter_influence(),
        "traceability": view_6_traceability(),
    }


def main() -> None:
    """Print all 6 views with headers."""
    views = generate_all_views()

    labels = {
        "structural": "View 1: Structural (SystemIR)",
        "canonical": "View 2: Canonical GDS (CanonicalGDS)",
        "architecture_by_role": "View 3: Architecture by Role (GDSSpec)",
        "architecture_by_domain": "View 4: Architecture by Domain (GDSSpec)",
        "parameter_influence": "View 5: Parameter Influence (GDSSpec)",
        "traceability": "View 6: Traceability (GDSSpec)",
    }

    for key, mermaid in views.items():
        print(f"\n{'=' * 60}")
        print(f"  {labels[key]}")
        print(f"{'=' * 60}\n")
        print(f"```mermaid\n{mermaid}\n```")


if __name__ == "__main__":
    main()
