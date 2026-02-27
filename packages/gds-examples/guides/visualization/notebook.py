"""GDS Visualization Guide — Interactive Marimo Notebook.

Explore all 6 gds-viz view types, 5 Mermaid themes, and cross-DSL
visualization using interactive controls. Every diagram renders live
as you change selections.

Run interactively:
    uv run marimo edit guides/visualization/notebook.py

Run as read-only app:
    uv run marimo run guides/visualization/notebook.py
"""

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium", app_title="GDS Visualization Guide")


# ── Setup ────────────────────────────────────────────────────


@app.cell
def imports():
    import marimo as mo

    return (mo,)


@app.cell
def header(mo):
    mo.md(
        """
        # GDS Visualization Guide

        The `gds-viz` package provides **6 complementary views** of any GDS
        model. Each view answers a different question about the system's
        structure, from compiled topology to parameter traceability.

        All views produce **Mermaid** diagrams that render in GitHub, GitLab,
        VS Code, Obsidian, and here in marimo via `mo.mermaid()`.

        This notebook is organized into three sections:

        1. **All 6 Views** — explore every view type on the SIR Epidemic model
        2. **Theme Customization** — see how the 5 built-in themes change the palette
        3. **Cross-DSL Views** — same API works on hand-built and DSL-compiled models
        """
    )
    return ()


# ── Section 1: Build the SIR model ──────────────────────────


@app.cell
def build_sir():
    import sys
    from pathlib import Path

    # Add stockflow/ and control/ to path for model imports
    _examples_root = Path(__file__).resolve().parent.parent.parent
    for _subdir in ("stockflow", "control"):
        _path = str(_examples_root / _subdir)
        if _path not in sys.path:
            sys.path.insert(0, _path)

    from sir_epidemic.model import build_spec, build_system

    from gds.canonical import project_canonical

    sir_spec = build_spec()
    sir_system = build_system()
    sir_canonical = project_canonical(sir_spec)
    return sir_canonical, sir_spec, sir_system


# ── Section 2: All 6 Views ──────────────────────────────────


@app.cell
def section_all_views_header(mo):
    mo.md(
        """
        ---

        ## Section 1: The 6 GDS Views

        Select a view from the dropdown to see it rendered live.
        Each view uses a different `gds-viz` function and shows a
        different perspective on the same SIR Epidemic model.
        """
    )
    return ()


@app.cell
def view_selector(mo):
    view_dropdown = mo.ui.dropdown(
        options={
            "Structural (SystemIR)": "structural",
            "Canonical GDS (h = f . g)": "canonical",
            "Architecture by Role": "role",
            "Architecture by Domain": "domain",
            "Parameter Influence": "params",
            "Traceability": "trace",
        },
        value="Structural (SystemIR)",
        label="Select view",
    )
    return (view_dropdown,)


@app.cell
def render_selected_view(mo, view_dropdown, sir_spec, sir_system, sir_canonical):
    from gds_viz import (
        canonical_to_mermaid,
        params_to_mermaid,
        spec_to_mermaid,
        system_to_mermaid,
        trace_to_mermaid,
    )

    _view_id = view_dropdown.value

    _descriptions = {
        "structural": (
            "### View 1: Structural\n\n"
            "Compiled block graph from `SystemIR`. Shows composition "
            "topology with role-based shapes and wiring types.\n\n"
            "- **Stadium** `([...])` = BoundaryAction (exogenous input)\n"
            "- **Double-bracket** `[[...]]` = terminal Mechanism (state sink)\n"
            "- **Solid arrow** = forward covariant flow\n\n"
            "**API:** `system_to_mermaid(system)`"
        ),
        "canonical": (
            "### View 2: Canonical GDS\n\n"
            "Mathematical decomposition: "
            "X_t &rarr; U &rarr; g &rarr; f &rarr; X_{t+1}.\n\n"
            "Shows the abstract dynamical system with state (X), "
            "input (U), policy (g), mechanism (f), and parameter "
            "space (&Theta;).\n\n"
            "**API:** `canonical_to_mermaid(canonical)`"
        ),
        "role": (
            "### View 3: Architecture by Role\n\n"
            "Blocks grouped by GDS role: Boundary (U), Policy (g), "
            "Mechanism (f). Entity cylinders show which state variables "
            "each mechanism writes.\n\n"
            "**API:** `spec_to_mermaid(spec)`"
        ),
        "domain": (
            "### View 4: Architecture by Domain\n\n"
            "Blocks grouped by domain tag (Observation, Decision, "
            "State Update). Shows organizational ownership.\n\n"
            "**API:** `spec_to_mermaid(spec, group_by='domain')`"
        ),
        "params": (
            "### View 5: Parameter Influence\n\n"
            "&Theta; &rarr; blocks &rarr; entities causal map. "
            "Answers: *if I change parameter X, which state variables "
            "are affected?*\n\n"
            "**API:** `params_to_mermaid(spec)`"
        ),
        "trace": (
            "### View 6: Traceability\n\n"
            "Traces `Susceptible.count` (S) backwards through the block "
            "graph. Answers: *what blocks and parameters could cause "
            "this variable to change?*\n\n"
            "**API:** `trace_to_mermaid(spec, entity, variable)`"
        ),
    }

    _mermaid_generators = {
        "structural": lambda: system_to_mermaid(sir_system),
        "canonical": lambda: canonical_to_mermaid(sir_canonical),
        "role": lambda: spec_to_mermaid(sir_spec),
        "domain": lambda: spec_to_mermaid(sir_spec, group_by="domain"),
        "params": lambda: params_to_mermaid(sir_spec),
        "trace": lambda: trace_to_mermaid(sir_spec, "Susceptible", "count"),
    }

    _mermaid_str = _mermaid_generators[_view_id]()

    mo.vstack(
        [
            mo.md(_descriptions[_view_id]),
            mo.mermaid(_mermaid_str),
        ]
    )
    return ()


