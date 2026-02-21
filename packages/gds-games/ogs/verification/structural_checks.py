"""Structural composition checks S-001 through S-007.

These checks verify that the composition structure of a pattern is
well-formed — that games are wired correctly, flows respect their
direction, and the overall graph has valid topology. They operate
on the flat IR representation (``PatternIR``) after compilation.

Unlike type checks (T-series), which verify individual flow labels
against game signatures, structural checks verify global properties
like acyclicity (S-004) and composition-specific invariants.
"""

from ogs.ir.models import (
    CompositionType,
    FlowDirection,
    GameType,
    InputType,
    PatternIR,
)
from ogs.verification.findings import Finding, Severity
from ogs.verification.tokens import tokens_subset


def check_s001_sequential_type_compatibility(pattern: PatternIR) -> list[Finding]:
    """S-001: In sequential composition G1;G2, verify Y1 = X2.

    For each covariant game-to-game flow, the flow label tokens must be
    a subset of BOTH the source Y and target X tokens. This verifies
    the structural composition requirement.
    """
    findings = []
    game_sigs = {g.name: g.signature for g in pattern.games}
    game_names = set(game_sigs.keys())

    for flow in pattern.flows:
        if flow.direction != FlowDirection.COVARIANT:
            continue
        if flow.is_corecursive:
            continue  # Corecursive flows are temporal Y→X, not within-step
        if flow.source not in game_names or flow.target not in game_names:
            continue

        src_y = game_sigs[flow.source][1]  # Y (codomain)
        tgt_x = game_sigs[flow.target][0]  # X (domain)

        if not src_y or not tgt_x:
            continue  # T-002 handles missing signatures

        label_in_y = tokens_subset(flow.label, src_y)
        label_in_x = tokens_subset(flow.label, tgt_x)
        compatible = label_in_y and label_in_x

        findings.append(
            Finding(
                check_id="S-001",
                severity=Severity.ERROR,
                message=(
                    f"Sequential {flow.source} ; {flow.target}: "
                    f"Y={src_y!r}, X={tgt_x!r}, flow={flow.label!r}"
                    + ("" if compatible else " — type mismatch")
                ),
                source_elements=[flow.source, flow.target],
                passed=compatible,
            )
        )

    return findings


