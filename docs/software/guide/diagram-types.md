# Diagram Types

`gds-software` supports six software architecture diagram types, each with its own element vocabulary, GDS mapping, and composition structure.

## Data Flow Diagram (DFD)

Data flow diagrams model **data movement** through a system -- processes transform data, external entities provide/consume it, and data stores persist it.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `ExternalEntity` | Actor outside the system boundary | BoundaryAction |
| `Process` | Data transformation step | Policy |
| `DataStore` | Persistent data repository | Mechanism + Entity |
| `DataFlow` | Directed data movement | Wiring |

### GDS Mapping

Three-tier composition with optional temporal loop:

```
Composition: (entities |) >> (processes |) >> (stores |)
                 .loop([stores -> processes])  # if stores exist
Canonical:   h = g (no stores) or h = f . g (with stores)
```

### Checks

DFD-001..DFD-005 (5 checks). See [Verification](verification.md#dfd-checks).

### Example

```python
from gds_software import (
    ExternalEntity, Process, DataStore, DataFlow, DFDModel,
)

model = DFDModel(
    name="Order Processing",
    entities=[ExternalEntity(name="Customer")],
    processes=[Process(name="Validate"), Process(name="Ship")],
    stores=[DataStore(name="Orders")],
    flows=[
        DataFlow(name="Request", source="Customer", target="Validate"),
        DataFlow(name="Save", source="Validate", target="Orders"),
        DataFlow(name="Lookup", source="Orders", target="Ship"),
        DataFlow(name="Notify", source="Ship", target="Customer"),
    ],
)
```

---

## State Machine (SM)

State machines model **behavioral transitions** -- states connected by event-triggered transitions with optional guards.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `State` | A discrete system state | Mechanism + Entity |
| `Event` | External trigger | BoundaryAction |
| `Transition` | State change on event | Policy |
| `Guard` | Boolean condition on transition | (embedded in Transition) |
| `Region` | Orthogonal concurrent partition | ParallelComposition |

### GDS Mapping

Three-tier composition:

```
Composition: (events |) >> (transitions |) >> (states |)
                 .loop([states -> transitions])
Canonical:   h = f . g (stateful)
```

### Checks

SM-001..SM-006 (6 checks). See [Verification](verification.md#state-machine-checks).

### Example

```python
from gds_software import (
    State, Event, Transition, StateMachineModel,
)

model = StateMachineModel(
    name="Door",
    states=[
        State(name="Closed", is_initial=True),
        State(name="Open"),
        State(name="Locked"),
    ],
    events=[Event(name="open"), Event(name="close"), Event(name="lock"), Event(name="unlock")],
    transitions=[
        Transition(source="Closed", target="Open", event="open"),
        Transition(source="Open", target="Closed", event="close"),
        Transition(source="Closed", target="Locked", event="lock"),
        Transition(source="Locked", target="Closed", event="unlock"),
    ],
)
```

---

## Component Diagram (CP)

Component diagrams model **software structure** -- components with provided/required interfaces connected by connectors.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `Component` | Software module with interfaces | Policy |
| `InterfaceDef` | Named interface contract | (metadata) |
| `Connector` | Wiring between components via interface | Wiring |

### GDS Mapping

Single-tier parallel composition:

```
Composition: (components |)
Canonical:   h = g (stateless)
```

### Port Naming

Uses ` + ` delimiter for token overlap: `"{Interface} + Provided"`, `"{Interface} + Required"`.

### Checks

CP-001..CP-004 (4 checks). See [Verification](verification.md#component-checks).

### Example

```python
from gds_software import (
    Component, InterfaceDef, Connector, ComponentModel,
)

model = ComponentModel(
    name="Microservices",
    components=[
        Component(name="AuthService", provides=["Auth"], requires=["UserDB"]),
        Component(name="UserStore", provides=["UserDB"]),
    ],
    interfaces=[InterfaceDef(name="Auth"), InterfaceDef(name="UserDB")],
    connectors=[
        Connector(name="Auth->Users", source="AuthService", target="UserStore", interface="UserDB"),
    ],
)
```

---

## C4 Model

C4 models describe **system context and containers** -- people, systems, containers, and components with relationships.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `Person` | Human user/actor | BoundaryAction |
| `ExternalSystem` | System outside the boundary | BoundaryAction |
| `Container` | Deployable unit (app, database, etc.) | Policy |
| `C4Component` | Component within a container | Policy |
| `C4Relationship` | Directed dependency | Wiring |

### GDS Mapping

Two-tier composition:

```
Composition: (persons | externals) >> (containers | components)
Canonical:   h = g (stateless)
```

### Checks

C4-001..C4-004 (4 checks). See [Verification](verification.md#c4-checks).

### Example

```python
from gds_software import (
    Person, ExternalSystem, Container, C4Relationship, C4Model,
)

model = C4Model(
    name="E-Commerce",
    persons=[Person(name="Shopper")],
    external_systems=[ExternalSystem(name="Payment Gateway")],
    containers=[
        Container(name="Web App", technology="React"),
        Container(name="API", technology="FastAPI"),
        Container(name="Database", technology="PostgreSQL"),
    ],
    relationships=[
        C4Relationship(source="Shopper", target="Web App", description="Browses"),
        C4Relationship(source="Web App", target="API", description="API calls"),
        C4Relationship(source="API", target="Database", description="Reads/writes"),
        C4Relationship(source="API", target="Payment Gateway", description="Charges"),
    ],
)
```

---

## Entity-Relationship Diagram (ERD)

ERDs model **data structure** -- entities with attributes connected by relationships with cardinality.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `ERDEntity` | Data entity with attributes | Policy |
| `Attribute` | Entity field (name, type, PK/FK flags) | (embedded in ERDEntity) |
| `ERDRelationship` | Association between entities | Wiring |
| `Cardinality` | Relationship multiplicity (ONE, MANY) | (embedded in ERDRelationship) |

### GDS Mapping

Single-tier parallel composition:

```
Composition: (entities |)
Canonical:   h = g (stateless)
```

### Checks

ER-001..ER-004 (4 checks). See [Verification](verification.md#erd-checks).

### Example

```python
from gds_software import (
    ERDEntity, Attribute, ERDRelationship, Cardinality, ERDModel,
)

model = ERDModel(
    name="Blog",
    entities=[
        ERDEntity(
            name="User",
            attributes=[
                Attribute(name="id", type="int", is_pk=True),
                Attribute(name="email", type="str"),
            ],
        ),
        ERDEntity(
            name="Post",
            attributes=[
                Attribute(name="id", type="int", is_pk=True),
                Attribute(name="author_id", type="int", is_fk=True),
                Attribute(name="title", type="str"),
            ],
        ),
    ],
    relationships=[
        ERDRelationship(
            name="writes",
            source="User", target="Post",
            source_cardinality=Cardinality.ONE,
            target_cardinality=Cardinality.MANY,
        ),
    ],
)
```

---

## Dependency Graph (DG)

Dependency graphs model **module dependencies** with optional layered architecture constraints.

### Elements

| Element | Description | GDS Role |
|---------|-------------|----------|
| `Module` | Software module/package | Policy |
| `Dep` | Directed dependency between modules | Wiring |
| `Layer` | Architectural layer (for ordering constraints) | (metadata) |

### GDS Mapping

Single-tier parallel composition:

```
Composition: (modules |)
Canonical:   h = g (stateless)
```

### Checks

DG-001..DG-004 (4 checks). See [Verification](verification.md#dependency-checks).

### Example

```python
from gds_software import (
    Module, Dep, Layer, DependencyModel,
)

model = DependencyModel(
    name="Clean Architecture",
    modules=[
        Module(name="handlers", layer="application"),
        Module(name="services", layer="domain"),
        Module(name="repository", layer="infrastructure"),
    ],
    deps=[
        Dep(source="handlers", target="services"),
        Dep(source="repository", target="services"),
    ],
    layers=[
        Layer(name="application", order=0),
        Layer(name="domain", order=1),
        Layer(name="infrastructure", order=2),
    ],
)
```
