"""Generate all 6 GDS visualization views for the Gordon-Schaefer Fishery model.

Usage:
    uv run python examples/fisheries/generate_views.py          # print to stdout
    uv run python examples/fisheries/generate_views.py --save   # write VIEWS.md

Output can be pasted into GitHub/GitLab markdown, rendered at https://mermaid.live,
or viewed in VS Code / Obsidian markdown preview.
"""

import sys
from pathlib import Path

from fisheries.model import build_spec, build_system
from gds.canonical import project_canonical
from gds_viz import (
    canonical_to_mermaid,
    params_to_mermaid,
    spec_to_mermaid,
    system_to_mermaid,
    trace_to_mermaid,
)

TITLE = "Gordon-Schaefer Bioeconomic Fishery"

# Trace Fish Stock.biomass — tracing it backwards reveals the full causal
# chain: environmental conditions, growth computation, harvest pressure,
# quota enforcement, and the temporal feedback loop.
TRACE_ENTITY = "Fish Stock"
TRACE_VARIABLE = "biomass"
TRACE_SYMBOL = "N"


def generate_views() -> str:
    """Generate all 6 views and return as a markdown string."""
    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    sections = []
    sections.append(f"# {TITLE} — Visualization Views\n")
    sections.append(
        "Six complementary views of the same model. This is the first GDS\n"
        "example to combine all four composition operators (>>, |, .feedback(),\n"
        ".loop()) with all four block roles (BoundaryAction, Policy,\n"
        "ControlAction, Mechanism).\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. Shows three wiring styles:\n"
        "solid arrows (forward flow), **thick arrows** (.feedback() quota\n"
        "signal, CONTRAVARIANT), and **dashed arrows** (.loop() temporal\n"
        "state propagation, COVARIANT across timesteps).\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition h = f . g with ControlAction d:\n"
        "X_t → U → g(observe, compute) → d(quota) → f(update) → X_{t+1}.\n"
        "The quota enforcer (d) sits between policies and mechanisms.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "All four GDS roles present: 4 BoundaryActions (exogenous inputs),\n"
        "3 Policies (growth, harvest, profit), 1 ControlAction (quota\n"
        "enforcement), 2 Mechanisms (state updates with temporal output).\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag: Ecology (population dynamics),\n"
        "Economics (market, profit, fleet), Regulation (quota enforcement),\n"
        "and Shared (harvest pressure bridges ecology and economics).\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. Six parameters: ecological\n"
        "(intrinsic_growth_rate, base_carrying_capacity), harvest\n"
        "(catchability_coefficient), economic (cost_per_unit_effort,\n"
        "effort_adjustment_speed), and regulatory (quota_limit).\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals that fish biomass is influenced by environmental conditions,\n"
        "growth parameters, harvest pressure, quota enforcement, and the\n"
        "fleet's effort level — the full bioeconomic causal chain.\n"
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
