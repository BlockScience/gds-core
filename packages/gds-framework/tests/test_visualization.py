"""Test that gds.visualization raises ImportError directing to gds-viz."""

import pytest


def test_import_raises_with_migration_message():
    with pytest.raises(ImportError, match="gds-viz"):
        import gds.visualization  # noqa: F401
