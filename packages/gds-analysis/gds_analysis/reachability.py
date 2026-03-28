"""Reachable set computation via trajectory sampling.

Paper Definition 4.1: R(x) = union over u in U_x of {f(x, u)}

Given a state x, the reachable set R(x) is the set of all states
reachable in one step by applying any admissible input. For discrete
input spaces, this can be computed exactly by enumeration. For
continuous spaces, Monte Carlo sampling approximates R(x).

Paper Definition 4.2: X_C ⊆ X is the configuration space — the
largest set of mutually reachable states.
"""

from __future__ import annotations

from typing import Any

from gds import GDSSpec  # noqa: TC002
from gds_sim import Model, Simulation


def reachable_set(
    spec: GDSSpec,
    model: Model,
    state: dict[str, Any],
    *,
    input_samples: list[dict[str, Any]],
    state_key: str | None = None,
) -> list[dict[str, Any]]:
    """Compute the reachable set R(x) by running one timestep per input.

    Parameters
    ----------
    spec
        GDSSpec (used for structural metadata; not directly executed).
    model
        A gds_sim.Model with policies and SUFs already wired.
    state
        The current state x from which to compute reachability.
    input_samples
        List of input dicts to try. Each dict overrides the policy
        outputs for one simulation step. For BoundaryAction blocks,
        these represent exogenous inputs u ∈ U_x.
    state_key
        If provided, extract only this key from each reached state
        for comparison. Otherwise return full state dicts.

    Returns
    -------
    List of distinct reached states (one per input sample that
    produced a unique next state).
    """
    reached: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for sample in input_samples:
        next_state = _step_once(model, state, sample)
        fingerprint = _state_fingerprint(next_state, state_key)
        if fingerprint not in seen:
            seen.add(fingerprint)
            reached.append(next_state)

    return reached


def reachable_graph(
    spec: GDSSpec,
    model: Model,
    initial_states: list[dict[str, Any]],
    *,
    input_samples: list[dict[str, Any]],
    max_depth: int = 1,
    state_key: str | None = None,
) -> dict[tuple[Any, ...], list[tuple[Any, ...]]]:
    """Build a reachability graph by BFS from initial states.

    Parameters
    ----------
    spec
        GDSSpec for structural metadata.
    model
        A gds_sim.Model with policies and SUFs wired.
    initial_states
        Starting states for the BFS.
    input_samples
        Inputs to try at each state (same set applied everywhere).
    max_depth
        Maximum BFS depth (number of steps from initial states).
    state_key
        Key to extract for state fingerprinting.

    Returns
    -------
    Adjacency dict: state fingerprint -> list of reachable state
    fingerprints.
    """
    graph: dict[tuple[Any, ...], list[tuple[Any, ...]]] = {}
    frontier = list(initial_states)
    visited: set[tuple[Any, ...]] = set()

    for _ in range(max_depth):
        next_frontier: list[dict[str, Any]] = []
        for state in frontier:
            fp = _state_fingerprint(state, state_key)
            if fp in visited:
                continue
            visited.add(fp)

            neighbors = reachable_set(
                spec,
                model,
                state,
                input_samples=input_samples,
                state_key=state_key,
            )
            neighbor_fps = [_state_fingerprint(n, state_key) for n in neighbors]
            graph[fp] = neighbor_fps
            next_frontier.extend(neighbors)

        frontier = next_frontier
        if not frontier:
            break

    return graph


def configuration_space(
    graph: dict[tuple[Any, ...], list[tuple[Any, ...]]],
) -> list[set[tuple[Any, ...]]]:
    """Find strongly connected components (SCCs) of a reachability graph.

    Paper Definition 4.2: X_C is the set of mutually reachable states.

    Returns SCCs sorted by size (largest first). The largest SCC is
    the configuration space X_C.

    Uses Tarjan's algorithm.
    """
    index_counter = [0]
    stack: list[tuple[Any, ...]] = []
    lowlink: dict[tuple[Any, ...], int] = {}
    index: dict[tuple[Any, ...], int] = {}
    on_stack: set[tuple[Any, ...]] = set()
    sccs: list[set[tuple[Any, ...]]] = []

    def strongconnect(v: tuple[Any, ...]) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc: set[tuple[Any, ...]] = set()
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.add(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in graph:
        if v not in index:
            strongconnect(v)

    return sorted(sccs, key=len, reverse=True)


def _step_once(
    model: Model,
    state: dict[str, Any],
    policy_override: dict[str, Any],
) -> dict[str, Any]:
    """Run the model for exactly one timestep with overridden inputs.

    Creates a temporary model whose policies return the override dict,
    runs for 1 timestep, and returns the resulting state.
    """

    def _override_policy(st: dict, params: dict, **kw: Any) -> dict:
        return policy_override

    override_blocks = []
    for block in model.state_update_blocks:
        override_blocks.append(
            {
                "policies": {name: _override_policy for name in block.policies},
                "variables": dict(block.variables),
            }
        )

    temp_model = Model(
        initial_state=dict(state),
        state_update_blocks=override_blocks,
        params={},
    )
    sim = Simulation(model=temp_model, timesteps=1, runs=1)
    results = sim.run()
    rows = results.to_list()
    return rows[-1] if rows else dict(state)


def _state_fingerprint(
    state: dict[str, Any],
    state_key: str | None,
) -> tuple[Any, ...]:
    """Create a hashable fingerprint of a state for deduplication."""
    if state_key is not None:
        return (state_key, state.get(state_key))
    return tuple(
        sorted(
            (k, v)
            for k, v in state.items()
            if not k.startswith(("timestep", "substep", "run", "subset"))
        )
    )
