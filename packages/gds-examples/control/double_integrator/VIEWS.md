# Double Integrator — Visualization Views

Six complementary views of the same model, compiled from the
gds-control DSL. Classical state-space (A,B,C,D) maps to GDS
(X,U,g,f) — sensors are C (observation), controller is K (control law),
dynamics mechanisms are A (state transition).

## View 1: Structural
Compiled block graph from SystemIR. Note the temporal loops from
position/velocity Dynamics back to their respective sensors — state
at timestep t feeds observation at timestep t+1.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    force([force]):::boundary
    pos_sensor[pos_sensor]:::generic
    vel_sensor[vel_sensor]:::generic
    PD[PD]:::generic
    position_Dynamics[position Dynamics]:::generic
    velocity_Dynamics[velocity Dynamics]:::generic
    force --force Reference--> PD
    pos_sensor --pos_sensor Measurement--> PD
    vel_sensor --vel_sensor Measurement--> PD
    PD --PD Control--> position_Dynamics
    PD --PD Control--> velocity_Dynamics
    position_Dynamics -.position State..-> pos_sensor
    velocity_Dynamics -.velocity State..-> vel_sensor
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t → U → g → f → X_{t+1}.
g contains 3 policies (2 sensors + PD controller), f contains
2 mechanisms (position/velocity Dynamics). No ControlAction blocks.

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
    X_t(["X_t<br/>position.value, velocity.value"]):::state
    X_next(["X_{t+1}<br/>position.value, velocity.value"]):::state
    Theta{{"Θ<br/>force"}}:::param
    subgraph U ["Boundary (U)"]
        force[force]:::boundary
    end
    subgraph g ["Policy (g)"]
        pos_sensor[pos_sensor]:::policy
        vel_sensor[vel_sensor]:::policy
        PD[PD]:::policy
    end
    subgraph f ["Mechanism (f)"]
        position_Dynamics[position Dynamics]:::mechanism
        velocity_Dynamics[velocity Dynamics]:::mechanism
    end
    X_t --> U
    U --> g
    g --> f
    position_Dynamics -.-> |position.value| X_next
    velocity_Dynamics -.-> |velocity.value| X_next
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 3: Architecture by Role
Blocks grouped by GDS role. Only 3 roles used: BoundaryAction (force),
Policy (sensors + controller), Mechanism (dynamics). ControlAction
is intentionally unused — it would break the (A,B,C,D) mapping.

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
        force([force]):::boundary
    end
    subgraph policy ["Policy (g)"]
        pos_sensor[pos_sensor]:::policy
        vel_sensor[vel_sensor]:::policy
        PD[PD]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        position_Dynamics[[position Dynamics]]:::mechanism
        velocity_Dynamics[[velocity Dynamics]]:::mechanism
    end
    entity_position[("position<br/>value")]:::entity
    entity_velocity[("velocity<br/>value")]:::entity
    position_Dynamics -.-> entity_position
    velocity_Dynamics -.-> entity_velocity
    PD --ControlSpace--> position_Dynamics
    PD --ControlSpace--> velocity_Dynamics
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
```

## View 4: Architecture by Domain
Blocks grouped by domain tag assigned by the gds-control compiler.

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
    subgraph Ungrouped ["Ungrouped"]
        force([force]):::boundary
        pos_sensor[pos_sensor]:::policy
        vel_sensor[vel_sensor]:::policy
        PD[PD]:::policy
        position_Dynamics[[position Dynamics]]:::mechanism
        velocity_Dynamics[[velocity Dynamics]]:::mechanism
    end
    entity_position[("position<br/>value")]:::entity
    entity_velocity[("velocity<br/>value")]:::entity
    position_Dynamics -.-> entity_position
    velocity_Dynamics -.-> entity_velocity
    PD --ControlSpace--> position_Dynamics
    PD --ControlSpace--> velocity_Dynamics
```

## View 5: Parameter Influence
Θ → blocks → entities causal map. This model has no explicit
parameters — the DSL focuses on structural topology, not gains.

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
    no_params[No parameters defined]:::empty
```

## View 6: Traceability — position.value (x)
Traces position.value backwards through the block graph.
Reveals the causal chain: force reference + sensor measurements
→ PD controller → position Dynamics → position state.

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
    target(["position.value (value)"]):::target
    PD[PD]
    position_Dynamics[position Dynamics]
    position_Dynamics ==> target
    PD --> position_Dynamics
```
