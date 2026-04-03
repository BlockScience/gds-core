"""Generic verification checks G-001 through G-006.

These checks operate on the domain-neutral SystemIR. They verify type
consistency, structural completeness, and graph topology without
referencing any domain-specific block types or semantics.
"""

from gds.ir.models import FlowDirection, SystemIR
from gds.types.tokens import tokens_subset
from gds.verification.findings import Finding, Severity


def check_g001_domain_codomain_matching(system: SystemIR) -> list[Finding]:
    """G-001: Domain/Codomain Matching.

    For every covariant block-to-block wiring, verify the label is consistent
    with source forward_out or target forward_in. Contravariant wirings are
    skipped (handled by G-003).

    Property: For every wiring w where w.direction = COVARIANT and both
    endpoints are blocks: tokens(w.label) is a subset of
    tokens(source.forward_out) OR tokens(target.forward_in).

    See: docs/framework/design/check-specifications.md
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
    """G-002: Signature Completeness.

    Every block must have at least one non-empty input slot and at least one
    non-empty output slot. BoundaryAction blocks (block_type == "boundary") are
    exempt from the input requirement -- they have no inputs by design, since
    they model exogenous signals entering the system from outside.

    Property: For every block b: has_output(b) is True, and (if b is not
    a BoundaryAction) has_input(b) is True, where has_input/has_output check
    that at least one of the forward/backward slots is non-empty.

    See: docs/framework/design/check-specifications.md
    """
    findings = []
    for block in system.blocks:
        fwd_in, fwd_out, bwd_in, bwd_out = block.signature
        has_input = bool(fwd_in) or bool(bwd_in)
        has_output = bool(fwd_out) or bool(bwd_out)

        # BoundaryAction blocks have no inputs by design — only check outputs
        is_boundary = block.block_type == "boundary"
        has_required = has_output if is_boundary else has_input and has_output

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
    """G-003: Direction Consistency.

    Validate direction flag consistency and contravariant port-slot matching.

    Two validations:

    A) Flag consistency -- ``direction``, ``is_feedback``, ``is_temporal`` must
       not contradict:
       - COVARIANT + is_feedback -> ERROR (feedback implies contravariant)
       - CONTRAVARIANT + is_temporal -> ERROR (temporal implies covariant)

    B) Contravariant port-slot matching -- for CONTRAVARIANT wirings, the label
       must be a token-subset of the source's backward_out (signature[3]) or
       the target's backward_in (signature[2]). G-001 already covers the
       covariant side.

    Property: (A) NOT (COVARIANT AND is_feedback) and NOT (CONTRAVARIANT AND
    is_temporal). (B) For contravariant wirings: tokens(label) is a subset of
    tokens(source.backward_out) OR tokens(target.backward_in).

    See: docs/framework/design/check-specifications.md
    """
    findings = []
    block_sigs = {b.name: b.signature for b in system.blocks}

    for wiring in system.wirings:
        # A) Flag consistency
        if wiring.direction == FlowDirection.COVARIANT and wiring.is_feedback:
            findings.append(
                Finding(
                    check_id="G-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Wiring {wiring.label!r} "
                        f"({wiring.source} -> {wiring.target}): "
                        f"COVARIANT + is_feedback — contradiction"
                    ),
                    source_elements=[wiring.source, wiring.target],
                    passed=False,
                )
            )
            continue

        if wiring.direction == FlowDirection.CONTRAVARIANT and wiring.is_temporal:
            findings.append(
                Finding(
                    check_id="G-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Wiring {wiring.label!r} "
                        f"({wiring.source} -> {wiring.target}): "
                        f"CONTRAVARIANT + is_temporal — contradiction"
                    ),
                    source_elements=[wiring.source, wiring.target],
                    passed=False,
                )
            )
            continue

        # B) Contravariant port-slot matching (G-001 covers covariant)
        if wiring.direction == FlowDirection.CONTRAVARIANT:
            if wiring.source not in block_sigs or wiring.target not in block_sigs:
                # Non-block endpoints — G-004 handles dangling references
                continue

            src_bwd_out = block_sigs[wiring.source][3]  # backward_out
            tgt_bwd_in = block_sigs[wiring.target][2]  # backward_in

            if not src_bwd_out and not tgt_bwd_in:
                findings.append(
                    Finding(
                        check_id="G-003",
                        severity=Severity.ERROR,
                        message=(
                            f"Wiring {wiring.label!r} "
                            f"({wiring.source} -> {wiring.target}): "
                            f"CONTRAVARIANT but both backward "
                            f"ports are empty"
                        ),
                        source_elements=[wiring.source, wiring.target],
                        passed=False,
                    )
                )
                continue

            compatible = tokens_subset(wiring.label, src_bwd_out) or tokens_subset(
                wiring.label, tgt_bwd_in
            )
            findings.append(
                Finding(
                    check_id="G-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Wiring {wiring.label!r}: "
                        f"{wiring.source} bwd_out={src_bwd_out!r} -> "
                        f"{wiring.target} bwd_in={tgt_bwd_in!r}"
                        + ("" if compatible else " — MISMATCH")
                    ),
                    source_elements=[wiring.source, wiring.target],
                    passed=compatible,
                )
            )

    return findings


def check_g004_dangling_wirings(system: SystemIR) -> list[Finding]:
    """G-004: Dangling Wirings.

    Flag wirings whose source or target is not in the system's block or input
    set. A dangling reference indicates a typo or missing block.

    Property: For every wiring w: w.source in N and w.target in N, where
    N = {b.name for b in blocks} union {i.name for i in inputs}.

    See: docs/framework/design/check-specifications.md
    """
    findings = []
    known_names = {b.name for b in system.blocks}
    for inp in system.inputs:
        known_names.add(inp.name)

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
    """G-005: Sequential Type Compatibility.

    In stack (sequential) composition, the wiring label must be a token-subset
    of BOTH the source's forward_out AND the target's forward_in. This is
    stricter than G-001, which only requires matching one side.

    Property: For every covariant, non-temporal wiring w between blocks:
    tokens(w.label) is a subset of tokens(source.forward_out) AND
    tokens(w.label) is a subset of tokens(target.forward_in).

    See: docs/framework/design/check-specifications.md
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
    """G-006: Covariant Acyclicity.

    The covariant (forward) flow graph must be a directed acyclic graph (DAG).
    Temporal wirings and contravariant wirings are excluded because they do not
    create within-evaluation algebraic dependencies.

    Property: Let G_cov = (V, E_cov) where V = {b.name for b in blocks} and
    E_cov = {(w.source, w.target) for w in wirings if w.direction = COVARIANT
    and not w.is_temporal}. G_cov is acyclic.

    See: docs/framework/design/check-specifications.md
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
