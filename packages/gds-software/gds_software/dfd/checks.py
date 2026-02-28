"""DFD verification checks (DFD-001..DFD-005).

These operate on DFDModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.dfd.model import DFDModel


def check_dfd001_process_connectivity(model: DFDModel) -> list[Finding]:
    """DFD-001: Every process has at least one connected flow."""
    findings: list[Finding] = []
    for proc in model.processes:
        connected = any(
            f.source == proc.name or f.target == proc.name for f in model.data_flows
        )
        findings.append(
            Finding(
                check_id="DFD-001",
                severity=Severity.WARNING,
                message=(
                    f"Process {proc.name!r} has no connected flows"
                    if not connected
                    else f"Process {proc.name!r} has connected flows"
                ),
                source_elements=[proc.name],
                passed=connected,
            )
        )
    return findings


def check_dfd002_flow_validity(model: DFDModel) -> list[Finding]:
    """DFD-002: Flow source/target are declared elements."""
    findings: list[Finding] = []
    all_names = model.element_names
    for flow in model.data_flows:
        src_valid = flow.source in all_names
        findings.append(
            Finding(
                check_id="DFD-002",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.name!r} source {flow.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.name, flow.source],
                passed=src_valid,
            )
        )
        tgt_valid = flow.target in all_names
        findings.append(
            Finding(
                check_id="DFD-002",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.name!r} target {flow.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.name, flow.target],
                passed=tgt_valid,
            )
        )
    return findings


def check_dfd003_no_ext_to_ext(model: DFDModel) -> list[Finding]:
    """DFD-003: No direct flows between two external entities."""
    findings: list[Finding] = []
    ext_names = model.external_names
    for flow in model.data_flows:
        is_ext_to_ext = flow.source in ext_names and flow.target in ext_names
        findings.append(
            Finding(
                check_id="DFD-003",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.name!r} connects two external entities "
                    f"({flow.source!r} -> {flow.target!r})"
                    if is_ext_to_ext
                    else f"Flow {flow.name!r} does not connect two externals"
                ),
                source_elements=[flow.name],
                passed=not is_ext_to_ext,
            )
        )
    return findings


def check_dfd004_store_connectivity(model: DFDModel) -> list[Finding]:
    """DFD-004: Every data store has at least one connected flow."""
    findings: list[Finding] = []
    for store in model.data_stores:
        connected = any(
            f.source == store.name or f.target == store.name for f in model.data_flows
        )
        findings.append(
            Finding(
                check_id="DFD-004",
                severity=Severity.WARNING,
                message=(
                    f"DataStore {store.name!r} has no connected flows"
                    if not connected
                    else f"DataStore {store.name!r} has connected flows"
                ),
                source_elements=[store.name],
                passed=connected,
            )
        )
    return findings


def check_dfd005_process_output(model: DFDModel) -> list[Finding]:
    """DFD-005: Every process has at least one outgoing flow."""
    findings: list[Finding] = []
    for proc in model.processes:
        has_output = any(f.source == proc.name for f in model.data_flows)
        findings.append(
            Finding(
                check_id="DFD-005",
                severity=Severity.WARNING,
                message=(
                    f"Process {proc.name!r} has no outgoing flows"
                    if not has_output
                    else f"Process {proc.name!r} has outgoing flows"
                ),
                source_elements=[proc.name],
                passed=has_output,
            )
        )
    return findings


ALL_DFD_CHECKS = [
    check_dfd001_process_connectivity,
    check_dfd002_flow_validity,
    check_dfd003_no_ext_to_ext,
    check_dfd004_store_connectivity,
    check_dfd005_process_output,
]
