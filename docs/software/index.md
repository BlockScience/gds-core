# gds-software

[![PyPI](https://img.shields.io/pypi/v/gds-software)](https://pypi.org/project/gds-software/)
[![Python](https://img.shields.io/pypi/pyversions/gds-software)](https://pypi.org/project/gds-software/)
[![License](https://img.shields.io/github/license/BlockScience/gds-core)](https://github.com/BlockScience/gds-core/blob/main/LICENSE)

**Software architecture DSL over GDS semantics** -- DFDs, state machines, component diagrams, C4 models, ERDs, and dependency graphs with formal verification.

## What is this?

`gds-software` extends the GDS framework with software architecture vocabulary -- six diagram types commonly used in software engineering, each compiled to GDS specifications with structural verification. It provides:

- **6 diagram types** -- Data Flow Diagram (DFD), State Machine (SM), Component Diagram (CP), C4 Model, Entity-Relationship Diagram (ERD), Dependency Graph (DG)
- **Typed compilation** -- Each diagram compiles to GDS role blocks, entities, and composition trees
- **27 verification checks** -- Domain-specific structural validation across all diagram types
- **Canonical decomposition** -- Validated h = f &#x2218; g projection for all diagram types
- **Full GDS integration** -- All downstream tooling works immediately (canonical projection, semantic checks, gds-viz)

## Architecture

```
gds-framework (pip install gds-framework)
|
|  Domain-neutral composition algebra, typed spaces,
|  state model, verification engine, flat IR compiler.
|
+-- gds-software (pip install gds-software)
    |
    |  Software architecture DSL: 6 diagram types,
    |  compile_*(), domain verification, verify() dispatch.
    |
    +-- Your application
        |
        |  Concrete architecture models, analysis notebooks,
        |  verification runners.
```

## Diagram Types at a Glance

| Diagram | Elements | Checks | Canonical Form |
|---------|----------|--------|----------------|
| **DFD** | ExternalEntity, Process, DataStore, DataFlow | DFD-001..005 | Varies (stateful with data stores) |
| **State Machine** | State, Event, Transition, Guard, Region | SM-001..006 | Varies (stateful with states) |
| **Component** | Component, InterfaceDef, Connector | CP-001..004 | h = g (stateless) |
| **C4** | Person, ExternalSystem, Container, C4Component, C4Relationship | C4-001..004 | h = g (stateless) |
| **ERD** | ERDEntity, Attribute, ERDRelationship, Cardinality | ER-001..004 | h = g (stateless) |
| **Dependency** | Module, Dep, Layer | DG-001..004 | h = g (stateless) |

## GDS Role Mappings

All six diagram types follow a shared mapping pattern:

- Exogenous inputs (ExternalEntity, Person, Event) --> `BoundaryAction`
- Decision/observation logic (Process, Transition, Module, Component) --> `Policy`
- State updates (DataStore, State, stateful containers) --> `Mechanism` + `Entity`
- Connections (DataFlow, Connector, Dep, Relationship) --> `Wiring`

## Quick Start

```bash
uv add gds-software
# or: pip install gds-software
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on [gds-framework](../framework/index.md) by [BlockScience](https://block.science).
