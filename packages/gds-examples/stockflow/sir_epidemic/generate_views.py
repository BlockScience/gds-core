"""Generate all 6 GDS visualization views for the SIR Epidemic model.

Usage:
    uv run python examples/sir_epidemic/generate_views.py          # print to stdout
    uv run python examples/sir_epidemic/generate_views.py --save   # write VIEWS.md

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
from sir_epidemic.model import build_spec, build_system

TITLE = "SIR Epidemic"

# Which entity.variable to trace in View 6 — the most interesting
# state dimension to trace backwards through the block graph.
TRACE_ENTITY = "Susceptible"
TRACE_VARIABLE = "count"
TRACE_SYMBOL = "S"


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
    )

    # ── View 1: Structural ────────────────────────────────────────
    # WHY: Shows the compiled block graph — what the compiler actually
    # produces. Role-based shapes (stadium = BoundaryAction, double-bracket
    # = terminal Mechanism) and arrow styles (solid = forward, thick =
    # feedback, dashed = temporal) reveal composition topology at a glance.
    sections.append("## View 1: Structural")
    sections.append(
        "Compiled block graph from SystemIR. Shows composition topology "
        "with role-based shapes and wiring types.\n"
        "- **Stadium shape** `([...])` = BoundaryAction (exogenous input)\n"
        "- **Double-bracket** `[[...]]` = terminal Mechanism (state sink)\n"
        "- **Solid arrow** = forward covariant flow\n"
    )
    sections.append(f"```mermaid\n{system_to_mermaid(system)}\n```\n")

    # ── View 2: Canonical GDS ─────────────────────────────────────
    # WHY: Maps the model to the formal GDS decomposition: X_t → U → g → f → X_{t+1}.
    # This is the mathematical view — it strips away block names and shows
    # the abstract dynamical system structure with state, input, policy,
    # mechanism, and parameter spaces.
    sections.append("## View 2: Canonical GDS Decomposition")
    sections.append(
        "Mathematical decomposition: X_t → U → g → f → X_{t+1}.\n"
        "Shows the abstract dynamical system with state (X), input (U),\n"
        "policy (g), mechanism (f), and parameter space (Θ).\n"
    )
    sections.append(f"```mermaid\n{canonical_to_mermaid(canonical)}\n```\n")

    # ── View 3: Architecture by Role ──────────────────────────────
    # WHY: Groups blocks by their GDS role (boundary, policy, mechanism).
    # This view answers "what does each layer of the system do?" — useful
    # for reviewing whether the role decomposition is clean and complete.
    sections.append("## View 3: Architecture by Role")
    sections.append(
        "Blocks grouped by GDS role. Reveals the layered structure:\n"
        "boundary (observation) → policy (decision) → mechanism (state update).\n"
        "Entity cylinders show which state variables each mechanism writes.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec)}\n```\n")

    # ── View 4: Architecture by Domain ────────────────────────────
    # WHY: Groups blocks by their domain tag (Observation, Decision,
    # State Update). This is the "team view" — who owns what. Useful
    # when different teams or subsystems own different parts of the model.
    sections.append("## View 4: Architecture by Domain")
    sections.append(
        "Blocks grouped by domain tag. Shows organizational ownership:\n"
        "which subsystem or team is responsible for each block.\n"
    )
    sections.append(f"```mermaid\n{spec_to_mermaid(spec, group_by='domain')}\n```\n")

    # ── View 5: Parameter Influence ───────────────────────────────
    # WHY: Shows which parameters (Θ) affect which blocks, and through
    # those blocks which entities. This is the "what happens if I change
    # this parameter?" view — essential for sensitivity analysis planning.
    sections.append("## View 5: Parameter Influence")
    sections.append(
        'Θ → blocks → entities causal map. Answers: "if I change parameter X,\n'
        'which state variables are affected?" Essential for sensitivity analysis.\n'
    )
    sections.append(f"```mermaid\n{params_to_mermaid(spec)}\n```\n")

    # ── View 6: Traceability ──────────────────────────────────────
    # WHY: Traces a single state variable backwards through the block
    # graph to find all blocks and parameters that influence it. This is
    # the "root cause" view — if Susceptible.count behaves unexpectedly,
    # what blocks and parameters could be responsible?
    sections.append(
        f"## View 6: Traceability — {TRACE_ENTITY}.{TRACE_VARIABLE} ({TRACE_SYMBOL})"
    )
    sections.append(
        f"Traces {TRACE_ENTITY}.{TRACE_VARIABLE} backwards through the block graph.\n"
        'Answers: "what blocks and parameters influence this state variable?"\n'
        "Useful for debugging unexpected behavior or planning targeted tests.\n"
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
