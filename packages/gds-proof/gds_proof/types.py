"""SymPy type aliases used throughout gds-proof.

Using ``sympy.Basic`` as the base type for all SymPy expressions.
``SympyBoolean`` is a semantic alias — pydantic cannot enforce the
subtype at runtime, but the alias communicates intent clearly.
"""

from __future__ import annotations

import sympy

# Semantic alias for any SymPy expression (numeric or boolean)
SympyExpr = sympy.Basic

# Semantic alias for a SymPy Boolean expression (e.g. x > 0, And(p, q))
# In practice this is sympy.Basic; the alias signals expected type.
SympyBoolean = sympy.Basic
