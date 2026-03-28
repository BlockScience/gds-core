"""Dynamical analysis for GDS specifications.

Bridges gds-framework structural annotations to gds-sim runtime,
enabling constraint enforcement, metric computation, and reachability
analysis on concrete trajectories.
"""

__version__ = "0.1.0"

from gds_analysis.adapter import spec_to_model
from gds_analysis.constraints import guarded_policy
from gds_analysis.metrics import trajectory_distances

__all__ = [
    "guarded_policy",
    "spec_to_model",
    "trajectory_distances",
]
