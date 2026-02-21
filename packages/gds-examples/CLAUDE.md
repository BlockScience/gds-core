# Building GDS Models — Guide for Claude Code

Instructions for creating new example models in this directory.
Read `sir_epidemic/model.py` first — it's the most thoroughly documented.

## File Structure for a New Example

```
examples/
└── my_model/
    ├── __init__.py          # empty
    ├── model.py             # types, entities, spaces, blocks, build_spec(), build_system()
    ├── test_model.py        # tests for all layers
    └── generate_views.py    # visualization script (copy from sir_epidemic, adapt)
```

## Step-by-Step: Writing model.py

Follow this exact order. Each section builds on the previous one.

### 1. Module Docstring

Include: one-line summary, composition pattern, Concepts Covered, Prerequisites,
GDS Decomposition (X, U, g, f, Θ).

### 2. Types (TypeDef)

Define value constraints BEFORE anything that references them.

```python
from gds import typedef

Count = typedef("Count", int,
    constraint=lambda x: x >= 0,
    description="Non-negative count")
```

The `typedef()` helper takes positional name + type, keyword-only rest. It returns a standard `TypeDef`.

<details>
<summary>Verbose equivalent (without helper)</summary>

```python
from gds.types.typedef import TypeDef

Count = TypeDef(
    name="Count",
    python_type=int,
    constraint=lambda x: x >= 0,
    description="Non-negative count",
)
```
</details>

**Rules:**
- `python_type` is required — used for `isinstance` check
- `constraint` is optional — must be a `Callable[[Any], bool]`
- `constraint` must not raise exceptions (return False instead)
- Names must be unique within a spec (duplicate registration raises ValueError)
- TypeDef is frozen (immutable after creation)

### 3. Entities (Entity + StateVariable)

Define the state space X — what persists across timesteps.

```python
from gds import entity, state_var

agent = entity("Agent",
    wealth=state_var(Currency, symbol="W"))
```

The `entity()` helper takes variables as kwargs — each key becomes the variable name. `state_var()` omits the name (resolved from the kwarg key by `entity()`).

<details>
<summary>Verbose equivalent (without helpers)</summary>

```python
from gds.state import Entity, StateVariable

agent = Entity(
    name="Agent",
    variables={
        "wealth": StateVariable(name="wealth", typedef=Currency, symbol="W"),
    },
)
```
</details>

**Rules:**
- `symbol` is purely for documentation/math notation — never validated or used in compilation
- With the verbose form, variable dict keys must match the `StateVariable.name` (by convention); `entity()` handles this automatically
- Entity inherits from `Tagged` — can have tags
- Entity is frozen

### 4. Spaces (Space)

Define typed communication channels — transient signals within a timestep, NOT state.

```python
from gds import space

signal = space("TransferSignal",
    amount=Currency, recipient=AgentID)
```

The `space()` helper takes fields as kwargs (values are TypeDef instances).

<details>
<summary>Verbose equivalent (without helper)</summary>

```python
from gds.spaces import Space

signal = Space(
    name="TransferSignal",
    fields={"amount": Currency, "recipient": AgentID},
)
```
</details>

**Rules:**
- Field values must be TypeDef instances (not Python types)
- Space names must be unique within a spec
- Space is frozen
- `validate_data()` is strict — rejects extra fields (unlike Entity which ignores them)

### 5. Blocks

Define computational units with role-specific constraints.

#### Role Constraints (enforced at construction — immediate error)

| Role | `forward_in` | `forward_out` | `backward_in` | `backward_out` | `updates` |
|------|:---:|:---:|:---:|:---:|:---:|
| **BoundaryAction** | MUST be `()` | any | any | any | — |
| **Policy** | any | any | any | any | — |
| **ControlAction** | any | any | any | any | — |
| **Mechanism** | any | any | MUST be `()` | MUST be `()` | list of (entity, var) |

Violating the MUST constraints raises `GDSCompositionError` immediately.

#### Port Creation

