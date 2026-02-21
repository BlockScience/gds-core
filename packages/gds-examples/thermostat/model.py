"""Thermostat PID Control — feedback composition with CONTRAVARIANT wiring.

Demonstrates .feedback() for backward information flow within a timestep.
The Room Plant sends an Energy Cost signal backward to the PID Controller,
enabling cost-aware control decisions.

Concepts Covered:
    - .feedback() composition for within-timestep backward flow
    - CONTRAVARIANT flow direction (backward_out → backward_in)
    - ControlAction role — reads state and emits control signals
    - backward_in / backward_out ports on block interfaces
    - Multi-variable Entity (Room has temperature + energy_consumed)

Prerequisites: sir_epidemic (for basic roles, >>, |, TypeDef, Entity basics)

GDS Decomposition:
    X  = (T, E)             — room temperature, cumulative energy consumed
    U  = measured_temp       — exogenous sensor reading
    g  = pid_controller      — PID policy: computes heater command from
                               measured temp + energy cost feedback
    f  = update_room         — applies temperature and energy changes to X
    Θ  = {setpoint, Kp, Ki, Kd}

Composition: (sensor >> controller >> plant >> update).feedback(
    [Energy Cost: plant -> controller CONTRAVARIANT]
)
"""

from gds.blocks.composition import Wiring
from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.compiler.compile import compile_system
from gds.ir.models import FlowDirection, SystemIR
from gds.spaces import Space
from gds.spec import GDSSpec, SpecWiring, Wire
from gds.state import Entity, StateVariable
from gds.types.interface import Interface, port
from gds.types.typedef import TypeDef

# ══════════════════════════════════════════════════════════════════
# Types — runtime data validation via TypeDef
# GDS Mapping: Constrain the values that flow through spaces and
# state variables. Temperature is unconstrained (can be negative),
# while HeaterPower and EnergyCost must be non-negative.
# ══════════════════════════════════════════════════════════════════

# No constraint — temperature can be any float (including negative).
Temperature = TypeDef(
    name="Temperature",
    python_type=float,
    description="Temperature in degrees Celsius",
)

# Physical constraint: power output cannot be negative.
HeaterPower = TypeDef(
    name="HeaterPower",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Heater power output (watts)",
)

# Cumulative cost is monotonically non-decreasing.
EnergyCost = TypeDef(
    name="EnergyCost",
    python_type=float,
    constraint=lambda x: x >= 0,
    description="Cumulative energy cost",
)

# PID gains can be any float (including negative for derivative damping).
GainParam = TypeDef(
    name="GainParam",
    python_type=float,
    description="PID controller gain parameter",
)

# ══════════════════════════════════════════════════════════════════
# Entities — state space X dimensions
# GDS Mapping: Room is a multi-variable entity contributing two
# dimensions to X. Unlike sir_epidemic where each entity has one
# variable, this shows that entities can bundle related state.
# ══════════════════════════════════════════════════════════════════

# X = (T, E) — two state variables in a single entity
# T tracks the physical temperature, E tracks cumulative energy use.
room = Entity(
    name="Room",
    variables={
        "temperature": StateVariable(
            name="temperature", typedef=Temperature, symbol="T"
        ),
        "energy_consumed": StateVariable(
            name="energy_consumed", typedef=EnergyCost, symbol="E"
        ),
    },
    description="Room with temperature and energy tracking",
)

# ══════════════════════════════════════════════════════════════════
# Spaces — typed communication channels between blocks
# GDS Mapping: Four spaces carry signals along the pipeline. Note
# energy_cost_space flows BACKWARD (contravariant) — it uses the
# same Space mechanism but the Wiring direction determines flow.
# ══════════════════════════════════════════════════════════════════

# Forward: sensor → controller (measured temperature reading)
temperature_space = Space(
    name="TemperatureSpace",
    fields={"temperature": Temperature},
)

# Forward: controller → plant (heater power command)
command_space = Space(
    name="CommandSpace",
    fields={"heater_power": HeaterPower},
)

# Forward: plant → update mechanism (new temperature + energy to write)
room_state_space = Space(
    name="RoomStateSpace",
    fields={"temperature": Temperature, "energy": EnergyCost},
)

# Backward: plant → controller (energy cost for cost-aware control)
# This space flows CONTRAVARIANT — backward within the same timestep.
energy_cost_space = Space(
    name="EnergyCostSpace",
    fields={"cost": EnergyCost},
)

# ══════════════════════════════════════════════════════════════════
# Blocks — role decomposition with backward ports for feedback
# GDS Mapping: This model introduces two new concepts vs sir_epidemic:
#   1. backward_in / backward_out ports on interfaces
#   2. ControlAction role (reads state, emits control signals)
# The feedback loop is WITHIN a timestep (not across timesteps).
# ══════════════════════════════════════════════════════════════════

