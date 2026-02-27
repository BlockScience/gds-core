"""Path setup for visualization guide tests.

Adds the stockflow/ and control/ directories to sys.path so that
imports like ``from sir_epidemic.model import ...`` and
``from double_integrator.model import ...`` resolve correctly.
"""

import sys
from pathlib import Path

_examples_root = Path(__file__).resolve().parent.parent.parent

for subdir in ("stockflow", "control"):
    path = str(_examples_root / subdir)
    if path not in sys.path:
        sys.path.insert(0, path)
