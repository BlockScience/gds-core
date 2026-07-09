# GDS Documentation Reorganization Plan

## Purpose

The current documentation has grown from a `gds-framework`-centered site into a
multi-package ecosystem site. The navigation now contains tutorials, how-to
guides, package overviews, generated API reference, examples, design notes, and
research material, but the information architecture still makes `Framework`
look like the center of the whole ecosystem.

This plan reorganizes the docs so users can answer these questions quickly:

- How do I model a system?
- How do I verify it?
- How do I simulate it?
- How do I analyze trajectories or search parameters?
- Which package do I install and import?
- What is the difference between `gds-framework`, `gds-sim`, `gds-analysis`,
  and `gds_analysis.psuu`?

## Current Site Structure

Top-level navigation currently uses:

- `Home`
- `Learn`
- `How-To Guides`
- `Reference`
- `Case Studies`
- `Design & Research`
- `Changelog`

The source tree is package-shaped:

- `docs/framework`
- `docs/viz`
- `docs/games`
- `docs/business`
- `docs/stockflow`
- `docs/control`
- `docs/software`
- `docs/owl`
- `docs/sim`
- `docs/psuu`
- `docs/continuous`
- `docs/symbolic`
- `docs/proof`
- `docs/analysis`
- `docs/examples`
- `docs/guides`
- `docs/research`
- `docs/case-studies`

This is a reasonable file layout, but the navigation and page copy need to
better distinguish user journeys from package boundaries.

## Current Problems

### 1. `Framework` is overloaded

Readers can interpret "Framework" as:

- the `gds-framework` Python package
- the GDS conceptual framework
- the whole GDS ecosystem

The `/framework/` page is a `gds-framework` package overview, but users expect it
to explain the full stack. This is why `gds-sim` feels missing from the
reference page.

### 2. Stale package-era copy

`docs/framework/index.md` still says domain packages and simulation execution
are not yet built. That is now false. `gds-sim`, `gds-continuous`,
`gds-analysis`, and `gds_analysis.psuu` exist and are documented.

### 3. Ecosystem orientation is buried

`docs/framework/ecosystem.md` explains package relationships, but it is nested
under `Design & Research -> Ecosystem`. This page is orientation material, not a
research artifact.

### 4. `Reference` mixes several documentation types

The current `Reference` tab contains:

- package overview pages
- getting started pages
- user guides
- generated API reference

This makes `Reference` too large and makes generated API docs compete with
human explanation.

### 5. Simulation and analysis are not a first-class journey

The ecosystem now has a clear path:

```text
specification -> verification -> simulation -> analysis -> parameter search
```

But users must infer that path from package names.

### 6. Package naming is inconsistent

Some pages use old distribution names such as `gds-stockflow`, `gds-control`,
`gds-business`, while other pages use `gds-domains.*` imports. The docs need a
clear convention for:

- distribution package name
- import path
- docs section title
- deprecated compatibility packages

## External Documentation Patterns to Adopt

### Diataxis: separate user needs

Use the Diataxis distinction:

- Tutorials: learning-oriented, step-by-step
- How-to guides: task-oriented recipes
- Reference: factual API/package details
- Explanation: concepts, architecture, design rationale

GDS already has all four content types, but they are not cleanly separated in
navigation.

### scikit-learn: keep API reference subordinate to guides

API pages should point back to user guides. Raw class/function docs are not
enough for concept-heavy systems.

### FastAPI: progressive tutorial path

Tutorials should build gradually but remain useful as future reference. GDS
needs a path like:

```text
define a spec -> verify it -> render it -> simulate it -> analyze it
```

### Dask and Ray: route by job-to-be-done

Users should be routed by what they want to accomplish, not only by package
name.

### Mesa and PyMC: examples are first-class

Modeling libraries are learned through examples. GDS examples should be a major
surface, not just a secondary section.

## Target Top-Level Navigation

