"""Dynamical analysis for GDS specifications.

Bridges gds-framework structural annotations to gds-sim runtime,
enabling constraint enforcement, metric computation, and reachability
analysis on concrete trajectories.
"""

__version__ = "0.1.0"

from gds_analysis.adapter import spec_to_model
from gds_analysis.constraints import guarded_policy
from gds_analysis.metrics import trajectory_distances
from gds_analysis.reachability import (
    ReachabilityResult,
    configuration_space,
    reachable_graph,
    reachable_set,
)

__all__ = [
    "ReachabilityResult",
    "configuration_space",
    "guarded_policy",
    "reachable_graph",
    "reachable_set",
    "spec_to_model",
    "trajectory_distances",
]
