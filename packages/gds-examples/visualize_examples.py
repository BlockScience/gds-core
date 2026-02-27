"""Generate Mermaid diagrams for all example models.

Run this script to create visual diagrams of each example system:
    uv run python examples/visualize_examples.py

The output can be:
- Pasted directly into GitHub/GitLab markdown
- Rendered at https://mermaid.live
- Viewed in VS Code markdown preview
"""

import importlib

from gds_viz import system_to_mermaid


def main():
    examples = [
        ("SIR Epidemic", "sir_epidemic.model"),
        ("SIR Epidemic (DSL)", "sir_epidemic_dsl.model"),
        ("Thermostat PID", "thermostat.model"),
        ("Insurance Contract", "insurance.model"),
        ("Lotka-Volterra", "lotka_volterra.model"),
        ("Prisoner's Dilemma", "prisoners_dilemma.model"),
        ("Crosswalk Problem", "crosswalk.model"),
        ("Double Integrator", "double_integrator.model"),
    ]

    for name, module_path in examples:
        print(f"\n{'=' * 60}")
        print(f"{name}")
        print(f"{'=' * 60}\n")

        # Dynamically import the build_system function
        module = importlib.import_module(module_path)
        build_system = module.build_system

        # Build and visualize
        system = build_system()
        mermaid = system_to_mermaid(system)

        print("```mermaid")
        print(mermaid)
        print("```")

        # Stats
        print(f"\nStats: {len(system.blocks)} blocks, {len(system.wirings)} wirings")

        feedback_count = sum(1 for w in system.wirings if w.is_feedback)
        temporal_count = sum(1 for w in system.wirings if w.is_temporal)

        if feedback_count > 0:
            print(f"  - {feedback_count} feedback wiring(s)")
        if temporal_count > 0:
            print(f"  - {temporal_count} temporal wiring(s)")


if __name__ == "__main__":
    main()
