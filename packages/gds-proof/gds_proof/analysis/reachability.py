"""Deprecated — use ``gds_proof.analysis.inductive_safety`` instead.

This module re-exports all names from ``inductive_safety`` for backward
compatibility.  ``ReachabilityAnalysisResult`` is an alias for
``InductiveSafetyResult``, and ``analyze_reachability`` is an alias for
``analyze_inductive_safety``.

.. deprecated:: 0.2.0
    Will be removed in v1.0.0.
"""

from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "gds_proof.analysis.reachability is deprecated, "
    "use gds_proof.analysis.inductive_safety instead",
    DeprecationWarning,
    stacklevel=2,
)

from gds_proof.analysis.inductive_safety import (  # noqa: E402
    InductiveSafetyResult,
    MultiStepResult,
    MultiStepVerdict,
    PredicateSufficiencyResult,
    PredicateSufficiencyVerdict,
    SingleStepResult,
    SingleStepVerdict,
    analyze_inductive_safety,
    analyze_reachability,
)

# Deprecated alias for the result class
ReachabilityAnalysisResult = InductiveSafetyResult

__all__ = [
    "InductiveSafetyResult",
    "MultiStepResult",
    "MultiStepVerdict",
    "PredicateSufficiencyResult",
    "PredicateSufficiencyVerdict",
    "ReachabilityAnalysisResult",
    "SingleStepResult",
    "SingleStepVerdict",
    "analyze_inductive_safety",
    "analyze_reachability",
]
