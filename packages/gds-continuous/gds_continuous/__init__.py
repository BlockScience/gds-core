"""gds-continuous: Continuous-time ODE integration engine for the GDS ecosystem."""

__version__ = "0.1.0"

from gds_continuous.model import ODEExperiment, ODEModel, ODESimulation
from gds_continuous.results import ODEResults
from gds_continuous.types import EventFunction, ODEFunction, OutputFunction, Solver

__all__ = [
    "EventFunction",
    "ODEExperiment",
    "ODEFunction",
    "ODEModel",
    "ODEResults",
    "ODESimulation",
    "OutputFunction",
    "Solver",
]
