"""Reachable set computation via trajectory sampling.

Paper Definition 4.1: R(x) = union over u in U_x of {f(x, u)}

Given a state x, the reachable set R(x) is the set of all states
reachable in one step by applying any admissible input. For discrete
input spaces with exhaustive enumeration, R(x) is exact. For
continuous spaces, Monte Carlo sampling approximates R(x) without
coverage guarantees.

Paper Definition 4.2: X_C is the configuration space -- the largest
set of mutually reachable states (largest SCC of the reachability graph).

Note: configuration_space operates on the sampled graph, not the true
transition structure. Missing edges (unsampled inputs) may split or
merge SCCs. For discrete systems, provide exhaustive input samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gds_sim import Model, Simulation

_META_KEYS = frozenset({"timestep", "substep", "run", "subset"})


@dataclass
class ReachabilityResult:
    """Result of a reachable set computation with coverage metadata.

    Attributes
    ----------
    states
        Distinct reached states.
    n_samples
        Number of input samples tried.
    n_distinct
        Number of distinct states found.
    is_exhaustive
        Whether the caller declared the input samples as exhaustive.
        When True, ``states`` is the exact R(x). When False, it is
        a lower bound (unsampled inputs may reach additional states).
    """

    states: list[dict[str, Any]] = field(default_factory=list)
    n_samples: int = 0
    n_distinct: int = 0
    is_exhaustive: bool = False


def reachable_set(
    model: Model,
    state: dict[str, Any],
    *,
    input_samples: list[dict[str, Any]],
    state_key: str | None = None,
    exhaustive: bool = False,
    float_tolerance: float | None = None,
) -> ReachabilityResult:
    """Compute the reachable set R(x) by running one timestep per input.

    Parameters
    ----------
    model
        A gds_sim.Model with policies and SUFs already wired.
    state
        The current state x from which to compute reachability.
    input_samples
        List of input dicts to try. Each dict overrides the policy
        outputs for one simulation step. For discrete state spaces,
        pass exhaustive inputs and set ``exhaustive=True`` for exact
        R(x). For continuous spaces, results are approximate (no
        coverage guarantee).
    state_key
        If provided, extract only this key from each reached state
        for comparison. Otherwise return full state dicts.
    exhaustive
        If True, declares that ``input_samples`` covers the full
        input space. The result's ``is_exhaustive`` flag is set
        accordingly. This is a caller assertion, not verified.
    float_tolerance
        If provided, round float values to this number of decimal
        places before fingerprinting. This prevents distinct
        fingerprints from float rounding noise. For example,
        ``float_tolerance=6`` rounds to 6 decimal places.

    Returns
    -------
    ReachabilityResult
        Contains the distinct reached states plus coverage metadata.
    """
    reached: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for sample in input_samples:
        next_state = _step_once(model, state, sample)
        fingerprint = _state_fingerprint(next_state, state_key, float_tolerance)
        if fingerprint not in seen:
            seen.add(fingerprint)
            reached.append(next_state)

    return ReachabilityResult(
        states=reached,
        n_samples=len(input_samples),
        n_distinct=len(reached),
        is_exhaustive=exhaustive,
    )


def reachable_graph(
    model: Model,
    initial_states: list[dict[str, Any]],
    *,
    input_samples: list[dict[str, Any]],
    max_depth: int = 1,
    state_key: str | None = None,
    exhaustive: bool = False,
    float_tolerance: float | None = None,
) -> dict[tuple[Any, ...], list[tuple[Any, ...]]]:
    """Build a reachability graph by BFS from initial states.

    Parameters
    ----------
    model
        A gds_sim.Model with policies and SUFs wired.
    initial_states
        Starting states for the BFS.
    input_samples
        Inputs to try at each state (same set applied everywhere).
        For discrete systems, use exhaustive enumeration for exact
        graphs. For continuous systems, results are approximate.
    max_depth
        Maximum BFS depth (number of steps from initial states).
    state_key
        Key to extract for state fingerprinting.
    exhaustive
        Passed through to ``reachable_set`` at each node.
    float_tolerance
        Passed through to ``reachable_set`` at each node.

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
            fp = _state_fingerprint(state, state_key, float_tolerance)
            if fp in visited:
                continue
            visited.add(fp)

            result = reachable_set(
                model,
                state,
                input_samples=input_samples,
                state_key=state_key,
                exhaustive=exhaustive,
                float_tolerance=float_tolerance,
            )
            neighbor_fps = [
                _state_fingerprint(n, state_key, float_tolerance) for n in result.states
            ]
            graph[fp] = neighbor_fps
            next_frontier.extend(result.states)

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

    Uses iterative Tarjan's algorithm (no recursion limit).

    Note: SCCs are only as complete as the input graph. For sampled
    (non-exhaustive) graphs, missing edges may cause SCCs to be
    smaller than the true configuration space.
    """
    index_counter = 0
    stack: list[tuple[Any, ...]] = []
    lowlink: dict[tuple[Any, ...], int] = {}
    index: dict[tuple[Any, ...], int] = {}
    on_stack: set[tuple[Any, ...]] = set()
    sccs: list[set[tuple[Any, ...]]] = []

    for root in graph:
        if root in index:
            continue

        # Iterative Tarjan using an explicit work stack.
        work: list[tuple[tuple[Any, ...], list[tuple[Any, ...]]]] = [
            (root, list(graph.get(root, [])))
        ]

        while work:
            v, neighbors = work[-1]

            if v not in index:
                index[v] = index_counter
                lowlink[v] = index_counter
                index_counter += 1
                stack.append(v)
                on_stack.add(v)

            found_unvisited = False
            while neighbors:
                w = neighbors.pop()
                if w not in index:
                    work.append((w, list(graph.get(w, []))))
                    found_unvisited = True
                    break
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])

            if found_unvisited:
                continue

            if lowlink[v] == index[v]:
                scc: set[tuple[Any, ...]] = set()
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.add(w)
                    if w == v:
                        break
                sccs.append(scc)

            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[v])

    return sorted(sccs, key=len, reverse=True)


def _step_once(
    model: Model,
    state: dict[str, Any],
    policy_override: dict[str, Any],
) -> dict[str, Any]:
    """Run the model for exactly one timestep with overridden inputs.

    Creates a temporary model whose policies return the override dict,
    runs for 1 timestep, and returns the resulting state with metadata
    keys stripped.
    """
    clean_state = {k: v for k, v in state.items() if k not in _META_KEYS}

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
        initial_state=dict(clean_state),
        state_update_blocks=override_blocks,
        params={},
    )
    sim = Simulation(model=temp_model, timesteps=1, runs=1)
    results = sim.run()
    rows = results.to_list()
    raw = rows[-1] if rows else dict(clean_state)
    return {k: v for k, v in raw.items() if k not in _META_KEYS}


def _state_fingerprint(
    state: dict[str, Any],
    state_key: str | None,
    float_tolerance: float | None = None,
) -> tuple[Any, ...]:
    """Create a hashable fingerprint of a state for deduplication.

    Parameters
    ----------
    state
        State dict to fingerprint.
    state_key
        If provided, fingerprint only this key.
    float_tolerance
        If provided (as number of decimal places), round float values
        before fingerprinting to absorb rounding noise.
    """
    if state_key is not None:
        val = state.get(state_key)
        if float_tolerance is not None and isinstance(val, float):
            val = round(val, int(float_tolerance))
        return (state_key, val)

    items = []
    for k, v in sorted(state.items()):
        if k in _META_KEYS:
            continue
        if float_tolerance is not None and isinstance(v, float):
            v = round(v, int(float_tolerance))
        items.append((k, v))
    return tuple(items)
