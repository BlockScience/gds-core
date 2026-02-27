"""Generate all 6 GDS visualization views for the Thermostat PID DSL model.

Usage:
    uv run python control/thermostat_dsl/generate_views.py          # print to stdout
    uv run python control/thermostat_dsl/generate_views.py --save   # write VIEWS.md

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
from thermostat_dsl.model import build_spec, build_system

TITLE = "Thermostat PID (Control DSL)"

# Trace temperature -- the primary controlled variable. Tracing it reveals
# the full control loop: setpoint input + temp_sensor -> PID controller ->
# temperature Dynamics, plus the temporal loop from dynamics back to sensor.
TRACE_ENTITY = "temperature"
TRACE_VARIABLE = "value"
TRACE_SYMBOL = "T"


def generate_views() -> str:
    """Generate all 6 views and return as a markdown string."""
    spec = build_spec()
    system = build_system()
    canonical = project_canonical(spec)

    sections = []
    sections.append(f"# {TITLE} -- Visualization Views\n")
    sections.append(
        "Six complementary views of the same model, compiled from the\n"
        "gds-control DSL. Control elements (State, Input, Sensor, Controller)\n"
        "map to GDS roles -- Inputs become BoundaryActions, Sensors and\n"
        "Controllers become Policies, States become Mechanisms with Entities.\n"
        "\n"
        "Note: The raw thermostat model includes .feedback() (CONTRAVARIANT)\n"
        "for within-timestep energy cost feedback. The control DSL version\n"
        "captures the forward control loop with .loop() (COVARIANT) only.\n"
    )

    # -- View 1: Structural ---------------------------------------------------
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. Note the temporal loop from\n"
        "temperature Dynamics back to temp_sensor -- state at timestep t\n"
        "feeds observation at timestep t+1.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # -- View 2: Canonical GDS ------------------------------------------------
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t -> U -> g -> f -> X_{t+1}.\n"
        "g contains 2 policies (1 sensor + PID controller), f contains\n"
        "2 mechanisms (temperature/energy_consumed Dynamics). No ControlAction.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # -- View 3: Architecture by Role -----------------------------------------
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Only 3 roles used: BoundaryAction\n"
        "(setpoint), Policy (sensor + controller), Mechanism (dynamics).\n"
        "ControlAction is not used -- unlike the raw thermostat model.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # -- View 4: Architecture by Domain ---------------------------------------
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag assigned by the gds-control compiler.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # -- View 5: Parameter Influence ------------------------------------------
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Theta -> blocks -> entities causal map. This model has no explicit\n"
        "parameters -- the DSL focuses on structural topology, not gains.\n"
        "PID gains (Kp, Ki, Kd) would be parameters in the raw GDS version.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # -- View 6: Traceability -------------------------------------------------
    sections.append(
        f"## View 6: Traceability -- {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the causal chain: setpoint reference + sensor measurement\n"
        "-> PID controller -> temperature Dynamics -> temperature state.\n"
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
