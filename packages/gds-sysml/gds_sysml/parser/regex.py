"""Regex-based SysML v2 parser with @GDS* annotation extraction.

Tier 0 parser: works on SysML v2 textual notation files without requiring
any external tooling (SysON, OMG Pilot, etc.). Handles the subset of SysML v2
syntax needed for GDS model interchange:

- ``package`` declarations
- ``metadata def`` declarations (for @GDS* annotation types)
- ``part def`` / ``part usage`` (→ entities, state variables)
- ``action def`` / ``action usage`` (→ blocks with roles)
- ``port def`` / ``port usage`` (→ interface ports)
- ``attribute usage`` (→ state variables, parameters)
- ``connection usage`` (→ wirings)
- ``@GDS*`` metadata annotations with property bodies

Limitations:
- Does not handle full SysML v2 expression language
- Nesting is tracked by brace depth, not a full AST
- Imports and library references are not resolved
"""

from __future__ import annotations

import re
from pathlib import Path

from gds_sysml.model import (
    GDSAnnotation,
    SysMLAction,
    SysMLAttribute,
    SysMLConnection,
    SysMLModel,
    SysMLPart,
    SysMLPort,
)

# ── Regex patterns ──────────────────────────────────────────────

# @GDS* annotation: @GDSMechanism, @GDSPolicy { reads = [...]; }
_GDS_ANNOTATION = re.compile(
    r"@GDS(\w+)"
    r"(?:\s*\{([^}]*)\})?"  # optional { body }
)

# metadata def GDSFoo { ... }
_METADATA_DEF = re.compile(r"metadata\s+def\s+(\w+)")

# package Foo { ... }
_PACKAGE = re.compile(r"package\s+(\w+)")

# part def Foo { ... }  or  part foo : Foo { ... }
_PART_DEF = re.compile(r"part\s+def\s+(\w+)")
_PART_USAGE = re.compile(r"part\s+(\w+)\s*:\s*(\w+)")

# action def Foo { ... }  or  action foo : Foo { ... }
_ACTION_DEF = re.compile(r"action\s+def\s+(\w+)")
_ACTION_USAGE = re.compile(r"action\s+(\w+)\s*:\s*(\w+)")

# port def Foo { ... }  or  port foo : Foo
_PORT_DEF = re.compile(r"port\s+def\s+(\w+)")
_PORT_USAGE = re.compile(r"(in|out|inout)?\s*port\s+(\w+)\s*:\s*(\w+)")

# attribute foo : Type  or  attribute foo : Type = value
_ATTRIBUTE = re.compile(
    r"attribute\s+(\w+)\s*:\s*(\w+)"
    r"(?:\s*=\s*(.+?))?"
    r"\s*;"
)

# connection usage: connect source to target
_CONNECTION = re.compile(r"connect\s+([\w.]+)\s+to\s+([\w.]+)")

# flow usage: flow source to target (SysML v2 alternate syntax)
_FLOW = re.compile(r"flow\s+([\w.]+)\s+to\s+([\w.]+)")

# ── Annotation property parser ──────────────────────────────────


def _parse_annotation_body(body: str) -> dict[str, str | list[str]]:
    """Parse the body of a @GDS* annotation into key-value pairs.

    Handles:
    - ``key = "value";``
    - ``key = value;``
    - ``key = [a, b, c];`` (list values)
    """
    props: dict[str, str | list[str]] = {}
    if not body:
        return props

    for match in re.finditer(
        r"(\w+)\s*=\s*"
        r"(?:"
        r"\[([^\]]*)\]"  # list value
        r"|"
        r'"([^"]*)"'  # quoted string
        r"|"
        r"(\S+)"  # bare value
        r")\s*;?",
        body,
    ):
        key = match.group(1)
        if match.group(2) is not None:
            # List value: [a, b, c]
            items = [
                item.strip().strip('"').strip("'")
                for item in match.group(2).split(",")
                if item.strip()
            ]
            props[key] = items
        elif match.group(3) is not None:
            props[key] = match.group(3)
        elif match.group(4) is not None:
            props[key] = match.group(4).rstrip(";")

    return props


def _extract_annotations(line: str) -> list[GDSAnnotation]:
    """Extract all @GDS* annotations from a line."""
    annotations = []
    for m in _GDS_ANNOTATION.finditer(line):
        kind = m.group(1)
        body = m.group(2) or ""
        props = _parse_annotation_body(body)
        annotations.append(GDSAnnotation(kind=kind, properties=props))
    return annotations


# ── Main parser ─────────────────────────────────────────────────


