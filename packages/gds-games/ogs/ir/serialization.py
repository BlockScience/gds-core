"""IR document serialization -- JSON round-trip for the canonical IR."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from ogs.ir.models import PatternIR


class IRMetadata(BaseModel):
    """Metadata envelope for an IR document."""

    source_canvases: list[str]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parser_version: str = "0.1.0"


class IRDocument(BaseModel):
    """Top-level IR document containing one or more patterns."""

    version: str = "1.0"
    patterns: list[PatternIR]
    metadata: IRMetadata


def save_ir(doc: IRDocument, path: Path) -> None:
    """Serialize an IR document to JSON."""
    path.write_text(doc.model_dump_json(indent=2))


def load_ir(path: Path) -> IRDocument:
    """Deserialize an IR document from JSON."""
    return IRDocument.model_validate_json(path.read_text())
