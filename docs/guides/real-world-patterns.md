# Real-World Patterns

GDS examples like SIR epidemic and thermostat demonstrate the theory well, but production systems need different patterns. This guide shows how to model common software engineering concerns — data pipelines, state machines, human-in-the-loop workflows, and large type systems — using the GDS composition algebra.

Every example below is complete and runnable. Import, build, verify.

---

## Pattern 1: Data Pipeline (ETL)

**Use case:** An ingestion service reads raw records from an external source, validates and transforms them, then writes clean data to a store. This is the bread and butter of backend systems — ETL, event processing, message consumers.

**GDS mapping:**

- `BoundaryAction` — the data arrives from outside the system (an API, a queue, a file)
- `Policy` — validation and transformation logic (pure decision: accept, reject, reshape)
- `Mechanism` — the only thing that writes state (the persisted dataset)

```python
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    compile_system,
    entity,
    interface,
    space,
    state_var,
    typedef,
    verify,
)

# ── Types ──────────────────────────────────────────────────
# TypeDefs with constraints enforce data quality at the type level.
# These aren't just labels — check_value() validates real data.

RawPayload = typedef("RawPayload", str, description="Unvalidated JSON string")

CleanRecord = typedef(
    "CleanRecord",
    dict,
    constraint=lambda x: "id" in x and "amount" in x,
    description="Validated record with required fields",
)

RecordCount = typedef(
    "RecordCount",
    int,
    constraint=lambda x: x >= 0,
    description="Running count of ingested records",
)

SuccessFlag = typedef(
    "SuccessFlag",
    bool,
    description="Whether the record passed validation",
)

# ── Entity ─────────────────────────────────────────────────
# State that persists across pipeline runs. The dataset is the
# accumulator — every successful record increments the count.

dataset = entity(
    "Dataset",
    record_count=state_var(RecordCount, symbol="N"),
)

# ── Spaces ─────────────────────────────────────────────────
# Transient signals flowing through the pipeline within one run.

raw_space = space("RawIngestion", payload=RawPayload)
validated_space = space("ValidatedRecord", record=CleanRecord, valid=SuccessFlag)
write_space = space("WriteCommand", record=CleanRecord)

# ── Blocks ─────────────────────────────────────────────────

ingest = BoundaryAction(
    name="Data Ingest",
    interface=interface(forward_out=["Raw Ingestion"]),
)

validate_transform = Policy(
    name="Validate Transform",
    interface=interface(
        forward_in=["Raw Ingestion"],
        forward_out=["Write Command"],
    ),
    params_used=["schema_version"],
)

persist_record = Mechanism(
    name="Persist Record",
    interface=interface(forward_in=["Write Command"]),
    updates=[("Dataset", "record_count")],
)

# ── Spec ───────────────────────────────────────────────────

def build_etl_spec() -> GDSSpec:
    spec = GDSSpec(name="ETL Pipeline", description="Ingest → validate → persist")

    spec.collect(
        RawPayload, CleanRecord, RecordCount, SuccessFlag,
        raw_space, validated_space, write_space,
        dataset,
        ingest, validate_transform, persist_record,
    )

    spec.register_parameter("schema_version", typedef("SchemaVersion", int))

    spec.register_wiring(SpecWiring(
        name="Ingestion Flow",
        block_names=["Data Ingest", "Validate Transform", "Persist Record"],
        wires=[
            Wire(source="Data Ingest", target="Validate Transform", space="RawIngestion"),
            Wire(source="Validate Transform", target="Persist Record", space="WriteCommand"),
        ],
    ))

    errors = spec.validate_spec()
    assert errors == [], f"Spec validation failed: {errors}"
    return spec

# ── System ─────────────────────────────────────────────────

def build_etl_system():
    pipeline = ingest >> validate_transform >> persist_record
    return compile_system(name="ETL Pipeline", root=pipeline)
```

**Why this decomposition matters:** The Policy block contains all the validation logic but has no access to state. It cannot write to the dataset — only the Mechanism can. This separation is exactly what you want in a data pipeline: the transform step is pure, testable, and replaceable. If your validation rules change, only the Policy changes. The ingestion source (BoundaryAction) and the persistence logic (Mechanism) are stable.

---

## Pattern 2: State Machine

