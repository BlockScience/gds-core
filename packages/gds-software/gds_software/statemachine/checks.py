"""State machine verification checks (SM-001..SM-006).

These operate on StateMachineModel (pre-compilation declarations), not IR.
Each check returns a list of Finding objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds_software.statemachine.model import StateMachineModel


def check_sm001_initial_state(model: StateMachineModel) -> list[Finding]:
    """SM-001: Exactly one initial state exists."""
    initial = [s for s in model.states if s.is_initial]
    passed = len(initial) == 1
    return [
        Finding(
            check_id="SM-001",
            severity=Severity.ERROR,
            message=(
                f"State machine has {len(initial)} initial state(s), expected 1"
                if not passed
                else "State machine has exactly one initial state"
            ),
            source_elements=[s.name for s in initial] or ["<none>"],
            passed=passed,
        )
    ]


def check_sm002_reachability(model: StateMachineModel) -> list[Finding]:
    """SM-002: All states are reachable from the initial state."""
    if not any(s.is_initial for s in model.states):
        return []

    initial = model.initial_state
    # BFS from initial
    reachable: set[str] = set()
    queue = [initial.name]
    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)
        for t in model.transitions:
            if t.source == current and t.target not in reachable:
                queue.append(t.target)

    findings: list[Finding] = []
    for state in model.states:
        is_reachable = state.name in reachable
        findings.append(
            Finding(
                check_id="SM-002",
                severity=Severity.WARNING,
                message=(
                    f"State {state.name!r} is not reachable from initial state"
                    if not is_reachable
                    else f"State {state.name!r} is reachable"
                ),
                source_elements=[state.name],
                passed=is_reachable,
            )
        )
    return findings


def check_sm003_determinism(model: StateMachineModel) -> list[Finding]:
    """SM-003: No two transitions from the same state on the same event (without guards)."""
    findings: list[Finding] = []
    # Group transitions by (source, event)
    groups: dict[tuple[str, str], list[str]] = {}
    for t in model.transitions:
        key = (t.source, t.event)
        groups.setdefault(key, []).append(t.name)

    for (source, event), trans_names in groups.items():
        # Check if any of these transitions lack guards
        transitions = [t for t in model.transitions if t.name in trans_names]
        unguarded = [t for t in transitions if t.guard is None]

        if len(unguarded) > 1:
            findings.append(
                Finding(
                    check_id="SM-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Non-deterministic: {len(unguarded)} unguarded transitions "
                        f"from {source!r} on event {event!r}: "
                        f"{[t.name for t in unguarded]}"
                    ),
                    source_elements=[t.name for t in unguarded],
                    passed=False,
                )
            )

    if not findings:
        findings.append(
            Finding(
                check_id="SM-003",
                severity=Severity.ERROR,
                message="State machine is deterministic",
                source_elements=[],
                passed=True,
            )
        )
    return findings


def check_sm004_guard_completeness(model: StateMachineModel) -> list[Finding]:
    """SM-004: Transitions with guards from same state/event should be exhaustive."""
    findings: list[Finding] = []
    groups: dict[tuple[str, str], list[str]] = {}
    for t in model.transitions:
        key = (t.source, t.event)
        groups.setdefault(key, []).append(t.name)

    for (source, event), trans_names in groups.items():
        transitions = [t for t in model.transitions if t.name in trans_names]
        guarded = [t for t in transitions if t.guard is not None]
        unguarded = [t for t in transitions if t.guard is None]

        if guarded and not unguarded:
            # All guarded, no default — may not be exhaustive
            findings.append(
                Finding(
                    check_id="SM-004",
                    severity=Severity.WARNING,
                    message=(
                        f"All transitions from {source!r} on {event!r} are guarded "
                        f"with no default — may not be exhaustive"
                    ),
                    source_elements=[t.name for t in guarded],
                    passed=False,
                )
            )

    if not findings:
        findings.append(
            Finding(
                check_id="SM-004",
                severity=Severity.WARNING,
                message="Guard completeness is satisfied",
                source_elements=[],
                passed=True,
            )
        )
    return findings


def check_sm005_region_partition(model: StateMachineModel) -> list[Finding]:
    """SM-005: Region states must partition the state set (no overlaps, no gaps)."""
    if not model.regions:
        return [
            Finding(
                check_id="SM-005",
                severity=Severity.WARNING,
                message="No regions defined — partition check skipped",
                source_elements=[],
                passed=True,
            )
        ]

    findings: list[Finding] = []
    all_region_states: list[str] = []
    for region in model.regions:
        all_region_states.extend(region.states)

    # Check for overlaps
    seen: set[str] = set()
    for s in all_region_states:
        if s in seen:
            findings.append(
                Finding(
                    check_id="SM-005",
                    severity=Severity.ERROR,
                    message=f"State {s!r} appears in multiple regions",
                    source_elements=[s],
                    passed=False,
                )
            )
        seen.add(s)

    # Check for gaps
    for state in model.states:
        if state.name not in seen:
            findings.append(
                Finding(
                    check_id="SM-005",
                    severity=Severity.WARNING,
                    message=f"State {state.name!r} is not assigned to any region",
                    source_elements=[state.name],
                    passed=False,
                )
            )

    if not findings:
        findings.append(
            Finding(
                check_id="SM-005",
                severity=Severity.WARNING,
                message="Region partition is valid",
                source_elements=[],
                passed=True,
            )
        )
    return findings


def check_sm006_transition_validity(model: StateMachineModel) -> list[Finding]:
    """SM-006: Transition source/target are declared states, events are declared."""
    findings: list[Finding] = []
    for t in model.transitions:
        src_valid = t.source in model.state_names
        findings.append(
            Finding(
                check_id="SM-006",
                severity=Severity.ERROR,
                message=(
                    f"Transition {t.name!r} source {t.source!r} "
                    f"{'is' if src_valid else 'is NOT'} a declared state"
                ),
                source_elements=[t.name, t.source],
                passed=src_valid,
            )
        )
        tgt_valid = t.target in model.state_names
        findings.append(
            Finding(
                check_id="SM-006",
                severity=Severity.ERROR,
                message=(
                    f"Transition {t.name!r} target {t.target!r} "
                    f"{'is' if tgt_valid else 'is NOT'} a declared state"
                ),
                source_elements=[t.name, t.target],
                passed=tgt_valid,
            )
        )
        evt_valid = t.event in model.event_names
        findings.append(
            Finding(
                check_id="SM-006",
                severity=Severity.ERROR,
                message=(
                    f"Transition {t.name!r} event {t.event!r} "
                    f"{'is' if evt_valid else 'is NOT'} a declared event"
                ),
                source_elements=[t.name, t.event],
                passed=evt_valid,
            )
        )
    return findings


ALL_SM_CHECKS = [
    check_sm001_initial_state,
    check_sm002_reachability,
    check_sm003_determinism,
    check_sm004_guard_completeness,
    check_sm005_region_partition,
    check_sm006_transition_validity,
]
