"""Dynamical analysis for GDS specifications.

Bridges gds-framework structural annotations to gds-sim runtime,
enabling constraint enforcement, metric computation, reachability
analysis, linear systems analysis, and response metrics.
"""

__version__ = "0.1.2"

from gds_analysis.adapter import spec_to_model
from gds_analysis.backward_reachability import (
    BackwardReachableSet,
    Isochrone,
    backward_reachable_set,
    extract_isochrones,
)
from gds_analysis.constraints import guarded_policy
from gds_analysis.metrics import trajectory_distances
from gds_analysis.reachability import (
    ReachabilityResult,
    configuration_space,
    reachable_graph,
    reachable_set,
)
from gds_analysis.response import StepMetrics, step_response_metrics

__all__ = [
    "BackwardReachableSet",
    "Isochrone",
    "ReachabilityResult",
    "StepMetrics",
    "backward_reachable_set",
    "configuration_space",
    "extract_isochrones",
    "guarded_policy",
    "reachable_graph",
    "reachable_set",
    "spec_to_model",
    "step_response_metrics",
    "trajectory_distances",
]


# Lazy imports for optional modules (require [continuous] extra)
_LINEAR_EXPORTS = {
    "eigenvalues",
    "is_stable",
    "is_marginally_stable",
    "frequency_response",
    "gain_margin",
    "phase_margin",
    "discretize",
    "lqr",
    "dlqr",
    "kalman",
    "gain_schedule",
}

_RESPONSE_SCIPY_EXPORTS = {
    "step_response",
    "impulse_response",
    "metrics_from_ode_results",
}


def __getattr__(name: str) -> object:
    """Lazy import for optional scipy-dependent functions."""
    if name in _LINEAR_EXPORTS:
        from gds_analysis import linear

        return getattr(linear, name)

    if name in _RESPONSE_SCIPY_EXPORTS:
        from gds_analysis import response

        return getattr(response, name)

    raise AttributeError(f"module 'gds_analysis' has no attribute {name!r}")
