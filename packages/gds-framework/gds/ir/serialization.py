"""IR document serialization — JSON round-trip for the generic SystemIR."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from gds.ir.models import SystemIR


class IRMetadata(BaseModel):
    """Metadata envelope for an IR document."""

    sources: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "0.2.1"


class IRDocument(BaseModel):
    """Top-level IR document containing one or more systems."""

    version: str = "1.0"
    systems: list[SystemIR]
    metadata: IRMetadata


def save_ir(doc: IRDocument, path: Path) -> None:
    """Serialize an IR document to JSON."""
    path.write_text(doc.model_dump_json(indent=2))


def load_ir(path: Path) -> IRDocument:
    """Deserialize an IR document from JSON."""
    return IRDocument.model_validate_json(path.read_text())
