"""Cross-Domain Rosetta Stone — interactive marimo notebook.

Compares the same resource-pool scenario across three DSL views
(Stock-Flow, Control, Game Theory), showing how they all map to
the GDS canonical form h = f . g.

Run with: marimo run guides/rosetta/notebook.py
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        r"""
        # Cross-Domain Rosetta Stone

        The same **resource pool** scenario modeled in three domain-specific
        languages, all mapping to the GDS canonical form $h = f \circ g$.

        | DSL | Perspective | Key Idea |
        |-----|------------|----------|
        | **Stock-Flow** | Accumulation | Rates change resource level |
        | **Control** | Regulation | Controller tracks reference |
        | **Game Theory** | Strategic | Agents extract from pool |

        Each DSL compiles to a `GDSSpec`, from which `project_canonical()` extracts
        the formal decomposition. The table below summarises the **canonical spectrum**
        across all three views.
        """
    )
    return


@app.cell
def _(mo, comparison):
    _table = comparison.canonical_spectrum_table()
    mo.md(
        f"""
## Canonical Spectrum

```
{_table}
```

The spectrum reveals how the same real-world concept decomposes differently:

- **Stock-Flow** and **Control** are *dynamical* ($f \\neq \\emptyset$) — state
  evolves over time.
- **Game Theory** is *strategic* ($f = \\emptyset$) — pure policy, no persistent
  state.
"""
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---
        ## Stock-Flow View

        Models the resource pool as a stock that accumulates via supply inflow
        and depletes via consumption outflow. An auxiliary computes the net rate.

        **Key facts:** $|X|=1$, $|U|=2$, $|g|=3$, $|f|=1$, character = *Dynamical*
        """
    )
    return


