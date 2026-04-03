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
    """SC-001: Completeness.

    Every entity variable is updated by at least one mechanism. Detects orphan
    state variables that can never change -- a likely specification error.

    Property: Let U = {(e, v) for m in Mechanisms for (e, v) in m.updates}.
    For every entity e and variable v in e.variables: (e.name, v) in U.
    The mechanism update map is surjective onto the state variable set.

    See: docs/framework/design/check-specifications.md
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
    """SC-002: Determinism.

    Within each wiring, no two mechanisms update the same variable. Detects
    write conflicts where multiple mechanisms try to modify the same state
    variable within the same composition.

    Property: For every wiring w and every (entity, variable) pair (e, v):
    |{m in w.block_names : m is Mechanism, (e, v) in m.updates}| <= 1.
    The state transition f must be a function, not a multi-valued relation.

    See: docs/framework/design/check-specifications.md
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
    """SC-003: Reachability.

    Can signals reach from one block to another through the wiring graph?
    Maps to the GDS attainability correspondence.

    Property: There exists a directed path in the wire graph from from_block
    to to_block, where edges are (wire.source, wire.target) across all
    SpecWiring instances. Unlike other semantic checks, requires explicit
    from_block and to_block arguments.

    See: docs/framework/design/check-specifications.md
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
    """SC-005: Parameter References.

    All parameter references in blocks resolve to registered parameters.
    Validates that every ``params_used`` entry on blocks corresponds to a
    parameter definition in the spec's ``parameter_schema``.

    Property: For every block b implementing HasParams:
    {p for p in b.params_used} is a subset of spec.parameter_schema.names().

    See: docs/framework/design/check-specifications.md
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
    """SC-004: Type Safety.

    Wire spaces match source and target block expectations. Verifies that space
    references on wires correspond to registered spaces.

    Property: For every wire in every SpecWiring: if wire.space is non-empty,
    then wire.space is in spec.spaces. Referential integrity of space
    declarations on wiring channels.

    See: docs/framework/design/check-specifications.md
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
    """SC-006/SC-007: Canonical Wellformedness.

    Canonical projection structural validity. Two sub-checks:

    - SC-006: At least one mechanism exists (f is non-empty).
      Property: |project_canonical(spec).mechanism_blocks| >= 1.
    - SC-007: State space X is non-empty (entities with variables exist).
      Property: |project_canonical(spec).state_variables| >= 1.

    Together these ensure the canonical form h = f . g is non-degenerate.

    See: docs/framework/design/check-specifications.md
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
    """SC-008: Admissibility References.

    Every registered AdmissibleInputConstraint references an existing
    BoundaryAction and valid (entity, variable) pairs.

    Property: For every AdmissibleInputConstraint ac:
    (1) ac.boundary_block in spec.blocks,
    (2) spec.blocks[ac.boundary_block] is BoundaryAction,
    (3) for all (e, v) in ac.depends_on: e in spec.entities and
        v in spec.entities[e].variables.

    See: docs/framework/design/check-specifications.md
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
    """SC-009: Transition Reads.

    Every TransitionSignature references an existing Mechanism, reads valid
    (entity, variable) pairs, and depends_on_blocks are registered blocks.

    Property: For every TransitionSignature ts:
    (1) ts.mechanism in spec.blocks,
    (2) spec.blocks[ts.mechanism] is Mechanism,
    (3) for all (e, v) in ts.reads: e in spec.entities and
        v in spec.entities[e].variables,
    (4) for all b in ts.depends_on_blocks: b in spec.blocks.

    See: docs/framework/design/check-specifications.md
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


def check_controlaction_pathway(spec: GDSSpec) -> list[Finding]:
    """SC-010: ControlAction outputs must not feed the g pathway.

    The output map y = C(x, d) produces observable output Y. Its signals
    must not be routed back into Policy or BoundaryAction blocks, which
    form the input map g. Doing so would conflate the output map C with
    the policy map g, breaking the canonical separation h = f . g.

    ControlAction outputs MAY feed Mechanism blocks (state dynamics can
    depend on observations) or exit the system boundary.
    """
    findings: list[Finding] = []

    # Identify ControlAction blocks
    ca_blocks: set[str] = set()
    for bname, block in spec.blocks.items():
        if isinstance(block, ControlAction):
            ca_blocks.add(bname)

    if not ca_blocks:
        return findings

    # Identify g-pathway blocks (Policy + BoundaryAction)
    g_blocks: set[str] = set()
    for bname, block in spec.blocks.items():
        if isinstance(block, (Policy, BoundaryAction)):
            g_blocks.add(bname)

    # Check wiring: no wire from CA output to g-pathway input
    for wiring in spec.wirings.values():
        for wire in wiring.wires:
            if wire.source in ca_blocks and wire.target in g_blocks:
                findings.append(
                    Finding(
                        check_id="SC-010",
                        severity=Severity.WARNING,
                        message=(
                            f"ControlAction block {wire.source!r} output is wired to "
                            f"g-pathway block {wire.target!r}. ControlAction outputs "
                            f"(output map C) should not feed Policy or BoundaryAction "
                            f"blocks (input map g)."
                        ),
                        source_elements=[wire.source, wire.target],
                        passed=False,
                    )
                )

    if not findings:
        findings.append(
            Finding(
                check_id="SC-010",
                severity=Severity.INFO,
                message="ControlAction outputs are not routed to the g pathway.",
                source_elements=list(ca_blocks),
                passed=True,
            )
        )

    return findings


def check_execution_contract_compatibility(spec: GDSSpec) -> list[Finding]:
    """SC-011: ExecutionContract well-formedness and compatibility.

    When a GDSSpec has an execution_contract, verify it is internally
    consistent.  This check is a placeholder for future cross-composition
    validation (when GDSSpec gains sub-spec references).

    Currently validates:
    - If execution_contract is set with time_domain="discrete", the SystemIR
      (if compilable) should have no algebraic loops in non-temporal wirings
      (this is already checked by G-006, so we just note the dependency).
    - Contract field consistency (discrete-only fields).
    """
    findings: list[Finding] = []

    if spec.execution_contract is None:
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.INFO,
                message=(
                    "No ExecutionContract declared — spec is valid "
                    "for structural verification only."
                ),
                source_elements=[spec.name],
                passed=True,
            )
        )
        return findings

    contract = spec.execution_contract

    # Validate contract is well-formed (redundant with __post_init__ but defensive)
    if contract.time_domain == "discrete" and contract.update_ordering not in (
        "Moore",
        "Mealy",
    ):
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.ERROR,
                message=f"Invalid update_ordering: {contract.update_ordering!r}",
                source_elements=[spec.name],
                passed=False,
            )
        )

    if not findings:
        findings.append(
            Finding(
                check_id="SC-011",
                severity=Severity.INFO,
                message=(
                    f"ExecutionContract declared: "
                    f"{contract.time_domain}/{contract.synchrony}"
                    f"/{contract.update_ordering}"
                ),
                source_elements=[spec.name],
                passed=True,
            )
        )

    return findings
