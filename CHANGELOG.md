# Changelog

## 2026-04-05 — Package Consolidation (14 → 8 packages)

Implements the consolidation plan from issue #143. Reduces the monorepo from
14 independently published packages to 8, eliminating the N^2 integration
problem and simplifying user installation.

### New packages

- **gds-domains v0.1.0** — consolidates all 6 domain DSLs (stockflow, control,
  business, software, games, symbolic) into a single package with optional extras.
  Install what you need: `pip install gds-domains[games,symbolic]`.
  Import paths: `from gds_domains.stockflow import StockFlowModel`, etc.

- **gds-interchange v0.1.0** — replaces gds-owl as a broader interchange hub.
  OWL/RDF functionality lives at `gds_interchange.owl`. Future bridges (SysML,
  FMI, SBML) will land as additional subpackages.

### Merged packages

- **gds-analysis v0.2.0** — absorbs gds-psuu. PSUU functionality is now at
  `gds_analysis.psuu`. Install with `pip install gds-analysis[psuu]` for Optuna.

### Deprecated packages (shim-only, v0.99.0)

The following packages now re-export from their consolidated locations with a
`DeprecationWarning`. They will be removed in v0.3.0:

- `gds-owl` → use `gds-interchange` (`from gds_interchange.owl import ...`)
- `gds-psuu` → use `gds-analysis` (`from gds_analysis.psuu import ...`)
- `gds-stockflow` → use `gds-domains` (`from gds_domains.stockflow import ...`)
- `gds-control` → use `gds-domains` (`from gds_domains.control import ...`)
- `gds-business` → use `gds-domains` (`from gds_domains.business import ...`)
- `gds-software` → use `gds-domains` (`from gds_domains.software import ...`)
- `gds-games` → use `gds-domains` (`from gds_domains.games import ...`)
- `gds-symbolic` → use `gds-domains` (`from gds_domains.symbolic import ...`)

### Unchanged packages

- `gds-framework` ��� core engine (no changes)
- `gds-sim` — discrete-time simulation (standalone, no changes)
- `gds-continuous` — continuous-time ODE engine (standalone, no changes)
- `gds-viz` — visualization (no changes)
- `gds-examples` — updated imports to use `gds_domains.*`

### Migration guide

Replace old imports with new paths:

```python
# Before
from stockflow import StockFlowModel
from gds_control import ControlModel
from ogs import OpenGame
from gds_owl import spec_to_graph

# After
from gds_domains.stockflow import StockFlowModel
from gds_domains.control import ControlModel
from gds_domains.games import OpenGame
from gds_interchange.owl import spec_to_graph
```

Old imports continue to work with a deprecation warning until v0.3.0.

---

## 2026-04-03 — Tier 0 + Tier 1 Complete

Driven by external reviews from Zargham and Jamsheed (Shorish) against the
GDS paper (Zargham & Shorish 2022). The reviews identified foundational gaps
in notation alignment, formal property statements, ControlAction semantics,
temporal agnosticism documentation, and execution contract formalization.
This release closes all Tier 0 and Tier 1 roadmap items.

### gds-framework v0.3.0

**Breaking:** `CanonicalGDS.input_ports` now contains only controlled inputs (U_c);
disturbance-tagged BoundaryAction ports are in the new `disturbance_ports` field.

New capabilities:
- **ExecutionContract** — DSL-layer time model declaration (`discrete`, `continuous`,
  `event`, `atemporal`) with Moore/Mealy ordering. Attached as optional field on
  GDSSpec. A spec without a contract remains valid for structural verification.
- **ControlAction canonical projection** — `CanonicalGDS` now extracts output ports
  (Y) and renders the output map `y = C(x, d)` in the formula.
- **Disturbance input partition** — `disturbance_ports` on `CanonicalGDS` separates
  policy-bypassing exogenous inputs (W) from controlled inputs (U_c) via
  `tags={"role": "disturbance"}` on BoundaryAction.
- **TypeDef.constraint_kind** — optional named constraint pattern (`non_negative`,
  `positive`, `probability`, `bounded`, `enum`) enabling round-trip export via SHACL.

New verification checks:
- **SC-010** — ControlAction outputs must not feed the g pathway (Policy/BoundaryAction)
- **SC-011** — ExecutionContract well-formedness
- **DST-001** — Disturbance-tagged BoundaryAction must not wire to Policy

Documentation:
- Formal property statements for all 15 core checks (G-001..G-006, SC-001..SC-009)
- Requirement traceability markers on all verification tests
- Tests for SC-005..SC-009 (previously untested)
- Controller-plant duality design document
- Temporal agnosticism invariant with three-layer stack diagram
- Audit of 30+ docs replacing "timestep" with temporally neutral vocabulary
- Assurance claims document with verification passport template
- Execution semantics design document with DSL contract mapping
- Disturbance formalization design document
- Notation harmonized with Zargham & Shorish (2022)

### gds-owl v0.2.0

- **SHACL constraint promotion** — `TypeDef.constraint_kind` metadata exports as SHACL
  property shapes (`sh:minInclusive`, `sh:maxInclusive`, `sh:minExclusive`, `sh:in`).
  Constraints with a `constraint_kind` are now R2 round-trippable; those without remain
  R3 lossy. Import reconstructs Python callable constraints from SHACL metadata.
- New ontology properties: `constraintKind`, `constraintLow`, `constraintHigh`, `constraintValue`
- New `build_constraint_shapes()` public API

### gds-psuu v0.2.1

- **Parameter schema validation** — `ParameterSpace.from_parameter_schema()` creates
  sweep dimensions from declared ParameterDef entries. `validate_against_schema()`
  catches missing params, type mismatches, and out-of-bounds sweeps.
- **PSUU-001 check** following the GDS Finding pattern
- Sweep runner validates against schema when `parameter_schema` is provided

### gds-stockflow v0.1.1

- Emit `ExecutionContract(time_domain="discrete")` from `compile_model()`

### gds-control v0.1.1

- Emit `ExecutionContract(time_domain="discrete")` from `compile_model()`

### gds-games v0.3.2

- Emit `ExecutionContract(time_domain="atemporal")` from `compile_pattern_to_spec()`

### gds-software v0.1.1

- Emit `ExecutionContract` from all 6 compilers: `atemporal` for DFD, C4, component,
  ERD, dependency; `discrete` for state machines

### gds-business v0.1.1

- Emit `ExecutionContract` from all 3 compilers: `discrete` for CLD and supply chain,
  `atemporal` for value stream maps

### gds-analysis v0.1.1

- Guard `gds-continuous` import in `backward_reachability.py` (previously caused
  ImportError when gds-continuous wasn't installed)

## gds-framework v0.2.3

- Add `StructuralWiring` to public API (compiler intermediate for domain DSL wiring emitters)
- Switch to dynamic versioning — `__version__` in `__init__.py` is the single source of truth
- Tighten `gds-framework>=0.2.3` lower bound across all dependent packages

## gds-games v0.2.0

- Add canonical bridge (`compile_pattern_to_spec`) — projects OGS patterns to `GDSSpec`
- Add view stratification architecture
- Require `gds-framework>=0.2.3`

## gds-stockflow v0.1.0

- Initial release — declarative stock-flow DSL over GDS semantics

## gds-control v0.1.0

- Initial release — state-space control DSL over GDS semantics

## gds-viz v0.1.2

- Mermaid renderers for structural, canonical, architecture, parameter, and traceability views
