"""Type consistency checks T-001 through T-006.

These checks verify that individual flows and game signatures are
internally consistent — that flow labels match game port types, that
games have complete signatures, and that flow directions match their
semantic types.

All comparisons use token-based matching (see ``tokens.py``): signature
strings are split on `` + `` and ``, `` into normalized tokens, and
compatibility is checked via set containment (subset) or overlap.

Key distinction from structural checks (S-series): type checks validate
per-flow / per-game properties, while structural checks validate
global composition invariants (acyclicity, independence, etc.).
"""

from ogs.ir.models import FlowDirection, FlowType, PatternIR
from ogs.verification.findings import Finding, Severity
from ogs.verification.tokens import tokens_subset


def check_t001_domain_codomain_matching(pattern: PatternIR) -> list[Finding]:
    """T-001: For every covariant game-to-game flow, verify the flow label
    is consistent with source codomain (Y) or target domain (X).

    Uses token-based comparison: flow label tokens must be a subset of
    the source Y tokens OR the target X tokens.
    """
    findings = []
    game_sigs = {g.name: g.signature for g in pattern.games}

    for flow in pattern.flows:
        if flow.direction != FlowDirection.COVARIANT:
            continue
        if flow.source not in game_sigs or flow.target not in game_sigs:
            continue  # input-to-game flows handled by T-006

        src_y = game_sigs[flow.source][1]  # codomain (Y)
        tgt_x = game_sigs[flow.target][0]  # domain (X)

        if not src_y or not tgt_x:
            findings.append(
                Finding(
                    check_id="T-001",
                    severity=Severity.ERROR,
                    message=(
                        f"Cannot verify domain/codomain: "
                        f"{flow.source} Y={src_y!r}, {flow.target} X={tgt_x!r}"
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=False,
                )
            )
            continue

        compatible = tokens_subset(flow.label, src_y) or tokens_subset(
            flow.label, tgt_x
        )
        findings.append(
            Finding(
                check_id="T-001",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.label!r}: {flow.source} "
                    f"Y={src_y!r} -> {flow.target} X={tgt_x!r}"
                    + ("" if compatible else " — MISMATCH")
                ),
                source_elements=[flow.source, flow.target],
                passed=compatible,
            )
        )

    return findings


def check_t002_signature_completeness(pattern: PatternIR) -> list[Finding]:
    """T-002: Every OpenGameIR must have all four (X,Y,R,S) slots.

    Slots must be defined (even if empty set).

    A game is valid if it has at least one non-empty input slot (X or R)
    and at least one non-empty output slot (Y or S). Games that only
    produce contravariant output (utility computations) have empty Y
    but non-empty S, which is valid.
    """
    findings = []
    for game in pattern.games:
        x, y, r, s = game.signature
        has_input = bool(x) or bool(r)
        has_output = bool(y) or bool(s)
        has_required = has_input and has_output

        missing = []
        if not has_input:
            missing.append("no inputs (X or R)")
        if not has_output:
            missing.append("no outputs (Y or S)")

        findings.append(
            Finding(
                check_id="T-002",
                severity=Severity.ERROR,
                message=(
                    f"{game.name}: signature ({x!r}, {y!r}, {r!r}, {s!r})"
                    + (f" — {', '.join(missing)}" if missing else "")
                ),
                source_elements=[game.name],
                passed=has_required,
            )
        )

    return findings


def check_t003_flow_type_consistency(pattern: PatternIR) -> list[Finding]:
    """T-003: Covariant flows must not be utility/coutility; contravariant must be."""
    findings = []
    for flow in pattern.flows:
        if flow.direction == FlowDirection.COVARIANT:
            ok = flow.flow_type != FlowType.UTILITY_COUTILITY
            findings.append(
                Finding(
                    check_id="T-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Covariant flow {flow.label!r} "
                        f"({flow.source} -> {flow.target})"
                        f" has type {flow.flow_type.value}"
                        + ("" if ok else " — should not be utility/coutility")
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=ok,
                )
            )
        else:
            ok = flow.flow_type == FlowType.UTILITY_COUTILITY
            findings.append(
                Finding(
                    check_id="T-003",
                    severity=Severity.ERROR,
                    message=(
                        f"Contravariant flow {flow.label!r} "
                        f"({flow.source} -> {flow.target})"
                        f" has type {flow.flow_type.value}"
                        + ("" if ok else " — should be utility/coutility")
                    ),
                    source_elements=[flow.source, flow.target],
                    passed=ok,
                )
            )

    return findings


def check_t004_input_type_resolution(pattern: PatternIR) -> list[Finding]:
    """T-004: Every InputIR.schema_hint must resolve to a known type."""
    findings = []
    for inp in pattern.inputs:
        has_hint = bool(inp.schema_hint)
        findings.append(
            Finding(
                check_id="T-004",
                severity=Severity.WARNING,
                message=(
                    f"Input {inp.name!r}: schema_hint={inp.schema_hint!r}"
                    + ("" if has_hint else " — no schema hint")
                ),
                source_elements=[inp.name],
                passed=has_hint,
            )
        )

    return findings


def check_t005_unused_inputs(pattern: PatternIR) -> list[Finding]:
    """T-005: Flag inputs with no outgoing flows."""
    findings = []
    flow_sources = {f.source for f in pattern.flows}

    for inp in pattern.inputs:
        used = inp.name in flow_sources
        findings.append(
            Finding(
                check_id="T-005",
                severity=Severity.INFO,
                message=(
                    f"Input {inp.name!r}"
                    + ("" if used else " — unused (no outgoing flows)")
                ),
                source_elements=[inp.name],
                passed=used,
            )
        )

    return findings


def check_t006_dangling_flows(pattern: PatternIR) -> list[Finding]:
    """T-006: Flag flows whose source or target is not in the pattern."""
    findings = []
    known_names = {g.name for g in pattern.games} | {i.name for i in pattern.inputs}

    for flow in pattern.flows:
        src_ok = flow.source in known_names
        tgt_ok = flow.target in known_names
        ok = src_ok and tgt_ok

        issues = []
        if not src_ok:
            issues.append(f"source {flow.source!r} unknown")
        if not tgt_ok:
            issues.append(f"target {flow.target!r} unknown")

        findings.append(
            Finding(
                check_id="T-006",
                severity=Severity.ERROR,
                message=(
                    f"Flow {flow.label!r} ({flow.source} -> {flow.target})"
                    + (f" — {', '.join(issues)}" if issues else "")
                ),
                source_elements=[flow.source, flow.target],
                passed=ok,
            )
        )

    return findings
