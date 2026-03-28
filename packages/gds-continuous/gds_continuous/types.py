"""Type definitions for gds-continuous."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

ODEFunction = Callable[[float, list[float], dict[str, Any]], list[float]]
"""ODE right-hand side: (t, y, params) -> dy/dt."""

OutputFunction = Callable[[float, list[float], dict[str, Any]], list[float]]
"""Output equation: (t, y, params) -> observations."""

Params = dict[str, Any]
"""Parameter dict for a single subset."""

EventFunction = Callable[[float, list[float], dict[str, Any]], float]
"""Event function for solve_ivp: (t, y, params) -> float.

Zero-crossing triggers event."""

Solver = Literal["RK45", "RK23", "DOP853", "Radau", "BDF", "LSODA"]
"""SciPy ODE solver method names."""