Recommended target:

```yaml
nav:
  - Home: index.md
  - Start Here:
      - Overview: start/index.md
      - Install: start/install.md
      - 10-Minute Model: start/ten-minute-model.md
      - Learning Path: examples/learning-path.md
      - Choosing a Package: packages/choosing.md
  - Concepts:
      - Overview: concepts/index.md
      - GDS in Practice: concepts/gds-in-practice.md
      - Specification vs Execution: concepts/specification-vs-execution.md
      - Blocks, State, and Parameters: concepts/blocks-state-parameters.md
      - Verification Layers: concepts/verification-layers.md
      - Simulation and Analysis Stack: concepts/simulation-analysis-stack.md
  - Packages:
      - Overview: packages/index.md
      - Foundation:
          - gds-framework: framework/index.md
          - gds-viz: viz/index.md
          - gds-interchange / OWL: owl/index.md
          - gds-proof: proof/index.md
      - Domain DSLs:
          - Stock-Flow: stockflow/index.md
          - Control: control/index.md
          - Games: games/index.md
          - Software: software/index.md
          - Business: business/index.md
          - Symbolic Math: symbolic/index.md
      - Simulation & Analysis:
          - Overview: packages/simulation-analysis.md
          - gds-sim: sim/index.md
          - gds-continuous: continuous/index.md
          - gds-analysis: analysis/index.md
          - PSUU: psuu/index.md
  - Examples:
      - Overview: examples/index.md
      - Learning Path: examples/learning-path.md
      - Building Models: examples/building-models.md
      - Feature Matrix: examples/feature-matrix.md
      - Models:
          - SIR Epidemic: examples/examples/sir-epidemic.md
          - Thermostat PID: examples/examples/thermostat.md
          - Lotka-Volterra: examples/examples/lotka-volterra.md
          - Prisoner's Dilemma: examples/examples/prisoners-dilemma.md
          - Insurance Contract: examples/examples/insurance.md
          - Crosswalk Problem: examples/examples/crosswalk.md
          - Evolution of Trust: examples/examples/evolution-of-trust.md
  - How-To:
      - Overview: guides/index.md
      - Verify a Model: guides/verification.md
      - Visualize a Model: guides/visualization.md
      - Simulate a Model: guides/simulation.md
      - Run a Parameter Sweep: guides/parameter-sweep.md
      - Bridge a Spec to Simulation: analysis/getting-started.md
      - Export OWL/SHACL: owl/getting-started.md
      - Interoperability: guides/interoperability.md
      - Best Practices: guides/best-practices.md
      - Troubleshooting: guides/troubleshooting.md
  - API Reference:
      - Overview: api/index.md
      - Framework API:
          - gds: framework/api/init.md
          - gds.blocks: framework/api/blocks.md
          - gds.types: framework/api/types.md
          - gds.state: framework/api/state.md
          - gds.spaces: framework/api/spaces.md
          - gds.spec: framework/api/spec.md
          - gds.canonical: framework/api/canonical.md
          - gds.compiler: framework/api/compiler.md
          - gds.ir: framework/api/ir.md
          - gds.verification: framework/api/verification.md
          - gds.query: framework/api/query.md
          - gds.parameters: framework/api/parameters.md
          - gds.serialize: framework/api/serialize.md
      - Domain APIs:
          # Existing domain API pages grouped here.
      - Simulation APIs:
          - gds_sim: sim/api/init.md
          - gds_sim.model: sim/api/model.md
          - gds_sim.types: sim/api/types.md
          - gds_sim.engine: sim/api/engine.md
          - gds_sim.results: sim/api/results.md
          - gds_sim.parallel: sim/api/parallel.md
          - gds_sim.compat: sim/api/compat.md
      - Analysis APIs:
          - gds_analysis.psuu: psuu/api/init.md
          - gds_analysis.psuu.metric: psuu/api/metric.md
          - gds_analysis.psuu.kpi: psuu/api/kpi.md
          - gds_analysis.psuu.evaluation: psuu/api/evaluation.md
          - gds_analysis.psuu.space: psuu/api/space.md
          - gds_analysis.psuu.objective: psuu/api/objective.md
          - gds_analysis.psuu.optimizers: psuu/api/optimizers.md
          - gds_analysis.psuu.sensitivity: psuu/api/sensitivity.md
          - gds_analysis.psuu.sweep: psuu/api/sweep.md
          - gds_analysis.psuu.results: psuu/api/results.md
  - Case Studies:
      - Overview: case-studies/index.md
      - Axelrod Tournament: case-studies/axelrod.md
  - Design & Research:
      # Keep design docs and research docs here.
  - Changelog: changelog.md
```

