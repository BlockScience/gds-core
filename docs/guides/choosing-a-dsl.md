# Choosing a DSL

Five domain-specific languages compile to the same GDS core. This guide helps you pick the right one for your problem -- or decide when to use the framework directly.

---

## Starting from the Problem

The Decision Matrix below is a technical reference — it assumes you already know your primitives. In practice, most modelers start earlier: with a domain question.

The same system can often be modeled with more than one DSL. An epidemic could be stockflow (if you care about accumulation rates) or raw framework (if you just need a state transition). A supply chain could be stockflow (stocks and flows), CLD (causal influences), or SCN (inventory and topology). The DSL choice depends on **what you want to verify**, not just what domain you are in.

The natural workflow is: **Problem → What do I want to check? → DSL**. Once you pick a DSL, roles and block structure follow more naturally because the DSL embeds domain conventions about what matters.

---

## Decision Matrix

| If your system has... | Use | Package | Why |
|---|---|---|---|
| Stocks accumulating over time | **gds-domains** | `gds_domains.stockflow` | Native stock/flow/auxiliary semantics with accumulation dynamics |
| State-space dynamics (A, B, C, D matrices) | **gds-domains** | `gds_domains.control` | Control theory mapping with sensors, controllers, plant states |
| Strategic agents making decisions | **gds-domains** | `gds_domains.games` | Game-theoretic composition with utility/payoff channels |
| Software architecture to formalize | **gds-domains** | `gds_domains.software` | Six diagram types: DFD, SM, Component, C4, ERD, Dependency |
| Business processes or supply chains | **gds-domains** | `gds_domains.business` | Causal loop, supply chain network, value stream mapping |
| None of the above | **gds-framework** | `gds` | Build your own vocabulary on the composition algebra |

---

## DSL Profiles

### gds-domains (stockflow)

**Domain:** System dynamics -- stocks, flows, auxiliaries, converters.

**Best for:** Accumulation dynamics, resource pools, population models, anything modeled with stock-flow diagrams.

**Example:** SIR epidemic model, Lotka-Volterra predator-prey, inventory management.

```python
from gds_domains.stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from gds_domains.stockflow.dsl.model import StockFlowModel

model = StockFlowModel(
    name="Population",
    stocks=[Stock(name="Population", initial=1000.0, non_negative=True)],
    flows=[
        Flow(name="births", target="Population"),
        Flow(name="deaths", source="Population"),
    ],
    converters=[Converter(name="birth_rate"), Converter(name="death_rate")],
    auxiliaries=[
        Auxiliary(name="net_growth", inputs=["birth_rate", "death_rate"]),
    ],
)
```

**Canonical form:** `h = f . g` with |X| = number of stocks, |f| = number of accumulation mechanisms.

**Domain checks:** SF-001 (orphan stocks), SF-003 (auxiliary cycles), SF-004 (unused converters), plus 2 more.

---

### gds-domains (control)

**Domain:** Feedback control systems -- states, inputs, sensors, controllers.

**Best for:** Thermostat-like control loops, PID controllers, any system with plant state, measurement, and actuation.

**Example:** Temperature regulation, resource level tracking, robotic control.

```python
from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.control.dsl.model import ControlModel

model = ControlModel(
    name="Thermostat",
    states=[State(name="temperature", initial=20.0)],
    inputs=[Input(name="heater")],
    sensors=[Sensor(name="temp_sensor", observes=["temperature"])],
    controllers=[
        Controller(name="pid", reads=["temp_sensor", "heater"], drives=["temperature"]),
    ],
)
```

**Canonical form:** `h = f . g` with |X| = number of states, full dynamical character.

**DSL element mapping:** State -> Mechanism + Entity, Input -> BoundaryAction, Sensor -> Policy, Controller -> Policy.

---

### gds-domains (games / OGS)

**Domain:** Game theory -- strategic interactions, decision games, payoff computation.

**Best for:** Multi-agent decision problems, mechanism design, auction theory, commons dilemmas.

**Example:** Prisoner's dilemma, resource extraction games, insurance contracts.

