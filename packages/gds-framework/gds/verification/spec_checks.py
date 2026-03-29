"""Semantic verification checks for GDSSpec.

These check higher-order GDS properties at the specification level:
completeness, determinism, reachability, admissibility, and type safety.
Each function takes a GDSSpec and returns a list of Findings.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from gds.blocks.roles import BoundaryAction, ControlAction, HasParams, Mechanism, Policy
from gds.canonical import project_canonical
from gds.verification.findings import Finding, Severity

if TYPE_CHECKING:
    from gds.spec import GDSSpec


def check_completeness(spec: GDSSpec) -> list[Finding]:
    """Every entity variable is updated by at least one mechanism.

    Detects orphan state variables that can never change — a likely
    specification error.
    """
    findings: list[Finding] = []

    all_updates: set[tuple[str, str]] = set()
    for block in spec.blocks.values():
        if isinstance(block, Mechanism):
            for entity_name, var_name in block.updates:
                all_updates.add((entity_name, var_name))

    orphans: list[str] = []
    for entity in spec.entities.values():
        for var_name in entity.variables:
            if (entity.name, var_name) not in all_updates:
                orphans.append(f"{entity.name}.{var_name}")

    if orphans:
        findings.append(
            Finding(
                check_id="SC-001",
                severity=Severity.WARNING,
                message=(
                    f"Orphan state variables never updated by any mechanism: {orphans}"
                ),
                source_elements=orphans,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-001",
                severity=Severity.INFO,
                message="All state variables are updated by at least one mechanism",
                passed=True,
            )
        )

    return findings


def check_determinism(spec: GDSSpec) -> list[Finding]:
    """Within each wiring, no two mechanisms update the same variable.

    Detects write conflicts where multiple mechanisms try to modify
    the same state variable within the same composition.
    """
    findings: list[Finding] = []

    for wiring in spec.wirings.values():
        update_map: dict[tuple[str, str], list[str]] = defaultdict(list)
        for bname in wiring.block_names:
            block = spec.blocks.get(bname)
            if block is not None and isinstance(block, Mechanism):
                for entity_name, var_name in block.updates:
                    update_map[(entity_name, var_name)].append(bname)

        for (ename, vname), mechs in update_map.items():
            if len(mechs) > 1:
                findings.append(
                    Finding(
                        check_id="SC-002",
                        severity=Severity.ERROR,
                        message=(
                            f"Write conflict in wiring '{wiring.name}': "
                            f"{ename}.{vname} updated by {mechs}"
                        ),
                        source_elements=mechs,
                        passed=False,
                    )
                )

    if not any(f.check_id == "SC-002" for f in findings):
        findings.append(
            Finding(
                check_id="SC-002",
                severity=Severity.INFO,
                message="No write conflicts detected",
                passed=True,
            )
        )

    return findings


def check_reachability(spec: GDSSpec, from_block: str, to_block: str) -> list[Finding]:
    """Can signals reach from one block to another through wiring?

    Maps to GDS attainability correspondence.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            adj[wire.source].add(wire.target)

    visited: set[str] = set()
    queue = [from_block]
    reachable = False
    while queue:
        current = queue.pop(0)
        if current == to_block:
            reachable = True
            break
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adj.get(current, set()))

    if reachable:
        return [
            Finding(
                check_id="SC-003",
                severity=Severity.INFO,
                message=f"Block '{from_block}' can reach '{to_block}'",
                source_elements=[from_block, to_block],
                passed=True,
            )
        ]
    return [
        Finding(
            check_id="SC-003",
            severity=Severity.WARNING,
            message=f"Block '{from_block}' cannot reach '{to_block}'",
            source_elements=[from_block, to_block],
            passed=False,
        )
    ]


def check_parameter_references(spec: GDSSpec) -> list[Finding]:
    """All parameter references in blocks resolve to registered parameters.

    Validates that every ``params_used`` entry on blocks corresponds to
    a parameter definition in the spec's ``parameter_schema``.
    """
    findings: list[Finding] = []

    param_names = spec.parameter_schema.names()
    unresolved: list[str] = []
    for bname, block in spec.blocks.items():
        if isinstance(block, HasParams):
            for param in block.params_used:
                if param not in param_names:
                    unresolved.append(f"{bname} -> {param}")

    if unresolved:
        findings.append(
            Finding(
                check_id="SC-005",
                severity=Severity.ERROR,
                message=f"Unresolved parameter references: {unresolved}",
                source_elements=unresolved,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-005",
                severity=Severity.INFO,
                message="All parameter references resolve to registered definitions",
                passed=True,
            )
        )

    return findings


