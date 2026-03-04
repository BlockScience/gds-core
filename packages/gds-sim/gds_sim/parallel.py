"""Multi-run parallelism via ProcessPoolExecutor."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

from gds_sim.engine import execute_simulation
from gds_sim.results import Results

if TYPE_CHECKING:
    from gds_sim.model import Experiment, Simulation
    from gds_sim.types import Params


def execute_experiment(experiment: Experiment) -> Results:
    """Execute all simulations in an experiment, optionally in parallel."""
    all_results: list[Results] = []

    for sim in experiment.simulations:
        n_subsets = len(sim.model._param_subsets)
        total_jobs = n_subsets * sim.runs

        if total_jobs <= 1 or experiment.processes == 1:
            all_results.append(execute_simulation(sim))
        else:
            all_results.append(_parallel_simulation(sim, experiment.processes))

    return Results.merge(all_results)


def _parallel_simulation(sim: Simulation, max_workers: int | None) -> Results:
    """Run a simulation's (subset, run) pairs across processes."""
    jobs: list[tuple[Simulation, Params, int, int]] = [
        (sim, params, si, ri)
        for si, params in enumerate(sim.model._param_subsets)
        for ri in range(sim.runs)
    ]

    partial_results: list[Results] = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run_single, *job) for job in jobs]
        for f in futures:
            partial_results.append(f.result())

    return Results.merge(partial_results)


def _run_single(
    sim: Simulation, params: Params, subset_idx: int, run_idx: int
) -> Results:
    """Execute a single (subset, run) pair — picklable top-level function."""
    from gds_sim.engine import _execute_single_run

    results = Results(list(sim.model._state_keys))
    _execute_single_run(sim, results, params, subset_idx, run_idx)
    return results