# ── All 6 views at once (tabs) ──────────────────────────────


@app.cell
def all_views_tabs_header(mo):
    mo.md(
        """
        ---

        ### All 6 Views at a Glance

        Use the tabs below to quickly compare all views side-by-side.
        """
    )
    return ()


@app.cell
def all_views_tabs(mo, sir_spec, sir_system, sir_canonical):
    from gds_viz import (
        canonical_to_mermaid,
        params_to_mermaid,
        spec_to_mermaid,
        system_to_mermaid,
        trace_to_mermaid,
    )

    _tabs = mo.ui.tabs(
        {
            "1. Structural": mo.mermaid(system_to_mermaid(sir_system)),
            "2. Canonical": mo.mermaid(canonical_to_mermaid(sir_canonical)),
            "3. By Role": mo.mermaid(spec_to_mermaid(sir_spec)),
            "4. By Domain": mo.mermaid(spec_to_mermaid(sir_spec, group_by="domain")),
            "5. Parameters": mo.mermaid(params_to_mermaid(sir_spec)),
            "6. Traceability": mo.mermaid(
                trace_to_mermaid(sir_spec, "Susceptible", "count")
            ),
        }
    )
    return (_tabs,)


# ── Section 3: Theme Customization ──────────────────────────


@app.cell
def section_themes_header(mo):
    mo.md(
        """
        ---

        ## Section 2: Theme Customization

        Every `gds-viz` view function accepts a `theme=` parameter.
        There are **5 built-in Mermaid themes** — select one below
        to see how it changes the palette.

        Themes affect node fills, strokes, text colors, and subgraph
        backgrounds. Choose based on your rendering context:

        | Theme | Best for |
        |-------|----------|
        | `neutral` | Light backgrounds (GitHub, docs) |
        | `default` | Mermaid's blue-toned Material style |
        | `dark` | Dark-mode renderers |
        | `forest` | Green-tinted, earthy |
        | `base` | Minimal chrome, very light |
        """
    )
    return ()


@app.cell
def theme_controls(mo):
    theme_dropdown = mo.ui.dropdown(
        options=["neutral", "default", "dark", "forest", "base"],
        value="neutral",
        label="Theme",
    )
    theme_view_dropdown = mo.ui.dropdown(
        options={
            "Structural": "structural",
            "Architecture by Role": "role",
        },
        value="Structural",
        label="View",
    )
    mo.hstack([theme_dropdown, theme_view_dropdown], justify="start", gap=1)
    return theme_dropdown, theme_view_dropdown


@app.cell
def render_themed_view(mo, theme_dropdown, theme_view_dropdown, sir_spec, sir_system):
    from gds_viz import spec_to_mermaid, system_to_mermaid

    _theme = theme_dropdown.value
    _view = theme_view_dropdown.value

    if _view == "structural":
        _mermaid = system_to_mermaid(sir_system, theme=_theme)
    else:
        _mermaid = spec_to_mermaid(sir_spec, theme=_theme)

    mo.vstack(
        [
            mo.md(f"**Theme: `{_theme}`** | **View: {_view}**"),
            mo.mermaid(_mermaid),
        ]
    )
    return ()


@app.cell
def theme_comparison_header(mo):
    mo.md(
        """
        ### Side-by-Side: Neutral vs Dark

        The two most common choices compared on the structural view.
        """
    )
    return ()


@app.cell
def theme_side_by_side(mo, sir_system):
    from gds_viz import system_to_mermaid

    _neutral = system_to_mermaid(sir_system, theme="neutral")
    _dark = system_to_mermaid(sir_system, theme="dark")

    mo.hstack(
        [
            mo.vstack([mo.md("**Neutral**"), mo.mermaid(_neutral)]),
            mo.vstack([mo.md("**Dark**"), mo.mermaid(_dark)]),
        ],
        widths="equal",
    )
    return ()


# ── Section 4: Cross-DSL Views ──────────────────────────────


