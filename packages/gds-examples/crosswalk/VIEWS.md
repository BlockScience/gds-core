# Crosswalk Problem — Visualization Views

Six complementary views of the same model, from compiled topology
to mathematical decomposition to parameter traceability.
Key feature: discrete Markov state transitions with a single
design parameter (crosswalk location) demonstrating mechanism design.

## View 1: Structural
Compiled block graph from SystemIR. A pure linear pipeline with
no feedback or temporal wiring — 4 blocks in sequence.
All arrows are solid forward (covariant) flow.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Observe_Traffic([Observe Traffic]):::boundary
    Pedestrian_Decision[Pedestrian Decision]:::generic
    Safety_Check[Safety Check]:::generic
    Traffic_Transition[[Traffic Transition]]:::mechanism
    Observe_Traffic --Observation Signal--> Pedestrian_Decision
    Pedestrian_Decision --Crossing Decision--> Safety_Check
    Safety_Check --Safety Signal--> Traffic_Transition
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t -> U -> g -> d -> f -> X_{t+1}.
The ControlAction (Safety Check) populates the decision (d)
layer with crosswalk_location as the design parameter.

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
    X_t(["X_t<br/>traffic_state"]):::state
    X_next(["X_{t+1}<br/>traffic_state"]):::state
    Theta{{"Θ<br/>crosswalk_location"}}:::param
    subgraph U ["Boundary (U)"]
        Observe_Traffic[Observe Traffic]:::boundary
    end
    subgraph g ["Policy (g)"]
        Pedestrian_Decision[Pedestrian Decision]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Traffic_Transition[Traffic Transition]:::mechanism
    end
    subgraph ctrl ["Control"]
        Safety_Check[Safety Check]:::control
    end
    X_t --> U
    U --> g
    g --> f
    Traffic_Transition -.-> |Street.traffic_state| X_next
    f -.-> Safety_Check
    Safety_Check -.-> g
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style ctrl fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 3: Architecture by Role
Blocks grouped by GDS role — all 4 roles present:
- **BoundaryAction**: Observe Traffic (exogenous input)
- **Policy**: Pedestrian Decision (observation -> action)
- **ControlAction**: Safety Check (admissibility constraint)
- **Mechanism**: Traffic Transition (Markov state update)

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
        Observe_Traffic([Observe Traffic]):::boundary
    end
    subgraph policy ["Policy (g)"]
        Pedestrian_Decision[Pedestrian Decision]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Traffic_Transition[[Traffic Transition]]:::mechanism
    end
    subgraph control ["Control"]
        Safety_Check[Safety Check]:::control
    end
    entity_Street[("Street<br/>traffic_state: X")]:::entity
    Traffic_Transition -.-> entity_Street
    Observe_Traffic --ObservationSpace--> Pedestrian_Decision
    Pedestrian_Decision --CrossingDecisionSpace--> Safety_Check
    Safety_Check --SafetySignalSpace--> Traffic_Transition
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style control fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 4: Architecture by Domain
Blocks grouped by domain tag. Three domains:
Environment (observe + transition), Pedestrian (decision),
Infrastructure (safety check with crosswalk parameter).

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
    subgraph Environment ["Environment"]
        Observe_Traffic([Observe Traffic]):::boundary
        Traffic_Transition[[Traffic Transition]]:::mechanism
    end
    subgraph Pedestrian ["Pedestrian"]
        Pedestrian_Decision[Pedestrian Decision]:::policy
    end
    subgraph Infrastructure ["Infrastructure"]
        Safety_Check[Safety Check]:::control
    end
    entity_Street[("Street<br/>traffic_state: X")]:::entity
    Traffic_Transition -.-> entity_Street
    Observe_Traffic --ObservationSpace--> Pedestrian_Decision
    Pedestrian_Decision --CrossingDecisionSpace--> Safety_Check
    Safety_Check --SafetySignalSpace--> Traffic_Transition
```

## View 5: Parameter Influence
Theta -> blocks -> entities causal map. The single parameter
(crosswalk_location) flows through Safety Check only —
demonstrating that mechanism design operates at the
admissibility layer, not at the policy or mechanism level.

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
    param_crosswalk_location{{"crosswalk_location"}}:::param
    Safety_Check[Safety Check]
    entity_Street[("Street<br/>X")]:::entity
    param_crosswalk_location -.-> Safety_Check
    Traffic_Transition -.-> entity_Street
    Safety_Check --> Traffic_Transition
```

## View 6: Traceability — Street.traffic_state (X)
Traces Street.traffic_state backwards through the block graph.
Reveals the full causal chain from observation through pedestrian
decision, safety check (with crosswalk_location parameter), to
the traffic state transition.

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
    target(["Street.traffic_state (X)"]):::target
    Observe_Traffic[Observe Traffic]
    Pedestrian_Decision[Pedestrian Decision]
    Safety_Check[Safety Check]
    Traffic_Transition[Traffic Transition]
    param_crosswalk_location{{"crosswalk_location"}}:::param
    Traffic_Transition ==> target
    Observe_Traffic --> Pedestrian_Decision
    Pedestrian_Decision --> Safety_Check
    Safety_Check --> Traffic_Transition
    param_crosswalk_location -.-> Safety_Check
```