# BoundaryAction: exogenous temperature reading (same role as sir_epidemic).
temperature_sensor = BoundaryAction(
    name="Temperature Sensor",
    interface=Interface(
        forward_out=(port("Measured Temperature"),),
    ),
    tags={"domain": "Sensor"},
)

# Policy with backward_in: the PID controller receives energy cost feedback
# from the plant WITHIN the same timestep. This backward_in port is what
# makes .feedback() possible — it accepts contravariant signals.
pid_controller = Policy(
    name="PID Controller",
    interface=Interface(
        forward_in=(port("Measured Temperature"),),
        forward_out=(port("Heater Command"),),
        backward_in=(port("Energy Cost"),),  # Receives feedback from plant
    ),
    params_used=["setpoint", "Kp", "Ki", "Kd"],
    tags={"domain": "Controller"},
)

# ControlAction: a new role not seen in sir_epidemic.
# Unlike Mechanism (which writes state), ControlAction reads state and
# emits control signals. It has both forward_in, forward_out, AND
# backward_out — the backward_out port sends energy cost back to the
# controller within the same timestep.
room_plant = ControlAction(
    name="Room Plant",
    interface=Interface(
        forward_in=(port("Heater Command"),),
        forward_out=(port("Room State"),),
        backward_out=(port("Energy Cost"),),  # Sends feedback to controller
    ),
    tags={"domain": "Plant"},
)

# Mechanism: writes the updated temperature and energy to entity state.
# Same role as sir_epidemic — forward_in only, declares what it updates.
update_room = Mechanism(
    name="Update Room",
    interface=Interface(
        forward_in=(port("Room State"),),
    ),
    updates=[("Room", "temperature"), ("Room", "energy_consumed")],
    tags={"domain": "Plant"},
)


def build_spec() -> GDSSpec:
    """Build the complete thermostat PID specification.

    Note the wiring includes a backward wire (Room Plant → PID Controller)
    using EnergyCostSpace. In SpecWiring, backward wires look like normal
    Wire entries — the direction is determined by the port types on the
    blocks' interfaces (backward_out → backward_in).
    """
    spec = GDSSpec(
        name="Thermostat PID",
        description="PID-controlled thermostat with energy cost feedback",
    )

    # Types
    spec.register_type(Temperature)
    spec.register_type(HeaterPower)
    spec.register_type(EnergyCost)
    spec.register_type(GainParam)

    # Spaces
    spec.register_space(temperature_space)
    spec.register_space(command_space)
    spec.register_space(room_state_space)
    spec.register_space(energy_cost_space)

    # Entities
    spec.register_entity(room)

    # Blocks
    spec.register_block(temperature_sensor)
    spec.register_block(pid_controller)
    spec.register_block(room_plant)
    spec.register_block(update_room)

    # Parameters — the configuration space Θ
    spec.register_parameter("setpoint", Temperature)
    spec.register_parameter("Kp", GainParam)
    spec.register_parameter("Ki", GainParam)
    spec.register_parameter("Kd", GainParam)

    # Wiring — includes both forward and backward connections
    spec.register_wiring(
        SpecWiring(
            name="Thermostat Loop",
            block_names=[
                "Temperature Sensor",
                "PID Controller",
                "Room Plant",
                "Update Room",
            ],
            wires=[
                Wire(
                    source="Temperature Sensor",
                    target="PID Controller",
                    space="TemperatureSpace",
                ),
                Wire(
                    source="PID Controller", target="Room Plant", space="CommandSpace"
                ),
                Wire(source="Room Plant", target="Update Room", space="RoomStateSpace"),
                # Backward wire: plant sends energy cost back to controller
                Wire(
                    source="Room Plant",
                    target="PID Controller",
                    space="EnergyCostSpace",
                ),
            ],
        )
    )

    return spec


def build_system() -> SystemIR:
    """Build and compile the thermostat system with feedback.

    Step-by-step composition:
      1. Build the forward pipeline with >> (same as sir_epidemic)
      2. Add .feedback() with an explicit CONTRAVARIANT wiring

    .feedback() creates a FeedbackLoop node in the composition tree.
    Unlike .loop() (temporal, across timesteps), .feedback() operates
    WITHIN a single timestep — the plant computes and sends energy cost
    back to the controller before the timestep ends.

    The Wiring specifies:
      - source_block/port: where the backward signal originates
      - target_block/port: where it arrives
      - direction=CONTRAVARIANT: marks this as backward flow
    """
    # Step 1: Forward sequential pipeline (same pattern as sir_epidemic)
    pipeline = temperature_sensor >> pid_controller >> room_plant >> update_room
    # Step 2: Add within-timestep feedback via .feedback()
    system = pipeline.feedback(
        [
            Wiring(
                source_block="Room Plant",
                source_port="Energy Cost",
                target_block="PID Controller",
                target_port="Energy Cost",
                direction=FlowDirection.CONTRAVARIANT,
            )
        ]
    )
    return compile_system(name="Thermostat PID", root=system)