```python
from gds_domains.games.dsl.games import CovariantFunction, DecisionGame
from gds_domains.games.dsl.pattern import Pattern, PatternInput
from gds_domains.games.dsl.types import InputType, Signature, port

agent = DecisionGame(
    name="Player",
    signature=Signature(
        x=(port("Resource Signal"),),
        y=(port("Extraction Decision"),),
        r=(port("Player Payoff"),),
    ),
    logic="Choose extraction amount",
)
```

**Canonical form:** `h = g` (stateless -- no mechanisms, no state). All game blocks map to Policy.

**Key difference:** OGS uses `OpenGame` (a subclass of `AtomicBlock`) with its own `PatternIR`, which projects back to `SystemIR` via `PatternIR.to_system_ir()`. It also has backward (contravariant) channels for utility signals.

---

### gds-domains (software)

**Domain:** Software architecture -- six diagram types for formalizing system structure.

**Best for:** Documenting and verifying software architectures, data flows, state machines, component interactions.

**Diagram types:**

| Type | What it models |
|------|----------------|
| DFD (Data Flow Diagram) | Processes, data stores, external entities |
| SM (State Machine) | States and transitions |
| Component | Provided/required interfaces |
| C4 | Context, container, component views |
| ERD (Entity-Relationship) | Data model relationships |
| Dependency | Module dependencies |

```python
from gds_domains.software.dsl.elements import DFDProcess, DFDDataStore, DFDExternalEntity
from gds_domains.software.dsl.model import SoftwareModel

model = SoftwareModel(
    name="Order System",
    diagram_type="dfd",
    processes=[DFDProcess(name="Process Order")],
    data_stores=[DFDDataStore(name="Order DB")],
    external_entities=[DFDExternalEntity(name="Customer")],
)
```

**Canonical form:** Varies by diagram type. DFD with data stores has state (|X| > 0). ERD and Dependency are typically stateless.

**Domain checks:** 27 checks across all six diagram types.

---

### gds-domains (business)

**Domain:** Business dynamics -- causal loops, supply chains, value streams.

**Best for:** Business process modeling, supply chain optimization, value stream analysis.

**Diagram types:**

| Type | What it models |
|------|----------------|
| CLD (Causal Loop Diagram) | Reinforcing/balancing feedback loops |
| SCN (Supply Chain Network) | Nodes, links, inventory accumulation |
| VSM (Value Stream Map) | Process steps, buffers, cycle times |

```python
from gds_domains.business.cld.elements import Variable, CausalLink
from gds_domains.business.cld.model import CLDModel

model = CLDModel(
    name="Market Dynamics",
    variables=[Variable(name="Demand"), Variable(name="Price"), Variable(name="Supply")],
    links=[
        CausalLink(source="Demand", target="Price", polarity="+"),
        CausalLink(source="Price", target="Supply", polarity="+"),
        CausalLink(source="Supply", target="Demand", polarity="-"),
    ],
)
```

**Canonical form:** CLD is stateless (`h = g`). SCN has full dynamics (`h = f . g`). VSM is stateful only with buffers.

**Domain checks:** 11 checks across all three diagram types.

---

## Feature Comparison

### State and Canonical Form

| DSL | Has State? | Canonical Form | Character |
|-----|-----------|----------------|-----------|
| gds-domains (stockflow) | Yes (stocks) | `h = f . g` | Dynamical -- state-dominant accumulation |
| gds-domains (control) | Yes (plant states) | `h = f . g` | Dynamical -- full feedback control |
| gds-domains (games) | No | `h = g` | Strategic -- pure policy computation |
| gds-domains (software) | Varies by diagram | Varies | Diagram-dependent |
| gds-domains (business CLD) | No | `h = g` | Stateless -- pure signal relay |
| gds-domains (business SCN) | Yes (inventory) | `h = f . g` | Dynamical -- inventory accumulation |
| gds-domains (business VSM) | Optional (buffers) | Varies | Stateful only with buffers |

!!! note "The canonical spectrum"
    All DSLs compile to the same `h = f . g` decomposition with varying dimensionality of the state space X. When |X| = 0, the system is stateless and `h = g`. When both |f| > 0 and |g| > 0, the system is fully dynamical. GDS is a **unified transition calculus** -- not just a dynamical systems framework.

