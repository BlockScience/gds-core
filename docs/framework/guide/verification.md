# Verification Check Catalog

GDS runs 13 verification checks across two registries to validate both structural
topology and domain semantics. This page is the complete reference for every check.

## Overview

Verification answers the question: *is this specification well-formed?* It does not
simulate or solve — it validates structure.

There are two independent check registries:

| Registry | Checks | Operates on | What it validates |
|---|---|---|---|
| **Generic** | G-001 through G-006 | `SystemIR` | Structural topology — port matching, acyclicity, dangling references |
| **Semantic** | SC-001 through SC-007 | `GDSSpec` | Domain properties — completeness, determinism, type safety, canonical form |

Generic checks run on the compiled IR (after `compile_system()`). Semantic checks
run on the specification (the `GDSSpec` registry). Both produce `Finding` objects
with a check ID, severity, message, and pass/fail status.

### When to run verification

- **After building a SystemIR** — run `verify(system)` to check all generic checks
- **After building a GDSSpec** — call individual semantic check functions
- **During development** — run checks incrementally to catch errors early
- **In tests** — assert that all checks pass for valid models

### Running generic checks

```python
from gds import compile_system, verify

ir = compile_system("My Model", composed_system)
report = verify(ir)

print(f"{report.checks_passed}/{report.checks_total} checks passed")
for finding in report.findings:
    if not finding.passed:
        print(f"  [{finding.severity.value}] {finding.check_id}: {finding.message}")
```

### Running semantic checks

Semantic checks are called individually against a `GDSSpec`:

```python
from gds.verification.spec_checks import (
    check_completeness,
    check_determinism,
    check_parameter_references,
    check_type_safety,
    check_canonical_wellformedness,
)

spec = build_spec()

findings = []
findings += check_completeness(spec)
findings += check_determinism(spec)
findings += check_parameter_references(spec)
findings += check_type_safety(spec)
findings += check_canonical_wellformedness(spec)

for f in findings:
    if not f.passed:
        print(f"[{f.severity.value}] {f.check_id}: {f.message}")
```

---

## Generic Checks (G-001 through G-006)

These checks operate on `SystemIR` — the flat intermediate representation produced
by `compile_system()`. They validate structural topology without referencing any
domain-specific block types or semantics.

All generic checks run automatically when you call `verify(system)`.

### G-001: Domain/Codomain Matching

**What it checks:** For every covariant block-to-block wiring, the wiring label
must be a token-subset of the source block's `forward_out` or the target block's
`forward_in`. This ensures that signals flowing forward through the system
reference ports that actually exist on the connected blocks.

**Severity:** ERROR

**Skips:** Contravariant wirings (handled by G-003 instead).

**Trigger example:** Block A outputs `"Temperature"` but Block B expects
`"Pressure"`. A wiring labeled `"humidity"` connects them — the label matches
neither side.

