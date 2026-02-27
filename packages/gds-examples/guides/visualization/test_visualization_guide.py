"""Tests for the visualization guide scripts and marimo notebook.

Verifies that all demo scripts produce valid Mermaid output, that
the gds-viz API works correctly across themes, view types, and DSLs,
and that the interactive marimo notebook is a valid marimo app.
"""

import importlib.util
from pathlib import Path

import pytest

from guides.visualization.all_views_demo import (
    generate_all_views,
    view_1_structural,
    view_2_canonical,
    view_3_architecture_by_role,
    view_4_architecture_by_domain,
    view_5_parameter_influence,
    view_6_traceability,
)
from guides.visualization.cross_dsl_views import (
    double_integrator_views,
    generate_cross_dsl_views,
    sir_views,
)
from guides.visualization.theme_customization import (
    ALL_THEMES,
    demo_all_themes,
    demo_default_vs_dark,
    demo_theme_with_spec_view,
)

# ── Helpers ───────────────────────────────────────────────────


def _assert_valid_mermaid(output: str) -> None:
    """Assert that a string looks like valid Mermaid output.

    Checks for:
        - Non-empty output
        - Theme init directive
        - Flowchart declaration (TD or LR or RL)
        - At least one node or subgraph
    """
    assert output, "Mermaid output is empty"
    assert "%%{init:" in output, "Missing Mermaid theme directive"
    assert any(f"flowchart {d}" in output for d in ("TD", "LR", "RL")), (
        "Missing flowchart declaration"
    )
    # Must have at least one node (bracket or parenthesis)
    assert "[" in output or "(" in output, "No nodes found in output"


# ── All Views Demo ────────────────────────────────────────────


class TestAllViewsDemo:
    """Tests for all_views_demo.py — all 6 views from the SIR model."""

    def test_view_1_structural_valid_mermaid(self):
        output = view_1_structural()
        _assert_valid_mermaid(output)
        assert "flowchart TD" in output
        assert "Contact_Process" in output
        assert "Infection_Policy" in output

    def test_view_2_canonical_valid_mermaid(self):
        output = view_2_canonical()
        _assert_valid_mermaid(output)
        assert "flowchart LR" in output
        assert "X_t" in output
        assert "X_next" in output

    def test_view_3_architecture_by_role_valid_mermaid(self):
        output = view_3_architecture_by_role()
        _assert_valid_mermaid(output)
        assert "Boundary (U)" in output
        assert "Policy (g)" in output
        assert "Mechanism (f)" in output

    def test_view_4_architecture_by_domain_valid_mermaid(self):
        output = view_4_architecture_by_domain()
        _assert_valid_mermaid(output)
        # SIR blocks have domain tags: Observation, Decision, State Update
        assert "Observation" in output or "Decision" in output

    def test_view_5_parameter_influence_valid_mermaid(self):
        output = view_5_parameter_influence()
        _assert_valid_mermaid(output)
        assert "param_beta" in output
        assert "param_gamma" in output

    def test_view_6_traceability_valid_mermaid(self):
        output = view_6_traceability()
        _assert_valid_mermaid(output)
        assert "flowchart RL" in output
        assert "target" in output

    def test_generate_all_views_returns_6_views(self):
        views = generate_all_views()
        assert len(views) == 6
        expected_keys = {
            "structural",
            "canonical",
            "architecture_by_role",
            "architecture_by_domain",
            "parameter_influence",
            "traceability",
        }
        assert set(views.keys()) == expected_keys

    def test_all_views_produce_valid_mermaid(self):
        views = generate_all_views()
        for _name, output in views.items():
            _assert_valid_mermaid(output)


# ── Theme Customization ──────────────────────────────────────


class TestThemeCustomization:
    """Tests for theme_customization.py — all 5 Mermaid themes."""

    def test_all_themes_list_has_5_themes(self):
        assert len(ALL_THEMES) == 5
        assert set(ALL_THEMES) == {"neutral", "default", "dark", "forest", "base"}

    def test_demo_all_themes_returns_all_5(self):
        results = demo_all_themes()
        assert len(results) == 5
        for theme in ALL_THEMES:
            assert theme in results

    def test_each_theme_produces_valid_mermaid(self):
        results = demo_all_themes()
        for _theme, output in results.items():
            _assert_valid_mermaid(output)

    def test_theme_directive_matches_requested_theme(self):
        results = demo_all_themes()
        for theme, output in results.items():
            assert f'"theme":"{theme}"' in output

    def test_default_vs_dark_produces_two_outputs(self):
        neutral, dark = demo_default_vs_dark()
        _assert_valid_mermaid(neutral)
        _assert_valid_mermaid(dark)
        assert '"theme":"neutral"' in neutral
        assert '"theme":"dark"' in dark

    def test_default_vs_dark_have_different_styles(self):
        neutral, dark = demo_default_vs_dark()
        # Dark theme has inverted colors (dark fills, light text)
        assert neutral != dark

    def test_theme_with_spec_view_returns_all_5(self):
        results = demo_theme_with_spec_view()
        assert len(results) == 5
        for theme, output in results.items():
            _assert_valid_mermaid(output)
            assert f'"theme":"{theme}"' in output


