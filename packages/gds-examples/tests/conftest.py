"""Shared test fixtures for guide tests.

Adds domain example directories (games/, stockflow/, control/) to sys.path
so that tests can import models like ``sir_epidemic.model``.
"""

import sys
from pathlib import Path

_examples_root = Path(__file__).resolve().parent.parent

for _subdir in ("games", "stockflow", "control"):
    _path = str(_examples_root / _subdir)
    if _path not in sys.path:
        sys.path.insert(0, _path)
