"""Shared color palette and style helpers for gds-viz renderers.

Provides theme-aligned palettes for Mermaid's five built-in themes.
Each palette defines node fills, strokes, and text colors that harmonize
with the theme's canvas, edge, and subgraph defaults.
"""

from __future__ import annotations

from typing import Literal

# --- Theme support ---
MermaidTheme = Literal["default", "neutral", "dark", "forest", "base"]

DEFAULT_THEME: MermaidTheme = "neutral"

# Legacy constant — kept for backward compatibility
THEME_DIRECTIVE = f'%%{{init:{{"theme":"{DEFAULT_THEME}"}}}}%%'


def theme_directive(theme: MermaidTheme | None = None) -> str:
    """Return the Mermaid init directive for the given theme.

    Args:
        theme: Mermaid theme name. None uses the default ('neutral').
    """
    t = theme or DEFAULT_THEME
    return f'%%{{init:{{"theme":"{t}"}}}}%%'


# ---------------------------------------------------------------------------
# Per-theme palettes
# ---------------------------------------------------------------------------
# Each palette contains:
#   roles      — classDef styles for boundary / policy / mechanism / control / generic
#   entity     — entity cylinder style
#   param      — parameter hexagon style
#   state      — state variable (X_t) style
#   target     — traceability target style
#   empty      — placeholder / no-data style
#   subgraphs  — subgraph background styles keyed by role

_PALETTES: dict[MermaidTheme, dict] = {
    # ------------------------------------------------------------------
    # NEUTRAL — muted gray canvas, saturated classDef fills pop nicely
    # ------------------------------------------------------------------
    "neutral": {
        "roles": {
            "boundary": "fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f",
            "policy": "fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f",
            "mechanism": "fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d",
            "control": "fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764",
            "generic": "fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b",
        },
        "entity": "fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a",
        "param": "fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12",
        "state": "fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a",
        "target": "fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d",
        "empty": "fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569",
        "subgraphs": {
            "boundary": "fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af",
            "policy": "fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e",
            "mechanism": "fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534",
            "control": "fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87",
        },
    },
    # ------------------------------------------------------------------
    # DEFAULT — Mermaid's blue-toned default; softer Material-ish fills
    # ------------------------------------------------------------------
    "default": {
        "roles": {
            "boundary": "fill:#bbdefb,stroke:#1976d2,stroke-width:2px,color:#0d47a1",
            "policy": "fill:#fff9c4,stroke:#f9a825,stroke-width:2px,color:#f57f17",
            "mechanism": "fill:#c8e6c9,stroke:#388e3c,stroke-width:2px,color:#1b5e20",
            "control": "fill:#e1bee7,stroke:#8e24aa,stroke-width:2px,color:#4a148c",
            "generic": "fill:#cfd8dc,stroke:#546e7a,stroke-width:1px,color:#263238",
        },
        "entity": "fill:#eceff1,stroke:#607d8b,stroke-width:2px,color:#263238",
        "param": "fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px,color:#bf360c",
        "state": "fill:#b2dfdb,stroke:#00897b,stroke-width:2px,color:#004d40",
        "target": "fill:#ffcdd2,stroke:#e53935,stroke-width:2px,color:#b71c1c",
        "empty": "fill:#eceff1,stroke:#90a4ae,stroke-width:1px,color:#546e7a",
        "subgraphs": {
            "boundary": "fill:#e3f2fd,stroke:#64b5f6,stroke-width:1px,color:#1565c0",
            "policy": "fill:#fff8e1,stroke:#ffca28,stroke-width:1px,color:#ff8f00",
            "mechanism": "fill:#e8f5e9,stroke:#66bb6a,stroke-width:1px,color:#2e7d32",
            "control": "fill:#f3e5f5,stroke:#ce93d8,stroke-width:1px,color:#7b1fa2",
        },
    },
    # ------------------------------------------------------------------
    # DARK — dark canvas; saturated fills with light text for contrast
    # ------------------------------------------------------------------
    "dark": {
        "roles": {
            "boundary": "fill:#1e40af,stroke:#60a5fa,stroke-width:2px,color:#dbeafe",
            "policy": "fill:#92400e,stroke:#fbbf24,stroke-width:2px,color:#fef3c7",
            "mechanism": "fill:#166534,stroke:#4ade80,stroke-width:2px,color:#dcfce7",
            "control": "fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#f3e8ff",
            "generic": "fill:#334155,stroke:#94a3b8,stroke-width:1px,color:#e2e8f0",
        },
        "entity": "fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#e2e8f0",
        "param": "fill:#7c2d12,stroke:#fb923c,stroke-width:2px,color:#ffedd5",
        "state": "fill:#134e4a,stroke:#2dd4bf,stroke-width:2px,color:#ccfbf1",
        "target": "fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fee2e2",
        "empty": "fill:#1e293b,stroke:#475569,stroke-width:1px,color:#94a3b8",
        "subgraphs": {
            "boundary": "fill:#172554,stroke:#3b82f6,stroke-width:1px,color:#93c5fd",
            "policy": "fill:#451a03,stroke:#d97706,stroke-width:1px,color:#fcd34d",
            "mechanism": "fill:#052e16,stroke:#16a34a,stroke-width:1px,color:#86efac",
            "control": "fill:#3b0764,stroke:#9333ea,stroke-width:1px,color:#d8b4fe",
        },
    },
    # ------------------------------------------------------------------
    # FOREST — green-tinted; earthy, nature-inspired fills
    # ------------------------------------------------------------------
    "forest": {
        "roles": {
            "boundary": "fill:#a7f3d0,stroke:#059669,stroke-width:2px,color:#064e3b",
            "policy": "fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#78350f",
            "mechanism": "fill:#86efac,stroke:#15803d,stroke-width:2px,color:#14532d",
            "control": "fill:#d9f99d,stroke:#65a30d,stroke-width:2px,color:#365314",
            "generic": "fill:#d1d5db,stroke:#6b7280,stroke-width:1px,color:#1f2937",
        },
        "entity": "fill:#ecfdf5,stroke:#34d399,stroke-width:2px,color:#064e3b",
        "param": "fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f",
        "state": "fill:#d1fae5,stroke:#10b981,stroke-width:2px,color:#065f46",
        "target": "fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#7f1d1d",
        "empty": "fill:#f3f4f6,stroke:#9ca3af,stroke-width:1px,color:#6b7280",
        "subgraphs": {
            "boundary": "fill:#d1fae5,stroke:#6ee7b7,stroke-width:1px,color:#047857",
            "policy": "fill:#fef9c3,stroke:#facc15,stroke-width:1px,color:#a16207",
            "mechanism": "fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534",
            "control": "fill:#ecfccb,stroke:#a3e635,stroke-width:1px,color:#4d7c0f",
        },
    },
    # ------------------------------------------------------------------
    # BASE — minimal chrome; very light fills, thin strokes
    # ------------------------------------------------------------------
    "base": {
        "roles": {
            "boundary": "fill:#eff6ff,stroke:#3b82f6,stroke-width:1px,color:#1e40af",
            "policy": "fill:#fffbeb,stroke:#f59e0b,stroke-width:1px,color:#92400e",
            "mechanism": "fill:#f0fdf4,stroke:#22c55e,stroke-width:1px,color:#166534",
            "control": "fill:#faf5ff,stroke:#a855f7,stroke-width:1px,color:#581c87",
            "generic": "fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,color:#475569",
        },
        "entity": "fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#334155",
        "param": "fill:#fff7ed,stroke:#f97316,stroke-width:1px,color:#9a3412",
        "state": "fill:#f0fdfa,stroke:#14b8a6,stroke-width:1px,color:#115e59",
        "target": "fill:#fef2f2,stroke:#ef4444,stroke-width:1px,color:#991b1b",
        "empty": "fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px,color:#94a3b8",
        "subgraphs": {
            "boundary": "fill:#f8fafc,stroke:#93c5fd,stroke-width:1px,color:#2563eb",
            "policy": "fill:#fffbeb,stroke:#fcd34d,stroke-width:1px,color:#b45309",
            "mechanism": "fill:#f0fdf4,stroke:#86efac,stroke-width:1px,color:#15803d",
            "control": "fill:#faf5ff,stroke:#d8b4fe,stroke-width:1px,color:#7c3aed",
        },
    },
}