```python
from gds.ir.models import BlockIR, FlowDirection, SystemIR, WiringIR

system = SystemIR(
    name="Bad Wiring",
    blocks=[
        BlockIR(name="A", signature=("", "Temperature", "", "")),
        BlockIR(name="B", signature=("Pressure", "", "", "")),
    ],
    wirings=[
        WiringIR(
            source="A", target="B", label="humidity",
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

**Example finding (failure):**

```
[error] G-001: Wiring 'humidity': A out='Temperature' -> B in='Pressure' — MISMATCH
```

**Example finding (pass):**

```
[error] G-001: Wiring 'temperature': Sensor out='Temperature' -> Controller in='Temperature'
```

!!! note
    For generic checks (G-001..G-006), passing findings retain `severity=ERROR` — the severity
    indicates what *would* be reported if the check failed. For semantic checks (SC-001..SC-007),
    passing findings use `severity=INFO`. Use the `passed` field to distinguish pass from fail.

---

### G-002: Signature Completeness

**What it checks:** Every block must have at least one non-empty input slot
(forward_in or backward_in) AND at least one non-empty output slot (forward_out
or backward_out). A block with no inputs or no outputs is structurally isolated.

**Severity:** ERROR

**Trigger example:** A block with a completely empty signature — no ports at all.

```python
system = SystemIR(
    name="Incomplete",
    blocks=[
        BlockIR(name="Valid", signature=("In", "Out", "", "")),
        BlockIR(name="Orphan", signature=("", "", "", "")),
    ],
    wirings=[],
)
```

**Example finding (failure):**

```
[error] G-002: Orphan: signature ('', '', '', '') — no inputs, no outputs
```

!!! warning "G-002 and BoundaryActions"
    G-002 flags `BoundaryAction` blocks (which have no `forward_in` by design)
    and terminal `Mechanism` blocks (which may have no `forward_out`). These are
    valid GDS boundaries — expect G-002 failures on them. When testing, either
    skip G-002 or accept these as known findings.

---

### G-003: Direction Consistency

**What it checks:** Two validations on every wiring:

**A) Flag consistency** — the `direction`, `is_feedback`, and `is_temporal` flags
must not contradict each other:

- `COVARIANT` + `is_feedback=True` is a contradiction (feedback implies contravariant flow)
- `CONTRAVARIANT` + `is_temporal=True` is a contradiction (temporal implies covariant flow)

**B) Contravariant port-slot matching** — for `CONTRAVARIANT` wirings, the label
must be a token-subset of the source's `backward_out` (signature slot 3) or the
target's `backward_in` (signature slot 2). This is the backward-flow counterpart
of what G-001 does for covariant wirings.

**C) Non-empty backward ports** — for `CONTRAVARIANT` wirings, at least one of
`src_bwd_out` or `tgt_bwd_in` must be non-empty. If both are empty, G-003 emits
`"CONTRAVARIANT but both backward ports are empty"` with `passed=False`.

**Severity:** ERROR

**Trigger example (flag contradiction):**

```python
system = SystemIR(
    name="Contradiction",
    blocks=[BlockIR(name="A"), BlockIR(name="B")],
    wirings=[
        WiringIR(
            source="A", target="B", label="x",
            direction=FlowDirection.COVARIANT,
            is_feedback=True,  # contradicts COVARIANT
        ),
    ],
)
```

**Example finding (flag contradiction):**

```
[error] G-003: Wiring 'x' (A -> B): COVARIANT + is_feedback — contradiction
```

**Trigger example (contravariant mismatch):**

```python
system = SystemIR(
    name="Mismatch",
    blocks=[
        BlockIR(name="A", signature=("", "", "", "Cost")),
        BlockIR(name="B", signature=("", "", "Reward", "")),
    ],
    wirings=[
        WiringIR(
            source="A", target="B", label="unrelated",
            direction=FlowDirection.CONTRAVARIANT,
            is_feedback=True,
        ),
    ],
)
```

**Example finding (contravariant mismatch):**

```
[error] G-003: Wiring 'unrelated': A bwd_out='Cost' -> B bwd_in='Reward' — MISMATCH
```

---

### G-004: Dangling Wirings

**What it checks:** Every wiring's `source` and `target` must reference a block
or input that exists in the system. A wiring pointing to a non-existent block is
dangling — either a typo or a missing block.

**Severity:** ERROR

**Recognized endpoints:** Block names (`system.blocks`) and input names
(`system.inputs`). Inputs are valid wiring sources (they represent exogenous signals
entering the system).

**Trigger example:**

```python
system = SystemIR(
    name="Dangling",
    blocks=[BlockIR(name="B", signature=("Signal", "", "", ""))],
    wirings=[
        WiringIR(
            source="Ghost", target="B", label="signal",
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

**Example finding (failure):**

```
[error] G-004: Wiring 'signal' (Ghost -> B) — source 'Ghost' unknown
```

---

### G-005: Sequential Type Compatibility

**What it checks:** In stack (sequential) composition, the wiring label must be a
token-subset of BOTH the source's `forward_out` AND the target's `forward_in`.
This is stricter than G-001, which only requires the label to match one side.

G-005 enforces that the types are compatible on both ends of a sequential connection.

**Severity:** ERROR

**Skips:** Temporal wirings (`is_temporal=True`), contravariant wirings, and wirings where either endpoint is not in the block set (e.g., `InputIR` endpoints).

**Additional failure mode:** If either `src_out` or `tgt_in` is empty (the block has no forward ports), G-001 emits `"Cannot verify domain/codomain: ..."` with `passed=False`.

**Trigger example:**

```python
system = SystemIR(
    name="Incompatible",
    blocks=[
        BlockIR(name="A", signature=("", "X", "", "")),
        BlockIR(name="B", signature=("Y", "", "", "")),
    ],
    wirings=[
        WiringIR(
            source="A", target="B", label="z",
            direction=FlowDirection.COVARIANT,
        ),
    ],
)
```

**Example finding (failure):**

```
[error] G-005: Stack A ; B: out='X', in='Y', wiring='z' — type mismatch
```

---

### G-006: Covariant Acyclicity

**What it checks:** The covariant (forward) flow graph must be a directed acyclic
graph (DAG). A cycle in the covariant graph means an algebraic loop within a
single timestep — Block A depends on Block B which depends on Block A, with no
temporal delay to break the cycle.

**Severity:** ERROR

**Excludes:** Temporal wirings (`is_temporal=True`) and contravariant wirings.
These are legitimate backward or cross-timestep connections that do not create
algebraic loops.

**Detection method:** DFS-based cycle detection on the adjacency graph of
covariant, non-temporal wirings.

**Trigger example:**

```python
system = SystemIR(
    name="Cycle",
    blocks=[
        BlockIR(name="A", signature=("Signal", "Signal", "", "")),
        BlockIR(name="B", signature=("Signal", "Signal", "", "")),
        BlockIR(name="C", signature=("Signal", "Signal", "", "")),
    ],
    wirings=[
        WiringIR(source="A", target="B", label="signal",
                 direction=FlowDirection.COVARIANT),
        WiringIR(source="B", target="C", label="signal",
                 direction=FlowDirection.COVARIANT),
        WiringIR(source="C", target="A", label="signal",
                 direction=FlowDirection.COVARIANT),
    ],
)
```

**Example finding (failure):**

```
[error] G-006: Covariant flow graph contains a cycle: A -> B -> C
```

**Example finding (pass):**

```
[error] G-006: Covariant flow graph is acyclic (DAG)
```

---

## Semantic Checks (SC-001 through SC-007)

These checks operate on `GDSSpec` — the specification-level registry. They
validate domain properties that require knowledge of entities, roles, parameters,
and the canonical decomposition.

Semantic checks are called individually (not through `verify()`).

### SC-001: Completeness

**What it checks:** Every entity variable must be updated by at least one
`Mechanism`. A state variable that no mechanism ever updates is an orphan — it
was declared but will never change, which is almost always a specification error.

**Severity:** WARNING (orphan variables may be intentional in degenerate cases)

**Trigger example:**

```python
from gds import GDSSpec, Entity, StateVariable, Policy
from gds.types.typedef import TypeDef
from gds.types.interface import Interface, port

Count = TypeDef(name="Count", python_type=int)

spec = GDSSpec(name="Orphan Demo")
spec.register_type(Count)
spec.register_entity(Entity(
    name="Reservoir",
    variables={"level": StateVariable(name="level", typedef=Count, symbol="L")},
))
# No mechanism updates Reservoir.level
spec.register_block(Policy(
    name="Observe",
    interface=Interface(forward_out=(port("Level Signal"),)),
))
```

**Example finding (failure):**

```
[warning] SC-001: Orphan state variables never updated by any mechanism: ['Reservoir.level']
```

**Example finding (pass):**

```
[info] SC-001: All state variables are updated by at least one mechanism
```

---

### SC-002: Determinism

**What it checks:** Within each wiring (a named composition), no two mechanisms
may update the same entity variable. If `MechanismA` and `MechanismB` both list
`("Counter", "value")` in their `updates` and both appear in the same `SpecWiring`,
that is a write conflict — the final state is ambiguous.

**Severity:** ERROR

**Trigger example:**

```python
spec = GDSSpec(name="Write Conflict Demo")
# ... register Counter entity with "value" variable ...

inc = Mechanism(
    name="Increment Counter",
    interface=Interface(forward_in=(port("Delta Signal"),)),
    updates=[("Counter", "value")],
)
dec = Mechanism(
    name="Decrement Counter",
    interface=Interface(forward_in=(port("Delta Signal"),)),
    updates=[("Counter", "value")],
)
spec.register_block(inc)
spec.register_block(dec)
spec.register_wiring(SpecWiring(
    name="Counter Pipeline",
    block_names=["Source", "Increment Counter", "Decrement Counter"],
    wires=[
        Wire(source="Source", target="Increment Counter"),
        Wire(source="Source", target="Decrement Counter"),
    ],
))
```

**Example finding (failure):**

```
[error] SC-002: Write conflict in wiring 'Counter Pipeline': Counter.value updated by ['Increment Counter', 'Decrement Counter']
```

**Example finding (pass):**

```
[info] SC-002: No write conflicts detected
```

---

### SC-003: Reachability

**What it checks:** Whether signals can reach from one named block to another
through the wiring graph. This maps to the GDS attainability correspondence — can
a boundary input ultimately influence a state update?

**Severity:** WARNING (unreachable blocks may indicate disconnected subgraphs)

**Note:** Unlike other semantic checks, SC-003 requires two extra arguments
(`from_block` and `to_block`). It is not called automatically — you invoke it
for specific block pairs.

```python
from gds.verification.spec_checks import check_reachability

findings = check_reachability(spec, from_block="Sensor", to_block="Update Tank")
```

**Example finding (reachable):**

```
[info] SC-003: Block 'Sensor' can reach 'Update Tank'
```

**Example finding (unreachable):**

```
[warning] SC-003: Block 'Sensor' cannot reach 'Update Tank'
```

---

### SC-004: Type Safety

**What it checks:** Every wire in every `SpecWiring` that references a `space`
must reference a space that is registered in the spec. An unregistered space name
on a wire means the data channel is undefined.

**Severity:** ERROR

**Trigger example:**

```python
spec.register_wiring(SpecWiring(
    name="Pipeline",
    block_names=["A", "B"],
    wires=[
        Wire(source="A", target="B", space="NonExistentSpace"),
    ],
))
# "NonExistentSpace" is not registered via spec.register_space()
```

**Example finding (failure):**

```
[error] SC-004: Wire A -> B references unregistered space 'NonExistentSpace'
```

**Example finding (pass):**

```
[info] SC-004: All wire space references are valid
```

---

### SC-005: Parameter References

**What it checks:** Every `params_used` entry on every block must correspond to a
parameter registered in the spec's `parameter_schema`. If a block declares that it
uses parameter `"flow_rate"` but no such parameter is registered, the reference is
dangling.

**Severity:** ERROR

**Trigger example:**

```python
source = BoundaryAction(
    name="Source",
    interface=Interface(forward_out=(port("Signal"),)),
    params_used=["flow_rate"],  # references a parameter
)
spec.register_block(source)
# But spec.register_parameter("flow_rate", ...) is never called
```

**Example finding (failure):**

```
[error] SC-005: Unresolved parameter references: ['Source -> flow_rate']
```

**Example finding (pass):**

```
[info] SC-005: All parameter references resolve to registered definitions
```

---

### SC-006: Canonical Wellformedness — Mechanisms

**What it checks:** The canonical projection (`project_canonical(spec)`) must
contain at least one mechanism. If no mechanisms exist, the state transition
function *f* is empty — the system has no state dynamics.

**Severity:** WARNING (stateless specs like pure game-theoretic models may
legitimately have no mechanisms)

**Example finding (failure):**

```
[warning] SC-006: No mechanisms found — state transition f is empty
```

**Example finding (pass):**

```
[info] SC-006: State transition f has 3 mechanism(s)
```

---

### SC-007: Canonical Wellformedness — State Space

**What it checks:** The canonical projection must contain at least one state
variable. If no entities with variables are defined, the state space *X* is empty.

**Severity:** WARNING

**Note:** SC-006 and SC-007 are produced by the same function
(`check_canonical_wellformedness`). Call it once to get both findings.

```python
from gds.verification.spec_checks import check_canonical_wellformedness

findings = check_canonical_wellformedness(spec)
# Returns findings for both SC-006 and SC-007
```

**Example finding (failure):**

```
[warning] SC-007: State space X is empty — no entity variables defined
```

**Example finding (pass):**

```
[info] SC-007: State space X has 4 variable(s)
```

---

## Understanding the Output

### Finding

Every check produces one or more `Finding` objects:

```python
class Finding(BaseModel):
    check_id: str              # e.g. "G-001", "SC-002"
    severity: Severity         # ERROR, WARNING, or INFO
    message: str               # Human-readable description
    source_elements: list[str] # Block/variable names involved
    passed: bool               # True = check passed, False = violation
    exportable_predicate: str  # Reserved for formal export
```

Key points:

- **`passed`** is the primary field — it tells you whether the check succeeded.
  A finding with `passed=True` is informational confirmation.
- **`severity`** indicates the importance level. Generic checks (G-001..G-006)
  retain their failure severity even on pass. Semantic checks (SC-001..SC-007)
  emit `Severity.INFO` on pass.
- **`source_elements`** names the blocks, variables, or wirings involved. Useful
  for tracing back to the specification.

### Severity Levels

| Level | Meaning | Action |
|---|---|---|
| `ERROR` | Structural violation — the model is invalid | Must fix before the model is usable |
| `WARNING` | Suspicious pattern — may be intentional | Review and either fix or accept |
| `INFO` | Informational — no action needed | Confirmation that a check passed |

### VerificationReport

The `verify()` function returns a `VerificationReport`:

```python
class VerificationReport(BaseModel):
    system_name: str
    findings: list[Finding]

    @property
    def errors(self) -> int: ...       # Count of failed ERROR findings
    @property
    def warnings(self) -> int: ...     # Count of failed WARNING findings
    @property
    def info_count(self) -> int: ...   # Count of failed INFO findings
    @property
    def checks_passed(self) -> int: ... # Count of passed findings
    @property
    def checks_total(self) -> int: ... # Total number of findings
```

Typical usage:

```python
report = verify(system)
assert report.errors == 0, f"Verification failed: {report.errors} errors"
```

---

## Writing Custom Checks

Use the `@gds_check` decorator to register custom verification functions. Custom
checks follow the same `Callable[[SystemIR], list[Finding]]` signature as the
built-in generic checks.

### Registration

```python
from gds import gds_check, Finding, Severity
from gds.ir.models import SystemIR

@gds_check("CUSTOM-001", Severity.WARNING)
def check_max_block_count(system: SystemIR) -> list[Finding]:
    """Flag systems with more than 20 blocks."""
    count = len(system.blocks)
    if count > 20:
        return [Finding(
            check_id="CUSTOM-001",
            severity=Severity.WARNING,
            message=f"System has {count} blocks (limit: 20)",
            source_elements=[],
            passed=False,
        )]
    return [Finding(
        check_id="CUSTOM-001",
        severity=Severity.WARNING,
        message=f"Block count ({count}) within limit",
        source_elements=[],
        passed=True,
    )]
```

The decorator:

1. Attaches `check_id` and `severity` as function attributes
2. Adds the function to a module-level custom check registry

### Running custom checks

Custom checks do not run automatically with `verify()`. Use `all_checks()` to
get the combined list of built-in + custom checks:

```python
from gds import all_checks, verify

report = verify(system, checks=all_checks())
```

Or pass custom checks explicitly:

```python
from gds import verify

report = verify(system, checks=[check_max_block_count])
```

### Retrieving registered checks

```python
from gds import get_custom_checks

custom = get_custom_checks()  # All @gds_check-decorated functions
```

---

## Filtering and Suppressing Checks

### Running a subset of checks

Pass a specific list to `verify()`:

```python
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g004_dangling_wirings,
    check_g006_covariant_acyclicity,
)

# Only run the checks you care about
report = verify(system, checks=[
    check_g001_domain_codomain_matching,
    check_g004_dangling_wirings,
    check_g006_covariant_acyclicity,
])
```

### Skipping G-002 for boundary blocks

G-002 flags `BoundaryAction` (no inputs) and terminal `Mechanism` (no outputs) as
errors. For valid GDS models these are expected. A common pattern in tests:

```python
from gds.verification.generic_checks import (
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
)

# All generic checks except G-002
checks_sans_g002 = [
    check_g001_domain_codomain_matching,
    check_g003_direction_consistency,
    check_g004_dangling_wirings,
    check_g005_sequential_type_compatibility,
    check_g006_covariant_acyclicity,
]
report = verify(system, checks=checks_sans_g002)
```

### Filtering findings after the fact

```python
report = verify(system)

# Only look at failures
failures = [f for f in report.findings if not f.passed]

# Only errors (ignore warnings)
errors = [f for f in report.findings if not f.passed and f.severity == Severity.ERROR]

# Group by check ID
from collections import defaultdict
by_check = defaultdict(list)
for f in report.findings:
    by_check[f.check_id].append(f)
```

### Intentional edge cases

Some findings are expected in valid models:

- **SC-001 (orphan state)** — WARNING severity. A state variable intentionally
  held constant (e.g., a fixed capacity) will trigger this. Accept the warning
  or add a no-op mechanism.
- **SC-006/SC-007 (empty canonical)** — WARNING severity. Stateless models (pure
  policy compositions, game-theoretic specs) legitimately have no mechanisms or
  state variables.
- **G-002 (incomplete signature)** — ERROR severity but expected on boundary
  blocks. Skip this check or filter the findings.

---

## Quick Reference

| Code | Name | Operates on | Severity | What it validates |
|---|---|---|---|---|
| G-001 | Domain/codomain matching | `SystemIR` | ERROR | Covariant wiring label matches source out or target in |
| G-002 | Signature completeness | `SystemIR` | ERROR | Every block has at least one input and one output |
| G-003 | Direction consistency | `SystemIR` | ERROR | No flag contradictions; contravariant port-slot matching |
| G-004 | Dangling wirings | `SystemIR` | ERROR | Wiring endpoints exist in the block/input set |
| G-005 | Sequential type compatibility | `SystemIR` | ERROR | Stack wiring label matches both source out AND target in |
| G-006 | Covariant acyclicity | `SystemIR` | ERROR | Forward flow graph is a DAG (no algebraic loops) |
| SC-001 | Completeness | `GDSSpec` | WARNING | Every entity variable updated by some mechanism |
| SC-002 | Determinism | `GDSSpec` | ERROR | No variable updated by multiple mechanisms in same wiring |
| SC-003 | Reachability | `GDSSpec` | WARNING | Signal path exists between two named blocks |
| SC-004 | Type safety | `GDSSpec` | ERROR | Wire space references resolve to registered spaces |
| SC-005 | Parameter references | `GDSSpec` | ERROR | Block `params_used` match registered parameter names |
| SC-006 | Canonical wellformedness (f) | `GDSSpec` | WARNING | At least one mechanism exists (f is non-empty) |
| SC-007 | Canonical wellformedness (X) | `GDSSpec` | WARNING | At least one state variable exists (X is non-empty) |
