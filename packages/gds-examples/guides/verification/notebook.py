"""GDS Verification Guide — Interactive Marimo Notebook.

Explore the three layers of GDS verification by running checks on
deliberately broken models, inspecting findings, and watching the
fix-and-reverify workflow in action.

Run interactively:
    uv run marimo edit guides/verification/notebook.py

Run as read-only app:
    uv run marimo run guides/verification/notebook.py
"""

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium", app_title="GDS Verification Guide")


# ── Setup ────────────────────────────────────────────────────


@app.cell
def imports():
    import marimo as mo

    return (mo,)


@app.cell
def header(mo):
    mo.md(
        """
        # GDS Verification Guide

        GDS has **three layers** of verification checks, each operating
        on a different representation:

        | Layer | Checks | Operates on | Catches |
        |-------|--------|-------------|---------|
        | Generic | G-001..G-006 | `SystemIR` | Structural topology errors |
        | Semantic | SC-001..SC-007 | `GDSSpec` | Domain property violations |
        | Domain | SF-001..SF-005 | DSL model | DSL-specific errors |

        This notebook walks through each layer with deliberately broken
        models, showing what each check detects and how to fix it.
        """
    )
    return ()


# ── Section 1: Generic Checks ───────────────────────────────


@app.cell
def section_generic_header(mo):
    mo.md(
        """
        ---

        ## Section 1: Generic Checks (G-series)

        Generic checks operate on the compiled `SystemIR` — the flat
        block graph with typed wirings. They verify **structural
        topology** independent of any domain semantics.

        Select a broken model below to see which check catches the error.
        """
    )
    return ()


@app.cell
def generic_selector(mo):
    generic_dropdown = mo.ui.dropdown(
        options={
            "G-004: Dangling Wiring": "dangling",
            "G-001/G-005: Type Mismatch": "type_mismatch",
            "G-006: Covariant Cycle": "cycle",
            "G-003: Direction Contradiction": "direction",
            "G-002: Incomplete Signature": "signature",
        },
        value="dangling",
        label="Broken model",
    )
    return (generic_dropdown,)


@app.cell
def run_generic_check(mo, generic_dropdown):
    from gds.verification.engine import verify
    from gds.verification.generic_checks import (
        check_g001_domain_codomain_matching,
        check_g002_signature_completeness,
        check_g003_direction_consistency,
        check_g004_dangling_wirings,
        check_g005_sequential_type_compatibility,
        check_g006_covariant_acyclicity,
    )
    from guides.verification.broken_models import (
        covariant_cycle_system,
        dangling_wiring_system,
        direction_contradiction_system,
        incomplete_signature_system,
        type_mismatch_system,
    )

    _models = {
        "dangling": (
            dangling_wiring_system,
            [check_g004_dangling_wirings],
            "A wiring references block **'Ghost'** which doesn't exist. "
            "G-004 checks that every wiring source and target names a "
            "real block in the system.",
        ),
        "type_mismatch": (
            type_mismatch_system,
            [
                check_g001_domain_codomain_matching,
                check_g005_sequential_type_compatibility,
            ],
            "Block A outputs **'Temperature'** but Block B expects "
            "**'Pressure'**. The wiring label 'humidity' matches "
            "neither. G-001 checks label/port matching; G-005 checks "
            "sequential type compatibility.",
        ),
        "cycle": (
            covariant_cycle_system,
            [check_g006_covariant_acyclicity],
            "Blocks A &rarr; B &rarr; C &rarr; A form a **covariant "
            "cycle** — an algebraic loop within a single timestep. "
            "G-006 checks that the covariant flow graph is acyclic.",
        ),
        "direction": (
            direction_contradiction_system,
            [check_g003_direction_consistency],
            "A wiring is marked **COVARIANT** but also "
            "**is_feedback=True** — a contradiction, since feedback "
            "implies contravariant flow. G-003 catches this.",
        ),
        "signature": (
            incomplete_signature_system,
            [check_g002_signature_completeness],
            "Block **'Orphan'** has a completely empty signature — "
            "no forward or backward ports at all. G-002 flags blocks "
            "with no inputs and no outputs.",
        ),
    }

    _model_fn, _checks, _description = _models[generic_dropdown.value]
    _system = _model_fn()
    _report = verify(_system, checks=_checks)

    _failures = [f for f in _report.findings if not f.passed]
    _passes = [f for f in _report.findings if f.passed]

    _findings_rows = []
    for _f in _report.findings:
        _icon = "PASS" if _f.passed else "FAIL"
        _findings_rows.append(
            f"| {_icon} | {_f.check_id} | {_f.severity.name} | {_f.message} |"
        )
    _findings_table = (
        "| Status | Check | Severity | Message |\n"
        "|--------|-------|----------|---------|\n" + "\n".join(_findings_rows)
    )

    mo.vstack(
        [
            mo.md(f"### {_system.name}\n\n{_description}"),
            mo.md(f"**Results:** {len(_passes)} passed, {len(_failures)} failed"),
            mo.md(_findings_table),
        ]
    )
    return ()


