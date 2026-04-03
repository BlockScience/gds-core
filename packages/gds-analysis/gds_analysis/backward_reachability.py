"""Backward reachable set computation for continuous-time systems.

Given a target set and continuous-time dynamics, computes the set of
states from which the target is reachable by integrating backward in
time. Uses gds-continuous's ODE engine for integration.

The pattern follows the Homicidal Chauffeur approach: sample initial
conditions on the target set boundary, integrate backward for time T,
and collect the reached states as the backward reachable set B(T).

Isochrones are level sets of the backward reachable tube: B(t) for
t in {t1, t2, ...} extracted from the trajectory data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gds_continuous import ODEModel, ODESimulation
    from gds_continuous.types import ODEFunction


@dataclass
class BackwardReachableSet:
    """Result of backward reachable set computation.

    Attributes
    ----------
    trajectories
        List of (times, states) for each initial condition on the
        target set. States are dicts keyed by state_names.
    target_points
        Initial conditions on the target set boundary.
    state_names
        Ordered state variable names.
    integration_time
        Total backward integration time T.
    n_trajectories
        Number of trajectories computed.
    """

    trajectories: list[tuple[list[float], list[dict[str, float]]]]
    target_points: list[dict[str, float]]
    state_names: list[str]
    integration_time: float
    n_trajectories: int


@dataclass
class Isochrone:
    """A level set of the backward reachable tube at time t.

    Attributes
    ----------
    time
        The backward time at which this isochrone is extracted.
    points
        State dicts at this time from each trajectory.
    """

    time: float
    points: list[dict[str, float]]


def backward_reachable_set(
    dynamics: ODEFunction,
    state_names: list[str],
    target_points: list[dict[str, float]],
    integration_time: float,
    params: dict[str, Any] | None = None,
    *,
    solver: str = "RK45",
    rtol: float = 1e-8,
    atol: float = 1e-10,
    max_step: float = 0.05,
    t_eval: list[float] | None = None,
) -> BackwardReachableSet:
    """Compute the backward reachable set by integrating backward from
    a target set.

    Parameters
    ----------
    dynamics
        Forward dynamics: (t, y, params) -> dy/dt. The function is
        automatically negated for backward integration.
    state_names
        Ordered state variable names.
    target_points
        Initial conditions on the target set boundary. Each dict maps
        state_names to float values.
    integration_time
        Total backward integration time T > 0.
    params
        Parameters passed to the dynamics function.
    solver
        ODE solver (RK45, RK23, DOP853, Radau, BDF, LSODA).
    rtol, atol
        Solver tolerances.
    max_step
        Maximum step size.
    t_eval
        Custom evaluation time points. If None, uses solver's adaptive
        stepping.

    Returns
    -------
    BackwardReachableSet with trajectories and metadata.
    """
    try:
        from gds_continuous import ODEModel, ODESimulation
    except ImportError as exc:
        raise ImportError(
            "backward_reachable_set requires gds-continuous. "
            "Install it with: pip install gds-analysis[continuous]"
        ) from exc

    params = params or {}

    def backward_rhs(t: float, y: list[float], p: dict[str, Any]) -> list[float]:
        fwd = dynamics(t, y, p)
        return [-v for v in fwd]

    trajectories: list[tuple[list[float], list[dict[str, float]]]] = []

    for ic in target_points:
        model = ODEModel(
            state_names=state_names,
            initial_state={n: ic[n] for n in state_names},
            rhs=backward_rhs,
            params={k: [v] for k, v in params.items()},
        )
        sim = ODESimulation(
            model=model,
            t_span=(0.0, integration_time),
            t_eval=t_eval,
            solver=solver,
            rtol=rtol,
            atol=atol,
            max_step=max_step,
        )
        results = sim.run()
        times = results.times
        rows = results.to_list()
        states = [{n: row[n] for n in state_names} for row in rows]
        trajectories.append((times, states))

    return BackwardReachableSet(
        trajectories=trajectories,
        target_points=target_points,
        state_names=state_names,
        integration_time=integration_time,
        n_trajectories=len(target_points),
    )


def extract_isochrones(
    brs: BackwardReachableSet,
    times: list[float],
    *,
    tolerance: float = 0.05,
) -> list[Isochrone]:
    """Extract isochrones (level sets) from backward reachable set.

    Parameters
    ----------
    brs
        Result of backward_reachable_set().
    times
        Target times at which to extract isochrones.
    tolerance
        Time matching tolerance — a trajectory point at time t is
        included in the isochrone for target time T if |t - T| < tol.

    Returns
    -------
    List of Isochrone objects, one per requested time.
    """
    isochrones: list[Isochrone] = []

    for target_t in times:
        points: list[dict[str, float]] = []
        for traj_times, traj_states in brs.trajectories:
            best_idx = None
            best_dist = float("inf")
            for i, t in enumerate(traj_times):
                dist = abs(t - target_t)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
            if best_idx is not None and best_dist < tolerance:
                points.append(traj_states[best_idx])
        isochrones.append(Isochrone(time=target_t, points=points))

    return isochrones