**Use case:** An order progresses through a lifecycle: `PENDING` → `APPROVED` or `REJECTED`. Only valid transitions are allowed. This pattern appears in every workflow engine, approval system, and document lifecycle.

**GDS mapping:**

- `TypeDef` with a constraint — the status enum is a constrained string type
- `Policy` — encodes the transition table (which transitions are valid)
- `Mechanism` — applies the validated transition to state

```python
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    compile_system,
    entity,
    interface,
    space,
    state_var,
    typedef,
    verify,
)

# ── Types ──────────────────────────────────────────────────
# The status type constrains values to a known set. The
# constraint lambda replaces a traditional enum check.

VALID_STATUSES = {"PENDING", "APPROVED", "REJECTED", "CANCELLED"}

OrderStatus = typedef(
    "OrderStatus",
    str,
    constraint=lambda x: x in VALID_STATUSES,
    description="Order lifecycle status",
)

OrderID = typedef("OrderID", str, description="Unique order identifier")

TransitionRequest = typedef(
    "TransitionRequest",
    str,
    constraint=lambda x: x in VALID_STATUSES,
    description="Requested target status",
)

TransitionValid = typedef(
    "TransitionValid",
    bool,
    description="Whether the requested transition is allowed",
)

# ── Transition table ───────────────────────────────────────
# This is the business logic — which status transitions are
# allowed. Defined as data, referenced by the Policy block
# via params_used.

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"CANCELLED"},
    "REJECTED": set(),
    "CANCELLED": set(),
}

# ── Entity ─────────────────────────────────────────────────

order = entity(
    "Order",
    status=state_var(OrderStatus, symbol="S"),
)

# ── Spaces ─────────────────────────────────────────────────

request_space = space("TransitionRequest", order_id=OrderID, target_status=TransitionRequest)
decision_space = space("TransitionDecision", order_id=OrderID, new_status=OrderStatus, valid=TransitionValid)

# ── Blocks ─────────────────────────────────────────────────

receive_request = BoundaryAction(
    name="Receive Transition Request",
    interface=interface(forward_out=["Transition Request"]),
)

# The Policy block is where the transition table lives. It
# reads the requested transition and the current status,
# then decides whether to allow it. No state mutation here.
validate_transition = Policy(
    name="Validate Transition",
    interface=interface(
        forward_in=["Transition Request"],
        forward_out=["Transition Decision"],
    ),
    params_used=["transition_rules"],
)

apply_transition = Mechanism(
    name="Apply Transition",
    interface=interface(forward_in=["Transition Decision"]),
    updates=[("Order", "status")],
)

# ── Spec ───────────────────────────────────────────────────

def build_state_machine_spec() -> GDSSpec:
    spec = GDSSpec(
        name="Order State Machine",
        description="Status lifecycle with validated transitions",
    )

    spec.collect(
        OrderStatus, OrderID, TransitionRequest, TransitionValid,
        request_space, decision_space,
        order,
        receive_request, validate_transition, apply_transition,
    )

    # The transition rules are a parameter — they configure
    # the Policy but don't change the structural decomposition.
    TransitionRules = typedef("TransitionRules", dict, description="Allowed transition map")
    spec.register_parameter("transition_rules", TransitionRules)

    spec.register_wiring(SpecWiring(
        name="Order Lifecycle",
        block_names=[
            "Receive Transition Request",
            "Validate Transition",
            "Apply Transition",
        ],
        wires=[
            Wire(source="Receive Transition Request", target="Validate Transition", space="TransitionRequest"),
            Wire(source="Validate Transition", target="Apply Transition", space="TransitionDecision"),
        ],
    ))

    errors = spec.validate_spec()
    assert errors == [], f"Spec validation failed: {errors}"
    return spec

# ── System ─────────────────────────────────────────────────

def build_state_machine_system():
    pipeline = receive_request >> validate_transition >> apply_transition
    return compile_system(name="Order State Machine", root=pipeline)
```

**Design insight:** The transition table is a parameter, not hardcoded into the Policy. This means you can analyze the spec structurally — "which blocks depend on transition_rules?" — without executing the validation logic. The Mechanism only applies transitions that the Policy has already validated. State mutation is always guarded by a decision layer.

---

## Pattern 3: Human-in-the-Loop

**Use case:** A document requires human approval before it can be published. A reviewer reads the document, decides to approve or reject, and the system applies the decision. This pattern covers approval workflows, content moderation, manual QA gates.