# ── Fix and Re-verify ────────────────────────────────────────


@app.cell
def fix_reverify_header(mo):
    mo.md(
        """
        ---

        ### Fix and Re-verify

        The core workflow: build a broken model, run checks, inspect
        findings, fix the errors, re-verify. Below we compare the
        dangling-wiring system against its fixed counterpart.
        """
    )
    return ()


@app.cell
def fix_reverify_demo(mo):
    from gds.verification.engine import verify
    from guides.verification.broken_models import (
        dangling_wiring_system,
        fixed_pipeline_system,
    )

    _broken_report = verify(dangling_wiring_system())
    _fixed_report = verify(fixed_pipeline_system())

    _broken_failures = [f for f in _broken_report.findings if not f.passed]
    _fixed_failures = [f for f in _fixed_report.findings if not f.passed]

    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md(
                        "**Broken** (dangling wiring)\n\n"
                        f"- Checks: {_broken_report.checks_total}\n"
                        f"- Errors: {_broken_report.errors}\n"
                        f"- Passed: {_broken_report.checks_passed}"
                    ),
                    mo.md(
                        "\n".join(
                            f"- **{f.check_id}**: {f.message}" for f in _broken_failures
                        )
                        or "*(no failures)*"
                    ),
                ]
            ),
            mo.vstack(
                [
                    mo.md(
                        "**Fixed** (clean pipeline)\n\n"
                        f"- Checks: {_fixed_report.checks_total}\n"
                        f"- Errors: {_fixed_report.errors}\n"
                        f"- Passed: {_fixed_report.checks_passed}"
                    ),
                    mo.md(
                        "\n".join(
                            f"- **{f.check_id}**: {f.message}" for f in _fixed_failures
                        )
                        or "All checks passed."
                    ),
                ]
            ),
        ],
        widths="equal",
    )
    return ()


# ── Section 2: Semantic Checks ──────────────────────────────


@app.cell
def section_semantic_header(mo):
    mo.md(
        """
        ---

        ## Section 2: Semantic Checks (SC-series)

        Semantic checks operate on `GDSSpec` — the specification
        registry with types, entities, blocks, and parameters. They
        verify **domain properties** like completeness, determinism,
        and canonical well-formedness.

        These are complementary to generic checks: a model can pass
        all G-checks but fail SC-checks (and vice versa).
        """
    )
    return ()


@app.cell
def semantic_selector(mo):
    semantic_dropdown = mo.ui.dropdown(
        options={
            "SC-001: Orphan State Variable": "orphan",
            "SC-002: Write Conflict": "conflict",
            "SC-006/007: Empty Canonical": "empty",
        },
        value="orphan",
        label="Broken spec",
    )
    return (semantic_dropdown,)


@app.cell
def run_semantic_check(mo, semantic_dropdown):
    from gds.verification.spec_checks import (
        check_canonical_wellformedness,
        check_completeness,
        check_determinism,
    )
    from guides.verification.broken_models import (
        empty_canonical_spec,
        orphan_state_spec,
        write_conflict_spec,
    )

    _specs = {
        "orphan": (
            orphan_state_spec,
            check_completeness,
            "Entity **Reservoir** has variable `level` but no "
            "mechanism updates it. SC-001 flags this as a **WARNING** "
            "— the state variable is structurally orphaned.",
        ),
        "conflict": (
            write_conflict_spec,
            check_determinism,
            "Two mechanisms both update `Counter.value` within the "
            "same wiring. SC-002 flags this as an **ERROR** — the "
            "state transition is non-deterministic.",
        ),
        "empty": (
            empty_canonical_spec,
            check_canonical_wellformedness,
            "A spec with no mechanisms and no entities. SC-006 flags "
            "the empty state transition (f is empty); SC-007 flags "
            "the empty state space (X is empty).",
        ),
    }

    _spec_fn, _check_fn, _description = _specs[semantic_dropdown.value]
    _spec = _spec_fn()
    _findings = _check_fn(_spec)

    _failures = [f for f in _findings if not f.passed]
    _passes = [f for f in _findings if f.passed]

    _rows = []
    for _f in _findings:
        _icon = "PASS" if _f.passed else "FAIL"
        _rows.append(f"| {_icon} | {_f.check_id} | {_f.severity.name} | {_f.message} |")
    _table = (
        "| Status | Check | Severity | Message |\n"
        "|--------|-------|----------|---------|\n" + "\n".join(_rows)
    )

    mo.vstack(
        [
            mo.md(f"### {_spec.name}\n\n{_description}"),
            mo.md(f"**Results:** {len(_passes)} passed, {len(_failures)} failed"),
            mo.md(_table),
        ]
    )
    return ()


