"""Interactive Getting Started guide for GDS — marimo notebook.

A progressive 5-stage tutorial that teaches GDS fundamentals using a
thermostat control system. Run with: marimo run notebook.py
"""

import marimo

__generated_with = "0.13.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        """
        # Build Your First GDS Model

        This interactive notebook walks you through **five stages** of building
        a Generalized Dynamical Systems (GDS) specification for a thermostat
        control system.

        | Stage | What You Learn |
        |-------|---------------|
        | **1 -- Minimal Model** | Types, Entity, BoundaryAction, Mechanism, `>>` |
        | **2 -- Feedback** | Policy, parameters, temporal loop (`.loop()`) |
        | **3 -- DSL Shortcut** | `gds-control` ControlModel, canonical |
        | **4 -- Verification & Viz** | Generic/semantic checks, Mermaid diagrams |
        | **5 -- Query API** | `SpecQuery` for static analysis of your spec |

        Use the dropdown below to jump to a specific stage, or scroll through
        the notebook to follow the full progression.
        """
    )
    return


@app.cell
def _(mo):
    _stage_selector = mo.ui.dropdown(
        options={
            "Stage 1 -- Minimal Model": "stage1",
            "Stage 2 -- Feedback": "stage2",
            "Stage 3 -- DSL Shortcut": "stage3",
            "Stage 4 -- Verification & Visualization": "stage4",
            "Stage 5 -- Query API": "stage5",
        },
        value="Stage 1 -- Minimal Model",
        label="Jump to stage:",
    )
    return (_stage_selector,)


# ══════════════════════════════════════════════════════════════
# Stage 1: Minimal Model
# ══════════════════════════════════════════════════════════════


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Stage 1 -- Minimal Model

        The simplest possible GDS model: a **heater** (BoundaryAction) warms a
        **room** (Entity with one state variable). Two blocks composed with `>>`.

        - **BoundaryAction**: exogenous input -- no `forward_in` ports
        - **Mechanism**: state update -- writes to entity variables, no backward ports
        - **`>>`**: sequential composition via token-matched port wiring
        """
    )
    return


@app.cell
def _(mo):
    from guides.getting_started.stage1_minimal import build_spec as _build_spec_s1
    from guides.getting_started.stage1_minimal import build_system as _build_system_s1

    _spec_s1 = _build_spec_s1()
    _system_s1 = _build_system_s1()

    _summary_s1 = mo.md(
        f"""
        ### What Stage 1 Creates

        | Component | Count | Details |
        |-----------|------:|---------|
        | Entities  | {len(_spec_s1.entities)} | {", ".join(_spec_s1.entities.keys())} |
        | Blocks    | {len(_spec_s1.blocks)} | {", ".join(_spec_s1.blocks.keys())} |
        | Wirings   | {len(_system_s1.wirings)} | auto-wired via token overlap |
        | Parameters | {len(_spec_s1.parameters)} | *(none yet -- added in stage 2)* |
        """
    )

    from gds_viz import system_to_mermaid as _s2m

    _mermaid_s1 = mo.mermaid(_s2m(_system_s1))

    mo.vstack(
        [
            _summary_s1,
            mo.md("### Structural Diagram"),
            _mermaid_s1,
        ]
    )
    return


# ══════════════════════════════════════════════════════════════
# Stage 2: Feedback
# ══════════════════════════════════════════════════════════════


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Stage 2 -- Adding Feedback

        Extend the minimal model with **observation and control**:

        - A **Sensor** (Policy) reads the room temperature
        - A **Controller** (Policy) decides the heat command
          using a `setpoint` parameter
        - A **TemporalLoop** (`.loop()`) feeds updated temperature back to the sensor
          across timesteps

        New operators: `|` (parallel composition) and `.loop()` (temporal feedback).
        """
    )
    return


@app.cell
def _(mo):
    from guides.getting_started.stage2_feedback import (
        build_spec as _build_spec_s2,
    )
    from guides.getting_started.stage2_feedback import (
        build_system as _build_system_s2,
    )

    _spec_s2 = _build_spec_s2()
    _system_s2 = _build_system_s2()

    _temporal_s2 = [w for w in _system_s2.wirings if w.is_temporal]

    _comparison = mo.md(
        f"""
        ### Stage 1 vs Stage 2

        | Property | Stage 1 | Stage 2 | Change |
        |----------|--------:|--------:|--------|
        | Blocks   | 2 | {len(_system_s2.blocks)} | +Sensor, +Controller (Policy role) |
        | Wirings  | 1 | {len(_system_s2.wirings)} | +inter-tier wiring, +temporal |
        | Temporal | 0 | {len(_temporal_s2)} | `.loop()` feeds state back to sensor |
        | Parameters | 0 | {len(_spec_s2.parameters)} | `setpoint` for controller |
        """
    )

    from gds_viz import system_to_mermaid as _s2m_2

    _mermaid_s2 = mo.mermaid(_s2m_2(_system_s2))

    mo.vstack(
        [
            _comparison,
            mo.md("### Structural Diagram (with Temporal Loop)"),
            _mermaid_s2,
        ]
    )
    return


# ══════════════════════════════════════════════════════════════
# Stage 3: DSL Shortcut
# ══════════════════════════════════════════════════════════════


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Stage 3 -- DSL Shortcut

        Rebuild the same thermostat using the **gds-control** DSL. Declare
        states, inputs, sensors, and controllers -- the compiler generates all
        types, spaces, entities, blocks, wirings, and the temporal loop
        automatically.

        **~15 lines of DSL vs ~60 lines of manual GDS construction.**
        """
    )
    return


