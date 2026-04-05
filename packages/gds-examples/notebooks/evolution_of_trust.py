"""The Evolution of Trust — Iterated Prisoner's Dilemma Interactive Notebook.

Inspired by Nicky Case's "The Evolution of Trust" (https://ncase.me/trust/).
Demonstrates 8 strategies, round-robin tournaments, and evolutionary dynamics
built on an OGS game structure.

Run interactively:
    uv run marimo edit notebooks/evolution_of_trust.py

Run as read-only app:
    uv run marimo run notebooks/evolution_of_trust.py
"""
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gds-examples",
#     "plotly>=5.0",
#     "marimo>=0.20.0",
# ]
# ///

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium", app_title="The Evolution of Trust")


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

    from evolution_of_trust.model import (
        P,
        R,
        S,
        T,
        build_ir,
        get_payoff,
    )
    from evolution_of_trust.strategies import (
        ALL_STRATEGIES,
        AlwaysCooperate,
        AlwaysDefect,
        Detective,
        GrimTrigger,
        Pavlov,
        RandomStrategy,
        TitForTat,
        TitForTwoTats,
    )
    from evolution_of_trust.tournament import (
        head_to_head,
        play_round_robin,
        run_evolution,
    )

    from gds_domains.games.viz import (
        architecture_by_domain_to_mermaid,
        structural_to_mermaid,
        terminal_conditions_to_mermaid,
    )

    ir = build_ir()

    strategy_map = {
        "Always Cooperate": AlwaysCooperate,
        "Always Defect": AlwaysDefect,
        "Tit for Tat": TitForTat,
        "Grim Trigger": GrimTrigger,
        "Detective": Detective,
        "Tit for Two Tats": TitForTwoTats,
        "Pavlov": Pavlov,
        "Random": RandomStrategy,
    }

    # Nicky Case color palette
    COLORS = {
        "Always Cooperate": "#FF75FF",
        "Always Defect": "#52537F",
        "Tit for Tat": "#4089DD",
        "Grim Trigger": "#EFC701",
        "Detective": "#F6B24C",
        "Tit for Two Tats": "#88A8CE",
        "Pavlov": "#86C448",
        "Random": "#FF5E5E",
    }

    return (
        R,
        S,
        T,
        P,
        ir,
        get_payoff,
        ALL_STRATEGIES,
        AlwaysCooperate,
        AlwaysDefect,
        Detective,
        GrimTrigger,
        Pavlov,
        RandomStrategy,
        TitForTat,
        TitForTwoTats,
        head_to_head,
        play_round_robin,
        run_evolution,
        architecture_by_domain_to_mermaid,
        structural_to_mermaid,
        terminal_conditions_to_mermaid,
        strategy_map,
        COLORS,
    )


# ── Header ───────────────────────────────────────────────────


@app.cell
def header(mo):
    mo.md(
        """
        # The Evolution of Trust

        *Inspired by [Nicky Case's interactive guide](
        https://ncase.me/trust/)
        to game theory and the evolution of cooperation.*

        This notebook explores the **iterated Prisoner's Dilemma**:

        1. **Head-to-Head** — watch two strategies
           face off round by round
        2. **Tournament** — round-robin competition
           among all 8 strategies
        3. **Evolution** — populations compete and
           evolve over generations
        """
    )
    return ()


# ── Game Structure (accordion) ───────────────────────────────


@app.cell
def game_structure(
    mo,
    ir,
    R,
    T,
    S,
    P,
    structural_to_mermaid,
    terminal_conditions_to_mermaid,
    architecture_by_domain_to_mermaid,
):
    _struct_tab = mo.ui.tabs(
        {
            "Structural": mo.vstack(
                [
                    mo.md(
                        "Full game topology: simultaneous "
                        "decisions feeding into payoff "
                        "computation with feedback."
                    ),
                    mo.mermaid(structural_to_mermaid(ir)),
                ]
            ),
            "Terminal Conditions": mo.vstack(
                [
                    mo.md("All four action profiles with their payoffs."),
                    mo.mermaid(terminal_conditions_to_mermaid(ir)),
                ]
            ),
            "By Domain": mo.vstack(
                [
                    mo.md(
                        "Architecture grouped by domain: "
                        "**Alice**, **Bob**, "
                        "and **Environment**."
                    ),
                    mo.mermaid(architecture_by_domain_to_mermaid(ir)),
                ]
            ),
        }
    )

    _payoff_detail = mo.md(
        f"""
**Payoff Matrix** — Nicky Case's non-zero-sum variant
where mutual defection yields zero:

|  | Cooperate | Defect |
|---|---|---|
| **Cooperate** | ({R}, {R}) | ({S}, {T}) |
| **Defect** | ({T}, {S}) | ({P}, {P}) |

| Parameter | Value | Meaning |
|---|---|---|
| R (Reward) | {R} | Mutual cooperation |
| T (Temptation) | {T} | Defect while other cooperates |
| S (Sucker) | {S} | Cooperate while other defects |
| P (Punishment) | {P} | Mutual defection |

S = {S} (negative!) means being exploited actually
*costs* you, making the stakes higher than standard PD.
"""
    )

    mo.accordion(
        {
            "Under the Hood: OGS Game Structure": _struct_tab,
            "Under the Hood: Payoff Matrix": _payoff_detail,
        }
    )
    return ()


