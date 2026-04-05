"""Diagram kind classification for software architecture models."""

from enum import StrEnum


class DiagramKind(StrEnum):
    """The six software architecture diagram types."""

    DFD = "dfd"
    STATE_MACHINE = "state_machine"
    COMPONENT = "component"
    C4 = "c4"
    ERD = "erd"
    DEPENDENCY = "dependency"
