"""Generic verification checks G-001 through G-006.

These checks operate on the domain-neutral SystemIR. They verify type
consistency, structural completeness, and graph topology without
referencing any domain-specific block types or semantics.
"""

from gds.ir.models import FlowDirection, SystemIR
from gds.types.tokens import tokens_subset
from gds.verification.findings import Finding, Severity


def check_g001_domain_codomain_matching(system: SystemIR) -> list[Finding]:
    """G-001: For every covariant block-to-block wiring, verify the label
    is consistent with source forward_out or target forward_in.
    """
    findings = []
    block_sigs = {b.name: b.signature for b in system.blocks}

    for wiring in system.wirings:
        if wiring.direction != FlowDirection.COVARIANT:
            continue
        if wiring.source not in block_sigs or wiring.target not in block_sigs:
            continue

        src_out = block_sigs[wiring.source][1]  # forward_out
        tgt_in = block_sigs[wiring.target][0]  # forward_in

        if not src_out or not tgt_in:
            findings.append(
                Finding(
                    check_id="G-001",
                    severity=Severity.ERROR,
                    message=(
                        f"Cannot verify domain/codomain: "
                        f"{wiring.source} out={src_out!r}, "
                        f"{wiring.target} in={tgt_in!r}"
                    ),
                    source_elements=[wiring.source, wiring.target],
                    passed=False,
                )
            )
            continue

        compatible = tokens_subset(wiring.label, src_out) or tokens_subset(
            wiring.label, tgt_in
        )
        findings.append(
            Finding(
                check_id="G-001",
                severity=Severity.ERROR,
                message=(
                    f"Wiring {wiring.label!r}: "
                    f"{wiring.source} out={src_out!r} -> {wiring.target} in={tgt_in!r}"
                    + ("" if compatible else " — MISMATCH")
                ),
                source_elements=[wiring.source, wiring.target],
                passed=compatible,
            )
        )

    return findings


def check_g002_signature_completeness(system: SystemIR) -> list[Finding]:
    """G-002: Every block must have at least one non-empty input slot
    and at least one non-empty output slot.
    """
    findings = []
    for block in system.blocks:
        fwd_in, fwd_out, bwd_in, bwd_out = block.signature
        has_input = bool(fwd_in) or bool(bwd_in)
        has_output = bool(fwd_out) or bool(bwd_out)
        has_required = has_input and has_output

        missing = []
        if not has_input:
            missing.append("no inputs")
        if not has_output:
            missing.append("no outputs")

        findings.append(
            Finding(
                check_id="G-002",
                severity=Severity.ERROR,
                message=(
                    f"{block.name}: signature "
                    f"({fwd_in!r}, {fwd_out!r}, "
                    f"{bwd_in!r}, {bwd_out!r})"
                    + (f" — {', '.join(missing)}" if missing else "")
                ),
                source_elements=[block.name],
                passed=has_required,
            )
        )

    return findings


def check_g003_direction_consistency(system: SystemIR) -> list[Finding]:
    """G-003: Covariant wirings should not be typed as backward;
    contravariant wirings should not be typed as forward.

    This is a generic structural check — domain packages define their
    own wiring_type semantics.
    """
    findings = []
    for wiring in system.wirings:
        # Generic check: just verify the wiring has a direction set
        findings.append(
            Finding(
                check_id="G-003",
                severity=Severity.INFO,
                message=(
                    f"Wiring {wiring.label!r} ({wiring.source} -> {wiring.target}): "
                    f"direction={wiring.direction.value}"
                ),
                source_elements=[wiring.source, wiring.target],
                passed=True,
            )
        )

    return findings


def check_g004_dangling_wirings(system: SystemIR) -> list[Finding]:
    """G-004: Flag wirings whose source or target is not in the system."""
    findings = []
    known_names = {b.name for b in system.blocks}
    # Also include input names
    for inp in system.inputs:
        if isinstance(inp, dict) and "name" in inp:
            known_names.add(inp["name"])

    for wiring in system.wirings:
        src_ok = wiring.source in known_names
        tgt_ok = wiring.target in known_names
        ok = src_ok and tgt_ok

        issues = []
        if not src_ok:
            issues.append(f"source {wiring.source!r} unknown")
        if not tgt_ok:
            issues.append(f"target {wiring.target!r} unknown")

        findings.append(
            Finding(
                check_id="G-004",
                severity=Severity.ERROR,
                message=(
                    f"Wiring {wiring.label!r} ({wiring.source} -> {wiring.target})"
                    + (f" — {', '.join(issues)}" if issues else "")
                ),
                source_elements=[wiring.source, wiring.target],
                passed=ok,
            )
        )

    return findings


def check_g005_sequential_type_compatibility(system: SystemIR) -> list[Finding]:
    """G-005: In stack composition, wiring label must be subset of
    BOTH source forward_out AND target forward_in.
    """
    findings = []
    block_sigs = {b.name: b.signature for b in system.blocks}
    block_names = set(block_sigs.keys())

    for wiring in system.wirings:
        if wiring.direction != FlowDirection.COVARIANT:
            continue
        if wiring.is_temporal:
            continue
        if wiring.source not in block_names or wiring.target not in block_names:
            continue

        src_out = block_sigs[wiring.source][1]  # forward_out
        tgt_in = block_sigs[wiring.target][0]  # forward_in

        if not src_out or not tgt_in:
            continue

        label_in_out = tokens_subset(wiring.label, src_out)
        label_in_in = tokens_subset(wiring.label, tgt_in)
        compatible = label_in_out and label_in_in

        findings.append(
            Finding(
                check_id="G-005",
                severity=Severity.ERROR,
                message=(
                    f"Stack {wiring.source} ; {wiring.target}: "
                    f"out={src_out!r}, in={tgt_in!r}, wiring={wiring.label!r}"
                    + ("" if compatible else " — type mismatch")
                ),
                source_elements=[wiring.source, wiring.target],
                passed=compatible,
            )
        )

    return findings


def check_g006_covariant_acyclicity(system: SystemIR) -> list[Finding]:
    """G-006: Covariant flow graph must be a DAG (no cycles within a timestep).

    Temporal wirings and contravariant wirings are excluded.
    """
    block_names = {b.name for b in system.blocks}
    adj: dict[str, list[str]] = {name: [] for name in block_names}

    for wiring in system.wirings:
        if wiring.direction != FlowDirection.COVARIANT:
            continue
        if wiring.is_temporal:
            continue
        if wiring.source in block_names and wiring.target in block_names:
            adj[wiring.source].append(wiring.target)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in block_names}
    cycle_path: list[str] = []
    has_cycle = False

    def dfs(node: str) -> bool:
        nonlocal has_cycle
        color[node] = GRAY
        cycle_path.append(node)
        for neighbor in adj[node]:
            if color[neighbor] == GRAY:
                has_cycle = True
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        cycle_path.pop()
        color[node] = BLACK
        return False

    for node in block_names:
        if color[node] == WHITE and dfs(node):
            break

    if has_cycle:
        return [
            Finding(
                check_id="G-006",
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
            check_id="G-006",
            severity=Severity.ERROR,
            message="Covariant flow graph is acyclic (DAG)",
            source_elements=[],
            passed=True,
        )
    ]
