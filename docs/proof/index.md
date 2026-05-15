# gds-proof

[![PyPI](https://img.shields.io/pypi/v/gds-proof)](https://pypi.org/project/gds-proof/)
[![Python](https://img.shields.io/pypi/pyversions/gds-proof)](https://pypi.org/project/gds-proof/)
[![License](https://img.shields.io/github/license/DynamicalSystemsGroup/gds-core)](https://github.com/DynamicalSystemsGroup/gds-core/blob/main/LICENSE)

**Deterministic model identity and SymPy-based invariant proof verification for GDS models.**

## What is this?

`gds-proof` is a formal verification layer for the GDS ecosystem. It proves that system invariants are preserved across state transitions using symbolic implication analysis powered by SymPy.

Where `gds-analysis` answers "what happens when I simulate this?", `gds-proof` answers "can I *prove* this property always holds?"

- **`analyze_invariants()`** -- 5-strategy symbolic implication prover for every (invariant, block) pair
- **`analyze_inductive_safety()`** -- 3-layer predicate-guarded inductive safety (single-step, predicate sufficiency, multi-step induction)
- **`ProofBuilder` / `verify_proof()`** -- user-authored multi-lemma proof scripts for INCONCLUSIVE results
- **`hash_model()` / `hash_proof()`** -- deterministic SHA-256 identity for models and proof scripts
- **`GDSSymbolicBlock` / `GDSSymbolicModel`** -- adapters bridging GDS structural types to the proof engine

## Architecture

```
gds-framework                   gds-proof
|                                |
|  GDSSpec, AtomicBlock,         |  SymbolicBlock/SymbolicModel protocols
|  Mechanism, Entity,            |  GDSSymbolicBlock/GDSSymbolicModel adapters
|  Finding, VerificationReport   |  analyze_invariants(), analyze_inductive_safety()
|                                |  ProofBuilder, verify_proof(), attach_proof()
+-------+                       |  hash_model(), hash_proof()
        |                        |  Finding integration (findings.py)
        +--- Your application ---+
             |
             |  Structural spec + symbolic expressions
             |  -> invariant proofs + VerificationReport
```

`gds-proof` sits at Layer 1 of the GDS ecosystem, alongside `gds-analysis`, `gds-domains`, and `gds-viz`. It depends on `gds-framework` for structural types and integrates with the existing verification pipeline via `Finding` and `VerificationReport`.

## Key Concepts

| Concept | What it is |
|---------|-----------|
| **Invariant** | A named SymPy BooleanExpr (e.g., `x >= 0`) that must hold across all transitions |
| **SymbolicBlock** | A block enriched with symbolic state transition `f(x, u)`, output map `c(x, u)`, and predicates |
| **Predicate** | Admissibility guard on inputs -- `U_{x} = {u : check(f(x, u)) = True}` |
| **Proof obligation** | `I(x) AND P(x,u) -> I(f(x,u))` for each (invariant, block) pair |
| **ProofScript** | Multi-lemma chain targeting one invariant, verified independently |
| **Model hash** | SHA-256 of canonical_dict -- changes when the model changes |

## The R1/R3 Gap

GDS blocks are structural (R1) -- they declare *what* state variables a mechanism updates, but not *how*. The proof engine needs symbolic expressions (R3). The adapter layer bridges this:

- **Structural (from GDSSpec)**: block names, entity variables, mechanism updates, parameter schema
- **Behavioral (from user)**: SymPy state transitions, output expressions, predicates
- **Bridge**: `GDSSymbolicBlock` wraps an `AtomicBlock` with user-supplied symbolic expressions

## Verification Integration

Proof results convert to `gds-framework` `Finding` objects via `findings.py`:

| Check ID | What it checks |
|----------|---------------|
| `PROOF-001` | Invariant preservation (symbolic analysis) |

`Finding.exportable_predicate` is populated with the invariant's canonical SymPy form, making it available to the OWL/RDF exporter in `gds-interchange`.

## Quick Start

```bash
uv add gds-proof
```

See [Getting Started](getting-started.md) for a full walkthrough.

## Credits

Built on [gds-framework](../framework/index.md) and [SymPy](https://www.sympy.org/) by [DynamicalSystemsGroup](https://dynamicalsystemsgroup.com).