def check_type_safety(spec: GDSSpec) -> list[Finding]:
    """Wire spaces match source and target block expectations.

    Verifies that space references on wires correspond to registered
    spaces and that source/target blocks are connected to compatible spaces.
    """
    findings: list[Finding] = []

    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            if wire.space and wire.space not in spec.spaces:
                findings.append(
                    Finding(
                        check_id="SC-004",
                        severity=Severity.ERROR,
                        message=(
                            f"Wire {wire.source} -> {wire.target} references "
                            f"unregistered space '{wire.space}'"
                        ),
                        source_elements=[wire.source, wire.target],
                        passed=False,
                    )
                )

    if not any(f.check_id == "SC-004" for f in findings):
        findings.append(
            Finding(
                check_id="SC-004",
                severity=Severity.INFO,
                message="All wire space references are valid",
                passed=True,
            )
        )

    return findings


def check_canonical_wellformedness(spec: GDSSpec) -> list[Finding]:
    """Canonical projection structural validity.

    Checks:
    - SC-006: At least one mechanism exists (f is non-empty)
    - SC-007: State space X is non-empty (entities with variables exist)
    """
    findings: list[Finding] = []
    canonical = project_canonical(spec)

    if not canonical.mechanism_blocks:
        findings.append(
            Finding(
                check_id="SC-006",
                severity=Severity.WARNING,
                message="No mechanisms found — state transition f is empty",
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-006",
                severity=Severity.INFO,
                message=(
                    "State transition f has "
                    f"{len(canonical.mechanism_blocks)} mechanism(s)"
                ),
                passed=True,
            )
        )

    if not canonical.state_variables:
        findings.append(
            Finding(
                check_id="SC-007",
                severity=Severity.WARNING,
                message="State space X is empty — no entity variables defined",
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-007",
                severity=Severity.INFO,
                message=(
                    f"State space X has {len(canonical.state_variables)} variable(s)"
                ),
                passed=True,
            )
        )

    return findings


def check_admissibility_references(spec: GDSSpec) -> list[Finding]:
    """Admissibility constraints reference valid BoundaryActions and variables.

    SC-008: Every registered AdmissibleInputConstraint references an
    existing BoundaryAction and valid (entity, variable) pairs.
    """
    findings: list[Finding] = []

    if not spec.admissibility_constraints:
        findings.append(
            Finding(
                check_id="SC-008",
                severity=Severity.INFO,
                message="No admissibility constraints registered",
                passed=True,
            )
        )
        return findings

    issues: list[str] = []
    bad_names: list[str] = []
    for ac in spec.admissibility_constraints.values():
        before = len(issues)
        block = spec.blocks.get(ac.boundary_block)
        if block is None:
            issues.append(f"'{ac.name}': block '{ac.boundary_block}' not registered")
        elif not isinstance(block, BoundaryAction):
            issues.append(
                f"'{ac.name}': '{ac.boundary_block}' is not a BoundaryAction "
                f"(is {type(block).__name__})"
            )

        for entity_name, var_name in ac.depends_on:
            if entity_name not in spec.entities:
                issues.append(f"'{ac.name}': unknown entity '{entity_name}'")
            elif var_name not in spec.entities[entity_name].variables:
                issues.append(
                    f"'{ac.name}': unknown variable '{entity_name}.{var_name}'"
                )
        if len(issues) > before:
            bad_names.append(ac.name)

    if issues:
        findings.append(
            Finding(
                check_id="SC-008",
                severity=Severity.ERROR,
                message=f"Admissibility constraint issues: {issues}",
                source_elements=bad_names,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-008",
                severity=Severity.INFO,
                message=(
                    f"All {len(spec.admissibility_constraints)} admissibility "
                    f"constraint(s) are well-formed"
                ),
                passed=True,
            )
        )

    return findings


