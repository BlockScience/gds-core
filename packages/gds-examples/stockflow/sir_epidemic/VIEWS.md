# SIR Epidemic — Visualization Views

Six complementary views of the same model, from compiled topology
to mathematical decomposition to parameter traceability.

## View 1: Structural
Compiled block graph from SystemIR. Shows composition topology with role-based shapes and wiring types.
- **Stadium shape** `([...])` = BoundaryAction (exogenous input)
- **Double-bracket** `[[...]]` = terminal Mechanism (state sink)
- **Solid arrow** = forward covariant flow

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Contact_Process([Contact Process]):::boundary
    Infection_Policy[Infection Policy]:::generic
    Update_Susceptible[[Update Susceptible]]:::mechanism
    Update_Infected[[Update Infected]]:::mechanism
    Update_Recovered[[Update Recovered]]:::mechanism
    Contact_Process --Contact Signal--> Infection_Policy
    Infection_Policy --Susceptible Delta--> Update_Susceptible
    Infection_Policy --Infected Delta--> Update_Infected
    Infection_Policy --Recovered Delta--> Update_Recovered
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t → U → g → f → X_{t+1}.
Shows the abstract dynamical system with state (X), input (U),
policy (g), mechanism (f), and parameter space (Θ).

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
    X_t(["X_t<br/>Susceptible.count, Infected.count, Recovered.count"]):::state
    X_next(["X_{t+1}<br/>Susceptible.count, Infected.count, Recovered.count"]):::state
    Theta{{"Θ<br/>gamma, beta, contact_rate"}}:::param
    subgraph U ["Boundary (U)"]
        Contact_Process[Contact Process]:::boundary
    end
    subgraph g ["Policy (g)"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Update_Susceptible[Update Susceptible]:::mechanism
        Update_Infected[Update Infected]:::mechanism
        Update_Recovered[Update Recovered]:::mechanism
    end
    X_t --> U
    U --> g
    g --> f
    Update_Susceptible -.-> |Susceptible.count| X_next
    Update_Infected -.-> |Infected.count| X_next
    Update_Recovered -.-> |Recovered.count| X_next
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 3: Architecture by Role
Blocks grouped by GDS role. Reveals the layered structure:
boundary (observation) → policy (decision) → mechanism (state update).
Entity cylinders show which state variables each mechanism writes.

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
        Contact_Process([Contact Process]):::boundary
    end
    subgraph policy ["Policy (g)"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Update_Susceptible[[Update Susceptible]]:::mechanism
        Update_Infected[[Update Infected]]:::mechanism
        Update_Recovered[[Update Recovered]]:::mechanism
    end
    entity_Susceptible[("Susceptible<br/>count: S")]:::entity
    entity_Infected[("Infected<br/>count: I")]:::entity
    entity_Recovered[("Recovered<br/>count: R")]:::entity
    Update_Susceptible -.-> entity_Susceptible
    Update_Infected -.-> entity_Infected
    Update_Recovered -.-> entity_Recovered
    Contact_Process --ContactSignalSpace--> Infection_Policy
    Infection_Policy --DeltaSpace--> Update_Infected
    Infection_Policy --DeltaSpace--> Update_Recovered
    Infection_Policy --DeltaSpace--> Update_Susceptible
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 4: Architecture by Domain
Blocks grouped by domain tag. Shows organizational ownership:
which subsystem or team is responsible for each block.

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
    subgraph Observation ["Observation"]
        Contact_Process([Contact Process]):::boundary
    end
    subgraph Decision ["Decision"]
        Infection_Policy[Infection Policy]:::policy
    end
    subgraph State_Update ["State Update"]
        Update_Susceptible[[Update Susceptible]]:::mechanism
        Update_Infected[[Update Infected]]:::mechanism
        Update_Recovered[[Update Recovered]]:::mechanism
    end
    entity_Susceptible[("Susceptible<br/>count: S")]:::entity
    entity_Infected[("Infected<br/>count: I")]:::entity
    entity_Recovered[("Recovered<br/>count: R")]:::entity
    Update_Susceptible -.-> entity_Susceptible
    Update_Infected -.-> entity_Infected
    Update_Recovered -.-> entity_Recovered
    Contact_Process --ContactSignalSpace--> Infection_Policy
    Infection_Policy --DeltaSpace--> Update_Infected
    Infection_Policy --DeltaSpace--> Update_Recovered
    Infection_Policy --DeltaSpace--> Update_Susceptible
```

## View 5: Parameter Influence
Θ → blocks → entities causal map. Answers: "if I change parameter X,
which state variables are affected?" Essential for sensitivity analysis.

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
    param_beta{{"beta"}}:::param
    param_contact_rate{{"contact_rate"}}:::param
    param_gamma{{"gamma"}}:::param
    Contact_Process[Contact Process]
    Infection_Policy[Infection Policy]
    entity_Infected[("Infected<br/>I")]:::entity
    entity_Recovered[("Recovered<br/>R")]:::entity
    entity_Susceptible[("Susceptible<br/>S")]:::entity
    param_beta -.-> Infection_Policy
    param_contact_rate -.-> Contact_Process
    param_gamma -.-> Infection_Policy
    Update_Susceptible -.-> entity_Susceptible
    Update_Recovered -.-> entity_Recovered
    Update_Infected -.-> entity_Infected
    Contact_Process --> Infection_Policy
    Infection_Policy --> Update_Infected
    Infection_Policy --> Update_Recovered
    Infection_Policy --> Update_Susceptible
```

## View 6: Traceability — Susceptible.count (S)
Traces Susceptible.count backwards through the block graph.
Answers: "what blocks and parameters influence this state variable?"
Useful for debugging unexpected behavior or planning targeted tests.

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
    target(["Susceptible.count (S)"]):::target
    Contact_Process[Contact Process]
    Infection_Policy[Infection Policy]
    Update_Susceptible[Update Susceptible]
    param_beta{{"beta"}}:::param
    param_contact_rate{{"contact_rate"}}:::param
    param_gamma{{"gamma"}}:::param
    Update_Susceptible ==> target
    Contact_Process --> Infection_Policy
    Infection_Policy --> Update_Susceptible
    param_contact_rate -.-> Contact_Process
    param_beta -.-> Infection_Policy
    param_gamma -.-> Infection_Policy
```
