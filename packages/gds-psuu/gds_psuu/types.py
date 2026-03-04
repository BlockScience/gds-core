"""Core type aliases for gds-psuu."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gds_sim import Results

ParamPoint = dict[str, Any]
"""A single point in parameter space: maps param names to concrete values."""

KPIFn = Callable[[Results], float]
"""Computes a scalar KPI score from simulation results (all Monte Carlo runs)."""

KPIScores = dict[str, float]
"""Maps KPI names to their computed scalar scores."""
