# Temporal Agnosticism of the Core Algebra

## Invariant Statement

> The composition algebra of gds-framework is temporally agnostic. The flag `is_temporal=True` on a wiring asserts structural recurrence and nothing else. No time model is implied or required by the core. The canonical form h = f . g is an atemporal map. Time models are DSL-layer declarations.

## Three-Layer Temporal Stack

```
Layer 0 — gds-framework (core)
  is_temporal=True encodes structural recurrence only:
  "a temporal boundary exists here."
  No commitment to what model of time governs that boundary.
  h = f . g is a single atemporal map application.
  The algebra is silent on discrete steps, continuous flow, and events.

Layer 1 — DSL (ExecutionContract)
  The DSL declares what "temporal boundary" means for its domain:
    discrete    — boundary is a discrete index step
    continuous  — boundary is a continuous-time interval
    event       — boundary is triggered by a discrete event
    atemporal   — boundary carries no time semantics (e.g., OGS iterated games)
  This is the DSL author's commitment, not the core's.

Layer 2 — Simulation (SolverInterface / runner)
  Required only to execute a specification.
  A solver or runner instantiates the time model concretely.
  The choice of solver (RK4, event queue, discrete stepper) is
  simulation-layer, not specification-layer.
  Specification and verification are fully valid without a solver.
```

## Proof by Inspection of Composition Operators

None of the four composition operators introduce a time model. They operate on structural interfaces only.

**StackComposition (`>>`)** chains `forward_out` to `forward_in` by token overlap. No temporal concept is referenced. The validator checks token sets, not time indices.

**ParallelComposition (`|`)** concatenates interfaces. No validation is performed between left and right. Time is not mentioned.

**FeedbackLoop (`.feedback()`)** routes `backward_out` to `backward_in` within a single evaluation. The wiring direction is `CONTRAVARIANT`. No time model is assumed -- "within a single evaluation" means "before the current map application completes," not "within a discrete timestep."

**TemporalLoop (`.loop()`)** routes `forward_out` to `forward_in` across evaluations. The wiring direction must be `COVARIANT`. The `is_temporal` flag is set on the resulting `WiringIR` edges. This flag tells the acyclicity checker (G-006) to exclude those edges from the covariant DAG constraint. It carries no semantic content about what kind of time governs the recurrence -- it is a structural recurrence marker only.

The `is_temporal` flag exists so that G-006 can distinguish "this edge closes a recurrence" from "this edge creates an illegal cycle." That is its entire semantics at Layer 0.

## The OGS Existence Proof

OGS (Open Game Specification) iterated games compile and verify correctly with temporal wirings but no time model. The canonical form degenerates to h = g with X = empty, f = empty. This is not a special case -- it is existence proof that the algebra is genuinely time-agnostic.

An OGS `IteratedGame` wraps a `OneShot` game with `.loop()` temporal wirings that carry strategy and payoff signals across rounds. The word "round" here is a game-theoretic concept, not a time concept. No discrete-time index, no continuous-time interval, and no event trigger is declared at the core level. The temporal wirings assert only: "there is structural recurrence here."

This demonstrates that the core algebra supports recurrence patterns that have nothing to do with physical time. The `.loop()` operator is about structural feedback topology, not about clocks.

## ExecutionContract Time Model Table

| time_domain | Meaning at DSL layer | Example DSL |
|---|---|---|
| discrete | Temporal boundary is a discrete index step | gds-stockflow, gds-control |
| continuous | Temporal boundary is a continuous-time interval | gds-continuous |
| event | Temporal boundary is triggered by an event | (future) |
| atemporal | Temporal boundary carries no time semantics | gds-games (OGS) |

## Vocabulary Guide

When writing documentation for the core framework (Layer 0), use temporally neutral language:

| Avoid (core docs) | Prefer |
|---|---|
| "within a single timestep" | "within a single evaluation" |
| "across timesteps" | "across temporal boundaries" |
| "next step" / "next timestep" | "subsequent application" or "recurrence" |
| "time t" / "t+1" subscripts | "evaluation k" / "k+1" (or omit indices) |
| "trajectory x_0, x_1, ..." | "sequence of states under repeated application of h" |
| "iteration" (implying counting) | "recurrence" or "repeated application" |

!!! note "DSL-layer exception"
    DSL-layer docs (gds-stockflow, gds-control, gds-continuous, gds-games) **may** use time-specific language because they have declared a time model via their `ExecutionContract`. The vocabulary guide applies only to core framework documentation.