**GDS mapping:**

- `BoundaryAction` — the human decision enters from outside the system boundary
- `Policy` — business rules that validate the approval (e.g., reviewer has authority)
- `Mechanism` — applies the approved decision to state

The key insight: the human reviewer is **outside the system boundary**. GDS models this naturally with `BoundaryAction` — the system does not control or predict what the human decides.

```python
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    compile_system,
    entity,
    interface,
    space,
    state_var,
    typedef,
    verify,
)

# ── Types ──────────────────────────────────────────────────

REVIEW_DECISIONS = {"APPROVE", "REJECT", "REQUEST_CHANGES"}

ReviewDecision = typedef(
    "ReviewDecision",
    str,
    constraint=lambda x: x in REVIEW_DECISIONS,
    description="Human reviewer's decision",
)

DOC_STATUSES = {"DRAFT", "IN_REVIEW", "APPROVED", "REJECTED", "CHANGES_REQUESTED"}

DocumentStatus = typedef(
    "DocumentStatus",
    str,
    constraint=lambda x: x in DOC_STATUSES,
    description="Document lifecycle status",
)

ReviewerID = typedef("ReviewerID", str, description="Reviewer identifier")
DocumentID = typedef("DocumentID", str, description="Document identifier")
ReviewNotes = typedef("ReviewNotes", str, description="Free-text reviewer comments")

# ── Entity ─────────────────────────────────────────────────

document = entity(
    "Document",
    status=state_var(DocumentStatus, symbol="S"),
)

# ── Spaces ─────────────────────────────────────────────────

# The human input space — what crosses the system boundary.
review_input_space = space(
    "ReviewInput",
    reviewer=ReviewerID,
    document=DocumentID,
    decision=ReviewDecision,
    notes=ReviewNotes,
)

# Internal decision space — after business rule validation.
validated_decision_space = space(
    "ValidatedDecision",
    document=DocumentID,
    new_status=DocumentStatus,
)

# ── Blocks ─────────────────────────────────────────────────

# BoundaryAction: the human reviewer. GDS treats this as an
# exogenous input — the system cannot predict or control
# what the reviewer decides. This is the right abstraction:
# the boundary separates "things we model" from "things we
# accept as given."
human_review = BoundaryAction(
    name="Human Review",
    interface=interface(forward_out=["Review Input"]),
    options=["APPROVE", "REJECT", "REQUEST_CHANGES"],
)

# Policy: validates the review against business rules.
# Does the reviewer have authority? Is the document in a
# reviewable state? The Policy answers these questions
# without touching state.
validate_review = Policy(
    name="Validate Review",
    interface=interface(
        forward_in=["Review Input"],
        forward_out=["Validated Decision"],
    ),
    params_used=["required_reviewer_role", "min_review_time"],
)

# Mechanism: the only block that writes state. Applies the
# validated decision to the document's status.
apply_review = Mechanism(
    name="Apply Review Decision",
    interface=interface(forward_in=["Validated Decision"]),
    updates=[("Document", "status")],
)

# ── Spec ───────────────────────────────────────────────────

def build_review_spec() -> GDSSpec:
    spec = GDSSpec(
        name="Document Review",
        description="Human-in-the-loop approval workflow",
    )

    spec.collect(
        ReviewDecision, DocumentStatus, ReviewerID, DocumentID, ReviewNotes,
        review_input_space, validated_decision_space,
        document,
        human_review, validate_review, apply_review,
    )

    RoleType = typedef("RoleType", str, description="Required reviewer role")
    DurationType = typedef("DurationType", int, constraint=lambda x: x >= 0, description="Minimum review time in seconds")
    spec.register_parameter("required_reviewer_role", RoleType)
    spec.register_parameter("min_review_time", DurationType)

    spec.register_wiring(SpecWiring(
        name="Review Pipeline",
        block_names=["Human Review", "Validate Review", "Apply Review Decision"],
        wires=[
            Wire(source="Human Review", target="Validate Review", space="ReviewInput"),
            Wire(source="Validate Review", target="Apply Review Decision", space="ValidatedDecision"),
        ],
    ))

    errors = spec.validate_spec()
    assert errors == [], f"Spec validation failed: {errors}"
    return spec

# ── System ─────────────────────────────────────────────────

def build_review_system():
    pipeline = human_review >> validate_review >> apply_review
    return compile_system(name="Document Review", root=pipeline)
```

