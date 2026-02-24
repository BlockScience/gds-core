"""Generate all 6 GDS visualization views for the Double Integrator model.

Usage:
    uv run python control/double_integrator/generate_views.py          # print to stdout
    uv run python control/double_integrator/generate_views.py --save   # write VIEWS.md

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
from double_integrator.model import build_spec, build_system

TITLE = "Double Integrator"

# Trace position — the primary controlled variable. Tracing it reveals
# the full control loop: force input + pos_sensor → PD controller →
# position Dynamics, plus the temporal loop from dynamics back to sensor.
TRACE_ENTITY = "position"
TRACE_VARIABLE = "value"
TRACE_SYMBOL = "x"


def generate_views() -> str:
    """Generate all 6 views and return as a markdown string."""
    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    sections = []
    sections.append(f"# {TITLE} — Visualization Views\n")
    sections.append(
        "Six complementary views of the same model, compiled from the\n"
        "gds-control DSL. Classical state-space (A,B,C,D) maps to GDS\n"
        "(X,U,g,f) — sensors are C (observation), controller is K (control law),\n"
        "dynamics mechanisms are A (state transition).\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. Note the temporal loops from\n"
        "position/velocity Dynamics back to their respective sensors — state\n"
        "at timestep t feeds observation at timestep t+1.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → f → X_{t+1}.\n"
        "g contains 3 policies (2 sensors + PD controller), f contains\n"
        "2 mechanisms (position/velocity Dynamics). No ControlAction blocks.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Only 3 roles used: BoundaryAction (force),\n"
        "Policy (sensors + controller), Mechanism (dynamics). ControlAction\n"
        "is intentionally unused — it would break the (A,B,C,D) mapping.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag assigned by the gds-control compiler.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. This model has no explicit\n"
        "parameters — the DSL focuses on structural topology, not gains.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the causal chain: force reference + sensor measurements\n"
        "→ PD controller → position Dynamics → position state.\n"
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
