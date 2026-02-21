"""Element type classification for stock-flow models."""

from enum import StrEnum


class ElementType(StrEnum):
    """The four stock-flow element categories."""

    STOCK = "stock"
    FLOW = "flow"
    AUXILIARY = "auxiliary"
    CONVERTER = "converter"