**Why BoundaryAction for humans:** The GDS boundary is not just a modeling convenience — it is a formal claim about what the system controls. By placing the human reviewer outside the boundary, you state that the system does not model human cognition, bias, or decision-making. It only models what happens once a decision arrives. This is the correct abstraction for any system that interacts with humans, external APIs, or third-party services.

---

## Pattern 4: Large Enum Types

**Use case:** A system classifies items into one of many categories — product types, geographic regions, compliance codes. With dozens or hundreds of valid values, you need a pattern that keeps the type system manageable.

**GDS mapping:**

- `TypeDef` with `constraint=lambda x: x in VALID_SET` — validates membership in a set
- Organize large enum sets as module-level constants grouped by domain
- Reference the same TypeDef across multiple spaces and entities

```python
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    SpecWiring,
    Wire,
    compile_system,
    entity,
    interface,
    space,
    state_var,
    typedef,
    verify,
)

# ── Organizing large value sets ────────────────────────────
# Group valid values by domain. These are plain Python sets —
# GDS doesn't prescribe how you organize them, but convention
# matters when you have 50+ categories.

# Product categories — hierarchical naming keeps things navigable
ELECTRONICS = {"LAPTOP", "PHONE", "TABLET", "MONITOR", "KEYBOARD", "MOUSE"}
CLOTHING = {"SHIRT", "PANTS", "JACKET", "SHOES", "HAT", "SCARF"}
FURNITURE = {"DESK", "CHAIR", "BOOKSHELF", "TABLE", "CABINET"}
FOOD = {"PRODUCE", "DAIRY", "MEAT", "BAKERY", "FROZEN", "CANNED"}

ALL_CATEGORIES = ELECTRONICS | CLOTHING | FURNITURE | FOOD

# Warehouse zones
ZONES = {"ZONE_A", "ZONE_B", "ZONE_C", "ZONE_D", "ZONE_E", "COLD_STORAGE", "OVERSIZED"}

# Priority levels
PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "DEFERRED"}

# ── Types ──────────────────────────────────────────────────
# Each typedef validates against its set. The constraint is a
# membership check — O(1) for sets.

ProductCategory = typedef(
    "ProductCategory",
    str,
    constraint=lambda x: x in ALL_CATEGORIES,
    description=f"Product category ({len(ALL_CATEGORIES)} valid values)",
)

WarehouseZone = typedef(
    "WarehouseZone",
    str,
    constraint=lambda x: x in ZONES,
    description="Physical warehouse zone",
)

Priority = typedef(
    "Priority",
    str,
    constraint=lambda x: x in PRIORITIES,
    description="Processing priority level",
)

ItemID = typedef("ItemID", str, description="SKU or item identifier")

Quantity = typedef(
    "Quantity",
    int,
    constraint=lambda x: x > 0,
    description="Positive item quantity",
)

# ── Derived type: zone-category mapping ────────────────────
# Sometimes you need a compound constraint — "this category
# belongs in this zone." Define the mapping as data and
# reference it from a space or a Policy parameter.

ZONE_ASSIGNMENT: dict[str, str] = {
    **{cat: "ZONE_A" for cat in ELECTRONICS},
    **{cat: "ZONE_B" for cat in CLOTHING},
    **{cat: "ZONE_C" for cat in FURNITURE},
    **{cat: "COLD_STORAGE" for cat in {"PRODUCE", "DAIRY", "MEAT", "FROZEN"}},
    **{cat: "ZONE_D" for cat in {"BAKERY", "CANNED"}},
}

# ── Entity ─────────────────────────────────────────────────

inventory_item = entity(
    "InventoryItem",
    category=state_var(ProductCategory, symbol="C"),
    zone=state_var(WarehouseZone, symbol="Z"),
)

# ── Spaces ─────────────────────────────────────────────────

intake_space = space(
    "ItemIntake",
    item_id=ItemID,
    category=ProductCategory,
    quantity=Quantity,
)

classification_space = space(
    "ClassificationResult",
    item_id=ItemID,
    category=ProductCategory,
    zone=WarehouseZone,
    priority=Priority,
)

# ── Blocks ─────────────────────────────────────────────────

receive_item = BoundaryAction(
    name="Receive Item",
    interface=interface(forward_out=["Item Intake"]),
)

classify_and_route = Policy(
    name="Classify And Route",
    interface=interface(
        forward_in=["Item Intake"],
        forward_out=["Classification Result"],
    ),
    params_used=["zone_assignment_rules", "priority_rules"],
)

update_inventory = Mechanism(
    name="Update Inventory",
    interface=interface(forward_in=["Classification Result"]),
    updates=[("InventoryItem", "category"), ("InventoryItem", "zone")],
)

# ── Spec ───────────────────────────────────────────────────

def build_inventory_spec() -> GDSSpec:
    spec = GDSSpec(
        name="Inventory Classification",
        description="Categorize and route items to warehouse zones",
    )

    spec.collect(
        ProductCategory, WarehouseZone, Priority, ItemID, Quantity,
        intake_space, classification_space,
        inventory_item,
        receive_item, classify_and_route, update_inventory,
    )

    ZoneRules = typedef("ZoneRules", dict, description="Category-to-zone mapping")
    PriorityRules = typedef("PriorityRules", dict, description="Priority assignment rules")
    spec.register_parameter("zone_assignment_rules", ZoneRules)
    spec.register_parameter("priority_rules", PriorityRules)

    spec.register_wiring(SpecWiring(
        name="Intake Pipeline",
        block_names=["Receive Item", "Classify And Route", "Update Inventory"],
        wires=[
            Wire(source="Receive Item", target="Classify And Route", space="ItemIntake"),
            Wire(source="Classify And Route", target="Update Inventory", space="ClassificationResult"),
        ],
    ))

    errors = spec.validate_spec()
    assert errors == [], f"Spec validation failed: {errors}"
    return spec

# ── System ─────────────────────────────────────────────────

def build_inventory_system():
    pipeline = receive_item >> classify_and_route >> update_inventory
    return compile_system(name="Inventory Classification", root=pipeline)
```

