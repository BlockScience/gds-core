# Thermostat PID — Visualization Views

Six complementary views of the same model, from compiled topology
to mathematical decomposition to parameter traceability.
Key feature: .feedback() creates CONTRAVARIANT (backward) wiring
visible as thick arrows in the structural view.

## View 1: Structural
Compiled block graph from SystemIR. The **thick arrow** from Room Plant
back to PID Controller shows the .feedback() CONTRAVARIANT wiring —
energy cost flows backward within the same timestep.

```mermaid
%%{init:{"theme":"neutral"}}%%
flowchart TD
    classDef boundary fill:#93c5fd,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef policy fill:#fcd34d,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef mechanism fill:#86efac,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef control fill:#d8b4fe,stroke:#9333ea,stroke-width:2px,color:#3b0764
    classDef generic fill:#cbd5e1,stroke:#64748b,stroke-width:1px,color:#1e293b
    Temperature_Sensor([Temperature Sensor]):::boundary
    PID_Controller[PID Controller]:::generic
    Room_Plant[Room Plant]:::generic
    Update_Room[[Update Room]]:::mechanism
    Temperature_Sensor --Measured Temperature--> PID_Controller
    PID_Controller --Heater Command--> Room_Plant
    Room_Plant --Room State--> Update_Room
    Room_Plant ==Energy Cost==> PID_Controller
```

## View 2: Canonical GDS Decomposition
Mathematical decomposition: X_t → U → g → f → X_{t+1}.
The ControlAction (Room Plant) maps to the control/decision layer,
distinct from the policy (PID Controller) and mechanism (Update Room).

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
    X_t(["X_t<br/>temperature, energy_consumed"]):::state
    X_next(["X_{t+1}<br/>temperature, energy_consumed"]):::state
    Theta{{"Θ<br/>Ki, setpoint, Kd, Kp"}}:::param
    subgraph U ["Boundary (U)"]
        Temperature_Sensor[Temperature Sensor]:::boundary
    end
    subgraph g ["Policy (g)"]
        PID_Controller[PID Controller]:::policy
    end
    subgraph f ["Mechanism (f)"]
        Update_Room[Update Room]:::mechanism
    end
    subgraph ctrl ["Control"]
        Room_Plant[Room Plant]:::control
    end
    X_t --> U
    U --> g
    g --> f
    Update_Room -.-> |Room.temperature| X_next
    Update_Room -.-> |Room.energy_consumed| X_next
    f -.-> Room_Plant
    Room_Plant -.-> g
    Theta -.-> g
    Theta -.-> f
    style U fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style g fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style f fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style ctrl fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 3: Architecture by Role
Blocks grouped by GDS role. This model uses 4 roles:
BoundaryAction (sensor), Policy (PID), ControlAction (plant),
Mechanism (update). Entity cylinders show the Room's two state variables.

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
        Temperature_Sensor([Temperature Sensor]):::boundary
    end
    subgraph policy ["Policy (g)"]
        PID_Controller[PID Controller]:::policy
    end
    subgraph mechanism ["Mechanism (f)"]
        Update_Room[[Update Room]]:::mechanism
    end
    subgraph control ["Control"]
        Room_Plant[Room Plant]:::control
    end
    entity_Room[("Room<br/>temperature: T, energy_consumed: E")]:::entity
    Update_Room -.-> entity_Room
    Temperature_Sensor --TemperatureSpace--> PID_Controller
    PID_Controller --CommandSpace--> Room_Plant
    Room_Plant --EnergyCostSpace--> PID_Controller
    Room_Plant --RoomStateSpace--> Update_Room
    style boundary fill:#dbeafe,stroke:#60a5fa,stroke-width:1px,color:#1e40af
    style policy fill:#fef3c7,stroke:#fbbf24,stroke-width:1px,color:#92400e
    style mechanism fill:#dcfce7,stroke:#4ade80,stroke-width:1px,color:#166534
    style control fill:#f3e8ff,stroke:#c084fc,stroke-width:1px,color:#581c87
```

## View 4: Architecture by Domain
Blocks grouped by domain tag. Maps to physical subsystems:
Sensor (temperature measurement), Controller (PID logic),
Plant (room + heater dynamics).

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
    subgraph Sensor ["Sensor"]
        Temperature_Sensor([Temperature Sensor]):::boundary
    end
    subgraph Controller ["Controller"]
        PID_Controller[PID Controller]:::policy
    end
    subgraph Plant ["Plant"]
        Room_Plant[Room Plant]:::control
        Update_Room[[Update Room]]:::mechanism
    end
    entity_Room[("Room<br/>temperature: T, energy_consumed: E")]:::entity
    Update_Room -.-> entity_Room
    Temperature_Sensor --TemperatureSpace--> PID_Controller
    PID_Controller --CommandSpace--> Room_Plant
    Room_Plant --EnergyCostSpace--> PID_Controller
    Room_Plant --RoomStateSpace--> Update_Room
```

## View 5: Parameter Influence
Θ → blocks → entities causal map. All parameters (setpoint, Kp, Ki, Kd)
flow through the PID Controller — confirming a single control point.

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
    param_Kd{{"Kd"}}:::param
    param_Ki{{"Ki"}}:::param
    param_Kp{{"Kp"}}:::param
    param_setpoint{{"setpoint"}}:::param
    PID_Controller[PID Controller]
    entity_Room[("Room<br/>T, E")]:::entity
    param_Kd -.-> PID_Controller
    param_Ki -.-> PID_Controller
    param_Kp -.-> PID_Controller
    param_setpoint -.-> PID_Controller
    Update_Room -.-> entity_Room
    PID_Controller --> Room_Plant
    Room_Plant --> PID_Controller
    Room_Plant --> Update_Room
```

## View 6: Traceability — Room.temperature (T)
Traces Room.temperature backwards through the block graph.
Reveals the full causal chain from sensor reading through PID control
to state update, including which parameters influence the outcome.

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
    target(["Room.temperature (T)"]):::target
    PID_Controller[PID Controller]
    Room_Plant[Room Plant]
    Temperature_Sensor[Temperature Sensor]
    Update_Room[Update Room]
    param_Kd{{"Kd"}}:::param
    param_Ki{{"Ki"}}:::param
    param_Kp{{"Kp"}}:::param
    param_setpoint{{"setpoint"}}:::param
    Update_Room ==> target
    PID_Controller --> Room_Plant
    Room_Plant --> PID_Controller
    Room_Plant --> Update_Room
    Temperature_Sensor --> PID_Controller
    param_setpoint -.-> PID_Controller
    param_Kp -.-> PID_Controller
    param_Ki -.-> PID_Controller
    param_Kd -.-> PID_Controller
```
