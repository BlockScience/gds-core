"""Nash Equilibrium in the Prisoner's Dilemma — Interactive Marimo Notebook.

Demonstrates the full pipeline: OGS game structure -> payoff matrices ->
Nash equilibrium computation -> dominance and Pareto analysis.

Run interactively:
    uv run marimo edit notebooks/nash_equilibrium.py

Run as read-only app:
    uv run marimo run notebooks/nash_equilibrium.py
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gds-examples",
#     "nashpy>=0.0.41",
#     "marimo>=0.20.0",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium", app_title="Nash Equilibrium: Prisoner's Dilemma")


# ── Imports ──────────────────────────────────────────────────


@app.cell
def imports():
    import marimo as mo

    return (mo,)


# ── Model Imports & Path Setup ───────────────────────────────


@app.cell
def model_setup():
    import sys
    from pathlib import Path

    _examples_root = Path(__file__).resolve().parent.parent
    _games_path = str(_examples_root / "games")
    if _games_path not in sys.path:
        sys.path.insert(0, _games_path)

    from prisoners_dilemma_nash.model import (
        P,
        R,
        S,
        T,
        analyze_game,
        build_ir,
        build_payoff_matrices,
        compute_nash_equilibria,
        verify_terminal_conditions,
    )

    from gds_domains.games.viz import (
        architecture_by_domain_to_mermaid,
        structural_to_mermaid,
        terminal_conditions_to_mermaid,
    )

    ir = build_ir()

    return (
        R,
        S,
        T,
        P,
        analyze_game,
        architecture_by_domain_to_mermaid,
        build_payoff_matrices,
        compute_nash_equilibria,
        ir,
        structural_to_mermaid,
        terminal_conditions_to_mermaid,
        verify_terminal_conditions,
    )


# ── Header ───────────────────────────────────────────────────


@app.cell
def header(mo):
    mo.md(
        """
        # Nash Equilibrium: Prisoner's Dilemma

        The **Prisoner's Dilemma** is the canonical example of a game where
        individually rational decisions lead to a collectively suboptimal outcome.
        Two players simultaneously choose to **Cooperate** or **Defect**, and the
        payoff structure creates a tension between self-interest and mutual benefit.

        This notebook walks through the full analysis pipeline:

        1. **Game Structure** — the OGS composition tree and metadata
        2. **Payoff Matrices** — extracted from PatternIR terminal conditions
        3. **Nash Equilibria** — computed via Nashpy support enumeration
        4. **Game Analysis** — dominance, Pareto optimality, and the dilemma itself
        """
    )
    return ()


# ── Game Structure ───────────────────────────────────────────


@app.cell
def game_structure(
    mo,
    ir,
    structural_to_mermaid,
    terminal_conditions_to_mermaid,
    architecture_by_domain_to_mermaid,
):
    _tabs = mo.ui.tabs(
        {
            "Structural": mo.vstack(
                [
                    mo.md(
                        "Full game topology: Alice and Bob make simultaneous "
                        "decisions, feeding into a payoff computation with "
                        "feedback loops carrying payoffs back to each player."
                    ),
                    mo.mermaid(structural_to_mermaid(ir)),
                ]
            ),
            "Terminal Conditions": mo.vstack(
                [
                    mo.md(
                        "State diagram of all possible outcomes. Each terminal "
                        "state is an action profile with associated payoffs."
                    ),
                    mo.mermaid(terminal_conditions_to_mermaid(ir)),
                ]
            ),
            "By Domain": mo.vstack(
                [
                    mo.md(
                        "Architecture grouped by domain: **Alice**, **Bob**, and "
                        "**Environment**. Shows the symmetric structure of the game."
                    ),
                    mo.mermaid(architecture_by_domain_to_mermaid(ir)),
                ]
            ),
        }
    )

    mo.vstack(
        [
            mo.md(
                """\
---

## Game Structure

The Prisoner's Dilemma is built from OGS primitives:
two `DecisionGame` blocks (Alice, Bob) composed in parallel,
sequenced into a `CovariantFunction` (payoff computation),
with feedback loops carrying payoffs back to the decision nodes.

```
(Alice | Bob) >> Payoff .feedback([payoff -> decisions])
```
"""
            ),
            _tabs,
        ]
    )
    return ()


# ── Payoff Matrices ──────────────────────────────────────────


@app.cell
def payoff_matrices(mo, ir, R, T, S, P, build_payoff_matrices):
    _alice_payoffs, _bob_payoffs = build_payoff_matrices(ir)

    mo.vstack(
        [
            mo.md(
                f"""\
---

## Payoff Matrices

Extracted from PatternIR terminal conditions. The standard PD
parameters satisfy **T > R > P > S** and **2R > T + S**:

| Parameter | Value | Meaning |
|-----------|-------|---------|
| R (Reward) | {R} | Mutual cooperation |
| T (Temptation) | {T} | Defect while other cooperates |
| S (Sucker) | {S} | Cooperate while other defects |
| P (Punishment) | {P} | Mutual defection |
"""
            ),
            mo.md(
                "**Alice's Payoffs:**\n\n"
                "| | Bob: Coop | Bob: Defect |\n"
                "|---|---|---|\n"
                f"| **Cooperate** | {_alice_payoffs[0, 0]:.0f} (R) "
                f"| {_alice_payoffs[0, 1]:.0f} (S) |\n"
                f"| **Defect** | {_alice_payoffs[1, 0]:.0f} (T) "
                f"| {_alice_payoffs[1, 1]:.0f} (P) |\n\n"
                "**Bob's Payoffs:**\n\n"
                "| | Bob: Coop | Bob: Defect |\n"
                "|---|---|---|\n"
                f"| **Cooperate** | {_bob_payoffs[0, 0]:.0f} (R) "
                f"| {_bob_payoffs[0, 1]:.0f} (T) |\n"
                f"| **Defect** | {_bob_payoffs[1, 0]:.0f} (S) "
                f"| {_bob_payoffs[1, 1]:.0f} (P) |"
            ),
        ]
    )
    return ()


# ── Nash Equilibria ──────────────────────────────────────────


@app.cell
def nash_equilibria(mo, ir, compute_nash_equilibria, verify_terminal_conditions):
    import numpy as _np

    equilibria = compute_nash_equilibria(ir)
    verification = verify_terminal_conditions(ir, equilibria)

    _actions = ["Cooperate", "Defect"]
    _eq_lines = []
    for _i, (_alice_strat, _bob_strat) in enumerate(equilibria):
        _alice_action = _actions[int(_np.argmax(_alice_strat))]
        _bob_action = _actions[int(_np.argmax(_bob_strat))]
        _eq_lines.append(
            f"- **NE {_i + 1}:** Alice = {_alice_action}, Bob = {_bob_action}"
        )

    _match_lines = []
    for _m in verification["matches"]:
        _match_lines.append(f"- **{_m.name}**: {_m.outcome}")
    _mismatch_lines = []
    for _mm in verification["mismatches"]:
        _mismatch_lines.append(f"- **{_mm.name}**: {_mm.outcome}")

    _match_text = "\n".join(_match_lines) if _match_lines else "- None"
    _mismatch_text = "\n".join(_mismatch_lines) if _mismatch_lines else "- None"

    mo.vstack(
        [
            mo.md(
                f"""\
---

## Nash Equilibria

Computed via **Nashpy** support enumeration on the extracted
payoff matrices.

### Computed Equilibria ({len(equilibria)} found)

{"\\n".join(_eq_lines)}

### Verification Against Declared Terminal Conditions

Cross-referencing computed equilibria against the hand-annotated
terminal conditions in the OGS Pattern:

**Matches** (declared NE confirmed by computation):

{_match_text}

**Mismatches** (declared NE not confirmed):

{_mismatch_text}
"""
            ),
        ]
    )
    return (equilibria,)


# ── Game Analysis ────────────────────────────────────────────


@app.cell
def game_analysis(mo, ir, analyze_game):
    analysis = analyze_game(ir)

    _alice_dom = analysis["alice_dominant_strategy"]
    _bob_dom = analysis["bob_dominant_strategy"]
    _pareto = analysis["pareto_optimal"]

    _pareto_rows = []
    for _o in _pareto:
        _pareto_rows.append(
            f"| {_o['alice_action']} | {_o['bob_action']} | "
            f"{_o['alice_payoff']:.0f} | {_o['bob_payoff']:.0f} |"
        )
    _pareto_table = "\n".join(_pareto_rows)

    mo.vstack(
        [
            mo.md(
                f"""\
---

## Game Analysis

### Dominant Strategies

A strategy is **strictly dominant** if it yields a higher payoff
regardless of the opponent's choice.

| Player | Dominant Strategy |
|--------|-------------------|
| Alice | **{_alice_dom or "None"}** |
| Bob | **{_bob_dom or "None"}** |

**Defect** strictly dominates for both players: no matter
what the opponent does, defecting always yields a higher
payoff (T > R and P > S).

### Pareto Optimal Outcomes ({len(_pareto)} of 4)

An outcome is **Pareto optimal** if no other outcome makes one player
better off without making the other worse off.

| Alice | Bob | Alice Payoff | Bob Payoff |
|-------|-----|-------------|------------|
{_pareto_table}

The Nash equilibrium (Defect, Defect) with payoffs (P, P) = (1, 1)
is **not** Pareto optimal — both players could do better with
(Cooperate, Cooperate) yielding (R, R) = (3, 3).
"""
            ),
        ]
    )
    return ()


# ── The Dilemma ──────────────────────────────────────────────


@app.cell
def the_dilemma(mo):
    mo.md(
        """
        ---

        ## The Dilemma

        The Prisoner's Dilemma is defined by this tension:

        > **The unique Nash equilibrium is not Pareto optimal.**

        Each player's dominant strategy (Defect) leads to a collectively
        worse outcome than mutual cooperation. This is the fundamental
        problem of non-cooperative game theory: **individual rationality
        does not imply collective rationality.**

        | Property | Outcome |
        |----------|---------|
        | Nash Equilibrium | (Defect, Defect) — payoff (1, 1) |
        | Pareto Optimum | (Cooperate, Cooperate) — payoff (3, 3) |
        | Dominant Strategy | Defect (for both players) |

        The OGS formalization makes this structure explicit: the game is
        **stateless** (h = g, no mechanism layer), all computation lives
        in the policy layer, and the feedback loop carries payoff
        information — not state updates.
        """
    )
    return ()


if __name__ == "__main__":
    app.run()
