"""Re-exports from gds.verification.findings for backwards compatibility.

The OGS VerificationReport uses 'pattern_name' while GDS uses 'system_name'.
We provide a thin wrapper for backwards compatibility.
"""

from gds.verification.findings import Finding, Severity
from gds.verification.findings import VerificationReport as _GDSVerificationReport


class VerificationReport(_GDSVerificationReport):
    """OGS-compatible verification report with pattern_name alias."""

    def __init__(self, **data):
        # Map pattern_name to system_name for GDS base
        if "pattern_name" in data and "system_name" not in data:
            data["system_name"] = data["pattern_name"]
        super().__init__(**data)

    @property
    def pattern_name(self) -> str:
        """Alias for system_name — OGS calls it 'pattern_name'."""
        return self.system_name


__all__ = ["Finding", "Severity", "VerificationReport"]