@app.cell
def _(mo):
    from guides.getting_started.stage3_dsl import (
        build_canonical as _build_canonical_s3,
    )
    from guides.getting_started.stage3_dsl import (
        build_spec as _build_spec_s3,
    )
    from guides.getting_started.stage3_dsl import (
        build_system as _build_system_s3,
    )

    _spec_s3 = _build_spec_s3()
    _system_s3 = _build_system_s3()
    _canonical_s3 = _build_canonical_s3()
    _n_temporal_s3 = len([w for w in _system_s3.wirings if w.is_temporal])

    _dsl_comparison = mo.md(
        f"""
        ### Manual (Stage 2) vs DSL (Stage 3)

        | Property | Manual | DSL | Notes |
        |----------|-------:|----:|-------|
        | Blocks   | 4 | {len(_spec_s3.blocks)} | Same count |
        | Entities | 1 | {len(_spec_s3.entities)} | `Room` vs `temperature` |
        | Types    | 3 | {len(_spec_s3.types)} | DSL generates type set |
        | Temporal | 1 | {_n_temporal_s3} | Same structure |

        ### Canonical Decomposition: h = f . g

        The canonical projection separates the system into:
        - **X** (state): {len(_canonical_s3.state_variables)} variable(s)
        - **U** (boundary): {len(_canonical_s3.boundary_blocks)} block(s)
        - **g** (policy): {len(_canonical_s3.policy_blocks)} block(s)
        - **f** (mechanism): {len(_canonical_s3.mechanism_blocks)} block(s)
        """
    )

    from gds_viz import canonical_to_mermaid as _c2m

    _canonical_mermaid = mo.mermaid(_c2m(_canonical_s3))

    mo.vstack(
        [
            _dsl_comparison,
            mo.md("### Canonical Diagram"),
            _canonical_mermaid,
        ]
    )
    return


# ══════════════════════════════════════════════════════════════
# Stage 4: Verification & Visualization
# ══════════════════════════════════════════════════════════════


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Stage 4 -- Verification & Visualization

        GDS provides two layers of verification:

        1. **Generic checks (G-001..G-006)** on `SystemIR` -- structural topology
        2. **Semantic checks (SC-001..SC-007)** on `GDSSpec` -- domain properties

        Plus three Mermaid diagram views of the compiled system.
        """
    )
    return


@app.cell
def _(mo):
    from guides.getting_started.stage3_dsl import (
        build_spec as _build_spec_s4,
    )
    from guides.getting_started.stage3_dsl import (
        build_system as _build_system_s4,
    )
    from guides.getting_started.stage4_verify_viz import (
        generate_architecture_view as _gen_arch,
    )
    from guides.getting_started.stage4_verify_viz import (
        generate_canonical_view as _gen_canon,
    )
    from guides.getting_started.stage4_verify_viz import (
        generate_structural_view as _gen_struct,
    )
    from guides.getting_started.stage4_verify_viz import (
        run_generic_checks as _run_generic,
    )
    from guides.getting_started.stage4_verify_viz import (
        run_semantic_checks as _run_semantic,
    )

    _system_s4 = _build_system_s4()
    _spec_s4 = _build_spec_s4()

    # -- Generic checks --
    _report = _run_generic(_system_s4)
    _generic_rows = "\n".join(
        f"| {f.check_id} | {'PASS' if f.passed else 'FAIL'} | {f.message} |"
        for f in _report.findings
    )
    _generic_table = mo.md(
        f"""
        ### Generic Checks (SystemIR)

        | Check | Result | Message |
        |-------|--------|---------|
        {_generic_rows}

        **Summary**: {_report.checks_passed}/{_report.checks_total} passed,\
 {_report.errors} errors
        """
    )

    # -- Semantic checks --
    _semantic_results = _run_semantic(_spec_s4)
    _semantic_rows = "\n".join(f"| {line} |" for line in _semantic_results)
    _semantic_table = mo.md(
        f"""
        ### Semantic Checks (GDSSpec)

        | Result |
        |--------|
        {_semantic_rows}
        """
    )

    # -- Mermaid views in tabs --
    _structural_mermaid = mo.mermaid(_gen_struct(_system_s4))
    _architecture_mermaid = mo.mermaid(_gen_arch(_spec_s4))
    _canonical_mermaid_s4 = mo.mermaid(_gen_canon(_spec_s4))

    _diagram_tabs = mo.ui.tabs(
        {
            "Structural": _structural_mermaid,
            "Architecture": _architecture_mermaid,
            "Canonical": _canonical_mermaid_s4,
        }
    )

    mo.vstack(
        [
            _generic_table,
            _semantic_table,
            mo.md("### Diagrams"),
            _diagram_tabs,
        ]
    )
    return


# ══════════════════════════════════════════════════════════════
# Stage 5: Query API
# ══════════════════════════════════════════════════════════════


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Stage 5 -- Query API

        `SpecQuery` provides static analysis over a `GDSSpec` without running
        any simulation. It answers structural questions about information flow,
        parameter influence, and causal chains.
        """
    )
    return