This is the target structure, not a required one-shot migration. It should be
implemented incrementally.

## New Pages to Add

### `docs/packages/index.md`

Canonical ecosystem package map.

Required sections:

- What the package layer model is
- Package table with distribution name, import path, and use case
- Architecture diagram
- "What do you want to do?" routing table
- Notes on deprecated compatibility packages

Suggested routing table:

| Goal | Start Here | Package |
|---|---|---|
| Define a typed system specification | `gds-framework` overview | `gds-framework` |
| Use a domain vocabulary | Choosing a Package | `gds-domains.*` |
| Render Mermaid diagrams | Visualization guide | `gds-viz` |
| Export OWL/SHACL/SPARQL | OWL guide | `gds-interchange` |
| Run discrete-time simulations | Simulation guide | `gds-sim` |
| Run ODE simulations | Continuous-Time guide | `gds-continuous` |
| Bridge `GDSSpec` to simulation | Analysis guide | `gds-analysis` |
| Sweep and optimize parameters | PSUU guide | `gds_analysis.psuu` |

### `docs/packages/simulation-analysis.md`

Explain the execution and analysis stack as one story.

Required sections:

- `gds-framework` defines verified specs
- `gds-analysis` bridges specs to runtime
- `gds-sim` executes discrete-time models
- `gds-continuous` executes ODE models
- `gds_analysis.psuu` evaluates, sweeps, optimizes, and runs sensitivity analysis

Suggested diagram:

```text
Domain DSLs
  stockflow / control / games / software / business
        |
        v
gds-framework
  typed specification + verification
        |
        v
gds-analysis
  bridge specs to runtime
        |
        v
gds-sim / gds-continuous
  execute trajectories
        |
        v
gds_analysis.psuu
  sweep, optimize, sensitivity
```

### `docs/concepts/index.md`

Landing page for explanation-oriented docs.

Initial links can point to existing pages instead of moving all content at once:

- Framework architecture
- Execution semantics
- Temporal agnosticism
- Assurance claims
- Simulation and analysis stack

### `docs/start/index.md`

Replace the split between `Learn -> Start Here` and `Getting Started Guide` with
a clearer entry point.

Required sections:

- Pick your path
- Install
- First model
- Next steps

### `docs/api/index.md`

Explain that API reference is factual module documentation and that most users
should start from package guides first.

## Existing Pages to Update

### `docs/framework/index.md`

Immediate required changes:

- Remove stale status saying simulation is not built.
- Add "Relationship to Simulation and Analysis".
- Clarify that `gds-framework` is specification and verification, not runtime.
- Link to `../sim/index.md`, `../analysis/index.md`, `../continuous/index.md`,
  and `../psuu/index.md`.

Suggested text:

```md
## Relationship to Simulation and Analysis

`gds-framework` defines typed specifications, compilation, canonical structure,
and structural verification. It does not directly execute trajectories.

Use:

- [`gds-sim`](../sim/index.md) for standalone discrete-time simulation
- [`gds-continuous`](../continuous/index.md) for ODE simulation
- [`gds-analysis`](../analysis/index.md) to bridge `GDSSpec` structures into
  simulation workflows
- [`gds_analysis.psuu`](../psuu/index.md) for parameter sweeps, optimization,
  and sensitivity analysis
```

