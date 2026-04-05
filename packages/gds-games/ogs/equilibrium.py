"""ogs.equilibrium — DEPRECATED: use gds_domains.games.equilibrium instead."""

from gds_domains.games.equilibrium import (  # noqa: F401
    NashResult,
    PayoffMatrices,
    compute_nash,
    extract_payoff_matrices,
)

__all__ = [
    "NashResult",
    "PayoffMatrices",
    "compute_nash",
    "extract_payoff_matrices",
]
