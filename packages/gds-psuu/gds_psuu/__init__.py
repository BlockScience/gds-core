"""gds-psuu: Parameter space search under uncertainty for the GDS ecosystem."""

__version__ = "0.1.0"

from gds_psuu.errors import PsuuError, PsuuSearchError, PsuuValidationError
from gds_psuu.evaluation import EvaluationResult, Evaluator
from gds_psuu.kpi import KPI, final_state_mean, final_state_std, time_average
from gds_psuu.optimizers.base import Optimizer
from gds_psuu.optimizers.grid import GridSearchOptimizer
from gds_psuu.optimizers.random import RandomSearchOptimizer
from gds_psuu.results import EvaluationSummary, SweepResults
from gds_psuu.space import (
    Constraint,
    Continuous,
    Discrete,
    FunctionalConstraint,
    Integer,
    LinearConstraint,
    ParameterSpace,
)
from gds_psuu.sweep import Sweep
from gds_psuu.types import KPIFn, KPIScores, ParamPoint

__all__ = [
    "KPI",
    "Constraint",
    "Continuous",
    "Discrete",
    "EvaluationResult",
    "EvaluationSummary",
    "Evaluator",
    "FunctionalConstraint",
    "GridSearchOptimizer",
    "Integer",
    "KPIFn",
    "KPIScores",
    "LinearConstraint",
    "Optimizer",
    "ParamPoint",
    "ParameterSpace",
    "PsuuError",
    "PsuuSearchError",
    "PsuuValidationError",
    "RandomSearchOptimizer",
    "Sweep",
    "SweepResults",
    "final_state_mean",
    "final_state_std",
    "time_average",
]
