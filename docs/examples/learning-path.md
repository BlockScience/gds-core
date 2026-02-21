# Learning Path

Start with SIR Epidemic and work down. Each example introduces one new concept while reinforcing the previous ones.

## Progression

### 1. [SIR Epidemic](examples/sir-epidemic.md) — Fundamentals

The foundation. Learn TypeDef, Entity, Space, BoundaryAction, Policy, Mechanism, `>>` sequential composition, and `|` parallel composition.

**Roles:** BoundaryAction, Policy, Mechanism

### 2. [Thermostat PID](examples/thermostat.md) — Feedback

Adds `.feedback()` for within-timestep backward information flow. Introduces CONTRAVARIANT flow direction and the ControlAction role.

**New:** `.feedback()`, backward ports, ControlAction

### 3. [Lotka-Volterra](examples/lotka-volterra.md) — Temporal Loops

Adds `.loop()` for cross-timestep iteration. Introduces COVARIANT temporal wiring and Mechanism with `forward_out`.

**New:** `.loop()`, temporal wiring, exit conditions

### 4. [Prisoner's Dilemma](examples/prisoners-dilemma.md) — Complex Composition

Most complex composition tree. Nested parallel (`(A | B) | C`), multi-entity state space, and combining all operators except `.feedback()`.

**New:** nested parallel, multi-entity state, complex trees

### 5. [Insurance Contract](examples/insurance.md) — Complete Taxonomy

Completes the 4-role taxonomy. The only example using all four roles: BoundaryAction, Policy, ControlAction, Mechanism.

**New:** complete role taxonomy, parameterized admissibility

### 6. [Crosswalk Problem](examples/crosswalk.md) — Mechanism Design

The canonical GDS example from BlockScience. Demonstrates mechanism design with a governance parameter constraining agent behavior via discrete Markov transitions.

**New:** mechanism design, governance parameters, discrete state

## Prerequisites

- Python 3.12+
- [gds-framework](https://pypi.org/project/gds-framework/) and [gds-viz](https://pypi.org/project/gds-viz/) (installed with gds-examples)
- Basic understanding of dynamical systems concepts
