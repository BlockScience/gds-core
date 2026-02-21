# Lotka-Volterra Predator-Prey — Visualization Views

Six complementary views of the same model, from compiled topology
to mathematical decomposition to parameter traceability.
Key feature: .loop() creates COVARIANT temporal wiring visible
as dashed arrows in the structural view.

## View 1: Structural
Compiled block graph from SystemIR. **Dashed arrows** show .loop()
temporal wiring — population signals flow from mechanisms back to
the policy at the NEXT timestep (contrast with thermostat's thick
feedback arrows which are within-timestep).

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Observe_Populations([Observe Populations]):::boundary
    Compute_Rates[Compute Rates]:::generic
    Update_Prey[Update Prey]:::generic
    Update_Predator[Update Predator]:::generic
    Observe_Populations --Population Signal--> Compute_Rates
    Compute_Rates --Prey Rate--> Update_Prey
    Compute_Rates --Predator Rate--> Update_Predator
    Update_Prey -.Population Signal..-> Compute_Rates
    Update_Predator -.Population Signal..-> Compute_Rates
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t → U → g → f → X_{t+1}.
The temporal loop is implicit in the X_t → X_{t+1} structure —
mechanisms produce the next state which becomes the next input.

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
    X_t(["X_t<br/>Prey.population, Predator.population"]):::state
    X_next(["X_{t+1}<br/>Prey.population, Predator.population"]):::state
    Theta{{"Θ<br/>predation_rate, predator_efficiency, prey_birth_rate, predator_death_rate"}}:::param
    subgraph U ["Boundary (U)"]
        Observe_Populations[Observe Populations]:::boundary
    end
    subgraph g ["Policy (g)"]
        Compute_Rates[Compute Rates]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Update_Prey[Update Prey]:::mechanism
        Update_Predator[Update Predator]:::mechanism
    end
    X_t --> U
    U --> g
    g --> f
    Update_Prey -.-> |Prey.population| X_next
    Update_Predator -.-> |Predator.population| X_next
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 3: Architecture by Role
Blocks grouped by GDS role. Note the mechanisms here have
forward_out ports (unlike SIR's terminal mechanisms), which
is what enables the .loop() temporal feedback.

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
        Observe_Populations([Observe Populations]):::boundary
    end
    subgraph policy ["Policy (g)"]
        Compute_Rates[Compute Rates]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Update_Prey[[Update Prey]]:::mechanism
        Update_Predator[[Update Predator]]:::mechanism
    end
    entity_Prey[("Prey<br/>population: x")]:::entity
    entity_Predator[("Predator<br/>population: y")]:::entity
    Update_Prey -.-> entity_Prey
    Update_Predator -.-> entity_Predator
    Observe_Populations --PopulationSignalSpace--> Compute_Rates
    Compute_Rates --RateSpace--> Update_Predator
    Compute_Rates --RateSpace--> Update_Prey
    Update_Prey --PopulationSignalSpace--> Compute_Rates
    Update_Predator --PopulationSignalSpace--> Compute_Rates
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 4: Architecture by Domain
Blocks grouped by domain tag. Shows species-specific vs. shared
blocks: Observe Populations and Compute Rates are 'Shared' because
they depend on both prey and predator populations.

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
    subgraph Shared ["Shared"]
        Observe_Populations([Observe Populations]):::boundary
        Compute_Rates[Compute Rates]:::policy
    end
    subgraph Prey ["Prey"]
        Update_Prey[[Update Prey]]:::mechanism
    end
    subgraph Predator ["Predator"]
        Update_Predator[[Update Predator]]:::mechanism
    end
    entity_Prey[("Prey<br/>population: x")]:::entity
    entity_Predator[("Predator<br/>population: y")]:::entity
    Update_Prey -.-> entity_Prey
    Update_Predator -.-> entity_Predator
    Observe_Populations --PopulationSignalSpace--> Compute_Rates
    Compute_Rates --RateSpace--> Update_Predator
    Compute_Rates --RateSpace--> Update_Prey
    Update_Prey --PopulationSignalSpace--> Compute_Rates
    Update_Predator --PopulationSignalSpace--> Compute_Rates
```

## View 5: Parameter Influence
Θ → blocks → entities causal map. All 4 rate parameters flow
through Compute Rates — each parameter indirectly affects BOTH
species because the Lotka-Volterra equations couple them.

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
    param_predation_rate{{"predation_rate"}}:::param
    param_predator_death_rate{{"predator_death_rate"}}:::param
    param_predator_efficiency{{"predator_efficiency"}}:::param
    param_prey_birth_rate{{"prey_birth_rate"}}:::param
    Compute_Rates[Compute Rates]
    entity_Predator[("Predator<br/>y")]:::entity
    entity_Prey[("Prey<br/>x")]:::entity
    param_predation_rate -.-> Compute_Rates
    param_predator_death_rate -.-> Compute_Rates
    param_predator_efficiency -.-> Compute_Rates
    param_prey_birth_rate -.-> Compute_Rates
    Update_Prey -.-> entity_Prey
    Update_Predator -.-> entity_Predator
    Compute_Rates --> Update_Predator
    Compute_Rates --> Update_Prey
    Update_Predator --> Compute_Rates
    Update_Prey --> Compute_Rates
```

## View 6: Traceability — Prey.population (x)
Traces Prey.population backwards through the block graph.
Reveals all parameters affecting prey dynamics — including predation_rate
which couples the predator population into the prey update.

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
    target(["Prey.population (x)"]):::target
    Compute_Rates[Compute Rates]
    Observe_Populations[Observe Populations]
    Update_Predator[Update Predator]
    Update_Prey[Update Prey]
    param_predation_rate{{"predation_rate"}}:::param
    param_predator_death_rate{{"predator_death_rate"}}:::param
    param_predator_efficiency{{"predator_efficiency"}}:::param
    param_prey_birth_rate{{"prey_birth_rate"}}:::param
    Update_Prey ==> target
    Compute_Rates --> Update_Prey
    Compute_Rates --> Update_Predator
    Observe_Populations --> Compute_Rates
    Update_Predator --> Compute_Rates
    Update_Prey --> Compute_Rates
    param_prey_birth_rate -.-> Compute_Rates
    param_predation_rate -.-> Compute_Rates
    param_predator_death_rate -.-> Compute_Rates
    param_predator_efficiency -.-> Compute_Rates
```
