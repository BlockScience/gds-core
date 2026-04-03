"""Dynamical analysis for GDS specifications.

Bridges gds-framework structural annotations to gds-sim runtime,
enabling constraint enforcement, metric computation, and reachability
analysis on concrete trajectories.
"""

__version__ = "0.1.1"

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

__all__ = [
    "BackwardReachableSet",
    "Isochrone",
    "ReachabilityResult",
    "backward_reachable_set",
    "configuration_space",
    "extract_isochrones",
    "guarded_policy",
    "reachable_graph",
    "reachable_set",
    "spec_to_model",
    "trajectory_distances",
]
