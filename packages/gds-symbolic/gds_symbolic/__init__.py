"""gds-symbolic: Symbolic math bridge for the GDS ecosystem."""

__version__ = "0.1.0"

from gds_symbolic.elements import OutputEquation, StateEquation
from gds_symbolic.errors import SymbolicError
from gds_symbolic.hamiltonian import (
    HamiltonianSpec,
    HamiltonianSystem,
    derive_from_model,
    derive_hamiltonian,
    verify_conservation,
)
from gds_symbolic.linearize import LinearizedSystem
from gds_symbolic.model import SymbolicControlModel

__all__ = [
    "HamiltonianSpec",
    "HamiltonianSystem",
    "LinearizedSystem",
    "OutputEquation",
    "StateEquation",
    "SymbolicControlModel",
    "SymbolicError",
    "derive_from_model",
    "derive_hamiltonian",
    "verify_conservation",
]