@app.cell
def _(mo, gds_viz, sf_view):
    _model = sf_view.build_model()
    _spec = sf_view.build_spec()
    _system = sf_view.build_system()
    _canonical = sf_view.build_canonical()

    _structural_mermaid = gds_viz.system_to_mermaid(_system)
    _canonical_mermaid = gds_viz.canonical_to_mermaid(_canonical)

    mo.vstack(
        [
            mo.md(f"**Model:** {_model.name}"),
            mo.ui.tabs(
                {
                    "Structural Diagram": mo.mermaid(_structural_mermaid),
                    "Canonical Diagram": mo.mermaid(_canonical_mermaid),
                    "Formula": mo.md(
                        f"$$\n{_canonical.formula()}\n$$\n\n"
                        f"- State X: `{list(_canonical.state_variables)}`\n"
                        f"- Inputs U: `{list(_canonical.input_ports)}`\n"
                        f"- Policy g: `{list(_canonical.policy_blocks)}`\n"
                        f"- Mechanism f: `{list(_canonical.mechanism_blocks)}`"
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---
        ## Control View

        Models the same resource pool as a feedback control system.
        A controller adjusts supply to track an exogenous target reference level.

        **Key facts:** $|X|=1$, $|U|=1$, $|g|=2$, $|f|=1$, character = *Dynamical*
        """
    )
    return


@app.cell
def _(mo, gds_viz, ctrl_view):
    _model = ctrl_view.build_model()
    _spec = ctrl_view.build_spec()
    _system = ctrl_view.build_system()
    _canonical = ctrl_view.build_canonical()

    _structural_mermaid = gds_viz.system_to_mermaid(_system)
    _canonical_mermaid = gds_viz.canonical_to_mermaid(_canonical)

    mo.vstack(
        [
            mo.md(f"**Model:** {_model.name}"),
            mo.ui.tabs(
                {
                    "Structural Diagram": mo.mermaid(_structural_mermaid),
                    "Canonical Diagram": mo.mermaid(_canonical_mermaid),
                    "Formula": mo.md(
                        f"$$\n{_canonical.formula()}\n$$\n\n"
                        f"- State X: `{list(_canonical.state_variables)}`\n"
                        f"- Inputs U: `{list(_canonical.input_ports)}`\n"
                        f"- Policy g: `{list(_canonical.policy_blocks)}`\n"
                        f"- Mechanism f: `{list(_canonical.mechanism_blocks)}`"
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---
        ## Game Theory View

        Models the resource pool as a two-player extraction game. Two agents
        simultaneously choose extraction amounts; a payoff function computes
        allocations. No persistent state — pure strategic interaction.

        **Key facts:** $|X|=0$, $|U|=1$, $|g|=3$, $|f|=0$, character = *Strategic*
        """
    )
    return


@app.cell
def _(mo, gds_viz, game_view):
    _pattern = game_view.build_pattern()
    _canonical = game_view.build_canonical()

    _canonical_mermaid = gds_viz.canonical_to_mermaid(_canonical)

    mo.vstack(
        [
            mo.md(f"**Pattern:** {_pattern.name}"),
            mo.ui.tabs(
                {
                    "Canonical Diagram": mo.mermaid(_canonical_mermaid),
                    "Formula": mo.md(
                        "Since there are no mechanisms ($|f|=0$), the canonical "
                        "form reduces to $h = g$ — pure policy.\n\n"
                        f"- State X: `{list(_canonical.state_variables)}`\n"
                        f"- Inputs U: `{list(_canonical.input_ports)}`\n"
                        f"- Policy g: `{list(_canonical.policy_blocks)}`\n"
                        f"- Mechanism f: `{list(_canonical.mechanism_blocks)}`"
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ---
        ## Cross-Domain Comparison

        Select a view below to explore in detail, or browse the tabs for a
        side-by-side comparison of all three canonical diagrams.
        """
    )
    return


@app.cell
def _(mo, gds_viz, sf_view, ctrl_view, game_view, comparison):
    _canonicals = comparison.build_all_canonicals()

    _sf_system = sf_view.build_system()
    _ctrl_system = ctrl_view.build_system()

    _sf_canonical_mermaid = gds_viz.canonical_to_mermaid(_canonicals["Stock-Flow"])
    _ctrl_canonical_mermaid = gds_viz.canonical_to_mermaid(_canonicals["Control"])
    _game_canonical_mermaid = gds_viz.canonical_to_mermaid(_canonicals["Game Theory"])

    view_dropdown = mo.ui.dropdown(
        options=["Stock-Flow", "Control", "Game Theory"],
        value="Stock-Flow",
        label="Select view:",
    )

    _comparison_tabs = mo.ui.tabs(
        {
            "Stock-Flow Canonical": mo.mermaid(_sf_canonical_mermaid),
            "Control Canonical": mo.mermaid(_ctrl_canonical_mermaid),
            "Game Theory Canonical": mo.mermaid(_game_canonical_mermaid),
        }
    )

    # Build comparison markdown from canonical data
    _rows = []
    for _name, _c in _canonicals.items():
        _x = len(_c.state_variables)
        _u = len(_c.input_ports)
        _g = len(_c.policy_blocks)
        _f = len(_c.mechanism_blocks)
        _char = "Dynamical" if _f > 0 else "Strategic"
        _form = _c.formula()
        _rows.append(f"| {_name} | {_x} | {_u} | {_g} | {_f} | {_form} | {_char} |")

    _comparison_md = mo.md(
        "### Comparison Data\n\n"
        "| View | |X| | |U| | |g| | |f| | Formula | Character |\n"
        "|------|-----|-----|-----|-----|---------|----------|\n" + "\n".join(_rows)
    )

    mo.vstack(
        [
            view_dropdown,
            _comparison_tabs,
            _comparison_md,
        ]
    )
    return (view_dropdown,)


@app.cell
def _(mo, gds_viz, view_dropdown, sf_view, ctrl_view, game_view):
    _selected = view_dropdown.value

    if _selected == "Stock-Flow":
        _canonical = sf_view.build_canonical()
        _system = sf_view.build_system()
        _detail_structural = mo.mermaid(gds_viz.system_to_mermaid(_system))
        _detail_canonical = mo.mermaid(gds_viz.canonical_to_mermaid(_canonical))
        _detail_content = mo.vstack(
            [
                mo.md(f"### {_selected} — Detail View"),
                mo.ui.tabs(
                    {
                        "Structural": _detail_structural,
                        "Canonical": _detail_canonical,
                    }
                ),
            ]
        )
    elif _selected == "Control":
        _canonical = ctrl_view.build_canonical()
        _system = ctrl_view.build_system()
        _detail_structural = mo.mermaid(gds_viz.system_to_mermaid(_system))
        _detail_canonical = mo.mermaid(gds_viz.canonical_to_mermaid(_canonical))
        _detail_content = mo.vstack(
            [
                mo.md(f"### {_selected} — Detail View"),
                mo.ui.tabs(
                    {
                        "Structural": _detail_structural,
                        "Canonical": _detail_canonical,
                    }
                ),
            ]
        )
    else:
        _canonical = game_view.build_canonical()
        _detail_canonical = mo.mermaid(gds_viz.canonical_to_mermaid(_canonical))
        _detail_content = mo.vstack(
            [
                mo.md(f"### {_selected} — Detail View"),
                mo.md("*(Game theory has no SystemIR structural diagram.)*"),
                _detail_canonical,
            ]
        )

    return (_detail_content,)


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import gds_viz
    from guides.rosetta import comparison, game_view
    from guides.rosetta import control_view as ctrl_view
    from guides.rosetta import stockflow_view as sf_view

    return comparison, ctrl_view, game_view, gds_viz, sf_view


if __name__ == "__main__":
    app.run()
