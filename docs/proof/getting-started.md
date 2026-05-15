# Getting Started

## Installation

```bash
uv add gds-proof
```

For development (monorepo):

```bash
git clone https://github.com/DynamicalSystemsGroup/gds-core.git
cd gds-core
uv sync --all-packages
```

## Your First Invariant Proof

The typical workflow: define a GDS spec, enrich blocks with symbolic expressions, declare invariants, and run the proof engine.

### 1. Define the structural spec

```python
import sympy
from gds import GDSSpec, Mechanism, Entity, interface, state_var, typedef

# Types and state
Balance = typedef("Balance", float)
account = Entity(
    name="Account",
    variables={"balance": state_var(Balance, symbol="x_prev")},
)

# Mechanism block
withdrawal = Mechanism(
    name="withdrawal",
    interface=interface(forward_in=["Balance Command"]),
    updates=[("Account", "balance")],
)

# Register in a spec
spec = GDSSpec(name="bank_account")
spec.collect(Balance, account, withdrawal)
```

### 2. Enrich with symbolic expressions

GDS blocks are structural -- they don't carry SymPy math. Use `GDSSymbolicBlock` to pair a block with its symbolic state transition:

```python
from gds_proof import (
    GDSSymbolicBlock, GDSSymbolicModel,
    Invariant, predicate_from_post_check,
)

X = sympy.Symbol("x_prev")  # pre-state (plain, no assumptions!)
U = sympy.Symbol("u")       # input

# Build a predicate: balance must remain positive after withdrawal
pred = predicate_from_post_check(
    name="no_overdraft",
    post_state_check=sympy.Symbol("x") > 0,   # desired post-state property
    state_transition={"x": X - U},             # x = x_prev - u
)

# Enrich the mechanism with symbolic expressions
symbolic_block = GDSSymbolicBlock(
    block=withdrawal,
    spec=spec,
    state_transition={"x_prev": X - U},        # f(x_prev, u) = x_prev - u
    output_expressions={"balance": X - U},      # observable output
    predicates_list=[pred.expr],                # admissibility guard
    inputs=frozenset({U}),
)
```

### 3. Declare invariants and run analysis

```python
from gds_proof import analyze_invariants, analyze_inductive_safety

# Build the proof-ready model
model = GDSSymbolicModel(
    spec=spec,
    enrichments={"withdrawal": symbolic_block},
    invariants_dict={
        "balance_nonneg": Invariant(
            name="balance_nonneg",
            expr=sympy.Ge(X, 0),  # x_prev >= 0
        ),
    },
    assumptions={
        X: {"nonnegative": True, "real": True},
        U: {"nonnegative": True, "real": True},
    },
)

# Run symbolic analysis
result = analyze_invariants(model)
for r in result.results:
    print(f"{r.invariant_name} x {r.mechanism_name}: "
          f"{r.status} ({r.proof_method})")

# Run inductive safety analysis
safety = analyze_inductive_safety(model)
print(f"Multi-step verdict: {safety.multi_step.verdict}")
```

### 4. Convert to VerificationReport

Integrate proof results with the existing verification pipeline:

```python
from gds_proof.findings import (
    symbolic_analysis_to_findings,
    proof_findings_to_report,
)

findings = symbolic_analysis_to_findings(result)
report = proof_findings_to_report("bank_account", findings)
print(f"Checks: {report.checks_total}, Errors: {report.errors}")
```

## Auxiliary Proofs for INCONCLUSIVE Results

When the automatic prover can't resolve a pair, build a manual proof script:

```python
from gds_proof import (
    hash_model, ProofBuilder, LemmaKind,
    verify_proof, attach_proof,
)

model_hash = hash_model(model)

# Build a proof script with a geometric series lemma
k = sympy.Symbol("k", integer=True, nonneg=True)
script = (
    ProofBuilder(
        model_hash, "balance_nonneg",
        "convergence_proof", "Balance converges to steady state",
    )
    .lemma(
        "series_limit",
        LemmaKind.EQUALITY,
        expr=sympy.Sum(sympy.Rational(1, 2) ** k, (k, 0, sympy.oo)),
        expected=sympy.Integer(2),
    )
    .build()
)

# Verify independently (no trust in original analyst)
proof_result = verify_proof(script, model_hash)
print(f"Proof status: {proof_result.status}")

# Attach to invariant if VERIFIED
if proof_result.status == "VERIFIED":
    inv = model.invariants()["balance_nonneg"]
    inv = attach_proof(inv, script, model_hash)
    print(f"Proof hash: {inv.proof_hash}")
```

## Next Steps

- [Proof Overview](index.md) -- architecture, key concepts, and verification integration
- [Framework](../framework/index.md) -- GDS specification and structural types
- [Analysis](../analysis/index.md) -- simulation-based reachability and PSUU
