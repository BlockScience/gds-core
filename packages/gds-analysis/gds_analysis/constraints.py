"""Runtime constraint enforcement for GDS simulations.

Wraps policy functions with AdmissibleInputConstraint guards that
validate outputs against the current state before passing them downstream.

The ``depends_on`` field from AdmissibleInputConstraint is used to project
state to only the declared dependencies before calling the constraint.
This enforces the R1 structural skeleton at runtime.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds.constraints import AdmissibleInputConstraint

logger = logging.getLogger(__name__)


class ConstraintViolation(Exception):
    """Raised when a policy output violates an admissibility constraint."""


def guarded_policy(
    policy_fn: Any,
    constraints: list[AdmissibleInputConstraint],
    *,
    on_violation: str = "warn",
) -> Any:
    """Wrap a policy function with admissibility constraint checks.

    Parameters
    ----------
    policy_fn
        The original policy callable.
    constraints
        List of AdmissibleInputConstraint objects to enforce.
    on_violation
        What to do when a constraint is violated:
        - "warn": log a warning and return the signal anyway
        - "raise": raise ConstraintViolation
        - "zero": return an empty signal dict

    Returns
    -------
    A wrapped policy function with the same signature.
    """

    def _guarded(state: dict, params: dict, **kw: Any) -> dict[str, Any]:
        signal = policy_fn(state, params, **kw)

        for ac in constraints:
            if ac.constraint is None:
                continue
            # Project state to declared dependencies (R1 skeleton).
            # If depends_on is empty, pass full state (fallback).
            if ac.depends_on:
                projected = {
                    f"{ent}.{var}": state.get(f"{ent}.{var}")
                    for ent, var in ac.depends_on
                }
            else:
                projected = state
            try:
                if not ac.constraint(projected, signal):
                    msg = (
                        f"Constraint '{ac.name}' violated for "
                        f"block '{ac.boundary_block}'"
                    )
                    if on_violation == "raise":
                        raise ConstraintViolation(msg)
                    elif on_violation == "zero":
                        logger.warning(msg)
                        return {}
                    else:
                        logger.warning(msg)
            except ConstraintViolation:
                raise
            except Exception:
                logger.exception(
                    "Constraint '%s' raised during evaluation",
                    ac.name,
                )

        return signal

    _guarded.__name__ = f"guarded_{getattr(policy_fn, '__name__', 'policy')}"
    _guarded.__wrapped__ = policy_fn  # type: ignore[attr-defined]
    return _guarded
