"""Generate all 6 GDS visualization views for the Thermostat PID model.

Usage:
    uv run python examples/thermostat/generate_views.py          # print to stdout
    uv run python examples/thermostat/generate_views.py --save   # write VIEWS.md

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
from thermostat.model import build_spec, build_system

TITLE = "Thermostat PID"

# Trace Room.temperature — the primary controlled variable. Tracing it
# reveals the full control loop: sensor → controller → plant → update,
# plus the feedback path from the plant's energy cost signal.
TRACE_ENTITY = "Room"
TRACE_VARIABLE = "temperature"
TRACE_SYMBOL = "T"


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
        "Key feature: .feedback() creates CONTRAVARIANT (backward) wiring\n"
        "visible as thick arrows in the structural view.\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    # WHY: The thick feedback arrow from Room Plant → PID Controller is
    # the distinguishing feature of this model. This view makes backward
    # (contravariant) flow visually obvious vs. normal forward flow.
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. The **thick arrow** from Room Plant\n"
        "back to PID Controller shows the .feedback() CONTRAVARIANT wiring —\n"
        "energy cost flows backward within the same timestep.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    # WHY: Shows how the feedback loop maps to the formal GDS structure.
    # The ControlAction (Room Plant) appears in a separate subgraph from
    # Policy and Mechanism, reflecting its distinct role in GDS theory.
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → f → X_{t+1}.\n"
        "The ControlAction (Room Plant) maps to the control/decision layer,\n"
        "distinct from the policy (PID Controller) and mechanism (Update Room).\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    # WHY: Shows the 4-role taxonomy in action: BoundaryAction (sensor),
    # Policy (PID controller), ControlAction (room plant), Mechanism
    # (update room). This is the first example with ControlAction.
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. This model uses 4 roles:\n"
        "BoundaryAction (sensor), Policy (PID), ControlAction (plant),\n"
        "Mechanism (update). Entity cylinders show the Room's two state variables.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    # WHY: Groups by domain tag (Sensor, Controller, Plant). Reveals
    # the physical decomposition of the thermostat system — each domain
    # maps to a physical subsystem in the real world.
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Maps to physical subsystems:\n"
        "Sensor (temperature measurement), Controller (PID logic),\n"
        "Plant (room + heater dynamics).\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    # WHY: All 4 parameters (setpoint, Kp, Ki, Kd) flow through the PID
    # Controller to affect Room state. This view confirms that parameter
    # changes only have ONE path to state — through the controller.
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. All parameters (setpoint, Kp, Ki, Kd)\n"
        "flow through the PID Controller — confirming a single control point.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    # WHY: Tracing Room.temperature backwards reveals the full causal
    # chain: sensor → controller (with params) → plant → update.
    # The feedback path is also visible if the traceability graph
    # includes backward edges.
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the full causal chain from sensor reading through PID control\n"
        "to state update, including which parameters influence the outcome.\n"
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