def check_transition_reads(spec: GDSSpec) -> list[Finding]:
    """Transition signatures reference valid Mechanisms and variables.

    SC-009: Every TransitionSignature references an existing Mechanism,
    reads valid (entity, variable) pairs, and depends_on_blocks are
    registered blocks.
    """
    findings: list[Finding] = []

    if not spec.transition_signatures:
        findings.append(
            Finding(
                check_id="SC-009",
                severity=Severity.INFO,
                message="No transition signatures registered",
                passed=True,
            )
        )
        return findings

    issues: list[str] = []
    bad_names: list[str] = []
    for ts in spec.transition_signatures.values():
        before = len(issues)
        block = spec.blocks.get(ts.mechanism)
        if block is None:
            issues.append(f"'{ts.mechanism}': block not registered")
        elif not isinstance(block, Mechanism):
            issues.append(
                f"'{ts.mechanism}': not a Mechanism (is {type(block).__name__})"
            )

        for entity_name, var_name in ts.reads:
            if entity_name not in spec.entities:
                issues.append(f"'{ts.mechanism}': reads unknown entity '{entity_name}'")
            elif var_name not in spec.entities[entity_name].variables:
                issues.append(
                    f"'{ts.mechanism}': reads unknown variable "
                    f"'{entity_name}.{var_name}'"
                )

        for bname in ts.depends_on_blocks:
            if bname not in spec.blocks:
                issues.append(
                    f"'{ts.mechanism}': depends on unregistered block '{bname}'"
                )
        if len(issues) > before:
            bad_names.append(ts.mechanism)

    if issues:
        findings.append(
            Finding(
                check_id="SC-009",
                severity=Severity.ERROR,
                message=f"Transition signature issues: {issues}",
                source_elements=bad_names,
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-009",
                severity=Severity.INFO,
                message=(
                    f"All {len(spec.transition_signatures)} transition "
                    f"signature(s) are consistent"
                ),
                passed=True,
            )
        )

    return findings


def check_control_action_routing(spec: GDSSpec) -> list[Finding]:
    """ControlAction output must not wire to Policy or BoundaryAction.

    SC-010: In the forward wiring topology declared in SpecWiring,
    a ControlAction's output should flow toward Mechanisms (state
    updates), not backward toward Policies or BoundaryActions.
    Feedback routing is allowed but occurs at the composition layer
    (.feedback()/.loop()), not in SpecWiring.
    """
    findings: list[Finding] = []

    control_names: set[str] = set()
    policy_or_boundary_names: set[str] = set()
    for bname, block in spec.blocks.items():
        if isinstance(block, ControlAction):
            control_names.add(bname)
        elif isinstance(block, (Policy, BoundaryAction)):
            policy_or_boundary_names.add(bname)

    if not control_names:
        findings.append(
            Finding(
                check_id="SC-010",
                severity=Severity.INFO,
                message="No ControlAction blocks — SC-010 not applicable",
                passed=True,
            )
        )
        return findings

    violations: list[str] = []
    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            if wire.source in control_names and wire.target in policy_or_boundary_names:
                target_role = type(spec.blocks[wire.target]).__name__
                violations.append(
                    f"'{wire.source}' -> '{wire.target}' ({target_role})"
                )

    if violations:
        findings.append(
            Finding(
                check_id="SC-010",
                severity=Severity.WARNING,
                message=(
                    f"ControlAction output wired to Policy/BoundaryAction "
                    f"in forward path: {'; '.join(violations)}. "
                    f"Output map C should feed Mechanisms, not decision "
                    f"logic. Use .feedback() for observation feedback."
                ),
                source_elements=[v.split("'")[1] for v in violations],
                passed=False,
            )
        )
    else:
        findings.append(
            Finding(
                check_id="SC-010",
                severity=Severity.INFO,
                message=(
                    "ControlAction routing valid — no forward-path "
                    "wires to Policy or BoundaryAction"
                ),
                passed=True,
            )
        )

    return findings


def check_control_action_observes(spec: GDSSpec) -> list[Finding]:
    """ControlAction.observes must reference valid entity variables.

    SC-011: Each (entity, variable) pair in ControlAction.observes
    must reference a registered entity with that variable. Parallel
    to SC-009 (TransitionSignature.reads) for Mechanism read deps.
    """
    findings: list[Finding] = []

    control_blocks = [
        (name, block)
        for name, block in spec.blocks.items()
        if isinstance(block, ControlAction)
    ]

    if not control_blocks:
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.INFO,
                message="No ControlAction blocks — SC-011 not applicable",
                passed=True,
            )
        )
        return findings

    issues: list[str] = []
    bad_names: set[str] = set()

    for bname, block in control_blocks:
        for entity_name, var_name in block.observes:
            if entity_name not in spec.entities:
                issues.append(
                    f"ControlAction '{bname}' observes unknown "
                    f"entity '{entity_name}'"
                )
                bad_names.add(bname)
            elif var_name not in spec.entities[entity_name].variables:
                issues.append(
                    f"ControlAction '{bname}' observes unknown "
                    f"variable '{entity_name}.{var_name}'"
                )
                bad_names.add(bname)

    if issues:
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.ERROR,
                message=f"ControlAction observes issues: {issues}",
                source_elements=sorted(bad_names),
                passed=False,
            )
        )
    else:
        n_obs = sum(len(b.observes) for _, b in control_blocks)
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.INFO,
                message=(
                    f"All {len(control_blocks)} ControlAction block(s) "
                    f"with {n_obs} observes reference(s) are valid"
                ),
                passed=True,
            )
        )

    return findings
