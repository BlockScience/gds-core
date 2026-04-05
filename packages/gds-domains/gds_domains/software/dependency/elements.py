"""Dependency graph element declarations.

These are plain frozen Pydantic models — user-facing declarations, NOT GDS blocks.
"""

from pydantic import BaseModel, Field


class Module(BaseModel, frozen=True):
    """A module or package in a dependency graph.

    Maps to: GDS Policy.
    """

    name: str
    layer: int = 0
    description: str = ""


class Dep(BaseModel, frozen=True):
    """A directed dependency between modules.

    Maps to: GDS Wiring (forward dependency).
    """

    source: str
    target: str
    description: str = ""


class Layer(BaseModel, frozen=True):
    """A named layer for organizing modules.

    Layers define ordering constraints — a module at layer N
    should only depend on modules at layer < N.
    """

    name: str
    depth: int = Field(description="Layer depth (0 = foundation)")
    description: str = ""