### `docs/index.md`

Update home page so it routes users by job-to-be-done before listing packages.

Add a short "What do you want to do?" table near the top.

### `docs/framework/ecosystem.md`

Either:

- move content into `docs/packages/index.md`, then redirect/link old page; or
- leave the page in place but make it a thin redirect-style page pointing to the
  new package map.

### `docs/analysis/index.md`

Ensure it answers:

- when to use `gds-analysis`
- how it relates to `gds-framework`, `gds-sim`, and PSUU
- when not to use it

### `docs/sim/index.md`

Ensure it answers:

- `gds-sim` runs plain Python model functions
- it is standalone and does not depend on `gds-framework`
- use `gds-analysis` when starting from `GDSSpec`

### `docs/psuu/index.md`

Ensure it consistently presents canonical import as `gds_analysis.psuu` and
`gds-psuu` as compatibility only.

## Naming Convention

Each package landing page should include a small identity block:

```md
| Distribution | Import | Role |
|---|---|---|
| `gds-analysis` | `gds_analysis` | Analysis bridge and reachability |
| `gds-analysis` | `gds_analysis.psuu` | Parameter search under uncertainty |
```

Rules:

- Page titles can use user-facing names, for example `PSUU`.
- First paragraph must state distribution and import path.
- Deprecated compatibility packages must be called out in an admonition.
- Do not mix distribution names and import paths in the same table column.

## Standard Package Landing Page Template

Every package overview should converge to:

```md
# Package Name

Badges.

One-sentence role.

## Package Identity

| Distribution | Import | Role |
|---|---|---|

## What Is This?

## When to Use It

## When Not to Use It

## Install

## Quick Start

## Relationship to the Ecosystem

## Next Steps
```

For smaller packages, `When Not to Use It` can be omitted, but
`Relationship to the Ecosystem` should be mandatory.

## Standard API Page Pattern

API pages should remain generated with `mkdocstrings`, but each API section
should have an overview page that says:

- These pages are reference, not tutorials.
- Start with the package guide if you are new.
- Link common tasks to how-to pages.

For example, `docs/api/index.md`:

```md
# API Reference

These pages document classes, functions, and modules. They are useful when you
already know which package you need.

If you are choosing a package, start with [Packages](../packages/index.md).
If you are learning concepts, start with [Concepts](../concepts/index.md).
```

## Migration Phases

### Phase 1: Fix correctness and orientation

Goal: remove immediate confusion without large file moves.

Tasks:

- Update `docs/framework/index.md` stale simulation status.
- Add relationship links from framework to simulation/analysis.
- Add `docs/packages/index.md`.
- Add `docs/packages/simulation-analysis.md`.
- Add those pages to nav under current `Reference` or `Learn` while preserving
  existing URLs.
- Run `uv run mkdocs build --strict`.

Acceptance criteria:

- `/framework/` no longer says simulation is not built.
- A user can find `gds-sim` from `/framework/` in one click.
- A user can find package distribution/import/use-case from one canonical page.

### Phase 2: Navigation restructuring

Goal: separate package docs from API reference.

Tasks:

- Rename nav label `Reference` to `Packages` or split into `Packages` and
  `API Reference`.
- Promote package overview pages under `Packages`.
- Move generated API pages under the `API Reference` nav grouping.
- Keep file paths stable where possible to avoid broken external links.
- Update `llmstxt.sections` to match the new conceptual grouping.
- Run `uv run mkdocs build --strict`.

Acceptance criteria:

- Top nav has a clear package map.
- API reference no longer dominates the package learning path.
- `llms.txt` grouping mirrors the human navigation well enough for agents.

### Phase 3: Content normalization

Goal: make package pages consistent.

