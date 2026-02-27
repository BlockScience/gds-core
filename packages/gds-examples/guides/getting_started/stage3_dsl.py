"""Stage 3 — Using a Domain DSL.

Rebuild the same thermostat model using the gds-control DSL. The DSL
lets you declare states, inputs, sensors, and controllers — the compiler
handles all type/space/entity/block/wiring generation automatically.

Contrast:
    Manual (stages 1-2):  ~60 lines of types, entities, blocks, interfaces
    DSL (this stage):     ~15 lines of declarations

The DSL produces the exact same GDS primitives: GDSSpec with entities,
blocks (BoundaryAction, Policy, Mechanism), wirings, and a SystemIR
with a temporal loop.

New concepts:
    - ControlModel declarative container
    - compile_model() -> GDSSpec
    - compile_to_system() -> SystemIR
    - How DSL elements map to GDS roles
"""

from gds.canonical import CanonicalGDS, project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds_control.dsl.compile import compile_model, compile_to_system
from gds_control.dsl.elements import Controller, Input, Sensor, State
from gds_control.dsl.model import ControlModel


def build_model() -> ControlModel:
    """Declare the thermostat as a ControlModel.

    Element -> GDS role mapping:
        State("temperature")  ->  Mechanism + Entity
        Input("heater")       ->  BoundaryAction
        Sensor("temp_sensor") ->  Policy (observer)
        Controller("thermo")  ->  Policy (decision logic)

    The compiler infers all types, spaces, interfaces, and wirings
    from these structural declarations. No manual port or token work.
    """
    return ControlModel(
        name="Thermostat DSL",
        states=[
            State(name="temperature", initial=20.0),
        ],
        inputs=[
            Input(name="heater"),
        ],
        sensors=[
            Sensor(name="temp_sensor", observes=["temperature"]),
        ],
        controllers=[
            Controller(
                name="thermo",
                reads=["temp_sensor", "heater"],
                drives=["temperature"],
            ),
        ],
        description="Thermostat built with the gds-control DSL",
    )


def build_spec() -> GDSSpec:
    """Compile the ControlModel to a full GDSSpec.

    The compiler auto-generates:
    - 4 semantic types (State, Reference, Measurement, Control)
    - 4 semantic spaces
    - 1 entity (temperature with a 'value' variable)
    - 4 blocks (1 BoundaryAction, 2 Policies, 1 Mechanism)
    - 1 SpecWiring with inter-block connections
    - 1 parameter (heater as exogenous reference)
    """
    return compile_model(build_model())


def build_system() -> SystemIR:
    """Compile to SystemIR with automatic composition tree.

    The compiler builds:
        (heater | temp_sensor) >> thermo >> temperature Dynamics
            .loop([temperature Dynamics -> temp_sensor COVARIANT])
    """
    return compile_to_system(build_model())


def build_canonical() -> CanonicalGDS:
    """Project the canonical h = f o g decomposition."""
    return project_canonical(build_spec())


if __name__ == "__main__":
    model = build_model()
    print(f"ControlModel: {model.name}")
    print(f"  States:      {[s.name for s in model.states]}")
    print(f"  Inputs:      {[i.name for i in model.inputs]}")
    print(f"  Sensors:     {[s.name for s in model.sensors]}")
    print(f"  Controllers: {[c.name for c in model.controllers]}")

    spec = build_spec()
    print(f"\nGDSSpec: {spec.name}")
    print(f"  Types:      {list(spec.types.keys())}")
    print(f"  Entities:   {list(spec.entities.keys())}")
    print(f"  Blocks:     {list(spec.blocks.keys())}")
    print(f"  Parameters: {list(spec.parameters.keys())}")
    print(f"  Errors:     {spec.validate_spec()}")

    system = build_system()
    print(f"\nSystemIR: {system.name}")
    print(f"  Blocks:   {[b.name for b in system.blocks]}")
    print(f"  Wirings:  {len(system.wirings)}")

    canonical = build_canonical()
    print(f"\nCanonical: {canonical.formula()}")
    print(f"  |X| = {len(canonical.state_variables)}")
    print(f"  |U| = {len(canonical.boundary_blocks)}")
    print(f"  |g| = {len(canonical.policy_blocks)}")
    print(f"  |f| = {len(canonical.mechanism_blocks)}")
