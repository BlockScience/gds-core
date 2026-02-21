"""Generate all 6 GDS visualization views for the Crosswalk Problem.

Usage:
    uv run python examples/crosswalk/generate_views.py          # print to stdout
    uv run python examples/crosswalk/generate_views.py --save   # write VIEWS.md

Output can be pasted into GitHub/GitLab markdown, rendered at https://mermaid.live,
or viewed in VS Code / Obsidian markdown preview.
"""

import sys
from pathlib import Path

from crosswalk.model import build_spec, build_system
from gds.canonical import project_canonical
from gds_viz import (
    canonical_to_mermaid,
    params_to_mermaid,
    spec_to_mermaid,
    system_to_mermaid,
    trace_to_mermaid,
)

TITLE = "Crosswalk Problem"

# Trace Street.traffic_state — the sole state variable. Tracing it
# reveals the full pipeline from observation through pedestrian decision,
# safety check (ControlAction with crosswalk_location param), to transition.
TRACE_ENTITY = "Street"
TRACE_VARIABLE = "traffic_state"
TRACE_SYMBOL = "X"


def generate_views() -> str:
    """Generate all 6 views and return as a markdown string."""
    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    sections = []
    sections.append(f"# {TITLE} — Visualization Views\n")
    sections.append(
        "Six complementary views of the same model, from compiled topology\n"
        "to mathematical decomposition to parameter traceability.\n"
        "Key feature: discrete Markov state transitions with a single\n"
        "design parameter (crosswalk location) demonstrating mechanism design.\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. A pure linear pipeline with\n"
        "no feedback or temporal wiring — 4 blocks in sequence.\n"
        "All arrows are solid forward (covariant) flow.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t -> U -> g -> d -> f -> X_{t+1}.\n"
        "The ControlAction (Safety Check) populates the decision (d)\n"
        "layer with crosswalk_location as the design parameter.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role — all 4 roles present:\n"
        "- **BoundaryAction**: Observe Traffic (exogenous input)\n"
        "- **Policy**: Pedestrian Decision (observation -> action)\n"
        "- **ControlAction**: Safety Check (admissibility constraint)\n"
        "- **Mechanism**: Traffic Transition (Markov state update)\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Three domains:\n"
        "Environment (observe + transition), Pedestrian (decision),\n"
        "Infrastructure (safety check with crosswalk parameter).\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Theta -> blocks -> entities causal map. The single parameter\n"
        "(crosswalk_location) flows through Safety Check only —\n"
        "demonstrating that mechanism design operates at the\n"
        "admissibility layer, not at the policy or mechanism level.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the full causal chain from observation through pedestrian\n"
        "decision, safety check (with crosswalk_location parameter), to\n"
        "the traffic state transition.\n"
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