# ── Strategy Catalog (accordion) ─────────────────────────────


@app.cell
def strategy_catalog(mo, COLORS):
    def _badge(name, ncase_name, logic):
        _c = COLORS[name]
        return mo.md(
            f'<span style="display:inline-block;'
            f"width:12px;height:12px;"
            f"border-radius:50%;background:{_c};"
            f'margin-right:6px;vertical-align:middle">'
            f"</span>"
            f"**{name}** ({ncase_name}) — {logic}"
        )

    _cards = mo.vstack(
        [
            _badge(
                "Always Cooperate",
                "Always Cooperate",
                "Always C",
            ),
            _badge(
                "Always Defect",
                "Always Cheat",
                "Always D",
            ),
            _badge(
                "Tit for Tat",
                "Copycat",
                "C first, then copy opponent's last",
            ),
            _badge(
                "Grim Trigger",
                "Grudger",
                "C until opponent D's, then D forever",
            ),
            _badge(
                "Detective",
                "Detective",
                "Probe C,D,C,C; exploit or TfT",
            ),
            _badge(
                "Tit for Two Tats",
                "Copykitten",
                "C unless opponent D'd last 2 rounds",
            ),
            _badge(
                "Pavlov",
                "Simpleton",
                "Win-stay, lose-shift",
            ),
            _badge(
                "Random",
                "Random",
                "50/50 coin flip",
            ),
        ],
        gap=0.25,
    )

    mo.accordion({"The 8 Strategies": _cards})
    return ()


# ── Head-to-Head Controls ────────────────────────────────────


@app.cell
def head_to_head_controls(mo, strategy_map):
    _names = list(strategy_map.keys())
    dropdown_a = mo.ui.dropdown(
        options=_names,
        value="Tit for Tat",
        label="Strategy A",
    )
    dropdown_b = mo.ui.dropdown(
        options=_names,
        value="Always Defect",
        label="Strategy B",
    )
    slider_rounds = mo.ui.slider(start=5, stop=50, step=5, value=10, label="Rounds")

    mo.vstack(
        [
            mo.md("---\n\n## Head-to-Head Match"),
            mo.hstack(
                [dropdown_a, dropdown_b, slider_rounds],
                gap=1,
            ),
        ]
    )

    return (dropdown_a, dropdown_b, slider_rounds)


# ── Head-to-Head Result ──────────────────────────────────────


