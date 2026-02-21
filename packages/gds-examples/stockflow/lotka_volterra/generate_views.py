"""Generate all 6 GDS visualization views for the Lotka-Volterra model.

Usage:
    uv run python examples/lotka_volterra/generate_views.py          # print to stdout
    uv run python examples/lotka_volterra/generate_views.py --save   # write VIEWS.md

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
from lotka_volterra.model import build_spec, build_system

TITLE = "Lotka-Volterra Predator-Prey"

# Trace Prey.population — tracing it backwards reveals both the direct
# update path AND the temporal feedback loop where updated populations
# feed back into rate computation at the next timestep.
TRACE_ENTITY = "Prey"
TRACE_VARIABLE = "population"
TRACE_SYMBOL = "x"


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
        "Key feature: .loop() creates COVARIANT temporal wiring visible\n"
        "as dashed arrows in the structural view.\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    # WHY: The dashed temporal arrows from Update Prey/Predator back to
    # Compute Rates are the key feature. Unlike thermostat's thick feedback
    # arrows (within-timestep), these dashed arrows cross timestep boundaries.
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. **Dashed arrows** show .loop()\n"
        "temporal wiring — population signals flow from mechanisms back to\n"
        "the policy at the NEXT timestep (contrast with thermostat's thick\n"
        "feedback arrows which are within-timestep).\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    # WHY: Shows the temporal loop as X_t → ... → f → X_{t+1}, with
    # the mechanisms emitting signals that become X_{t+1} inputs.
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → f → X_{t+1}.\n"
        "The temporal loop is implicit in the X_t → X_{t+1} structure —\n"
        "mechanisms produce the next state which becomes the next input.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    # WHY: Only 3 roles here (no ControlAction). The mechanisms have
    # forward_out ports — unusual for mechanisms, and necessary for
    # the temporal loop. This view shows the entity connections clearly.
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Note the mechanisms here have\n"
        "forward_out ports (unlike SIR's terminal mechanisms), which\n"
        "is what enables the .loop() temporal feedback.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    # WHY: Domain tags (Shared, Prey, Predator) show which blocks are
    # species-specific vs. shared. The "Shared" domain contains the
    # observation and rate computation that depend on both species.
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Shows species-specific vs. shared\n"
        "blocks: Observe Populations and Compute Rates are 'Shared' because\n"
        "they depend on both prey and predator populations.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    # WHY: All 4 rate parameters flow through Compute Rates and affect
    # both species. This view reveals that prey_birth_rate affects
    # predators too (indirectly, via population dynamics).
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. All 4 rate parameters flow\n"
        "through Compute Rates — each parameter indirectly affects BOTH\n"
        "species because the Lotka-Volterra equations couple them.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    # WHY: Tracing Prey.population backwards shows all blocks and
    # parameters that influence prey growth/decline, including the
    # predation_rate parameter that couples predator dynamics.
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals all parameters affecting prey dynamics — including predation_rate\n"
        "which couples the predator population into the prey update.\n"
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
