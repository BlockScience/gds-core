"""Lesson 1 -- Modeling a DC Motor Plant.

Build a symbolic model of a DC motor that controls angular position.
The motor converts voltage to torque, which spins a shaft against
viscous friction. We declare the structural GDS spec (blocks, wiring,
roles) and the behavioral ODEs in a single SymbolicControlModel, then
simulate the open-loop response to a constant voltage step.

New concepts:
    - SymbolicControlModel (from gds_domains.symbolic)
    - StateEquation / OutputEquation for symbolic ODEs
    - compile_model() / compile_to_system() for GDS compilation
    - to_ode_function() -> ODEFunction for simulation
    - ODEModel / ODESimulation (from gds_continuous)

GDS Decomposition:
    X  = (theta, omega)        -- angular position, angular velocity
    U  = V                     -- voltage input
    g  = voltage_command       -- trivial pass-through (open-loop)
    f  = motor_dynamics        -- dtheta/dt = omega, domega/dt = ...
    Theta = {J, b, K_t}       -- inertia, damping, torque constant

Composition:
    voltage_input >> voltage_command >> motor_dynamics
"""

from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from gds_domains.control.dsl.compile import compile_model, compile_to_system
from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.symbolic.elements import OutputEquation, StateEquation
from gds_domains.symbolic.model import SymbolicControlModel

# ---------------------------------------------------------------------------
# Motor parameters (repeated in every lesson for standalone use)
# ---------------------------------------------------------------------------

J = 0.01  # moment of inertia (kg*m^2)
b = 0.1  # viscous damping coefficient (N*m*s/rad)
K_t = 0.01  # motor torque constant (N*m/A, simplified V->torque)


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------


def build_model() -> SymbolicControlModel:
    """Declare the DC motor as a SymbolicControlModel.

    Structural layer (what GDS sees):
        2 states, 1 input, 1 sensor, 1 controller

    Behavioral layer (what the ODE integrator sees):
        dtheta/dt = omega
        domega/dt = -(b/J)*omega + (K_t/J)*V
    """
    return SymbolicControlModel(
        name="DC Motor Plant",
        states=[
            State(name="theta", initial=0.0),
            State(name="omega", initial=0.0),
        ],
        inputs=[
            Input(name="V"),
        ],
        sensors=[
            Sensor(name="position_sensor", observes=["theta"]),
        ],
        controllers=[
            Controller(
                name="voltage_command",
                reads=["position_sensor", "V"],
                drives=["theta", "omega"],
            ),
        ],
        state_equations=[
            StateEquation(state_name="theta", expr_str="omega"),
            StateEquation(
                state_name="omega",
                expr_str=f"-({b}/{J})*omega + ({K_t}/{J})*V",
            ),
        ],
        output_equations=[
            OutputEquation(sensor_name="position_sensor", expr_str="theta"),
        ],
        symbolic_params=[],
        description="DC motor angular position control plant",
    )


def build_spec() -> GDSSpec:
    """Compile the SymbolicControlModel to a full GDSSpec."""
    return compile_model(build_model())


def build_system() -> SystemIR:
    """Compile to SystemIR with automatic composition tree."""
    return compile_to_system(build_model())


def simulate_open_loop(
    voltage: float = 1.0,
    t_end: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    """Simulate open-loop step response (constant voltage).

    Returns (times, theta_values, omega_values).
    """
    from gds_continuous import ODEModel, ODESimulation

    model = build_model()
    ode_fn, state_order = model.to_ode_function()

    ode_model = ODEModel(
        state_names=state_order,
        initial_state={"theta": 0.0, "omega": 0.0},
        rhs=ode_fn,
        params={"V": [voltage]},
    )
    sim = ODESimulation(
        model=ode_model,
        t_span=(0.0, t_end),
        solver="RK45",
    )
    results = sim.run()

    return (
        results.times,
        results.state_array("theta"),
        results.state_array("omega"),
    )


if __name__ == "__main__":
    # --- Structural layer ---
    model = build_model()
    print("=== Lesson 1: DC Motor Plant ===\n")
    print(f"Model: {model.name}")
    print(f"  States:      {[s.name for s in model.states]}")
    print(f"  Inputs:      {[i.name for i in model.inputs]}")
    print(f"  Sensors:     {[s.name for s in model.sensors]}")
    print(f"  Controllers: {[c.name for c in model.controllers]}")

    spec = build_spec()
    print(f"\nGDSSpec: {spec.name}")
    print(f"  Blocks:     {list(spec.blocks.keys())}")
    print(f"  Errors:     {spec.validate_spec()}")

    system = build_system()
    print(f"\nSystemIR: {len(system.blocks)} blocks, {len(system.wirings)} wirings")

    # --- Behavioral layer ---
    print("\n--- Open-loop simulation (V=1.0, 2 seconds) ---")
    times, theta, omega = simulate_open_loop(voltage=1.0, t_end=2.0)
    print(f"  Final theta = {theta[-1]:.4f} rad")
    print(f"  Final omega = {omega[-1]:.4f} rad/s")
    print("  (Motor spins up to steady velocity, position ramps)")
