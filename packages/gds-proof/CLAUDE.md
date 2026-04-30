# CLAUDE.md — gds-proof

## Package Identity

`gds-proof` provides deterministic model identity and SymPy-based invariant
proof verification for GDS models.  Layer 1 package — depends on
`gds-framework` for structural types (`AtomicBlock`, `GDSSpec`, `Mechanism`,
`Finding`, `VerificationReport`).

- **Import**: `import gds_proof`
- **Dependencies**: `gds-framework>=0.3.0`, `sympy>=1.12`, `pydantic>=2.0`
- **Protocols**: `SymbolicBlock`, `SymbolicModel` (renamed from `ProofableBlock`, `ProofableModel`)
- **Adapters**: `GDSSymbolicBlock`, `GDSSymbolicModel` — bridge GDS types to proof protocols
- **Verification integration**: `findings.py` converts results to `Finding`/`VerificationReport`

---

## GDS Framework Integration

GDS blocks are structural (R1) — they declare *what* state variables a
mechanism updates, but not *how* (no SymPy expressions).  The adapter layer
bridges this gap:

```python
from gds_proof import GDSSymbolicBlock, GDSSymbolicModel, Invariant

# Wrap a Mechanism with symbolic expressions
block = GDSSymbolicBlock(
    block=mechanism,         # GDS AtomicBlock
    spec=spec,               # GDSSpec (for entity/symbol lookup)
    state_transition={"x_prev": X - U},
    output_expressions={"balance": X - U},
    predicates_list=[pred.expr],
    inputs=frozenset({U}),
)

# Wrap the spec with enrichments and invariants
model = GDSSymbolicModel(
    spec=spec,
    enrichments={"withdrawal": block},
    invariants_dict={"balance_nonneg": Invariant(...)},
)

# Results integrate with gds-framework VerificationReport
from gds_proof.findings import symbolic_analysis_to_findings, proof_findings_to_report
findings = symbolic_analysis_to_findings(analyze_invariants(model))
report = proof_findings_to_report("my_spec", findings)
```

`GDSSymbolicBlock` auto-derives `prev_state_symbols` from `Mechanism.updates`
+ `Entity.variables[var].symbol` when available.

---

## Block Formalism

Every block in the system is an open stateful system:

```
for u in U_{x_prev} <= U:
    x = f(x_prev, u)      # state transition
    y = c(x, u)           # observable output
```

- `x_prev` — pre-transition internal state (`prev_state_symbols`)
- `u` — input from the admissible set (`input_symbols`)
- `x` — post-transition state, not directly observable unless `c` reveals it
- `y` — observable output, expressed in terms of `x_prev + u` (with `x` substituted)

**Predicates** encode `U_{x_prev} = {u in U : check(f(x_prev, u)) = True}`:
- Free symbols in `prev_state_symbols | input_symbols`
- Constructed via `predicate_from_post_check(name, check(x), state_transition)`

**Open-world semantics**: port closure is NOT required.  Open inputs are
universally quantified over `U_{x_prev}`.

**Symbol rule**: symbols in invariants and substitutions must be PLAIN
(no assumptions baked in).  Assumptions belong in `model.assumption_context()`.

---

## Architecture

Ten modules across five directories:

| Module | Purpose |
|--------|---------|
| `types.py` | `SympyExpr`, `SympyBoolean` type aliases |
| `protocols.py` | `SymbolicBlock`, `SymbolicModel` protocols |
| `adapter.py` | `GDSSymbolicBlock`, `GDSSymbolicModel` — GDS type adapters |
| `findings.py` | Convert proof results to `Finding`/`VerificationReport` |
| `invariant.py` | `Invariant(BaseModel)` — named BooleanExpr with proof fields |
| `predicate.py` | `Predicate(BaseModel)` + `predicate_from_post_check()` |
| `identity/hashing.py` | `hash_model()`, `hash_proof()` — SHA-256 identity |
| `analysis/symbolic.py` | 5-strategy implication prover, `analyze_invariants()` |
| `analysis/inductive_safety.py` | 3-layer inductive safety, `analyze_inductive_safety()` |
| `analysis/proof.py` | `ProofScript`, `ProofBuilder`, `verify_proof()`, `attach_proof()` |
| `serialization/canonical.py` | `make_canonical_dict()`, `canonical_srepr()` |

### Naming: Inductive Safety vs. Reachability

