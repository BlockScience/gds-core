"""Architecture-aware visualization for Prisoner's Dilemma.

This module creates a diagram that explicitly shows:
- Agent vs Environment separation
- Private vs Public information flow
- Stateful world model objects
- Typed data flow (actions vs payoffs vs matrix)
- Process vs state distinction
"""

from prisoners_dilemma.model import build_system


def prisoners_dilemma_to_mermaid() -> str:
    """Generate architecture-aware Mermaid diagram for Prisoner's Dilemma.

    This diagram mirrors the architectural semantics:
    - Environment subgraph (payoff setting + realization processes)
    - Agent subgraphs (each with world model state + decision process)
    - Explicit private/public data flow annotations
    - Clear distinction between processes and stateful objects
    """
    lines = ["flowchart TD", ""]

    # ========== ENVIRONMENT ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% ENVIRONMENT",
            "    %% ======================",
            "",
            "    subgraph Environment",
            '        P_Setting["Payoff Matrix Setting Process<br/>(private: 2x2x2 payoff grid)"]',
            '        P_Realization["Payoff Realization Process"]',
            "    end",
            "",
        ]
    )

    # ========== ALICE AGENT ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% ALICE AGENT",
            "    %% ======================",
            "",
            '    subgraph Alice_Agent["Alice Agent"]',
            '        A_Model["Alice\'s Model of the World<br/>(private: strategy state)"]',
            '        A_Decision["Alice Decision Process<br/>(output: private action A)"]',
            "        A_Model --> A_Decision",
            "    end",
            "",
        ]
    )

    # ========== BOB AGENT ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% BOB AGENT",
            "    %% ======================",
            "",
            '    subgraph Bob_Agent["Bob Agent"]',
            '        B_Model["Bob\'s Model of the World<br/>(private: strategy state)"]',
            '        B_Decision["Bob Decision Process<br/>(output: private action B)"]',
            "        B_Model --> B_Decision",
            "    end",
            "",
        ]
    )

    # ========== ACTION FLOW (PRIVATE) ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% ACTION FLOW (PRIVATE)",
            "    %% ======================",
            "",
            '    A_Decision -- "private action A" --> P_Realization',
            '    B_Decision -- "private action B" --> P_Realization',
            "",
        ]
    )

    # ========== GAME CONFIG FLOW ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% GAME CONFIG FLOW",
            "    %% ======================",
            "",
            '    P_Setting -- "private payoff grid" --> P_Realization',
            "",
        ]
    )

    # ========== PUBLIC REALIZED PAYOFFS ==========
    lines.extend(
        [
            "    %% ======================",
            "    %% PUBLIC REALIZED PAYOFFS",
            "    %% ======================",
            "",
            '    P_Realization -- "public payoff a" --> A_Model',
            '    P_Realization -- "public payoff b" --> B_Model',
        ]
    )

    return "\n".join(lines)


def print_architecture_comparison():
    """Print both the standard and architecture-aware diagrams."""
    from gds_viz import system_to_mermaid

    system = build_system()

    print("=" * 70)
    print("STANDARD MERMAID DIAGRAM (flat block structure)")
    print("=" * 70)
    print()
    print("```mermaid")
    print(system_to_mermaid(system))
    print("```")
    print()

    print("=" * 70)
    print("ARCHITECTURE-AWARE DIAGRAM (agent/environment semantics)")
    print("=" * 70)
    print()
    print("```mermaid")
    print(prisoners_dilemma_to_mermaid())
    print("```")
    print()

    print("=" * 70)
    print("KEY DIFFERENCES")
    print("=" * 70)
    print()
    print("1. Agent / Environment Separation")
    print("   - Environment = Payoff matrix + realization")
    print("   - Agents = world model + decision process")
    print()
    print("2. Private vs Public Data")
    print("   - Actions: private")
    print("   - Payoff grid: private to environment")
    print("   - Realized payoffs: public")
    print("   - World models: private internal state")
    print()
    print("3. Stateful Objects")
    print("   - Alice's Model of the World (persistent state)")
    print("   - Bob's Model of the World (persistent state)")
    print("   - These feed decisions (not processes that 'update')")
    print()
    print("4. Explicit Typed Outputs")
    print("   - Decision outputs are boolean actions")
    print("   - Payoff grid explicitly typed")
    print("   - Realized payoffs explicitly labeled")
    print()


if __name__ == "__main__":
    print_architecture_comparison()
