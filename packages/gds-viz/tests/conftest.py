from __future__ import annotations

import sys
from pathlib import Path

EXAMPLES_ROOT = Path(__file__).resolve().parents[2] / "gds-examples"
if EXAMPLES_ROOT.is_dir():
    sys.path.insert(0, str(EXAMPLES_ROOT))
