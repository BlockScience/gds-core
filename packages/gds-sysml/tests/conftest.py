"""Shared test fixtures for gds-sysml."""

from pathlib import Path

import pytest

from gds_sysml.model import SysMLModel
from gds_sysml.parser.regex import parse_sysml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def satellite_sysml_path() -> Path:
    """Path to the simple satellite .sysml fixture."""
    return FIXTURES_DIR / "simple_satellite.sysml"


@pytest.fixture()
def satellite_sysml_text(satellite_sysml_path: Path) -> str:
    """Raw text of the simple satellite .sysml fixture."""
    return satellite_sysml_path.read_text(encoding="utf-8")


@pytest.fixture()
def satellite_model(satellite_sysml_path: Path) -> SysMLModel:
    """Parsed SysMLModel from the simple satellite fixture."""
    return parse_sysml(satellite_sysml_path)
