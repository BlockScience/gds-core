"""Diagram kind classification for business dynamics models."""

from enum import StrEnum


class BusinessDiagramKind(StrEnum):
    """The three business dynamics diagram types."""

    CLD = "cld"
    SUPPLY_CHAIN = "supply_chain"
    VSM = "vsm"