@app.cell
def _(mo):
    from guides.getting_started.stage5_query import (
        build_query as _build_query,
    )
    from guides.getting_started.stage5_query import (
        show_blocks_by_role as _show_blocks_by_role,
    )
    from guides.getting_started.stage5_query import (
        show_causal_chain as _show_causal_chain,
    )
    from guides.getting_started.stage5_query import (
        show_dependency_graph as _show_dep_graph,
    )
    from guides.getting_started.stage5_query import (
        show_entity_updates as _show_entity_updates,
    )
    from guides.getting_started.stage5_query import (
        show_param_influence as _show_param_influence,
    )

    _query = _build_query()

    # -- Parameter influence --
    _param_map = _show_param_influence(_query)
    _param_rows = "\n".join(
        f"| `{param}` | {', '.join(blocks)} |" for param, blocks in _param_map.items()
    )
    _param_table = mo.md(
        f"""
        ### Parameter Influence

        Which blocks does each parameter affect?

        | Parameter | Blocks |
        |-----------|--------|
        {_param_rows}
        """
    )

    # -- Entity updates --
    _entity_map = _show_entity_updates(_query)
    _entity_rows_list = []
    for _ent, _vars in _entity_map.items():
        for _var, _mechs in _vars.items():
            _entity_rows_list.append(f"| `{_ent}` | `{_var}` | {', '.join(_mechs)} |")
    _entity_rows = "\n".join(_entity_rows_list)
    _entity_table = mo.md(
        f"""
        ### Entity Update Map

        Which mechanisms update each entity variable?

        | Entity | Variable | Mechanisms |
        |--------|----------|------------|
        {_entity_rows}
        """
    )

    # -- Blocks by role --
    _by_role = _show_blocks_by_role(_query)
    _role_rows = "\n".join(
        f"| **{role}** | {', '.join(blocks)} |"
        for role, blocks in _by_role.items()
        if blocks
    )
    _role_table = mo.md(
        f"""
        ### Blocks by Role

        | Role | Blocks |
        |------|--------|
        {_role_rows}
        """
    )

    # -- Causal chain --
    _affecting = _show_causal_chain(_query, "temperature", "value")
    _causal_table = mo.md(
        f"""
        ### Causal Chain: temperature.value

        Blocks that can transitively affect `temperature.value`:

        {", ".join(f"`{b}`" for b in _affecting)}
        """
    )

    # -- Dependency graph --
    _dep_graph = _show_dep_graph(_query)
    _dep_rows = "\n".join(
        f"| `{src}` | {', '.join(f'`{t}`' for t in targets)} |"
        for src, targets in _dep_graph.items()
    )
    _dep_table = mo.md(
        f"""
        ### Dependency Graph

        Block-to-block information flow:

        | Source | Targets |
        |--------|---------|
        {_dep_rows}
        """
    )

    mo.vstack(
        [
            _param_table,
            _entity_table,
            _role_table,
            _causal_table,
            _dep_table,
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ---

        ## Summary

        You have built a complete GDS specification for a thermostat system,
        progressing through five stages:

        1. **Minimal model** -- types, entity, two blocks, sequential composition
        2. **Feedback** -- policies, parameters, temporal loop
        3. **DSL** -- same system in 15 lines with `gds-control`
        4. **Verification** -- structural and semantic checks, three diagram views
        5. **Query** -- static analysis of parameter influence and causal chains

        From here, explore the other examples (`sir_epidemic`, `lotka_volterra`,
        `prisoners_dilemma`) or build your own domain model.
        """
    )
    return


if __name__ == "__main__":
    app.run()
