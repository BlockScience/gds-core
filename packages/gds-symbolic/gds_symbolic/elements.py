"""Symbolic equation elements for annotating control models with ODEs."""

from __future__ import annotations

from pydantic import BaseModel


class StateEquation(BaseModel, frozen=True):
    """Symbolic ODE right-hand side for a single state variable.

    Declares: dx_i/dt = expr, where ``expr_str`` is a SymPy-parseable
    string (e.g. ``"-k*x + u"``).

    The string form is R1-serializable. The sympy.Expr object is R3 —
    reconstructed at lambdify time via ``sympy.sympify``.
    """

    state_name: str
    expr_str: str


class OutputEquation(BaseModel, frozen=True):
    """Symbolic observation equation: y_i = h(x, u).

    Maps a sensor's output to a symbolic expression over
    state variables and inputs.
    """

    sensor_name: str
    expr_str: str