```python
from gds import interface

block = Policy(
    name="My Policy",
    interface=interface(
        forward_in=["Input Signal"],
        forward_out=["Output A", "Output B"],
    ),
    params_used=["rate", "threshold"],         # references to Θ
    tags={"domain": "Control"},
)
```

The `interface()` helper accepts lists of strings instead of tuples of Port objects. Each string is auto-converted to a Port via `port()`. No more trailing-comma single-element tuples.

<details>
<summary>Verbose equivalent (without helper)</summary>

```python
from gds.types.interface import Interface, port

block = Policy(
    name="My Policy",
    interface=Interface(
        forward_in=(port("Input Signal"),),    # trailing comma for single-element tuple
        forward_out=(port("Output A"), port("Output B")),
    ),
    params_used=["rate", "threshold"],
    tags={"domain": "Control"},
)
```
</details>

**Rules:**
- Port names auto-tokenize: splits on spaces, lowercases → frozenset of tokens
- Port name tokens drive auto-wiring: `>>` matches by token overlap between forward_out and forward_in
- Use descriptive port names — they become wiring labels in diagrams

#### Mechanism Updates

```python
update = Mechanism(
    name="Update Agent",
    interface=interface(forward_in=["Transfer Result"]),
    updates=[("Agent", "wealth")],  # list of (entity_name, variable_name)
)
```

**Rules:**
- Tuples reference entity name and variable name as strings (validated at spec level, not construction)
- A Mechanism with empty updates is allowed but suspicious
- Multiple updates to different entities from one Mechanism is fine (see Payoff Realization in prisoners_dilemma)

#### Mechanism with forward_out (for temporal loops)

Mechanisms CAN have `forward_out` — this is how `.loop()` works.
The mechanism updates state AND emits a signal for the next timestep.

```python
update = Mechanism(
    name="Update Prey",
    interface=interface(
        forward_in=["Prey Rate"],
        forward_out=["Population Signal"],  # enables .loop()
    ),
    updates=[("Prey", "population")],
)
```

### 6. build_spec() → GDSSpec

Register everything into a single spec using `collect()`, which type-dispatches each object
to the right `register_*()` call. Registration order doesn't matter for correctness.

```python
def build_spec() -> GDSSpec:
    spec = GDSSpec(name="My Model", description="...")

    spec.collect(
        Currency, RateType,           # TypeDefs
        signal,                       # Spaces
        agent,                        # Entities
        my_block,                     # Blocks
    )

    # Wirings and parameters with shorthand names stay explicit
    spec.register_parameter("rate", RateType)
    spec.register_wiring(
        SpecWiring(
            name="Main Pipeline",
            block_names=["Block A", "Block B"],
            wires=[
                Wire(source="Block A", target="Block B", space="SignalSpace"),
            ],
        )
    )
    return spec
```

`collect()` handles TypeDef, Space, Entity, Block, and ParameterDef objects. SpecWiring and
`(name, typedef)` parameter shorthand stay explicit via `register_wiring()` / `register_parameter()`.

<details>
<summary>Verbose equivalent (without collect)</summary>

```python
spec.register_type(Currency)
spec.register_type(RateType)
spec.register_space(signal)
spec.register_entity(agent)
spec.register_block(my_block)
spec.register_parameter("rate", RateType)
```
</details>

**Rules:**
- Duplicate names raise ValueError at registration time
- Wire source/target/space are strings — validated only by `spec.validate_spec()`, not at registration
- `block_names` in SpecWiring is for documentation — not strictly enforced at registration
- `register_parameter` accepts either `ParameterDef` or `(name_str, typedef)` shorthand
- `params_used` on blocks must match registered parameter names (case-sensitive!)

### 7. build_system() → SystemIR

Compose blocks and compile.

```python
def build_system() -> SystemIR:
    pipeline = boundary >> policy >> mechanism
    return compile_system(name="My Model", root=pipeline)
```

## Composition Operators

### `>>` (Sequential / StackComposition)

