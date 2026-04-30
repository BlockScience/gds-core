"""gds-symbolic: Symbolic math bridge for the GDS ecosystem."""

from gds_domains.symbolic.elements import OutputEquation, StateEquation
from gds_domains.symbolic.errors import SymbolicError
from gds_domains.symbolic.hamiltonian import (
    HamiltonianSpec,
    HamiltonianSystem,
    derive_from_model,
    derive_hamiltonian,
    verify_conservation,
)
from gds_domains.symbolic.linearize import LinearizedSystem
from gds_domains.symbolic.model import SymbolicControlModel
from gds_domains.symbolic.transfer import (
    TransferFunction,
    TransferFunctionMatrix,
    characteristic_polynomial,
    controllability_matrix,
    is_controllable,
    is_minimum_phase,
    is_observable,
    observability_matrix,
    poles,
    sensitivity,
    ss_to_tf,
    zeros,
)

__all__ = [
    "HamiltonianSpec",
    "HamiltonianSystem",
    "LinearizedSystem",
    "OutputEquation",
    "StateEquation",
    "SymbolicControlModel",
    "SymbolicError",
    "TransferFunction",
    "TransferFunctionMatrix",
    "characteristic_polynomial",
    "controllability_matrix",
    "derive_from_model",
    "derive_hamiltonian",
    "is_controllable",
    "is_minimum_phase",
    "is_observable",
    "observability_matrix",
    "poles",
    "sensitivity",
    "ss_to_tf",
    "verify_conservation",
    "zeros",
]