def parse_sysml(source: str | Path) -> SysMLModel:
    """Parse a SysML v2 textual notation file into a SysMLModel.

    Args:
        source: Either the SysML source text directly, or a Path to a
            ``.sysml`` file.

    Returns:
        A populated SysMLModel with parts, actions, connections, and
        @GDS* annotations extracted.
    """
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    elif "\n" not in source and source.endswith(".sysml"):
        text = Path(source).read_text(encoding="utf-8")
    else:
        text = source

    model = SysMLModel()

    # State tracking
    context_stack: list[tuple[str, str]] = []  # (kind, name)
    brace_depth = 0
    pending_annotations: list[GDSAnnotation] = []

    # Collect all lines, stripping comments and joining multi-line annotations
    lines = _join_multiline_annotations(_strip_comments(text))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Count braces for depth tracking
        open_braces = stripped.count("{")
        close_braces = stripped.count("}")

        # Extract @GDS* annotations (they precede the element they annotate)
        line_annotations = _extract_annotations(stripped)
        if line_annotations and not any(
            p.search(stripped)
            for p in [
                _PART_DEF,
                _ACTION_DEF,
                _PORT_DEF,
                _PORT_USAGE,
                _ATTRIBUTE,
                _PART_USAGE,
                _ACTION_USAGE,
            ]
        ):
            pending_annotations.extend(line_annotations)
            brace_depth += open_braces - close_braces
            continue

        # Merge pending annotations with line annotations
        all_annotations = pending_annotations + line_annotations
        pending_annotations = []

        # Package declaration
        m = _PACKAGE.search(stripped)
        if m and not model.name:
            model.name = m.group(1)

        # Metadata def
        m = _METADATA_DEF.search(stripped)
        if m:
            model.metadata_defs.append(m.group(1))

        # Part def
        m = _PART_DEF.search(stripped)
        if m:
            name = m.group(1)
            part = SysMLPart(name=name, annotations=all_annotations)
            model.parts[name] = part
            if open_braces > close_braces:
                context_stack.append(("part", name))

        # Action def
        m = _ACTION_DEF.search(stripped)
        if m:
            name = m.group(1)
            action = SysMLAction(name=name, annotations=all_annotations)
            model.actions[name] = action
            if open_braces > close_braces:
                context_stack.append(("action", name))

        # Part usage (nested)
        m = _PART_USAGE.search(stripped)
        if m and context_stack:
            usage_name = m.group(1)
            parent_kind, parent_name = context_stack[-1]
            if parent_kind == "part" and parent_name in model.parts:
                old = model.parts[parent_name]
                model.parts[parent_name] = SysMLPart(
                    name=old.name,
                    annotations=old.annotations,
                    attributes=old.attributes,
                    ports=old.ports,
                    nested_parts=[*old.nested_parts, usage_name],
                )

        # Action usage (nested)
        m = _ACTION_USAGE.search(stripped)
        if m and context_stack:
            usage_name = m.group(1)
            parent_kind, parent_name = context_stack[-1]
            if parent_kind == "action" and parent_name in model.actions:
                old = model.actions[parent_name]
                model.actions[parent_name] = SysMLAction(
                    name=old.name,
                    annotations=old.annotations,
                    ports=old.ports,
                    attributes=old.attributes,
                    nested_actions=[*old.nested_actions, usage_name],
                )

        # Port usage
        m = _PORT_USAGE.search(stripped)
        if m and context_stack:
            direction = m.group(1) or ""
            port_name = m.group(2)
            port_type = m.group(3)
            port = SysMLPort(name=port_name, direction=direction, type_name=port_type)
            parent_kind, parent_name = context_stack[-1]
            if parent_kind == "action" and parent_name in model.actions:
                old = model.actions[parent_name]
                model.actions[parent_name] = SysMLAction(
                    name=old.name,
                    annotations=old.annotations,
                    ports=[*old.ports, port],
                    attributes=old.attributes,
                    nested_actions=old.nested_actions,
                )
            elif parent_kind == "part" and parent_name in model.parts:
                old = model.parts[parent_name]
                model.parts[parent_name] = SysMLPart(
                    name=old.name,
                    annotations=old.annotations,
                    attributes=old.attributes,
                    ports=[*old.ports, port],
                    nested_parts=old.nested_parts,
                )

        # Attribute usage
        m = _ATTRIBUTE.search(stripped)
        if m and context_stack:
            attr = SysMLAttribute(
                name=m.group(1),
                type_name=m.group(2),
                default_value=m.group(3) or "",
                annotations=all_annotations,
            )
            parent_kind, parent_name = context_stack[-1]
            if parent_kind == "part" and parent_name in model.parts:
                old = model.parts[parent_name]
                model.parts[parent_name] = SysMLPart(
                    name=old.name,
                    annotations=old.annotations,
                    attributes=[*old.attributes, attr],
                    ports=old.ports,
                    nested_parts=old.nested_parts,
                )
            elif parent_kind == "action" and parent_name in model.actions:
                old = model.actions[parent_name]
                model.actions[parent_name] = SysMLAction(
                    name=old.name,
                    annotations=old.annotations,
                    ports=old.ports,
                    attributes=[*old.attributes, attr],
                    nested_actions=old.nested_actions,
                )

        # Connection usage
        m = _CONNECTION.search(stripped) or _FLOW.search(stripped)
        if m:
            conn = SysMLConnection(source=m.group(1), target=m.group(2))
            model.connections.append(conn)

        # Update brace depth and context stack
        brace_depth += open_braces - close_braces
        for _ in range(close_braces):
            if context_stack and brace_depth <= len(context_stack) - 1:
                context_stack.pop()

    return model


def _join_multiline_annotations(lines: list[str]) -> list[str]:
    """Join multi-line @GDS* annotation bodies into single lines.

    When a ``@GDS*`` annotation opens a ``{`` that isn't closed on the same
    line, subsequent lines are concatenated until the closing ``}`` is found.
    This allows the regex-based parser to handle annotations formatted across
    multiple lines (common in SysON and OMG Pilot output).
    """
    result: list[str] = []
    accumulator = ""
    brace_depth = 0

    for line in lines:
        if accumulator:
            accumulator += " " + line.strip()
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                result.append(accumulator)
                accumulator = ""
                brace_depth = 0
        elif _GDS_ANNOTATION.search(line) and line.count("{") > line.count("}"):
            accumulator = line
            brace_depth = line.count("{") - line.count("}")
        else:
            result.append(line)

    if accumulator:
        result.append(accumulator)

    return result


def _strip_comments(text: str) -> list[str]:
    """Remove // line comments and /* block comments */ from SysML source."""
    # Remove block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    lines = []
    for line in text.splitlines():
        # Remove line comments
        comment_pos = line.find("//")
        if comment_pos >= 0:
            line = line[:comment_pos]
        lines.append(line)
    return lines
