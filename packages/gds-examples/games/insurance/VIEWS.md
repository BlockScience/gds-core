# Insurance Contract — Visualization Views

Six complementary views of the same model, from compiled topology
to mathematical decomposition to parameter traceability.
Key feature: the ControlAction role (Premium Calculation) completes
the 4-role GDS taxonomy — the only example to use all 4 roles.

## View 1: Structural
Compiled block graph from SystemIR. A pure linear pipeline with
no feedback or temporal wiring — the simplest topology alongside
SIR Epidemic. All arrows are solid forward (covariant) flow.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Claim_Arrival([Claim Arrival]):::boundary
    Risk_Assessment[Risk Assessment]:::generic
    Premium_Calculation[Premium Calculation]:::generic
    Claim_Payout[Claim Payout]:::generic
    Reserve_Update[[Reserve Update]]:::mechanism
    Claim_Arrival --Claim Event--> Risk_Assessment
    Risk_Assessment --Risk Score--> Premium_Calculation
    Premium_Calculation --Premium Decision--> Claim_Payout
    Claim_Payout --Payout Result--> Reserve_Update
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t → U → g → d → f → X_{t+1}.
The ControlAction (Premium Calculation) populates the decision (d)
layer — distinct from policy (g) and mechanism (f). This is the
only example where all canonical layers are populated.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart LR
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    X_t(["X_t<br/>reserve, premium_pool, coverage, claims_history"]):::state
    X_next(["X_{t+1}<br/>reserve, premium_pool, coverage, claims_history"]):::state
    Theta{{"Θ<br/>deductible, base_premium_rate, coverage_limit"}}:::param
    subgraph U ["Boundary (U)"]
        Claim_Arrival[Claim Arrival]:::boundary
    end
    subgraph g ["Policy (g)"]
        Risk_Assessment[Risk Assessment]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Claim_Payout[Claim Payout]:::mechanism
        Reserve_Update[Reserve Update]:::mechanism
    end
    subgraph ctrl ["Control"]
        Premium_Calculation[Premium Calculation]:::control
    end
    X_t --> U
    U --> g
    g --> f
    Claim_Payout -.-> |Policyholder.claims_history| X_next
    Claim_Payout -.-> |Policyholder.coverage| X_next
    Reserve_Update -.-> |Insurer.reserve| X_next
    Reserve_Update -.-> |Insurer.premium_pool| X_next
    f -.-> Premium_Calculation
    Premium_Calculation -.-> g
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style ctrl fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 3: Architecture by Role
Blocks grouped by GDS role — all 4 roles present:
- **BoundaryAction**: Claim Arrival (exogenous input)
- **Policy**: Risk Assessment (observation → assessment)
- **ControlAction**: Premium Calculation (admissibility control)
- **Mechanism**: Claim Payout + Reserve Update (state transitions)

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    subgraph boundary ["Boundary (U)"]
        Claim_Arrival([Claim Arrival]):::boundary
    end
    subgraph policy ["Policy (g)"]
        Risk_Assessment[Risk Assessment]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Claim_Payout[[Claim Payout]]:::mechanism
        Reserve_Update[[Reserve Update]]:::mechanism
    end
    subgraph control ["Control"]
        Premium_Calculation[Premium Calculation]:::control
    end
    entity_Insurer[("Insurer<br/>reserve: R, premium_pool: P")]:::entity
    entity_Policyholder[("Policyholder<br/>coverage: C, claims_history: H")]:::entity
    Reserve_Update -.-> entity_Insurer
    Claim_Payout -.-> entity_Policyholder
    Claim_Arrival --ClaimEventSpace--> Risk_Assessment
    Risk_Assessment --RiskScoreSpace--> Premium_Calculation
    Premium_Calculation --PremiumDecisionSpace--> Claim_Payout
    Claim_Payout --PayoutResultSpace--> Reserve_Update
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style control fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 4: Architecture by Domain
Blocks grouped by domain tag. Maps to insurance business units:
Claims (arrival + payout), Underwriting (risk + premium),
Reserves (financial accounting). Note that Underwriting owns
both the Policy and ControlAction roles.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    subgraph Claims ["Claims"]
        Claim_Arrival([Claim Arrival]):::boundary
        Claim_Payout[[Claim Payout]]:::mechanism
    end
    subgraph Underwriting ["Underwriting"]
        Risk_Assessment[Risk Assessment]:::policy
        Premium_Calculation[Premium Calculation]:::control
    end
    subgraph Reserves ["Reserves"]
        Reserve_Update[[Reserve Update]]:::mechanism
    end
    entity_Insurer[("Insurer<br/>reserve: R, premium_pool: P")]:::entity
    entity_Policyholder[("Policyholder<br/>coverage: C, claims_history: H")]:::entity
    Reserve_Update -.-> entity_Insurer
    Claim_Payout -.-> entity_Policyholder
    Claim_Arrival --ClaimEventSpace--> Risk_Assessment
    Risk_Assessment --RiskScoreSpace--> Premium_Calculation
    Premium_Calculation --PremiumDecisionSpace--> Claim_Payout
    Claim_Payout --PayoutResultSpace--> Reserve_Update
```

## View 5: Parameter Influence
Θ → blocks → entities causal map. All parameters flow through
Premium Calculation (ControlAction) only — risk assessment and
state updates are parameter-free. This confirms clean separation:
tuning Θ only changes the admissibility decision.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart LR
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    param_base_premium_rate{{"base_premium_rate"}}:::param
    param_coverage_limit{{"coverage_limit"}}:::param
    param_deductible{{"deductible"}}:::param
    Premium_Calculation[Premium Calculation]
    entity_Insurer[("Insurer<br/>R, P")]:::entity
    entity_Policyholder[("Policyholder<br/>C, H")]:::entity
    param_base_premium_rate -.-> Premium_Calculation
    param_coverage_limit -.-> Premium_Calculation
    param_deductible -.-> Premium_Calculation
    Reserve_Update -.-> entity_Insurer
    Claim_Payout -.-> entity_Policyholder
    Claim_Payout --> Reserve_Update
    Premium_Calculation --> Claim_Payout
```

## View 6: Traceability — Insurer.reserve (R)
Traces Insurer.reserve backwards through the block graph.
Reveals the full causal chain from claim arrival through risk assessment,
premium calculation (with all 3 Θ parameters), payout, to reserve update.
The complete audit trail for the insurer's financial position.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart RL
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    classDef entity fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#0f172a
    classDef param fill:#fdba74,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef state fill:#5eead4,stroke:#0d9488,stroke-width:2px,color:#134e4a
    classDef target fill:#fca5a5,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef empty fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,color:#475569
    target(["Insurer.reserve (R)"]):::target
    Claim_Arrival[Claim Arrival]
    Claim_Payout[Claim Payout]
    Premium_Calculation[Premium Calculation]
    Reserve_Update[Reserve Update]
    Risk_Assessment[Risk Assessment]
    param_base_premium_rate{{"base_premium_rate"}}:::param
    param_coverage_limit{{"coverage_limit"}}:::param
    param_deductible{{"deductible"}}:::param
    Reserve_Update ==> target
    Claim_Arrival --> Risk_Assessment
    Claim_Payout --> Reserve_Update
    Premium_Calculation --> Claim_Payout
    Risk_Assessment --> Premium_Calculation
    param_base_premium_rate -.-> Premium_Calculation
    param_deductible -.-> Premium_Calculation
    param_coverage_limit -.-> Premium_Calculation
```