Tasks:

- Apply package landing page template to:
  - `framework/index.md`
  - `sim/index.md`
  - `analysis/index.md`
  - `psuu/index.md`
  - `continuous/index.md`
  - `viz/index.md`
  - domain DSL index pages
- Add package identity tables.
- Add relationship-to-ecosystem sections.
- Normalize installation snippets.
- Clarify distribution vs import path.
- Run `uv run mkdocs build --strict`.

Acceptance criteria:

- Every package page answers "what is it?", "when do I use it?", and "how does
  it fit?"
- No package page contains stale claims about missing packages.

### Phase 4: Concept and how-to expansion

Goal: improve learning flow.

Tasks:

- Add or reorganize `docs/concepts`.
- Add `guides/simulation.md`.
- Add `guides/parameter-sweep.md`.
- Add "specification vs execution" concept page.
- Add "simulation and analysis stack" concept page.
- Cross-link examples to package guides and API reference.
- Run `uv run mkdocs build --strict`.

Acceptance criteria:

- New users can follow a coherent path from model definition to simulation.
- Experienced users can jump to task recipes without reading theory.

### Phase 5: Stale design/research audit

Goal: preserve research notes while preventing them from misleading current
users.

Tasks:

- Audit pages containing:
  - "future"
  - "not yet built"
  - "not planned"
  - old package names
  - outdated version status
- Add "Historical note" admonitions where the content is intentionally old.
- Update pages that are meant to reflect current architecture.
- Run `uv run mkdocs build --strict`.

Acceptance criteria:

- Historical design docs remain available.
- Current user-facing docs do not contradict current packages.

## MkDocs Implementation Notes

### Keep URLs stable where possible

Prefer nav relabeling over file moves for existing pages. If pages are moved,
add a redirect plugin or keep thin compatibility pages at old paths.

### Update `llmstxt`

The `llmstxt.sections` block should mirror the improved docs architecture.
This matters because GDS is concept-heavy and likely to be consumed by AI coding
agents.

### Maintain strict build

Every phase must pass:

```bash
uv run mkdocs build --strict
```

### Watch for public site lag

GitHub Pages publishes on pushes to `main` via `.github/workflows/docs.yml`.
After publishing, verify the deployed nav and page content.

## Validation Checklist

Run these before merging/pushing each docs reorganization phase:

- [ ] `uv run mkdocs build --strict`
- [ ] Search for stale claims:
  ```bash
  rg -n "not yet built|future|not planned|gds-psuu|n_calls|scikit-optimize" docs mkdocs.yml README.md
  ```
- [ ] Search for broken package references:
  ```bash
  rg -n "gds-stockflow|gds-control|gds-business|gds-software|gds-games" docs README.md
  ```
  Then confirm each occurrence is intentionally a distribution name or update it.
- [ ] Confirm `/framework/` links to simulation and analysis.
- [ ] Confirm package map includes distribution, import, and role.
- [ ] Confirm `llms.txt` and `llms-full.txt` build outputs include the new pages.

## Open Questions

- Should the docs use distribution package names such as `gds-control`, or the
  consolidated `gds-domains.control` import names as primary labels?
- Should `PSUU` live under `gds-analysis` only, or remain a first-class package
  section because users search for it by acronym?
- Should `Design & Research` stay in top-level nav, or should historical design
  docs be moved under `Concepts -> Design Notes`?
- Should generated API pages be grouped by module path or by package layer?
- Do we want redirects for old `framework/ecosystem.md` if a new
  `packages/index.md` becomes canonical?

## Recommended First PR

Scope:

- Add `docs/packages/index.md`.
- Add `docs/packages/simulation-analysis.md`.
- Update `docs/framework/index.md`.
- Add package map pages to nav without removing existing sections.
- Update `llmstxt.sections`.
- Run strict docs build.

Suggested commit message:

```text
docs: clarify package map and simulation stack
```

