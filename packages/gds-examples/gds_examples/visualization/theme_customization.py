"""MermaidTheme customization demo.

Demonstrates how to use and customize the 5 built-in Mermaid themes
supported by gds-viz. Each theme adjusts:
    - Node fill colors, strokes, and text colors
    - Subgraph background styling
    - Entity, parameter, state, and target node styles

Available themes:
    "neutral"  -- (default) muted gray canvas, saturated node fills
    "default"  -- Mermaid's blue-toned default, Material-ish fills
    "dark"     -- dark canvas, saturated fills with light text
    "forest"   -- green-tinted, earthy nature-inspired fills
    "base"     -- minimal chrome, very light fills, thin strokes

Usage (interactive notebook):
    uv run marimo edit packages/gds-examples/guides/visualization/notebook.py

Usage (tests):
    uv run --package gds-examples pytest packages/gds-examples/guides/visualization/ -v

Note: This module is designed to be imported by the test suite and marimo
notebook, which handle sys.path setup via conftest.py. Running as a
standalone script requires stockflow/ and control/ on sys.path.
"""

from gds_viz import MermaidTheme, system_to_mermaid

# All 5 built-in themes
ALL_THEMES: list[MermaidTheme] = ["neutral", "default", "dark", "forest", "base"]


def demo_all_themes() -> dict[MermaidTheme, str]:
    """Generate the same structural view with each built-in theme.

    Returns a dict mapping theme name to Mermaid diagram string.
    Each diagram has the same structure but different color palettes.
    """
    from sir_epidemic.model import build_system

    system = build_system()
    results: dict[MermaidTheme, str] = {}

    for theme in ALL_THEMES:
        results[theme] = system_to_mermaid(system, theme=theme)

    return results


def demo_default_vs_dark() -> tuple[str, str]:
    """Side-by-side comparison: neutral (default) vs dark theme.

    The neutral theme is best for light-background rendering (GitHub,
    VS Code light mode). The dark theme is optimized for dark-mode
    renderers with light text on dark fills.

    Returns:
        Tuple of (neutral_mermaid, dark_mermaid).
    """
    from sir_epidemic.model import build_system

    system = build_system()
    neutral = system_to_mermaid(system, theme="neutral")
    dark = system_to_mermaid(system, theme="dark")
    return neutral, dark


def demo_theme_with_spec_view() -> dict[MermaidTheme, str]:
    """Show theme support across different view types.

    Themes work with all gds-viz view functions:
        - system_to_mermaid(system, theme=...)
        - canonical_to_mermaid(canonical, theme=...)
        - spec_to_mermaid(spec, theme=...)
        - params_to_mermaid(spec, theme=...)
        - trace_to_mermaid(spec, entity, variable, theme=...)

    This demo generates the architecture-by-role view with each theme.
    """
    from sir_epidemic.model import build_spec

    from gds_viz import spec_to_mermaid

    spec = build_spec()
    results: dict[MermaidTheme, str] = {}
    for theme in ALL_THEMES:
        results[theme] = spec_to_mermaid(spec, theme=theme)
    return results


def main() -> None:
    """Print all theme variants."""
    print("=" * 60)
    print("  Theme Customization Demo")
    print("=" * 60)
    print()
    print("gds-viz supports 5 built-in Mermaid themes.")
    print("Pass theme= to any view function to change the palette.")
    print()

    # Show each theme applied to the structural view
    themed_views = demo_all_themes()
    for theme, mermaid in themed_views.items():
        print(f"\n--- Theme: {theme} ---\n")
        print(f"```mermaid\n{mermaid}\n```")

    # Show default vs dark comparison
    print("\n" + "=" * 60)
    print("  Default vs Dark comparison")
    print("=" * 60)
    neutral, dark = demo_default_vs_dark()
    print("\nNeutral (light backgrounds):")
    print(f"```mermaid\n{neutral}\n```")
    print("\nDark (dark backgrounds):")
    print(f"```mermaid\n{dark}\n```")


if __name__ == "__main__":
    main()