Chains blocks: output of left feeds input of right.

**Auto-wiring rule:** Matches `forward_out` ports to `forward_in` ports by token overlap.
If tokens don't overlap and both sides have ports, raises `GDSTypeError`.

```python
# "Contact Signal" tokens = {"contact", "signal"}
# If next block has forward_in with overlapping tokens, auto-wires
a >> b >> c  # left-associative: (a >> b) >> c
```

### `|` (Parallel / ParallelComposition)

Runs blocks side-by-side. No validation — blocks are independent.

```python
updates = update_a | update_b | update_c
```

### `.feedback()` (FeedbackLoop)

Within-timestep backward flow. Requires explicit `Wiring` with `CONTRAVARIANT` direction.

**The source block needs `backward_out`, the target block needs `backward_in`.**

```python
pipeline = a >> b >> c
system = pipeline.feedback([
    Wiring(
        source_block="C",      source_port="Cost Signal",
        target_block="B",      target_port="Cost Signal",
        direction=FlowDirection.CONTRAVARIANT,
    )
])
```

### `.loop()` (TemporalLoop)

Cross-timestep forward flow. Requires explicit `Wiring` with `COVARIANT` direction.

**COVARIANT is mandatory** — using CONTRAVARIANT raises `GDSTypeError` immediately.

**The source block needs `forward_out`, the target block needs `forward_in`.**

```python
system = pipeline.loop(
    [
        Wiring(
            source_block="Update",   source_port="Population",
            target_block="Compute",  target_port="Population",
            direction=FlowDirection.COVARIANT,
        )
    ],
    exit_condition="converged",  # optional string label
)
```

## Common Mistakes

### Construction-time errors (immediate crash)

```python
# ❌ BoundaryAction with forward_in → GDSCompositionError
BoundaryAction(name="Bad", interface=interface(forward_in=["X"]))

# ❌ Mechanism with backward ports → GDSCompositionError
Mechanism(name="Bad", interface=interface(backward_in=["X"]))

# ❌ >> with no token overlap → GDSTypeError
port_a = port("Temperature")   # tokens: {"temperature"}
port_b = port("Pressure")      # tokens: {"pressure"}
block_a >> block_b              # no overlap → error

# ❌ .loop() with CONTRAVARIANT → GDSTypeError
pipeline.loop([Wiring(..., direction=FlowDirection.CONTRAVARIANT)])
```

### Registration-time errors (at register call)

```python
# ❌ Duplicate name → ValueError
spec.register_type(Count)
spec.register_type(Count)  # "Type 'Count' already registered"
```

### Validation-time errors (at validate_spec)

```python
# ❌ Mechanism references non-existent entity
Mechanism(name="M", updates=[("Ghost", "x")])
spec.register_block(m)
spec.validate_spec()  # "Mechanism 'M' updates unknown entity 'Ghost'"

# ❌ Block references unregistered parameter (case-sensitive!)
Policy(name="P", params_used=["Rate"])  # capital R
spec.register_parameter("rate", RateType)  # lowercase r
spec.validate_spec()  # "Block 'P' references unregistered parameter 'Rate'"

# ❌ Wire references unregistered space
Wire(source="A", target="B", space="NonExistentSpace")
spec.validate_spec()  # error
```

### Silent issues (no error, but wrong)

```python
# ⚠️ Mechanism with no updates — compiles fine but does nothing
Mechanism(name="Noop", interface=interface(forward_in=["X"]), updates=[])

# ⚠️ Entity variable never updated — SC-001 warning, not error
# (register entity with variables but no mechanism updates them)

# ⚠️ Duplicate ports in interface — allowed but confusing
interface(forward_out=["X", "X"])  # two identical ports

# ⚠️ Tags have no effect on compilation or verification
# Don't rely on tags for correctness — they're stripped at compile time
```

## Writing Tests (test_model.py)

Follow the pattern in `sir_epidemic/test_model.py`. Test every layer:

```python
class TestTypes:
    # TypeDef.check_value() for valid/invalid/boundary values

class TestEntities:
    # Entity.validate_state() with good/bad/missing data

class TestBlocks:
    # isinstance checks for roles
    # Interface port counts
    # Mechanism.updates targets

class TestComposition:
    # Composition tree builds without error
    # flatten() yields expected block count
    # Token overlap exists for >> pairs

class TestSpec:
    # build_spec().validate_spec() == []
    # Entity/block/parameter counts
    # Parameter names match expected set

class TestVerification:
    # build_system() compiles
    # Generic checks pass (G-001, G-003..G-006; skip G-002 for boundary/terminal blocks)
    # Semantic checks pass (completeness, determinism, type_safety)
    # Reachability from boundary to terminal

class TestQuery:
    # SpecQuery.param_to_blocks() — parameter influence
    # SpecQuery.entity_update_map() — mechanism targets
    # SpecQuery.blocks_by_kind() — role counts
    # SpecQuery.blocks_affecting(entity, var) — causal chain
```

**G-002 note:** Skip `check_g002_signature_completeness` — it flags BoundaryActions (no inputs)
and terminal Mechanisms (no outputs) as errors, which is expected for valid GDS models.

## Visualization (generate_views.py)

Copy from any existing example and adapt. Key customization points:

```python
TITLE = "My Model"
TRACE_ENTITY = "Agent"      # most interesting entity for View 6
TRACE_VARIABLE = "wealth"   # most interesting variable to trace
TRACE_SYMBOL = "W"          # mathematical symbol
```

The 6 views are:
1. **Structural** — compiled block graph (SystemIR)
2. **Canonical** — X_t → U → g → f → X_{t+1} (CanonicalGDS)
3. **Architecture by Role** — blocks grouped by GDS role (GDSSpec)
4. **Architecture by Domain** — blocks grouped by domain tag (GDSSpec)
5. **Parameter Influence** — Θ → blocks → entities (GDSSpec)
6. **Traceability** — backwards trace from one state variable (GDSSpec)

Run: `uv run python examples/my_model/generate_views.py --save`

## Design Decisions to Make

When designing a new model, decide:

1. **What is state (X) vs. signal?** State persists across timesteps (Entity/StateVariable).
   Signals are transient within a timestep (Space). If in doubt, it's probably a signal.

2. **What is a parameter (Θ) vs. exogenous input (U)?** Parameters are fixed for a simulation
   run. Exogenous inputs can vary per timestep. Model parameters with `register_parameter`;
   model exogenous inputs with `BoundaryAction`.

3. **Which composition operator?**
   - Linear pipeline → `>>`
   - Independent parallel blocks → `|`
   - Within-timestep backward info → `.feedback()` with CONTRAVARIANT
   - Cross-timestep iteration → `.loop()` with COVARIANT

4. **ControlAction vs. Policy?** Policy is the core decision function (g).
   ControlAction is an admissibility/constraint enforcer (d) — it limits what
   actions are allowed. If unsure, use Policy.

5. **One Mechanism per entity vs. multi-entity Mechanism?** Prefer one mechanism
   per entity for clarity. Multi-entity mechanisms (like prisoners_dilemma's
   Payoff Realization) are valid but harder to reason about.

## Reference: Existing Examples by Complexity

| Example | Roles Used | Operators | Key Teaching Point |
|---------|-----------|-----------|-------------------|
| `sir_epidemic` | BA, P, M | `>>`, `\|` | Fundamentals, 3-role pipeline |
| `insurance` | BA, P, CA, M | `>>` | ControlAction, complete 4-role taxonomy |
| `thermostat` | BA, P, CA, M | `>>`, `.feedback()` | CONTRAVARIANT backward flow |
| `lotka_volterra` | BA, P, M | `>>`, `\|`, `.loop()` | COVARIANT temporal loops |
| `prisoners_dilemma` | BA, P, M | `\|`, `>>`, `.loop()` | Nested parallel, multi-entity |
