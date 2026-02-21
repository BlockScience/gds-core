"""Shared helpers for gds-viz renderers."""

from __future__ import annotations


def sanitize_id(name: str) -> str:
    """Convert a name to a valid Mermaid identifier.

    Replaces spaces and special chars with underscores.
    Prefixes with underscore if result starts with a digit
    (Mermaid IDs cannot start with digits).
    """
    result = (
        name.replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("(", "")
        .replace(")", "")
    )
    if not result or result[0].isdigit():
        result = "_" + result
    return result


def entity_id(ename: str) -> str:
    """Generate a unique Mermaid ID for an entity node.

    Prefixed with 'entity_' to avoid collisions with subgraph IDs
    (e.g. a tag group named "Alice" vs entity "Alice").
    """
    return f"entity_{sanitize_id(ename)}"


def param_id(pname: str) -> str:
    """Generate a unique Mermaid ID for a parameter node."""
    return f"param_{sanitize_id(pname)}"