def _palette(theme: MermaidTheme | None) -> dict:
    """Return the palette dict for a theme, falling back to default."""
    return _PALETTES.get(theme or DEFAULT_THEME, _PALETTES[DEFAULT_THEME])


# --- Legacy module-level constants (backward compat, point to neutral) ---

ROLE_STYLES: dict[str, str] = _PALETTES["neutral"]["roles"]
ENTITY_STYLE: str = _PALETTES["neutral"]["entity"]
PARAM_STYLE: str = _PALETTES["neutral"]["param"]
STATE_STYLE: str = _PALETTES["neutral"]["state"]
TARGET_STYLE: str = _PALETTES["neutral"]["target"]
EMPTY_STYLE: str = _PALETTES["neutral"]["empty"]
ROLE_SUBGRAPH_STYLES: dict[str, str] = _PALETTES["neutral"]["subgraphs"]

# Subgraph IDs used by canonical.py
CANONICAL_SUBGRAPH_IDS: dict[str, str] = {
    "U": "boundary",
    "g": "policy",
    "f": "mechanism",
    "ctrl": "control",
}


# --- Public helpers ---


def classdefs_for_roles(theme: MermaidTheme | None = None) -> list[str]:
    """Return classDef lines for all role styles."""
    p = _palette(theme)
    return [f"    classDef {name} {style}" for name, style in p["roles"].items()]


def classdefs_for_all(theme: MermaidTheme | None = None) -> list[str]:
    """Return classDef lines for roles + entity + param + state + target."""
    p = _palette(theme)
    lines = classdefs_for_roles(theme)
    lines.append(f"    classDef entity {p['entity']}")
    lines.append(f"    classDef param {p['param']}")
    lines.append(f"    classDef state {p['state']}")
    lines.append(f"    classDef target {p['target']}")
    lines.append(f"    classDef empty {p['empty']}")
    return lines


def subgraph_style_lines(
    sg_ids: dict[str, str], theme: MermaidTheme | None = None
) -> list[str]:
    """Return style lines for subgraphs based on role mapping.

    Args:
        sg_ids: Mapping of subgraph Mermaid ID to role key
                (e.g. {"U": "boundary", "g": "policy"}).
        theme: Mermaid theme name. None uses the default.
    """
    p = _palette(theme)
    sg_styles = p["subgraphs"]
    lines = []
    for sg_id, role in sg_ids.items():
        if role in sg_styles:
            lines.append(f"    style {sg_id} {sg_styles[role]}")
    return lines
