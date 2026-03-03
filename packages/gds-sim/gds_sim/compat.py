"""Auto-detect and wrap cadCAD-style function signatures.

cadCAD policies have 4 positional args:
    (params, substep, state_history, previous_state) -> Signal

cadCAD state update functions have 5 positional args:
    (params, substep, state_history, previous_state, policy_input) -> (key, val)

gds-sim native signatures:
    policy:  (state, params, **kw) -> Signal
    suf:     (state, params, signal=, **kw) -> (key, val)

Detection runs once at Model construction time — zero cost in the hot loop.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds_sim.types import PolicyFn, Signal, SUFn


def adapt_policy(fn: PolicyFn) -> PolicyFn:
    """Wrap a cadCAD 4-arg policy to the gds-sim signature, or pass through."""
    n = _positional_count(fn)
    if n == 4:

        def _wrapped(
            state: dict[str, Any], params: dict[str, Any], **kw: Any
        ) -> Signal:
            return fn(params, kw.get("substep", 0), [], state)

        return _wrapped
    return fn


def adapt_suf(fn: SUFn) -> SUFn:
    """Wrap a cadCAD 5-arg SUF to the gds-sim signature, or pass through."""
    n = _positional_count(fn)
    if n == 5:

        def _wrapped(
            state: dict[str, Any],
            params: dict[str, Any],
            *,
            signal: dict[str, Any] | None = None,
            **kw: Any,
        ) -> tuple[str, Any]:
            return fn(params, kw.get("substep", 0), [], state, signal or {})

        return _wrapped
    return fn


def _positional_count(fn: object) -> int:
    """Count positional (POSITIONAL_ONLY + POSITIONAL_OR_KEYWORD) parameters."""
    try:
        sig = inspect.signature(fn)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return 0
    return sum(
        1
        for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    )
