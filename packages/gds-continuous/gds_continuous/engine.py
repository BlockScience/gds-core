"""ODE integration engine — wraps scipy.integrate.solve_ivp."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds_continuous._compat import require_scipy
from gds_continuous.results import ODEResults

if TYPE_CHECKING:
    from gds_continuous.model import ODEExperiment, ODESimulation
    from gds_continuous.types import Params


def integrate_simulation(sim: ODESimulation) -> ODEResults:
    """Integrate across all param subsets and runs."""
    require_scipy()

    results_parts: list[ODEResults] = []
    for subset_idx, params in enumerate(sim.model._param_subsets):
        for run_idx in range(sim.runs):
            part = _integrate_single(sim, params, subset_idx, run_idx)
            results_parts.append(part)

    return ODEResults.merge(results_parts)


def integrate_experiment(experiment: ODEExperiment) -> ODEResults:
    """Execute all simulations in an experiment."""
    parts: list[ODEResults] = []
    for sim in experiment.simulations:
        parts.append(integrate_simulation(sim))
    return ODEResults.merge(parts)


def _integrate_single(
    sim: ODESimulation,
    params: Params,
    subset_idx: int,
    run_idx: int,
) -> ODEResults:
    """Single solve_ivp call for one (subset, run) pair."""
    from scipy.integrate import solve_ivp

    model = sim.model
    y0 = model.y0()

    def rhs(t: float, y: Any) -> list[float]:
        return model.rhs(t, list(y), params)

    # Wrap event functions to close over params
    events = []
    for event_fn in model.events:

        def _make_event(fn: Any) -> Any:
            def wrapped(t: float, y: Any) -> float:
                return fn(t, list(y), params)

            wrapped.terminal = getattr(fn, "terminal", False)  # type: ignore[attr-defined]
            wrapped.direction = getattr(fn, "direction", 0)  # type: ignore[attr-defined]
            return wrapped

        events.append(_make_event(event_fn))

    sol = solve_ivp(
        rhs,
        sim.t_span,
        y0,
        method=sim.solver,
        t_eval=sim.t_eval,
        rtol=sim.rtol,
        atol=sim.atol,
        max_step=sim.max_step,
        events=events or None,
        dense_output=False,
    )

    if not sol.success:
        msg = f"ODE integration failed: {sol.message}"
        raise RuntimeError(msg)

    results = ODEResults(
        model._state_order,
        model.output_names if model.output_fn else None,
    )
    results.append_solution(sol.t, sol.y, run=run_idx, subset=subset_idx)

    return results
