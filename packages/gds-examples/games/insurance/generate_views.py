"""Generate all 6 GDS visualization views for the Insurance Contract model.

Usage:
    uv run python examples/insurance/generate_views.py          # print to stdout
    uv run python examples/insurance/generate_views.py --save   # write VIEWS.md

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
from insurance.model import build_spec, build_system

TITLE = "Insurance Contract"

# Trace Insurer.reserve — the most critical state variable. Tracing it
# reveals the full claims pipeline from arrival through risk assessment,
# premium calculation (ControlAction with params), payout, and reserve update.
TRACE_ENTITY = "Insurer"
TRACE_VARIABLE = "reserve"
TRACE_SYMBOL = "R"


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
        "Key feature: the ControlAction role (Premium Calculation) completes\n"
        "the 4-role GDS taxonomy — the only example to use all 4 roles.\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    # WHY: A clean linear pipeline — the simplest structural view.
    # No feedback or temporal arrows. Useful as a baseline to contrast
    # with thermostat (feedback) and lotka_volterra (temporal).
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. A pure linear pipeline with\n"
        "no feedback or temporal wiring — the simplest topology alongside\n"
        "SIR Epidemic. All arrows are solid forward (covariant) flow.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    # WHY: Shows the ControlAction (Premium Calculation) in its own
    # subgraph distinct from Policy and Mechanism — this is the only
    # example where the control/decision (D) layer is populated.
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → d → f → X_{t+1}.\n"
        "The ControlAction (Premium Calculation) populates the decision (d)\n"
        "layer — distinct from policy (g) and mechanism (f). This is the\n"
        "only example where all canonical layers are populated.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    # WHY: All 4 GDS roles visible: BoundaryAction (Claim Arrival),
    # Policy (Risk Assessment), ControlAction (Premium Calculation),
    # Mechanism (Claim Payout + Reserve Update). Complete taxonomy.
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role — all 4 roles present:\n"
        "- **BoundaryAction**: Claim Arrival (exogenous input)\n"
        "- **Policy**: Risk Assessment (observation → assessment)\n"
        "- **ControlAction**: Premium Calculation (admissibility control)\n"
        "- **Mechanism**: Claim Payout + Reserve Update (state transitions)\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    # WHY: Domain tags (Claims, Underwriting, Reserves) map to insurance
    # business units. Shows how GDS roles cross organizational boundaries —
    # Underwriting owns both the Policy and ControlAction.
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Maps to insurance business units:\n"
        "Claims (arrival + payout), Underwriting (risk + premium),\n"
        "Reserves (financial accounting). Note that Underwriting owns\n"
        "both the Policy and ControlAction roles.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    # WHY: All 3 parameters (base_premium_rate, deductible, coverage_limit)
    # flow through the ControlAction. This view shows that parameter
    # tuning only affects the admissibility decision, not the risk
    # assessment or state updates — a clean separation of concerns.
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. All parameters flow through\n"
        "Premium Calculation (ControlAction) only — risk assessment and\n"
        "state updates are parameter-free. This confirms clean separation:\n"
        "tuning Θ only changes the admissibility decision.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    # WHY: Tracing Insurer.reserve backwards reveals the full claims
    # pipeline plus all 3 parameters. If the reserve is unexpectedly
    # low, this view shows every block and parameter to investigate.
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the full causal chain from claim arrival through risk assessment,\n"
        "premium calculation (with all 3 Θ parameters), payout, to reserve update.\n"
        "The complete audit trail for the insurer's financial position.\n"
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