# ── Cross-DSL Views ──────────────────────────────────────────


class TestCrossDslViews:
    """Tests for cross_dsl_views.py — same API, different DSLs."""

    def test_sir_views_valid_mermaid(self):
        views = sir_views()
        assert len(views) == 5
        for _name, output in views.items():
            _assert_valid_mermaid(output)

    def test_double_integrator_views_valid_mermaid(self):
        views = double_integrator_views()
        assert len(views) == 5
        for _name, output in views.items():
            _assert_valid_mermaid(output)

    def test_sir_structural_has_sir_blocks(self):
        views = sir_views()
        structural = views["structural"]
        assert "Contact_Process" in structural
        assert "Infection_Policy" in structural

    def test_double_integrator_structural_has_control_blocks(self):
        views = double_integrator_views()
        structural = views["structural"]
        assert "PD" in structural
        # Dynamics blocks from the control DSL
        assert "Dynamics" in structural

    def test_cross_dsl_returns_both_domains(self):
        all_views = generate_cross_dsl_views()
        assert "sir_epidemic" in all_views
        assert "double_integrator" in all_views

    def test_same_view_keys_across_domains(self):
        all_views = generate_cross_dsl_views()
        sir_keys = set(all_views["sir_epidemic"].keys())
        di_keys = set(all_views["double_integrator"].keys())
        assert sir_keys == di_keys

    def test_sir_has_parameters_double_integrator_does_not(self):
        all_views = generate_cross_dsl_views()
        sir_params = all_views["sir_epidemic"]["parameter_influence"]
        di_params = all_views["double_integrator"]["parameter_influence"]
        # SIR has beta, gamma, contact_rate
        assert "param_beta" in sir_params
        # Double integrator has no explicit parameters
        assert "No parameters defined" in di_params

    def test_both_canonical_views_have_x_nodes(self):
        all_views = generate_cross_dsl_views()
        for domain, views in all_views.items():
            canonical = views["canonical"]
            assert "X_t" in canonical, f"{domain} canonical missing X_t"
            assert "X_next" in canonical, f"{domain} canonical missing X_next"


# ── Integration: View Consistency ─────────────────────────────


class TestViewConsistency:
    """Cross-cutting tests verifying view consistency properties."""

    def test_structural_view_uses_td_layout(self):
        """Structural views always use top-down layout."""
        views = generate_all_views()
        assert "flowchart TD" in views["structural"]

    def test_canonical_view_uses_lr_layout(self):
        """Canonical views always use left-right layout."""
        views = generate_all_views()
        assert "flowchart LR" in views["canonical"]

    def test_traceability_view_uses_rl_layout(self):
        """Traceability views always use right-left layout."""
        views = generate_all_views()
        assert "flowchart RL" in views["traceability"]

    @pytest.mark.parametrize("theme", ALL_THEMES)
    def test_all_themes_produce_nonempty_output(self, theme):
        """Every theme produces non-empty valid Mermaid."""
        from sir_epidemic.model import build_system

        from gds_viz import system_to_mermaid

        system = build_system()
        output = system_to_mermaid(system, theme=theme)
        _assert_valid_mermaid(output)
        assert len(output) > 100


# ── Marimo Notebook ──────────────────────────────────────────

_NOTEBOOK_PATH = Path(__file__).parent / "notebook.py"


class TestMarimoNotebook:
    """Tests for the interactive marimo notebook."""

    def test_notebook_file_exists(self):
        assert _NOTEBOOK_PATH.exists()

    def test_notebook_imports_marimo(self):
        """The notebook file must import marimo at the top level."""
        source = _NOTEBOOK_PATH.read_text()
        assert "import marimo" in source

    def test_notebook_has_app_object(self):
        """The notebook defines a marimo App."""
        source = _NOTEBOOK_PATH.read_text()
        assert "app = marimo.App(" in source

    def test_notebook_has_cell_decorators(self):
        """The notebook defines cells with @app.cell."""
        source = _NOTEBOOK_PATH.read_text()
        assert source.count("@app.cell") >= 10

    def test_notebook_loads_as_module(self):
        """The notebook is valid Python and loads without error."""
        spec = importlib.util.spec_from_file_location("notebook", _NOTEBOOK_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "app")

    def test_notebook_covers_all_sections(self):
        """The notebook includes all 3 guide sections."""
        source = _NOTEBOOK_PATH.read_text()
        assert "All 6" in source or "6 Views" in source
        assert "Theme" in source
        assert "Cross-DSL" in source

    def test_notebook_uses_mo_mermaid(self):
        """The notebook renders Mermaid via mo.mermaid()."""
        source = _NOTEBOOK_PATH.read_text()
        assert "mo.mermaid(" in source

    def test_notebook_has_interactive_controls(self):
        """The notebook uses dropdowns for interactivity."""
        source = _NOTEBOOK_PATH.read_text()
        assert "mo.ui.dropdown(" in source

    def test_notebook_has_tabs(self):
        """The notebook uses tabs for all-views-at-once layout."""
        source = _NOTEBOOK_PATH.read_text()
        assert "mo.ui.tabs(" in source
