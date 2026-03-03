"""Core execution loop — the hot path.

Every line in this module matters for performance.
No deepcopy, no function wrapping, no key checks at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_sim.results import Results

if TYPE_CHECKING:
    from gds_sim.model import Simulation
    from gds_sim.types import Params, StateUpdateBlock


def execute_simulation(sim: Simulation) -> Results:
    """Execute a simulation across all param subsets and runs."""
    results = Results.preallocate(sim)

    for subset_idx, params in enumerate(sim.model._param_subsets):
        for run_idx in range(sim.runs):
            _execute_single_run(sim, results, params, subset_idx, run_idx)

    return results


def _execute_single_run(
    sim: Simulation,
    results: Results,
    params: Params,
    subset_idx: int,
    run_idx: int,
) -> None:
    """Execute a single (subset, run) trajectory."""
    state = dict(sim.model.initial_state)  # shallow copy
    blocks = sim.model.state_update_blocks
    timesteps = sim.timesteps
    hooks = sim.hooks

    if hooks.before_run:
        hooks.before_run(state, params)

    results.append(state, timestep=0, substep=0, run=run_idx, subset=subset_idx)

    for t in range(1, timesteps + 1):
        for s, block in enumerate(blocks):
            signal = _execute_policies(block, state, params, t, s)
            state = _execute_sufs(block, state, params, signal, t, s)
            results.append(
                state, timestep=t, substep=s + 1, run=run_idx, subset=subset_idx
            )

        if hooks.after_step and hooks.after_step(state, t) is False:
            break

    if hooks.after_run:
        hooks.after_run(state, params)


def _execute_policies(
    block: StateUpdateBlock,
    state: dict[str, Any],
    params: Params,
    t: int,
    s: int,
) -> dict[str, Any]:
    """Run all policies in a block, aggregating signals via dict.update."""
    policies = block.policies
    if not policies:
        return {}
    signal: dict[str, Any] = {}
    for fn in policies.values():
        result = fn(state, params, timestep=t, substep=s)
        if result:
            signal.update(result)
    return signal


def _execute_sufs(
    block: StateUpdateBlock,
    state: dict[str, Any],
    params: Params,
    signal: dict[str, Any],
    t: int,
    s: int,
) -> dict[str, Any]:
    """Run all SUFs in a block, producing a new state dict."""
    new_state = dict(state)  # shallow copy ~10ns
    for fn in block.variables.values():
        key, val = fn(state, params, signal=signal, timestep=t, substep=s)
        new_state[key] = val
    return new_state