def check_s002_parallel_independence(pattern: PatternIR) -> list[Finding]:
    """S-002: Games in parallel composition should share no direct flows."""
    findings = []

    if pattern.composition_type != CompositionType.PARALLEL:
        findings.append(
            Finding(
                check_id="S-002",
                severity=Severity.WARNING,
                message="Pattern is not parallel composition — S-002 not applicable",
                source_elements=[],
                passed=True,
            )
        )
        return findings

    game_names = {g.name for g in pattern.games}

    violations = [
        f for f in pattern.flows if f.source in game_names and f.target in game_names
    ]

    if violations:
        for flow in violations:
            findings.append(
                Finding(
                    check_id="S-002",
                    severity=Severity.WARNING,
                    message=(
                        f"Parallel independence violation: direct flow {flow.label!r} "
                        f"from {flow.source} to {flow.target}"
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=False,
                )
            )
    else:
        findings.append(
            Finding(
                check_id="S-002",
                severity=Severity.WARNING,
                message=(
                    "Parallel composition: no direct game-to-game flows (independent)"
                ),
                source_elements=[],
                passed=True,
            )
        )

    return findings


def check_s003_feedback_type_compatibility(pattern: PatternIR) -> list[Finding]:
    """S-003: In feedback composition, verify the feedback flow label is
    consistent with the source's S (coutility) slot.

    For each feedback flow, the flow label tokens must be a subset of
    the source S tokens.
    """
    findings = []
    game_sigs = {g.name: g.signature for g in pattern.games}

    for flow in pattern.flows:
        if not flow.is_feedback:
            continue
        if flow.source not in game_sigs or flow.target not in game_sigs:
            continue

        src_s = game_sigs[flow.source][3]  # S (coutility output)
        tgt_x = game_sigs[flow.target][0]  # X (observation input)

        if not src_s and not tgt_x:
            findings.append(
                Finding(
                    check_id="S-003",
                    severity=Severity.WARNING,
                    message=(
                        f"Feedback {flow.source} -> "
                        f"{flow.target}: both S and X are empty"
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=True,
                )
            )
            continue

        compatible = tokens_subset(flow.label, src_s)

        findings.append(
            Finding(
                check_id="S-003",
                severity=Severity.ERROR,
                message=(
                    f"Feedback {flow.source} -> {flow.target}: "
                    f"S={src_s!r}, X={tgt_x!r}, flow={flow.label!r}"
                    + ("" if compatible else " — type mismatch")
                ),
                source_elements=[flow.source, flow.target],
                passed=compatible,
            )
        )

    return findings


def check_s004_covariant_acyclicity(pattern: PatternIR) -> list[Finding]:
    """S-004: Covariant flow graph must be a DAG (no cycles).

    Within a single timestep, covariant data must flow in one direction —
    cycles would create infinite loops. Corecursive flows (Y→X across
    timesteps) and feedback flows (S→R, contravariant) are excluded from
    this check since they represent legitimate temporal or backward links.
    """
    # Build adjacency list from covariant game-to-game flows
    game_names = {g.name for g in pattern.games}
    adj: dict[str, list[str]] = {name: [] for name in game_names}

    for flow in pattern.flows:
        if flow.direction != FlowDirection.COVARIANT:
            continue
        if flow.is_corecursive:
            continue  # Corecursive Y→X flows are temporal, not within-step
        if flow.source in game_names and flow.target in game_names:
            adj[flow.source].append(flow.target)

    # DFS cycle detection with coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in game_names}
    cycle_path: list[str] = []
    has_cycle = False

    def dfs(node: str) -> bool:
        nonlocal has_cycle
        color[node] = GRAY
        cycle_path.append(node)
        for neighbor in adj[node]:
            if color[neighbor] == GRAY:
                # Found cycle — trim path to show only the cycle
                idx = cycle_path.index(neighbor)
                cycle_path[:] = cycle_path[idx:]
                has_cycle = True
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        cycle_path.pop()
        color[node] = BLACK
        return False

    for node in game_names:
        if color[node] == WHITE and dfs(node):
            break

    if has_cycle:
        return [
            Finding(
                check_id="S-004",
                severity=Severity.ERROR,
                message=(
                    f"Covariant flow graph contains a cycle: {' -> '.join(cycle_path)}"
                ),
                source_elements=cycle_path,
                passed=False,
            )
        ]

    return [
        Finding(
            check_id="S-004",
            severity=Severity.ERROR,
            message="Covariant flow graph is acyclic (DAG)",
            source_elements=[],
            passed=True,
        )
    ]


def check_s005_decision_space_validation(pattern: PatternIR) -> list[Finding]:
    """S-005: Every decision game must have a non-empty Y (decision output)
    and at least one incoming contravariant flow (utility feedback).
    """
    findings = []

    contra_targets = set()
    for flow in pattern.flows:
        if flow.direction == FlowDirection.CONTRAVARIANT:
            contra_targets.add(flow.target)

    for game in pattern.games:
        if game.game_type != GameType.DECISION:
            continue

        y_slot = game.signature[1]
        has_y = bool(y_slot)
        has_contra = game.name in contra_targets

        issues = []
        if not has_y:
            issues.append("empty Y slot (no decision output)")
        if not has_contra:
            issues.append("no incoming contravariant flow (no utility feedback)")

        passed = has_y and has_contra
        findings.append(
            Finding(
                check_id="S-005",
                severity=Severity.WARNING,
                message=(
                    f"Decision game {game.name!r}: Y={y_slot!r}"
                    + (f" — {'; '.join(issues)}" if issues else "")
                ),
                source_elements=[game.name],
                passed=passed,
            )
        )

    return findings


def check_s006_corecursive_wiring(pattern: PatternIR) -> list[Finding]:
    """S-006: Validate corecursive (temporal Y→X) flow wiring.

    Corecursive flows must satisfy two invariants:
    1. Direction must be covariant (they carry forward data across timesteps,
       not backward utility).
    2. The flow label tokens must be a subset of the source game's Y tokens
       (the data being forwarded must actually exist in the source's output).

    Only runs when corecursive flows are present in the pattern.
    """
    findings: list[Finding] = []
    game_sigs = {g.name: g.signature for g in pattern.games}

    corecursive_flows = [f for f in pattern.flows if f.is_corecursive]
    if not corecursive_flows:
        return findings

    for flow in corecursive_flows:
        # Must be covariant direction
        if flow.direction != FlowDirection.COVARIANT:
            findings.append(
                Finding(
                    check_id="S-006",
                    severity=Severity.ERROR,
                    message=(
                        f"Corecursive flow {flow.source} → {flow.target}: "
                        f"must be covariant (got {flow.direction.value})"
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=False,
                )
            )
            continue

        # Source Y tokens should overlap with target X tokens
        if flow.source not in game_sigs or flow.target not in game_sigs:
            continue

        src_y = game_sigs[flow.source][1]  # Y
        tgt_x = game_sigs[flow.target][0]  # X

        if not src_y or not tgt_x:
            findings.append(
                Finding(
                    check_id="S-006",
                    severity=Severity.WARNING,
                    message=(
                        f"Corecursive flow {flow.source} → {flow.target}: "
                        f"Y={src_y!r}, X={tgt_x!r} — cannot verify token overlap"
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=True,
                )
            )
            continue

        compatible = tokens_subset(flow.label, src_y)
        findings.append(
            Finding(
                check_id="S-006",
                severity=Severity.ERROR,
                message=(
                    f"Corecursive flow {flow.source} → {flow.target}: "
                    f"Y={src_y!r}, X={tgt_x!r}, flow={flow.label!r}"
                    + ("" if compatible else " — label not in source Y")
                ),
                source_elements=[flow.source, flow.target],
                passed=compatible,
            )
        )

    return findings


def check_s007_initialization_completeness(pattern: PatternIR) -> list[Finding]:
    """S-007: Every initialization input must have at least one outgoing flow."""
    findings = []

    flow_sources = {f.source for f in pattern.flows}
    init_inputs = [
        i for i in pattern.inputs if i.input_type == InputType.INITIALIZATION
    ]

    if not init_inputs:
        findings.append(
            Finding(
                check_id="S-007",
                severity=Severity.WARNING,
                message="No initialization inputs found",
                source_elements=[],
                passed=True,
            )
        )
        return findings

    for inp in init_inputs:
        connected = inp.name in flow_sources
        findings.append(
            Finding(
                check_id="S-007",
                severity=Severity.WARNING,
                message=(
                    f"Initialization input {inp.name!r}"
                    + ("" if connected else " — not connected to any game")
                ),
                source_elements=[inp.name],
                passed=connected,
            )
        )

    return findings
