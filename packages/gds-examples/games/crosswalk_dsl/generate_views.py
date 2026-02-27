"""Generate OGS visualization views for the Crosswalk Problem DSL example.

Produces 6 Mermaid diagram views from the OGS PatternIR, plus the GDS
canonical projection views via gds-viz.

Usage:
    uv run python games/crosswalk_dsl/generate_views.py          # stdout
    uv run python games/crosswalk_dsl/generate_views.py --save
"""

import sys
from pathlib import Path

from crosswalk_dsl.model import build_ir, build_spec
from ogs.viz import (
    architecture_by_domain_to_mermaid,
    architecture_by_role_to_mermaid,
    flow_topology_to_mermaid,
    hierarchy_to_mermaid,
    structural_to_mermaid,
    terminal_conditions_to_mermaid,
)

TITLE = "Crosswalk Problem (OGS DSL)"


def generate_views() -> str:
    """Generate all OGS views and return as a markdown string."""
    ir = build_ir()
    spec = build_spec()

    sections = []
    sections.append(f"# {TITLE} -- Visualization Views\n")
    sections.append(
        "Six OGS-specific views of the Crosswalk Problem pattern,\n"
        "built using the gds-games (OGS) typed DSL. A mechanism design\n"
        "model with discrete Markov state transitions.\n"
    )

    # -- View 1: Structural ---------------------------------------------------
    sections.append("## View 1: Structural")
    sections.append(
        "Full game topology with all flows. Pedestrian Decision is a\n"
        "decision game (rectangle). Safety Check and Traffic Transition\n"
        "are covariant functions (stadiums). Pure sequential pipeline.\n"
    )
    sections.append(f"```mermaid\n{structural_to_mermaid(ir)}\n```\n")

    # -- View 2: Architecture by Role -----------------------------------------
    sections.append("## View 2: Architecture by Role")
    sections.append(
        "Games grouped by GameType: decision game (Pedestrian Decision)\n"
        "and covariant functions (Safety Check, Traffic Transition).\n"
    )
    sections.append(f"```mermaid\n{architecture_by_role_to_mermaid(ir)}\n```\n")

    # -- View 3: Architecture by Domain ---------------------------------------
    sections.append("## View 3: Architecture by Domain")
    sections.append(
        "Games grouped by domain tag: Pedestrian, Infrastructure, and\n"
        "Environment. Shows the three-layer separation of concerns.\n"
    )
    sections.append(f"```mermaid\n{architecture_by_domain_to_mermaid(ir)}\n```\n")

    # -- View 4: Game Hierarchy -----------------------------------------------
    sections.append("## View 4: Game Hierarchy")
    sections.append(
        "Composition tree showing the nesting structure:\n"
        "Sequential(Pedestrian Decision, Safety Check, Traffic Transition).\n"
    )
    sections.append(f"```mermaid\n{hierarchy_to_mermaid(ir)}\n```\n")

    # -- View 5: Flow Topology ------------------------------------------------
    sections.append("## View 5: Flow Topology")
    sections.append(
        "Covariant (forward) flows only. Shows the linear signal chain\n"
        "from observation through decision to traffic state outcome.\n"
    )
    sections.append(f"```mermaid\n{flow_topology_to_mermaid(ir)}\n```\n")

    # -- View 6: Terminal Conditions ------------------------------------------
    sections.append("## View 6: Terminal Conditions")
    sections.append(
        "State transition diagram for three possible Markov outcomes:\n"
        "Safe Crossing (Stopped), Jaywalking Accident, No Crossing (Flowing).\n"
    )
    sections.append(f"```mermaid\n{terminal_conditions_to_mermaid(ir)}\n```\n")

    # -- GDS Projection Info --------------------------------------------------
    sections.append("## GDS Projection")
    sections.append(
        f"The OGS pattern projects to a GDS spec with "
        f"{len(spec.blocks)} blocks (3 Policy + 1 BoundaryAction).\n"
        "All atomic games map to Policy. The crosswalk_location design\n"
        "parameter is captured as an action space constraint, not as a\n"
        "GDS parameter (OGS does not use GDS ParameterDef).\n"
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