`analysis/inductive_safety.py` was renamed from `analysis/reachability.py` to
avoid collision with `gds_analysis.reachability` (which computes concrete
forward/backward state sets via simulation).  This module proves **symbolic
inductive safety** via predicate implication.  Deprecated aliases
(`analyze_reachability`, `ReachabilityAnalysisResult`) remain for backward compat.

---

## Verification Integration

Proof results convert to gds-framework `Finding` objects with check IDs:

| Check ID | What it checks |
|----------|---------------|
| `PROOF-001` | Invariant preservation (symbolic analysis) |

`Finding.exportable_predicate` is populated with the invariant's `canonical_srepr`
form, making it available to the OWL/RDF exporter in gds-interchange.

Connection to gds-framework placeholder fields:
- `Finding.exportable_predicate` — populated by `symbolic_analysis_to_findings()`
- `TransitionSignature.preserves_invariant` — future: auto-discover invariants

---

## Proof Identity Chain

```
model.canonical_dict()
    -> hash_model(model) -> model_hash          # 64-char SHA-256 hex
          -> hash_proof(script, model_hash) -> proof_hash
                -> verify_proof(script, model_hash) -> ProofResult
                      -> attach_proof(inv, script, model_hash) -> Invariant
```

---

## Symbolic Analysis — Five Strategies

`analyze_invariants(model)` runs `_analyze_pair()` for every `(invariant, block)` pair.

| Strategy | When it fires |
|----------|--------------|
| `VACUITY` | Invariant symbols disjoint from block domain |
| `DIRECT_SIMPLIFICATION` | `simplify(post_inv)` -> True/False |
| `PREDICATE_IMPLICATION` | `simplify(Implies(And(preds, pre), post))` -> True/False |
| `Q_SYSTEM` | `sympy.ask()` with `model.assumption_context()` |
| `BARE_IMPLICATION` | `simplify(Implies(pre, post))` without predicates |
| `EXCEPTION` | TypeError / RecursionError / SympifyError raised |

---

## Inductive Safety — Three Layers

`analyze_inductive_safety(model)` runs three analyses:

1. **Single-step**: all invariants + predicates in antecedent
2. **Predicate sufficiency**: predicates alone (self-certifying blocks)
3. **Multi-step induction**: PROVED iff all single-step pairs are PROVED

---

## Lyapunov Stability Proofs (`analysis/lyapunov.py`)

Control-theoretic stability templates using SymPy. Does not use the five-strategy
prover from `symbolic.py` — performs its own Hessian-based definiteness checks.

| Function | What it proves |
|----------|---------------|
| `lyapunov_candidate(V, f, states)` | V(x) > 0 and dV/dt < 0 (continuous) or ΔV < 0 (discrete) |
| `quadratic_lyapunov(P, A)` | V = x'Px via P > 0 and A'P + PA < 0 (eigenvalue check) |
| `find_quadratic_lyapunov(A, Q)` | Solve A'P + PA = -Q for P (SymPy linear system) |
| `passivity_certificate(V, s, f, h)` | dV/dt ≤ s(u, y) for dissipativity |

Results are `LyapunovResult` / `PassivityResult` with `Literal["PROVED", "FAILED", "INCONCLUSIVE"]` status fields.

**Limitation:** Only handles quadratic forms (constant Hessian) definitively. Non-quadratic V returns INCONCLUSIVE. For systems with n > 4, `find_quadratic_lyapunov` may be slow (use `scipy.linalg.solve_continuous_lyapunov` in `gds-analysis` instead).

---

## Commands

```bash
uv run python -m pytest packages/gds-proof/tests -v
uv run ruff check packages/gds-proof/
uv run ruff format --check packages/gds-proof/
```

---

## Key Constraints for Contributors

1. **Plain symbols only** — never bake assumptions into symbols in invariants or
   substitutions.  Put them in `assumption_context()`.
2. **`attach_proof()` is the only write path for `proof_hash`** — never set it
   directly.  It enforces that `verify_proof()` returned VERIFIED first.
3. **`proof_method` is non-nullable** — every `InvariantMechanismResult` must
   carry a `ProofMethod` value.
4. **`substitution()` maps both state AND output symbols** — implementors must
   include both `{x_prev: f(x_prev, u)}` and `{y: c(f(x_prev, u), u)}` entries.
5. **`make_canonical_dict()` for all `canonical_dict()` implementations** —
   never roll your own sort logic.
6. **Use `GDSSymbolicBlock`/`GDSSymbolicModel` for GDS integration** — don't
   implement `SymbolicBlock`/`SymbolicModel` directly when working with GDS types.
