# CLAUDE.md — gds-proof

## Package Identity

`gds-proof` provides deterministic model identity and SymPy-based invariant
proof verification for GDS models.  It is domain-agnostic: any object
satisfying `ProofableBlock` and `ProofableModel` can use it without importing
GDS-specific types.

- **Import**: `import gds_proof`
- **Dependencies**: `sympy>=1.12`, `pydantic>=2.0`
- **No dependency on `gds-framework`** — the package depends only on the
  structural protocols defined in `gds_proof.protocols`.

---

## Block Formalism

Every block in the system is an open stateful system:

```
for u ∈ U_{x_prev} ⊆ U:
    x = f(x_prev, u)      # state transition
    y = c(x, u)           # observable output
```

- `x_prev` — pre-transition internal state (`prev_state_symbols`)
- `u` — input from the admissible set (`input_symbols`)
- `x` — post-transition state, not directly observable unless `c` reveals it
- `y` — observable output, expressed in terms of `x_prev ∪ u` (with `x` substituted)
- `x_prev` does NOT appear explicitly in `c` — if a difference is needed,
  it is a dedicated state component in `x`

**Predicates** encode `U_{x_prev} = {u ∈ U : check(f(x_prev, u)) = True}`:
- Free symbols ⊆ `prev_state_symbols ∪ input_symbols`
- Constructed via `predicate_from_post_check(name, check(x), state_transition)`
- `post_state_form` field preserves the design intent for auditors

**Open-world semantics**: port closure is NOT required.  Open inputs are
universally quantified over `U_{x_prev}` — the predicate is the type system.
Invariants may reference output symbols of unwired blocks.  The composed
model is itself a block with open input product and full output product.

**Symbol rule**: symbols in invariants and substitutions must be PLAIN
(no assumptions baked in via `Symbol('x', nonnegative=True)`).  Assumptions
belong in `model.assumption_context()`.  Baked assumptions cause invariants
like `x >= 0` to simplify to `sympy.true` before the proof engine sees them.

---

## Architecture

Seven modules across four directories:

| Module | Purpose |
|--------|---------|
| `types.py` | `SympyExpr`, `SympyBoolean` type aliases |
| `protocols.py` | `ProofableBlock`, `ProofableModel` structural protocols |
| `invariant.py` | `Invariant(BaseModel)` — named BooleanExpr with proof fields |
| `predicate.py` | `Predicate(BaseModel)` + `predicate_from_post_check()` |
| `identity/hashing.py` | `hash_model()`, `hash_proof()` — SHA-256 identity |
| `analysis/symbolic.py` | 5-strategy implication prover, `analyze_invariants()` |
| `analysis/reachability.py` | 3-layer reachability, `analyze_reachability()` |
| `analysis/proof.py` | `ProofScript`, `ProofBuilder`, `verify_proof()`, `attach_proof()` |
| `serialization/canonical.py` | `make_canonical_dict()`, `canonical_srepr()`, `validate_block_predicates()` |

---

## Proof Identity Chain

```
model.canonical_dict()
    └─ hash_model(model) → model_hash          # 64-char SHA-256 hex
          └─ hash_proof(script, model_hash) → proof_hash
                └─ verify_proof(script, model_hash) → ProofResult
                      └─ attach_proof(inv, script, model_hash) → Invariant
```

- `model_hash` changes iff declared components change (excludes artifacts)
- `proof_hash` binds lemma chain content to a specific model version
- `attach_proof()` is the only sanctioned write path for `Invariant.proof_hash`
- `ProofScript.to_evidence()` / `from_evidence()` enable third-party re-verification

---

## Symbolic Analysis — Five Strategies

`analyze_invariants(model)` runs `_analyze_pair()` for every `(invariant, block)` pair.
Every result carries `proof_method` (non-nullable) recording which strategy fired:

| Strategy | When it fires |
|----------|--------------|
| `VACUITY` | Invariant symbols ∩ block domain = ∅ |
| `DIRECT_SIMPLIFICATION` | `simplify(post_inv)` → True/False |
| `PREDICATE_IMPLICATION` | `simplify(Implies(And(preds, pre), post))` → True/False |
| `Q_SYSTEM` | `sympy.ask()` with `model.assumption_context()` |
| `BARE_IMPLICATION` | `simplify(Implies(pre, post))` without predicates |
| `EXCEPTION` | TypeError / RecursionError / SympifyError raised |

Predicates in `PREDICATE_IMPLICATION` are pullbacks of post-state checks.
Including them in the antecedent exposes local block guarantees to the
global proof — this is the mechanism by which local invariants compose
into emergent global invariants.

---

## Reachability Analysis — Three Layers

`analyze_reachability(model)` runs three analyses:

1. **Single-step**: `[I_1 ∧ … ∧ I_n] ∧ [P_1 ∧ … ∧ P_m] → I_j(f(x, u))`
   — uses ALL invariants in the antecedent (starts from fully valid state)
2. **Predicate sufficiency**: `[P_1 ∧ … ∧ P_m] → I_j(f(x, u))`
   — tests whether the block is self-certifying for the invariant
3. **Multi-step induction**: PROVED iff all single-step pairs are PROVED

---

## Two Orthogonal Proof Fields on `Invariant`

```python
invariant.analytic_status   # "PROVED" | "DISPROVED" | "INCONCLUSIVE" | None
                            # Set by analyze_invariants() — automatic prover

invariant.proof_hash        # str | None
                            # Set by attach_proof() — user-authored ProofScript
```

These are independent.  `analytic_status = "INCONCLUSIVE"` + `proof_hash` set
is the primary use case for auxiliary proofs: the automatic prover cannot
resolve the pair, but the user constructs a targeted lemma chain that can.

---

## Lemma Kinds

```python
LemmaKind.EQUALITY   # simplify(expr - expected) == 0  or  expr.doit() == expected
LemmaKind.BOOLEAN    # simplify(expr) is sympy.true
LemmaKind.QUERY      # sympy.ask(expr, context) is True
```

Bitcoin 21M supply cap example (canonical demonstration):

```python
k = sympy.Symbol("k", integer=True, nonneg=True)
script = (
    ProofBuilder(model_hash, "total_supply_cap", "supply_cap_proof",
                 "Halving schedule converges to 21M BTC")
    .lemma("geometric_series", LemmaKind.EQUALITY,
           expr=Sum(210000 * 50 / 2**k, (k, 0, oo)),
           expected=Integer(21_000_000))
    .build()
)
result = verify_proof(script, model_hash)   # ProofStatus.VERIFIED
```

---

## Commands

```bash
# Run tests
uv run --package gds-proof pytest packages/gds-proof/tests -v

# Run with coverage
uv run --package gds-proof pytest packages/gds-proof/tests --cov=gds_proof

# Lint
uv run ruff check packages/gds-proof/

# Format check
uv run ruff format --check packages/gds-proof/
```

---

## Key Constraints for Contributors

1. **Plain symbols only** — never bake assumptions into symbols in invariants or
   substitutions.  Put them in `assumption_context()`.
2. **`attach_proof()` is the only write path for `proof_hash`** — never set it
   directly.  It enforces that `verify_proof()` returned VERIFIED first.
3. **`proof_method` is non-nullable** — every `InvariantMechanismResult` must
   carry a `ProofMethod` value.  The Pydantic validator enforces this.
4. **`substitution()` maps both state AND output symbols** — implementors must
   include both `{x_prev: f(x_prev, u)}` and `{y: c(f(x_prev, u), u)}` entries.
5. **`make_canonical_dict()` for all `canonical_dict()` implementations** —
   never roll your own sort logic.