**Patterns for scaling type systems:**

1. **Group constants by domain** — `ELECTRONICS`, `CLOTHING`, etc. Union them into `ALL_CATEGORIES` for the typedef constraint.
2. **Keep constraints as set membership** — `lambda x: x in VALID_SET` is O(1) and readable.
3. **Separate mapping data from types** — `ZONE_ASSIGNMENT` maps categories to zones but is not itself a TypeDef. It is a parameter value that the Policy block references.
4. **One TypeDef per semantic role** — even if `ProductCategory` and `WarehouseZone` are both constrained strings, they are different types because they mean different things. This lets GDS type-check spaces: a space field typed as `WarehouseZone` will not accept a raw `ProductCategory` value.

---

## Running verification

Every pattern above produces a valid spec and a compilable system. You can verify both layers:

```python
# Spec-level validation (structural)
spec = build_etl_spec()
errors = spec.validate_spec()
assert errors == []

# System-level verification (generic checks on compiled IR)
system = build_etl_system()
report = verify(system)
for finding in report.findings:
    print(f"[{finding.severity}] {finding.check_id}: {finding.message}")
```

The spec-level `validate_spec()` catches registration errors: unregistered types in spaces, missing blocks in wirings, mechanisms updating nonexistent entities, and unregistered parameter references.

The system-level `verify()` runs the six generic checks (G-001 through G-006) on the compiled IR, catching structural issues like domain/codomain mismatches, direction inconsistencies, dangling wirings, and cycles.

---

## Summary

| Pattern | BoundaryAction | Policy | Mechanism | Key Insight |
|---------|---------------|--------|-----------|-------------|
| ETL Pipeline | Data ingestion | Validate + transform | Write to store | Policy is pure; Mechanism is the only writer |
| State Machine | Transition request | Validate transitions | Apply status change | Transition table is a parameter, not hardcoded |
| Human-in-the-Loop | Human decision | Business rule check | Apply decision | Humans are outside the system boundary |
| Large Enum Types | Item intake | Classify + route | Update inventory | Group constants by domain; one TypeDef per role |

The recurring structure across all four patterns is the same three-tier pipeline:

```
BoundaryAction >> Policy >> Mechanism
```

This is not a coincidence. GDS decomposes every transition function as `h = f . g` — exogenous input enters at the boundary, decision logic lives in `g` (Policy), and state updates live in `f` (Mechanism). The patterns above show that this decomposition applies as naturally to order workflows and data pipelines as it does to epidemic models and thermostats.
