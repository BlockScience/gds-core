"""Path setup for Nash equilibrium guide tests.

Adds the games/ directory to sys.path so that imports like
``from prisoners_dilemma_nash.model import ...`` resolve correctly.
"""

import sys
from pathlib import Path

_examples_root = Path(__file__).resolve().parent.parent.parent

for subdir in ("games",):
    path = str(_examples_root / subdir)
    if path not in sys.path:
        sys.path.insert(0, path)
