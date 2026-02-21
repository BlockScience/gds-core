"""Element type classification for control system models."""

from enum import StrEnum


class ElementType(StrEnum):
    """The four control system element categories."""

    STATE = "state"
    INPUT = "input"
    SENSOR = "sensor"
    CONTROLLER = "controller"
