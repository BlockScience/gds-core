"""gds-symbolic — DEPRECATED: use gds_domains.symbolic instead."""

import warnings

warnings.warn(
    "Import from gds_domains.symbolic instead of gds_symbolic. "
    "The gds-symbolic package will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__version__ = "0.99.0"

from gds_domains.symbolic import (  # noqa: E402
    HamiltonianSpec,
    HamiltonianSystem,
    LinearizedSystem,
    OutputEquation,
    StateEquation,
    SymbolicControlModel,
    SymbolicError,
    derive_from_model,
    derive_hamiltonian,
    verify_conservation,
)

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