# ── Generic vs Semantic Comparison ───────────────────────────


@app.cell
def comparison_header(mo):
    mo.md(
        """
        ---

        ### Generic vs Semantic: Complementary Layers

        A well-formed model must pass **both** layers. Below we run
        both on the fixed model to confirm they are complementary.
        """
    )
    return ()


@app.cell
def comparison_demo(mo):
    from guides.verification.verification_demo import (
        demo_generic_vs_semantic,
    )

    _results = demo_generic_vs_semantic()
    _generic = _results["generic"]
    _semantic = _results["semantic"]

    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md(
                        "**Generic (G-series)**\n\n"
                        f"- Total: {_generic.checks_total}\n"
                        f"- Passed: {_generic.checks_passed}\n"
                        f"- Errors: {_generic.errors}"
                    ),
                ]
            ),
            mo.vstack(
                [
                    mo.md(
                        "**Semantic (SC-series)**\n\n"
                        f"- Total: {_semantic.checks_total}\n"
                        f"- Passed: {_semantic.checks_passed}\n"
                        f"- Errors: {_semantic.errors}"
                    ),
                ]
            ),
        ],
        widths="equal",
    )
    return ()


# ── Section 3: Domain Checks ────────────────────────────────


@app.cell
def section_domain_header(mo):
    mo.md(
        """
        ---

        ## Section 3: Domain Checks (SF-series)

        Domain checks operate on the **DSL model** before compilation.
        They catch errors that only make sense in the domain semantics
        — e.g., "orphan stock" is meaningless outside stock-flow.

        The StockFlow DSL provides SF-001..SF-005. These run before
        GDS compilation, giving early feedback in domain-native terms.
        """
    )
    return ()


@app.cell
def domain_selector(mo):
    domain_dropdown = mo.ui.dropdown(
        options={
            "SF-001: Orphan Stock": "orphan",
            "SF-003: Auxiliary Cycle": "cycle",
            "SF-004: Unused Converter": "converter",
        },
        value="orphan",
        label="Broken model",
    )
    return (domain_dropdown,)


@app.cell
def run_domain_check(mo, domain_dropdown):
    from guides.verification.domain_checks_demo import (
        cyclic_auxiliary_model,
        orphan_stock_model,
        unused_converter_model,
    )
    from stockflow.verification.checks import (
        check_sf001_orphan_stocks,
        check_sf003_auxiliary_acyclicity,
        check_sf004_converter_connectivity,
    )

    _models = {
        "orphan": (
            orphan_stock_model,
            check_sf001_orphan_stocks,
            "Stock **'Inventory'** has no connected flows — nothing "
            "fills or drains it. SF-001 flags this as a WARNING.",
        ),
        "cycle": (
            cyclic_auxiliary_model,
            check_sf003_auxiliary_acyclicity,
            "Auxiliary **'Price'** depends on 'Demand', which depends "
            "on 'Price' — a circular dependency. SF-003 flags this "
            "as an ERROR.",
        ),
        "converter": (
            unused_converter_model,
            check_sf004_converter_connectivity,
            "Converter **'Tax Rate'** is declared but no auxiliary "
            "reads from it. SF-004 flags this as a WARNING.",
        ),
    }

    _model_fn, _check_fn, _description = _models[domain_dropdown.value]
    _model = _model_fn()
    _findings = _check_fn(_model)

    _failures = [f for f in _findings if not f.passed]
    _passes = [f for f in _findings if f.passed]

    _rows = []
    for _f in _findings:
        _icon = "PASS" if _f.passed else "FAIL"
        _rows.append(f"| {_icon} | {_f.check_id} | {_f.severity.name} | {_f.message} |")
    _table = (
        "| Status | Check | Severity | Message |\n"
        "|--------|-------|----------|---------|\n" + "\n".join(_rows)
    )

    mo.vstack(
        [
            mo.md(f"### {_model.name}\n\n{_description}"),
            mo.md(f"**Results:** {len(_passes)} passed, {len(_failures)} failed"),
            mo.md(_table),
        ]
    )
    return ()