@app.cell
def head_to_head_result(
    mo,
    dropdown_a,
    dropdown_b,
    slider_rounds,
    strategy_map,
    head_to_head,
    COLORS,
):
    import plotly.graph_objects as _go

    _cls_a = strategy_map[dropdown_a.value]
    _cls_b = strategy_map[dropdown_b.value]
    _h2h = head_to_head(_cls_a(), _cls_b(), rounds=slider_rounds.value)
    _details = _h2h["round_details"]
    _result = _h2h["result"]
    _name_a = _result.strategy_a
    _name_b = _result.strategy_b
    _color_a = COLORS.get(_name_a, "#888")
    _color_b = COLORS.get(_name_b, "#888")

    # Scoreboard stats
    _winner = (
        _name_a
        if _result.score_a > _result.score_b
        else (_name_b if _result.score_b > _result.score_a else "Tie")
    )
    _stats = mo.hstack(
        [
            mo.stat(
                value=str(_result.score_a),
                label=_name_a,
                bordered=True,
            ),
            mo.stat(
                value=_winner,
                label="Winner",
                bordered=True,
            ),
            mo.stat(
                value=str(_result.score_b),
                label=_name_b,
                bordered=True,
            ),
        ],
        justify="center",
        gap=1,
    )

    # Cumulative score chart
    _rounds = [d["round"] for d in _details]
    _fig = _go.Figure()
    _fig.add_trace(
        _go.Scatter(
            x=_rounds,
            y=_h2h["cumulative_a"],
            mode="lines+markers",
            name=_name_a,
            line=dict(color=_color_a, width=3),
            marker=dict(size=8, color=_color_a),
            fill="tozeroy",
            fillcolor=(
                f"rgba({int(_color_a[1:3], 16)}, {int(_color_a[3:5], 16)}, "
                f"{int(_color_a[5:7], 16)}, 0.13)"
            ),
        )
    )
    _fig.add_trace(
        _go.Scatter(
            x=_rounds,
            y=_h2h["cumulative_b"],
            mode="lines+markers",
            name=_name_b,
            line=dict(color=_color_b, width=3),
            marker=dict(size=8, color=_color_b),
            fill="tozeroy",
            fillcolor=(
                f"rgba({int(_color_b[1:3], 16)}, {int(_color_b[3:5], 16)}, "
                f"{int(_color_b[5:7], 16)}, 0.13)"
            ),
        )
    )
    _fig.update_layout(
        title=dict(
            text=f"{_name_a} vs {_name_b}",
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Round",
            dtick=1,
            gridcolor="#eee",
        ),
        yaxis=dict(
            title="Cumulative Score",
            gridcolor="#eee",
            zeroline=True,
            zerolinecolor="#ccc",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(t=60, b=40, l=50, r=20),
        height=350,
    )

    # Action grid — colored C/D per round
    _action_rows = []
    for _d in _details:
        _ca = "**C**" if _d["action_a"] == "Cooperate" else "D"
        _cb = "**C**" if _d["action_b"] == "Cooperate" else "D"
        _action_rows.append(
            f"| {_d['round']} | {_ca} | {_cb} "
            f"| {_d['payoff_a']:+d} | {_d['payoff_b']:+d} |"
        )
    _action_table = mo.md(
        "| Round | A | B | A pts | B pts |\n"
        "|:---:|:---:|:---:|:---:|:---:|\n" + "\n".join(_action_rows)
    )

    mo.vstack(
        [
            _stats,
            mo.ui.plotly(_fig),
            mo.accordion({"Round-by-Round Details": _action_table}),
        ],
        gap=0.5,
    )
    return ()


# ── Tournament ───────────────────────────────────────────────


@app.cell
def tournament_result(mo, strategy_map, play_round_robin, COLORS):
    import plotly.graph_objects as _go

    _instances = [cls() for cls in strategy_map.values()]
    _tournament = play_round_robin(_instances, rounds_per_match=10)
    _avg = _tournament.avg_scores

    # Sort by avg score
    _sorted = sorted(_avg.items(), key=lambda x: x[1])
    _names = [s[0] for s in _sorted]
    _scores = [s[1] for s in _sorted]
    _bar_colors = [COLORS.get(n, "#888") for n in _names]

    _fig = _go.Figure()
    _fig.add_trace(
        _go.Bar(
            x=_scores,
            y=_names,
            orientation="h",
            marker=dict(
                color=_bar_colors,
                line=dict(color="#333", width=1),
            ),
            text=[f"{s:.1f}" for s in _scores],
            textposition="outside",
            textfont=dict(size=12),
        )
    )
    _fig.update_layout(
        title=dict(
            text="Round-Robin Tournament — Average Score per Match",
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Average Score",
            gridcolor="#eee",
            zeroline=True,
            zerolinecolor="#999",
            zerolinewidth=2,
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=13),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=50, b=40, l=130, r=60),
        height=380,
        showlegend=False,
    )

    # Winner callout
    _best = _sorted[-1]
    _worst = _sorted[0]

    mo.vstack(
        [
            mo.md(
                "---\n\n## Round-Robin Tournament\n\n"
                "Every strategy plays every other "
                "(plus itself) for 10 rounds."
            ),
            mo.ui.plotly(_fig),
            mo.hstack(
                [
                    mo.callout(
                        mo.md(f"**{_best[0]}** leads with {_best[1]:.1f} avg points"),
                        kind="success",
                    ),
                    mo.callout(
                        mo.md(
                            f"**{_worst[0]}** trails with {_worst[1]:.1f} avg points"
                        ),
                        kind="warn",
                    ),
                ],
                gap=1,
            ),
        ],
        gap=0.5,
    )
    return ()


# ── Evolution Controls ───────────────────────────────────────