@app.cell
def section_cross_dsl_header(mo):
    mo.md(
        """
        ---

        ## Section 3: Cross-DSL Views

        The `gds-viz` API is **DSL-neutral** — it operates on `GDSSpec`
        and `SystemIR`, which every compilation path produces.

        Compare the **SIR Epidemic** (hand-built with GDS primitives)
        against the **Double Integrator** (built via the `gds-control`
        DSL). The same view functions work unchanged on both.
        """
    )
    return ()


@app.cell
def build_double_integrator():
    from double_integrator.model import build_spec, build_system

    from gds.canonical import project_canonical

    di_spec = build_spec()
    di_system = build_system()
    di_canonical = project_canonical(di_spec)
    return di_canonical, di_spec, di_system


@app.cell
def cross_dsl_controls(mo):
    model_dropdown = mo.ui.dropdown(
        options={
            "SIR Epidemic (hand-built)": "sir",
            "Double Integrator (control DSL)": "di",
        },
        value="SIR Epidemic (hand-built)",
        label="Model",
    )
    cross_view_dropdown = mo.ui.dropdown(
        options={
            "Structural": "structural",
            "Canonical": "canonical",
            "Architecture by Role": "role",
            "Parameter Influence": "params",
            "Traceability": "trace",
        },
        value="Structural",
        label="View",
    )
    mo.hstack([model_dropdown, cross_view_dropdown], justify="start", gap=1)
    return cross_view_dropdown, model_dropdown


@app.cell
def render_cross_dsl_view(
    mo,
    model_dropdown,
    cross_view_dropdown,
    sir_spec,
    sir_system,
    sir_canonical,
    di_spec,
    di_system,
    di_canonical,
):
    from gds_viz import (
        canonical_to_mermaid,
        params_to_mermaid,
        spec_to_mermaid,
        system_to_mermaid,
        trace_to_mermaid,
    )

    _model = model_dropdown.value
    _view = cross_view_dropdown.value

    if _model == "sir":
        _spec, _system, _canonical = sir_spec, sir_system, sir_canonical
        _trace_entity, _trace_var = "Susceptible", "count"
        _label = "SIR Epidemic"
    else:
        _spec, _system, _canonical = di_spec, di_system, di_canonical
        _trace_entity, _trace_var = "position", "value"
        _label = "Double Integrator"

    _generators = {
        "structural": lambda: system_to_mermaid(_system),
        "canonical": lambda: canonical_to_mermaid(_canonical),
        "role": lambda: spec_to_mermaid(_spec),
        "params": lambda: params_to_mermaid(_spec),
        "trace": lambda: trace_to_mermaid(_spec, _trace_entity, _trace_var),
    }

    mo.vstack(
        [
            mo.md(f"**{_label}** | **{_view}**"),
            mo.mermaid(_generators[_view]()),
        ]
    )
    return ()


# ── Canonical Comparison ─────────────────────────────────────


@app.cell
def canonical_comparison_header(mo):
    mo.md(
        """
        ### Canonical Comparison

        Both models decompose into the same `h = f . g` structure,
        but with different dimensionalities. The SIR model has
        parameters (&Theta;); the double integrator does not.
        """
    )
    return ()


@app.cell
def canonical_comparison(mo, sir_canonical, di_canonical):
    from gds_viz import canonical_to_mermaid

    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md(f"**SIR Epidemic** — `{sir_canonical.formula()}`"),
                    mo.mermaid(canonical_to_mermaid(sir_canonical)),
                ]
            ),
            mo.vstack(
                [
                    mo.md(f"**Double Integrator** — `{di_canonical.formula()}`"),
                    mo.mermaid(canonical_to_mermaid(di_canonical)),
                ]
            ),
        ],
        widths="equal",
    )
    return ()


# ── API Reference ────────────────────────────────────────────


@app.cell
def api_reference(mo):
    mo.md(
        """
        ---

        ## API Quick Reference

        All functions live in `gds_viz` and return Mermaid strings.

        | Function | Input | View |
        |----------|-------|------|
        | `system_to_mermaid(system)` | `SystemIR` | Structural |
        | `canonical_to_mermaid(canonical)` | `CanonicalGDS` | Canonical |
        | `spec_to_mermaid(spec)` | `GDSSpec` | By role |
        | `spec_to_mermaid(spec, group_by=...)` | `GDSSpec` | By domain |
        | `params_to_mermaid(spec)` | `GDSSpec` | Parameters |
        | `trace_to_mermaid(spec, ent, var)` | `GDSSpec` | Traceability |

        All accept an optional `theme=` parameter:
        `"neutral"`, `"default"`, `"dark"`, `"forest"`, `"base"`.

        ### Usage Pattern

        ```python
        from gds_viz import system_to_mermaid
        from my_model import build_system

        system = build_system()
        mermaid_str = system_to_mermaid(system, theme="dark")
        # Paste into GitHub markdown, mermaid.live, or mo.mermaid()
        ```
        """
    )
    return ()


if __name__ == "__main__":
    app.run()
