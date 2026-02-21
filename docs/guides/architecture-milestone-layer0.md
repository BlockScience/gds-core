# Milestone: Layer 0 Stabilization

## What Changed

Three structural gaps between the architecture document and the codebase have been closed, bringing Layer 0 (Composition Core) into formal alignment with the documented contract.

### 1. Typed `InputIR`

`SystemIR.inputs` changed from `list[dict[str, Any]]` (untyped) to `list[InputIR]` (typed Pydantic model).

```python
class InputIR(BaseModel, frozen=True):
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- Layer 0 defines only `name` + a generic `metadata` bag
- Domain packages store their richer fields in `metadata` when projecting to SystemIR
- OGS's `to_system_ir()` now produces `InputIR` objects (previously built raw dicts, silently dropping the `shape` field)
- `compile_system()` accepts an optional `inputs` parameter; Layer 0 never infers inputs
- G-004 (dangling wirings) now uses typed attribute access (`inp.name`) instead of defensive `isinstance(inp, dict)` guards

### 2. Real G-003 Direction Consistency

The G-003 check was previously a stub that always passed with INFO severity. It now validates:

**A) Flag consistency** (ERROR severity):

- COVARIANT + `is_feedback=True` is a contradiction (feedback implies contravariant)
- CONTRAVARIANT + `is_temporal=True` is a contradiction (temporal implies covariant)

**B) Contravariant port-slot matching** (ERROR severity):

- For CONTRAVARIANT wirings, the label must be a token-subset of the source's `backward_out` or the target's `backward_in`
- This complements G-001, which only covers covariant wirings

### 3. Unified `sanitize_id`

Five duplicated copies of `_sanitize_id` across two packages (with one variant using a subtly different regex) have been replaced by a single canonical `sanitize_id()` in `gds.ir.models`:

```python
def sanitize_id(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized
```

Exported from `gds.__init__` and used by both gds-framework and gds-games.

## Why It Matters

- **Layer 0 is now formally consistent with the architecture document.** Every IR model is typed, every generic check validates real invariants, and shared utilities are consolidated.
- **New DSL development can proceed with confidence.** Domain packages (e.g., `gds-stockflow`, `gds-control`) can depend on a stable, well-typed Layer 0 contract.
- **The OGS interop bridge is cleaner.** `PatternIR.to_system_ir()` produces fully typed IR with no data loss.

## Acceptance Criteria

- [x] `SystemIR.inputs` is `list[InputIR]` (not `list[dict]`)
- [x] G-003 detects flag contradictions and contravariant port-slot mismatches
- [x] G-004 recognizes `InputIR` names as valid wiring endpoints
- [x] `sanitize_id` has a single definition used by all packages
- [x] All tests pass: 373 (gds-framework) + 162 (gds-games) + 57 (gds-viz) + 168 (gds-examples)
- [x] Lint clean across all packages

## Downstream Impact

**gds-games:** OGS `to_system_ir()` now produces `InputIR` objects and includes the previously-dropped `shape` field in metadata. OGS visualization and verification code uses the canonical `sanitize_id`. No behavioral changes to OGS tests.

**Future DSLs:** Any new domain package can import `InputIR` and `sanitize_id` from `gds` and depend on a complete, typed Layer 0 IR.
