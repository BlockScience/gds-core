"""VSM verification checks (VSM-001..VSM-004).

These operate on ValueStreamModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_business.vsm.model import ValueStreamModel


def check_vsm001_linear_process_flow(model: ValueStreamModel) -> list[Finding]:
    """VSM-001: Each step has at most 1 incoming and 1 outgoing material flow."""
    findings: list[Finding] = []
    for step in model.steps:
        incoming = sum(1 for f in model.material_flows if f.target == step.name)
        outgoing = sum(1 for f in model.material_flows if f.source == step.name)
        linear = incoming <= 1 and outgoing <= 1
        findings.append(
            Finding(
                check_id="VSM-001",
                severity=Severity.WARNING,
                message=(
                    f"Step {step.name!r}: {incoming} incoming, {outgoing} outgoing "
                    f"material flow(s) — "
                    f"{'linear' if linear else 'non-linear (branching detected)'}"
                ),
                source_elements=[step.name],
                passed=linear,
            )
        )
    return findings


def check_vsm002_push_pull_boundary(model: ValueStreamModel) -> list[Finding]:
    """VSM-002: Identifies where flow_type transitions from push to pull."""
    findings: list[Finding] = []
    transitions: list[tuple[str, str]] = []

    # Look for adjacent flows where type changes
    for i, flow in enumerate(model.material_flows):
        for other in model.material_flows[i + 1 :]:
            # Adjacent if one's target is the other's source
            if flow.target == other.source and flow.flow_type != other.flow_type:
                transitions.append(
                    (flow.target, f"{flow.flow_type}->{other.flow_type}")
                )
            elif other.target == flow.source and flow.flow_type != other.flow_type:
                transitions.append(
                    (flow.source, f"{other.flow_type}->{flow.flow_type}")
                )

    if transitions:
        for boundary_element, transition in transitions:
            findings.append(
                Finding(
                    check_id="VSM-002",
                    severity=Severity.INFO,
                    message=(
                        f"Push/pull boundary at {boundary_element!r}: {transition}"
                    ),
                    source_elements=[boundary_element],
                    passed=True,
                )
            )
    else:
        # Check if all flows are same type
        flow_types = {f.flow_type for f in model.material_flows}
        if len(flow_types) <= 1:
            ftype = next(iter(flow_types), "push")
            findings.append(
                Finding(
                    check_id="VSM-002",
                    severity=Severity.INFO,
                    message=f"All material flows are {ftype} — no push/pull boundary",
                    source_elements=[],
                    passed=True,
                )
            )
        else:
            findings.append(
                Finding(
                    check_id="VSM-002",
                    severity=Severity.INFO,
                    message="Mixed push/pull flows but no clear boundary detected",
                    source_elements=[],
                    passed=True,
                )
            )

    return findings


def check_vsm003_flow_reference_validity(model: ValueStreamModel) -> list[Finding]:
    """VSM-003: All flow source/target are declared elements."""
    findings: list[Finding] = []
    all_names = model.element_names

    for flow in model.material_flows:
        src_valid = flow.source in all_names
        findings.append(
            Finding(
                check_id="VSM-003",
                severity=Severity.ERROR,
                message=(
                    f"MaterialFlow source {flow.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.source],
                passed=src_valid,
            )
        )
        tgt_valid = flow.target in all_names
        findings.append(
            Finding(
                check_id="VSM-003",
                severity=Severity.ERROR,
                message=(
                    f"MaterialFlow target {flow.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.target],
                passed=tgt_valid,
            )
        )

    for flow in model.information_flows:
        src_valid = flow.source in all_names
        findings.append(
            Finding(
                check_id="VSM-003",
                severity=Severity.ERROR,
                message=(
                    f"InformationFlow source {flow.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.source],
                passed=src_valid,
            )
        )
        tgt_valid = flow.target in all_names
        findings.append(
            Finding(
                check_id="VSM-003",
                severity=Severity.ERROR,
                message=(
                    f"InformationFlow target {flow.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared element"
                ),
                source_elements=[flow.target],
                passed=tgt_valid,
            )
        )

    return findings


def check_vsm004_bottleneck_vs_takt(model: ValueStreamModel) -> list[Finding]:
    """VSM-004: Max cycle_time should not exceed customer takt_time."""
    findings: list[Finding] = []

    if not model.steps or not model.customers:
        findings.append(
            Finding(
                check_id="VSM-004",
                severity=Severity.WARNING,
                message="No steps or customers to check bottleneck vs takt",
                source_elements=[],
                passed=True,
            )
        )
        return findings

    max_cycle = max(s.cycle_time for s in model.steps)
    bottleneck = next(s for s in model.steps if s.cycle_time == max_cycle)

    for customer in model.customers:
        within_takt = max_cycle <= customer.takt_time
        findings.append(
            Finding(
                check_id="VSM-004",
                severity=Severity.WARNING,
                message=(
                    f"Bottleneck {bottleneck.name!r} (cycle_time={max_cycle}) "
                    f"{'<=' if within_takt else '>'} "
                    f"customer {customer.name!r} takt_time={customer.takt_time}"
                ),
                source_elements=[bottleneck.name, customer.name],
                passed=within_takt,
            )
        )

    return findings


ALL_VSM_CHECKS = [
    check_vsm001_linear_process_flow,
    check_vsm002_push_pull_boundary,
    check_vsm003_flow_reference_validity,
    check_vsm004_bottleneck_vs_takt,
]
