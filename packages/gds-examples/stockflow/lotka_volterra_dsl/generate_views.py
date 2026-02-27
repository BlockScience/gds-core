"""Generate all 6 GDS visualization views for the Lotka-Volterra DSL model.

Usage (from repo root)::

    uv run python \
      packages/gds-examples/stockflow/lotka_volterra_dsl/generate_views.py
    uv run python \
      packages/gds-examples/stockflow/lotka_volterra_dsl/generate_views.py \
      --save

Output can be pasted into GitHub/GitLab markdown, rendered at https://mermaid.live,
or viewed in VS Code / Obsidian markdown preview.
"""

import sys
from pathlib import Path

from gds.canonical import project_canonical
from gds_viz import (
    canonical_to_mermaid,
    params_to_mermaid,
    spec_to_mermaid,
    system_to_mermaid,
    trace_to_mermaid,
)
from lotka_volterra_dsl.model import build_spec, build_system

TITLE = "Lotka-Volterra (StockFlow DSL)"

# Trace Prey -- the primary population compartment. Tracing it reveals
# the interaction pathway: Prey Birth Rate converter -> Prey Growth auxiliary
# -> Prey Net Change flow -> Prey Accumulation, plus the temporal loop from
# accumulation back to the growth and predation auxiliaries.
TRACE_ENTITY = "Prey"
TRACE_VARIABLE = "level"
TRACE_SYMBOL = "x"


def generate_views() -> str:
    """Generate all 6 views and return as a markdown string."""
    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    sections = []
    sections.append(f"# {TITLE} -- Visualization Views\n")
    sections.append(
        "Six complementary views of the same model, compiled from the\n"
        "gds-stockflow DSL. Stock-flow elements (Stock, Flow, Auxiliary,\n"
        "Converter) map to GDS roles -- Converters become BoundaryActions,\n"
        "Auxiliaries and Flows become Policies, Stocks become Mechanisms\n"
        "with Entities.\n"
    )

    # -- View 1: Structural ---------------------------------------------------
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. Note the temporal loops from\n"
        "stock accumulation mechanisms back to auxiliaries -- stock levels\n"
        "at timestep t feed rate computations at timestep t+1.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # -- View 2: Canonical GDS ------------------------------------------------
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t -> U -> g -> f -> X_{t+1}.\n"
        "g contains 6 policies (4 auxiliaries + 2 flows), f contains\n"
        "2 mechanisms (stock accumulations). No ControlAction blocks.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # -- View 3: Architecture by Role -----------------------------------------
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Only 3 roles used: BoundaryAction\n"
        "(converters), Policy (auxiliaries + flows), Mechanism (stock\n"
        "accumulations). ControlAction is unused.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # -- View 4: Architecture by Domain ---------------------------------------
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag assigned by the gds-stockflow compiler.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # -- View 5: Parameter Influence ------------------------------------------
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Parameter -> blocks -> entities causal map. Four rate parameter\n"
        "converters feed their respective auxiliaries which drive the stock\n"
        "accumulations.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # -- View 6: Traceability -------------------------------------------------
    sections.append(
        f"## View 6: Traceability -- {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the"
        " block graph.\n"
        "Reveals the causal chain: rate converters -> auxiliaries\n"
        "-> Prey Net Change flow -> Prey Accumulation -> Prey state.\n"
    )
    sections.append(
        f"```mermaid\n{trace_to_mermaid(spec, TRACE_ENTITY, TRACE_VARIABLE)}\n```\n"
    )

    return "\n".join(sections)


def main() -> None:
    content = generate_views()

    if "--save" in sys.argv:
        out_path = Path(__file__).parent / "VIEWS.md"
        out_path.write_text(content)
        print(f"Wrote {out_path}")
    else:
        print(content)


if __name__ == "__main__":
    main()
