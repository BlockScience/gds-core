"""Pattern registry — auto-discovery of ``Pattern`` objects from a directory.

Usage::

    from ogs.registry import discover_patterns

    all_patterns = discover_patterns("./patterns")
    all_apps     = discover_patterns("./applications")

    for name, pattern in all_patterns.items():
        ir = compile_to_ir(pattern)
        report = verify(ir)

This eliminates both ``sys.path.insert()`` hacks in application files and
the repeated ``importlib.util`` boilerplate in test modules.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ogs.dsl.pattern import Pattern


def discover_patterns(
    directory: str | Path,
    attribute: str = "pattern",
) -> dict[str, Pattern]:
    """Scan a directory for Python files that expose a ``Pattern`` object.

    For each ``.py`` file found (excluding ``__init__.py`` and files whose
    stem starts with ``_``), the function attempts to import the module and
    retrieve the named ``attribute``.  Files that do not expose the attribute,
    or that fail to import, are silently skipped.

    Modules are registered in ``sys.modules`` under their stem name so that
    intra-project relative imports (e.g. ``from patterns._agents import ...``)
    continue to work correctly after discovery.

    Args:
        directory: Path to scan.  May be absolute or relative to the current
            working directory.
        attribute: Name of the module-level variable to look for.  Defaults
            to ``"pattern"``, the conventional top-level name used in
            pattern modules.

    Returns:
        An ordered ``dict`` mapping module stem name → ``Pattern`` object,
        in filesystem (alphabetical) order.  Empty dict if no matching
        modules are found.

    Raises:
        NotADirectoryError: If ``directory`` does not exist or is not a
            directory.

    Example — in a test file::

        from pathlib import Path
        import pytest
        from ogs.registry import discover_patterns

        PATTERNS_DIR = Path(__file__).parent.parent / "patterns"
        ALL_PATTERNS = discover_patterns(PATTERNS_DIR)

        @pytest.mark.parametrize("name,pattern", ALL_PATTERNS.items())
        def test_compile_all(name, pattern):
            from ogs import compile_to_ir, verify
            ir = compile_to_ir(pattern)
            report = verify(ir)
            assert report.passed, f"{name}: {report.errors}"

    Example — in an application file (replaces sys.path.insert)::

        from ogs.registry import discover_patterns
        base_patterns = discover_patterns(Path(__file__).parent.parent / "patterns")
        base = base_patterns["multi_party_agreement_zoomed_in"]
        pattern = base.specialize(name="My Application", ...)
    """
    directory = Path(directory).resolve()

    if not directory.exists():
        raise NotADirectoryError(f"discover_patterns: directory not found: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"discover_patterns: not a directory: {directory}")

    result: dict[str, Pattern] = {}

    for path in sorted(directory.glob("*.py")):
        stem = path.stem
        # Skip __init__ and private/internal modules
        if stem.startswith("_"):
            continue

        spec = importlib.util.spec_from_file_location(stem, path)
        if spec is None or spec.loader is None:
            continue

        mod = importlib.util.module_from_spec(spec)
        # Register so intra-project imports resolve correctly
        sys.modules[stem] = mod

        try:
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        except Exception:
            # Silently skip modules that fail to import (missing deps, etc.)
            sys.modules.pop(stem, None)
            continue

        obj = getattr(mod, attribute, None)
        if isinstance(obj, Pattern):
            result[stem] = obj

    return result
