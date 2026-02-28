# Verification

`gds-business` provides 11 domain-specific verification checks across three diagram types, plus access to the 6 GDS generic checks (G-001..G-006) via the unified `verify()` function.

## Using verify()

The `verify()` function auto-dispatches to the correct domain checks based on model type:

```python
from gds_business import verify

report = verify(model)                          # Domain + GDS checks
report = verify(model, include_gds_checks=False)  # Domain checks only
report = verify(model, domain_checks=[my_check])  # Custom checks
```

The returned `VerificationReport` contains a list of `Finding` objects with:

- `check_id` — e.g., "CLD-001", "SCN-002", "G-003"
- `severity` — ERROR, WARNING, or INFO
- `message` — human-readable description
- `passed` — whether the check passed
- `source_elements` — elements involved

## CLD Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| CLD-001 | Loop polarity classification | INFO | Finds all cycles, classifies as Reinforcing (R) or Balancing (B) by counting negative links |
| CLD-002 | Variable reachability | WARNING | Every variable appears in at least one link |
| CLD-003 | No self-loops | ERROR | No link has source == target |

### CLD-001: Loop Polarity

This is an **informational** check — it doesn't fail, but reports the structure of feedback loops:

```
[CLD-001] ✓ Loop Population -> Births -> Population: Reinforcing (R) (0 negative link(s))
[CLD-001] ✓ Loop Population -> Deaths -> Population: Balancing (B) (1 negative link(s))
```

### CLD-002: Variable Reachability

Flags isolated variables that don't participate in any causal relationship:

```
[CLD-002] ✗ Variable 'Unused' does NOT appear in any link
```

### CLD-003: No Self-Loops

Self-loops (a variable causing itself) are structurally invalid:

```
[CLD-003] ✗ Self-loop detected: 'X' -> 'X'
```

!!! note
    CLD-003 is also enforced at construction time by the `CausalLoopModel` validator. The check exists for completeness when running `verify()`.

## SCN Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| SCN-001 | Network connectivity | WARNING | All nodes reachable via BFS from demand/supply paths |
| SCN-002 | Shipment node validity | ERROR | source_node and target_node exist |
| SCN-003 | Demand target validity | ERROR | target_node exists |
| SCN-004 | No orphan nodes | WARNING | Every node in at least one shipment or demand |

### SCN-001: Network Connectivity

Uses BFS from demand targets to check reachability:

```
[SCN-001] ✗ Node 'Isolated Warehouse' is NOT reachable in the supply network
```

### SCN-004: No Orphan Nodes

Nodes not connected to any shipment or demand are flagged:

```
[SCN-004] ✗ Node 'Unused DC' is NOT connected
```

## VSM Checks

| ID | Name | Severity | What it checks |
|----|------|----------|----------------|
| VSM-001 | Linear process flow | WARNING | Each step has ≤1 incoming, ≤1 outgoing material flow |
| VSM-002 | Push/pull boundary | INFO | Identifies where flow_type transitions from push to pull |
| VSM-003 | Flow reference validity | ERROR | All flow source/target are declared elements |
| VSM-004 | Bottleneck vs takt | WARNING | Max cycle_time ≤ customer takt_time |

### VSM-001: Linear Process Flow

Value streams are typically linear. Branching may indicate modeling issues:

```
[VSM-001] ✗ Step 'Sorting': 1 incoming, 2 outgoing material flow(s) — non-linear (branching detected)
```

### VSM-002: Push/Pull Boundary

Lean manufacturing distinguishes push (schedule-driven) from pull (demand-driven) flows. This check identifies transition points:

```
[VSM-002] ✓ Push/pull boundary at 'Welding': push->pull
```

### VSM-004: Bottleneck vs Takt

The slowest process step (bottleneck) must not exceed customer takt time:

```
[VSM-004] ✗ Bottleneck 'Welding' (cycle_time=45.0) > customer 'End User' takt_time=40.0
```

## GDS Generic Checks

When `include_gds_checks=True` (default), the model is compiled to `SystemIR` and the 6 GDS generic checks run:

| ID | Name | What it checks |
|----|------|----------------|
| G-001 | Domain/codomain compatibility | Wiring type tokens match |
| G-002 | Signature completeness | Every block has inputs and outputs |
| G-003 | Unique block naming | No duplicate block names |
| G-004 | Wiring source existence | Wired blocks exist |
| G-005 | Wiring target existence | Wired blocks exist |
| G-006 | Hierarchy consistency | Block tree is well-formed |

!!! note
    G-002 will flag `BoundaryAction` blocks as having "no inputs" — this is expected since they are exogenous sources by design.