@app.cell
def evolution_controls(mo):
    slider_gens = mo.ui.slider(
        start=10,
        stop=100,
        step=10,
        value=30,
        label="Generations",
    )
    slider_noise = mo.ui.slider(
        start=0.0,
        stop=0.2,
        step=0.01,
        value=0.05,
        label="Noise",
    )
    slider_match_rounds = mo.ui.slider(
        start=5,
        stop=30,
        step=5,
        value=10,
        label="Rounds per Match",
    )

    mo.vstack(
        [
            mo.md(
                "---\n\n## Evolutionary Dynamics\n\n"
                "Strategies compete over generations. "
                "Each generation, the worst performer "
                "loses a member and the best gains one."
            ),
            mo.hstack(
                [
                    slider_gens,
                    slider_noise,
                    slider_match_rounds,
                ],
                gap=1,
            ),
        ]
    )

    return (slider_gens, slider_noise, slider_match_rounds)


# ── Evolution Result ─────────────────────────────────────────


@app.cell
def evolution_result(
    mo,
    slider_gens,
    slider_noise,
    slider_match_rounds,
    strategy_map,
    run_evolution,
    COLORS,
):
    import plotly.graph_objects as _go

    _initial_pops = {name: 5 for name in strategy_map}
    _snapshots = run_evolution(
        initial_populations=_initial_pops,
        strategy_factories=strategy_map,
        generations=slider_gens.value,
        rounds_per_match=slider_match_rounds.value,
        noise=slider_noise.value,
        seed=42,
    )

    _gens = [s.generation for s in _snapshots]
    _strat_names = list(strategy_map.keys())

    _fig = _go.Figure()

    # Stacked area — add in reverse so first strategy
    # is on top visually
    for _name in reversed(_strat_names):
        _pops = [s.populations.get(_name, 0) for s in _snapshots]
        _c = COLORS.get(_name, "#888")
        _fig.add_trace(
            _go.Scatter(
                x=_gens,
                y=_pops,
                mode="lines",
                name=_name,
                line=dict(width=0.5, color=_c),
                stackgroup="one",
                fillcolor=(
                    f"rgba({int(_c[1:3], 16)}, {int(_c[3:5], 16)}, "
                    f"{int(_c[5:7], 16)}, 0.8)"
                ),
                hovertemplate=(
                    f"<b>{_name}</b><br>Gen %{{x}}: %{{y}} members<extra></extra>"
                ),
            )
        )

    _fig.update_layout(
        title=dict(
            text="Population Over Generations",
            font=dict(size=18),
        ),
        xaxis=dict(
            title="Generation",
            gridcolor="#eee",
        ),
        yaxis=dict(
            title="Population",
            gridcolor="#eee",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(t=80, b=40, l=50, r=20),
        height=500,
        hovermode="x unified",
    )

    # Find survivors at final generation
    _final = _snapshots[-1].populations
    _survivors = {k: v for k, v in _final.items() if v > 0}
    _survivor_text = ", ".join(
        f"**{k}** ({v})"
        for k, v in sorted(
            _survivors.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    )

    mo.vstack(
        [
            mo.ui.plotly(_fig),
            mo.callout(
                mo.md(f"After {slider_gens.value} generations: {_survivor_text}"),
                kind="info",
            ),
        ],
        gap=0.5,
    )
    return ()


# ── The Lesson ───────────────────────────────────────────────


@app.cell
def the_lesson(mo):
    mo.vstack(
        [
            mo.md("---\n\n## The Lesson"),
            mo.callout(
                mo.md(
                    '*"What the game of trust teaches us '
                    "is that the success of trust depends "
                    "not just on individual character, but "
                    "on the environment — how many "
                    "interactions there are, whether there "
                    "are mistakes, and what the payoff "
                    'structure looks like."*'
                ),
                kind="neutral",
            ),
            mo.md(
                """
- **Tit-for-Tat** succeeds not by winning
  individual matches, but by building cooperation
  and retaliating against exploitation
- **Always Defect** thrives in short games but
  loses when cooperation has time to establish
- **Noise** (mistakes) favors forgiving strategies
  like **Tit-for-Two-Tats** and **Pavlov**
- The structure of the game matters as much
  as the strategies

---

*Built with [OGS](https://github.com/BlockScience/gds-core)
and inspired by
[The Evolution of Trust](https://ncase.me/trust/)
by Nicky Case.*
"""
            ),
        ]
    )
    return ()


if __name__ == "__main__":
    app.run()