# ── Domain + GDS Combined ───────────────────────────────────


@app.cell
def combined_header(mo):
    mo.md(
        """
        ---

        ### Domain + GDS: Full Verification Stack

        The StockFlow verification engine can run domain checks (SF)
        **and** generic GDS checks (G) together. Toggle below to
        see how a good model passes both, while a broken model shows
        failures at the domain layer alongside GDS results.
        """
    )
    return ()


@app.cell
def combined_selector(mo):
    combined_dropdown = mo.ui.dropdown(
        options={
            "Good Model (Population)": "good",
            "Broken Model (Orphan Stock)": "broken",
        },
        value="good",
        label="Model",
    )
    return (combined_dropdown,)


@app.cell
def run_combined(mo, combined_dropdown):
    from guides.verification.domain_checks_demo import (
        good_stockflow_model,
        orphan_stock_model,
    )
    from stockflow.verification.engine import verify as sf_verify

    if combined_dropdown.value == "good":
        _model = good_stockflow_model()
    else:
        _model = orphan_stock_model()

    _report = sf_verify(_model, include_gds_checks=True)

    _sf = [f for f in _report.findings if f.check_id.startswith("SF-")]
    _gds = [f for f in _report.findings if f.check_id.startswith("G-")]
    _sf_fail = [f for f in _sf if not f.passed]
    _gds_fail = [f for f in _gds if not f.passed]

    mo.hstack(
        [
            mo.vstack(
                [
                    mo.md(
                        f"**Domain (SF)** — {len(_sf)} checks, {len(_sf_fail)} failures"
                    ),
                    mo.md(
                        "\n".join(
                            f"- {'FAIL' if not f.passed else 'PASS'} "
                            f"**{f.check_id}**: {f.message}"
                            for f in _sf
                        )
                        or "*(no SF checks)*"
                    ),
                ]
            ),
            mo.vstack(
                [
                    mo.md(
                        f"**Generic (G)** — {len(_gds)} checks, "
                        f"{len(_gds_fail)} failures"
                    ),
                    mo.md(
                        "\n".join(
                            f"- {'FAIL' if not f.passed else 'PASS'} "
                            f"**{f.check_id}**: {f.message}"
                            for f in _gds
                        )
                        or "*(no G checks)*"
                    ),
                ]
            ),
        ],
        widths="equal",
    )
    return ()


# ── Reference ────────────────────────────────────────────────


@app.cell
def reference(mo):
    mo.md(
        """
        ---

        ## Check Reference

        ### Generic Checks (SystemIR)

        | ID | Name | Catches |
        |----|------|---------|
        | G-001 | Domain/codomain matching | Wiring label vs port mismatch |
        | G-002 | Signature completeness | Blocks with no ports |
        | G-003 | Direction consistency | COVARIANT + feedback flag |
        | G-004 | Dangling wirings | References to missing blocks |
        | G-005 | Sequential type compat | Mismatched >> port types |
        | G-006 | Covariant acyclicity | Algebraic loops |

        ### Semantic Checks (GDSSpec)

        | ID | Name | Catches |
        |----|------|---------|
        | SC-001 | Completeness | Orphan state variables |
        | SC-002 | Determinism | Write conflicts |
        | SC-003 | Reachability | Unreachable blocks |
        | SC-004 | Type safety | TypeDef violations |
        | SC-005 | Parameter refs | Unregistered params |
        | SC-006 | Canonical f | No mechanisms |
        | SC-007 | Canonical X | No state space |

        ### Domain Checks (StockFlowModel)

        | ID | Name | Catches |
        |----|------|---------|
        | SF-001 | Orphan stocks | Stocks with no flows |
        | SF-003 | Auxiliary cycles | Circular aux deps |
        | SF-004 | Converter connectivity | Unused converters |

        ### API Pattern

        ```python
        from gds.verification.engine import verify

        system = compile_system(name="My Model", root=pipeline)
        report = verify(system)

        for finding in report.findings:
            print(f"{finding.check_id}: {finding.message}")
        ```
        """
    )
    return ()


if __name__ == "__main__":
    app.run()
