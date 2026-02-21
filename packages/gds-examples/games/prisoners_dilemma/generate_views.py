"""Generate all 6 GDS visualization views for the Prisoner's Dilemma model.

Usage:
    uv run python examples/prisoners_dilemma/generate_views.py      # stdout
    uv run python examples/prisoners_dilemma/generate_views.py --save   # write VIEWS.md

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
from prisoners_dilemma.model import build_spec, build_system

TITLE = "Iterated Prisoner's Dilemma"

# Trace Alice.strategy_state — the adaptive strategy is the most
# interesting variable because it reveals the full learning loop:
# decision → payoff → world model update → (temporal) → next decision.
TRACE_ENTITY = "Alice"
TRACE_VARIABLE = "strategy_state"
TRACE_SYMBOL = "s_A"


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
        "Key feature: nested parallel composition (| within |) plus .loop()\n"
        "creates the most complex composition tree in the examples.\n"
    )

    # ── View 1: Structural ────────────────────────────────────────
    # WHY: The most complex structural diagram. Shows 6 blocks with
    # both parallel branches (Alice/Bob decisions) and temporal loops
    # (world model → decision). Dashed arrows show the learning loop.
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR — the most complex topology in the\n"
        " **Dashed arrows** show temporal learning loops (world model →\n"
        "decision at next round). Parallel branches for Alice and Bob are\n"
        "flattened by the compiler but visible in the wiring pattern.\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    # WHY: Shows how two independent policies (alice_decision, bob_decision)
    # map to the g layer, and how the payoff mechanism plus world model
    # mechanisms form the f layer.
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → f → X_{t+1}.\n"
        "Two independent policies (Alice, Bob) in the g layer, three\n"
        "mechanisms in the f layer. No Θ parameters — the payoff matrix\n"
        "is modeled as exogenous input (U), not configuration.\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    # WHY: Reveals the symmetric agent structure — two policies and
    # three mechanisms. The Payoff Realization mechanism is unique in
    # updating 3 state variables across 2 entities.
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Shows the symmetric agent structure:\n"
        "two Policy blocks (decisions) and two Mechanism blocks (world models)\n"
        "mirror each other. Payoff Realization updates 3 variables across\n"
        "2 entities — the most complex mechanism in the examples.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    # WHY: Domain tags (Alice, Bob, Environment) reveal the agent
    # boundaries — which blocks belong to which player vs. the shared
    # environment. This is the "information boundary" view.
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Reveals agent boundaries:\n"
        "Alice's blocks, Bob's blocks, and the shared Environment.\n"
        "This view highlights information asymmetry — each agent only\n"
        "sees its own world model and payoff, not the other's.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    # WHY: This model has Θ = {} (no parameters). The parameter influence
    # view will be empty or minimal, which itself is informative — it
    # shows that all variation comes from exogenous inputs and initial state.
    sections.append("## View 5: Parameter Influence")
    sections.append(
        "Θ → blocks → entities causal map. This model has no registered\n"
        "parameters (Θ = {}) — the payoff matrix is exogenous input, not\n"
        "configuration. All behavioral variation comes from initial state\n"
        "and the learning dynamics.\n"
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    # WHY: Tracing Alice.strategy_state reveals the full learning loop:
    # Alice World Model Update writes it, which depends on Alice Payoff
    # from Payoff Realization, which depends on both players' actions.
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        "Reveals the full learning loop: Alice's strategy depends on her payoff,\n"
        "which depends on BOTH players' actions — showing the strategic coupling\n"
        "even though each agent's decision is independent.\n"
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