### GDS Role Mapping

Every DSL maps its elements to the same four GDS roles:

| GDS Role | stockflow | control | games | software | business |
|----------|-----------|---------|-------|----------|----------|
| BoundaryAction | Converter | Input | PatternInput | External entity | External source |
| Policy | Flow, Auxiliary | Sensor, Controller | All game types | Process, Transform | Variable, Link |
| Mechanism | Accumulation | State Dynamics | (none) | Data store update | Inventory update |
| ControlAction | (unused) | (unused) | (unused) | (unused) | (unused) |

!!! warning
    `ControlAction` is unused across all five DSLs. Use `Policy` for all decision, observation, and control logic.

### Verification Depth

| DSL | Domain Checks | Generic (G-series) | Semantic (SC-series) |
|-----|---------------|---------------------|---------------------|
| gds-domains (stockflow) | 5 (SF-001..SF-005) | 6 (via SystemIR) | 7 (via GDSSpec) |
| gds-domains (control) | Domain validation | 6 (via SystemIR) | 7 (via GDSSpec) |
| gds-domains (games) | OGS-specific | 6 (via SystemIR) | 7 (via GDSSpec) |
| gds-domains (software) | 27 across 6 diagrams | 6 (via SystemIR) | 7 (via GDSSpec) |
| gds-domains (business) | 11 across 3 diagrams | 6 (via SystemIR) | 7 (via GDSSpec) |

---

## When to Use Raw gds-framework

Use the framework directly when:

1. **No DSL vocabulary fits.** Your domain does not map cleanly to stocks/flows, control loops, games, software diagrams, or business processes.

2. **You need custom block roles.** The existing roles (BoundaryAction, Policy, Mechanism) work, but you want domain-specific naming or constraints.

3. **You are exploring a new domain.** Build a prototype with raw blocks and composition, then decide if a DSL would help.

```python
from gds import (
    BoundaryAction,
    GDSSpec,
    Mechanism,
    Policy,
    compile_system,
    interface,
    verify,
)

# Build directly with the composition algebra
sensor = BoundaryAction(name="Sensor", interface=interface(forward_out=["Reading"]))
logic = Policy(name="Logic", interface=interface(forward_in=["Reading"], forward_out=["Command"]))
actuator = Mechanism(
    name="Actuator",
    interface=interface(forward_in=["Command"]),
    updates=[("Plant", "value")],
)

system = sensor >> logic >> actuator
system_ir = compile_system("Custom System", root=system)
report = verify(system_ir)
```

!!! tip
    If you find yourself repeating the same pattern across multiple raw-framework models, that is a signal to consider creating a DSL. All five existing DSLs started as repeated patterns that were factored into a compiler.

---

## Cross-DSL Interoperability

All DSLs compile to `GDSSpec`, which means you can:

1. **Compare models across DSLs** -- the canonical `h = f . g` decomposition works on any spec, regardless of which DSL produced it.

2. **Use the same verification pipeline** -- generic checks (G-001..G-006) and semantic checks (SC-001..SC-007) work on any compiled system or spec.

3. **Query any spec with SpecQuery** -- parameter influence, entity update maps, and dependency graphs work uniformly.

```python
from gds import SpecQuery, project_canonical

# Same analysis works regardless of which DSL compiled the spec
canonical = project_canonical(spec)
query = SpecQuery(spec)

print(f"State dimension: {len(canonical.state_space)}")
print(f"Mechanism count: {len(canonical.mechanisms)}")
print(f"Policy count: {len(canonical.policies)}")
```

For a concrete example of the same problem modeled through three different DSL lenses, see the [Rosetta Stone](rosetta-stone.md) guide.

---

## Summary

| Question | Answer |
|----------|--------|
| "I have accumulating stocks" | Use **gds-domains** (stockflow) |
| "I have feedback control loops" | Use **gds-domains** (control) |
| "I have strategic agents" | Use **gds-domains** (games) |
| "I have software to document" | Use **gds-domains** (software) |
| "I have business processes" | Use **gds-domains** (business) |
| "None of these fit" | Use **gds-framework** directly |
| "I want to compare across domains" | All compile to **GDSSpec** -- use the canonical decomposition |
