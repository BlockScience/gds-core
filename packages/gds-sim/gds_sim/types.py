"""Type definitions for gds-sim."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Core type aliases
# ---------------------------------------------------------------------------

State = dict[str, Any]
"""Runtime state — plain dict for speed."""

Signal = dict[str, Any]
"""Policy output signal dict."""

Params = dict[str, Any]
"""Parameter dict for a single subset."""

PolicyFn = Callable[..., Signal]
"""Policy function: (state, params, **kw) -> Signal."""

SUFn = Callable[..., tuple[str, Any]]
"""State update function: (state, params, signal=, **kw) -> (key, value)."""

BeforeRunHook = Callable[[State, Params], None]
"""Called before a run starts: (initial_state, params) -> None."""

AfterRunHook = Callable[[State, Params], None]
"""Called after a run completes: (final_state, params) -> None."""

AfterStepHook = Callable[[State, int], bool | None]
"""Called after each timestep: (state, timestep) -> False to stop early."""

HistoryOption = int | Literal["full"] | None
"""State history window: None=off, int=last N, 'full'=all."""


# ---------------------------------------------------------------------------
# Frozen config objects
# ---------------------------------------------------------------------------


class StateUpdateBlock(BaseModel):
    """A partial state update block: policies produce signals, SUFs update state."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    policies: dict[str, PolicyFn] = {}
    variables: dict[str, SUFn]


class Hooks(BaseModel):
    """Lifecycle hooks for a simulation run."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    before_run: BeforeRunHook | None = None
    after_run: AfterRunHook | None = None
    after_step: AfterStepHook | None = None
