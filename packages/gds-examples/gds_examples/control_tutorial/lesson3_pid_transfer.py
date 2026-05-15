"""Lesson 3 -- PID, Transfer Functions, and Bode Analysis.

Upgrade from P to PID control, then cross into the frequency domain.
Linearize the plant to get (A, B, C, D) matrices, convert to a transfer
function, and analyze poles, zeros, controllability, and the Bode plot.

New concepts:
    - linearize() -> LinearizedSystem (A, B, C, D)
    - ss_to_tf() -> TransferFunctionMatrix
    - poles(), zeros(), is_controllable(), is_observable()
    - frequency_response() for numerical Bode data
    - bode_plot() for visualization

GDS Decomposition:
    X  = (theta, omega)
    U  = theta_ref
    g  = pid_controller:  V = Kp*e + Ki*integral(e) + Kd*de/dt
    f  = motor_dynamics
    Theta = {J, b, K_t, Kp, Ki, Kd}

Composition:
    (reference | position_sensor) >> pid_controller >> motor_dynamics
        .loop(dynamics -> position_sensor)
"""

from gds_domains.control.dsl.elements import Controller, Input, Sensor, State
from gds_domains.symbolic.elements import OutputEquation, StateEquation
from gds_domains.symbolic.model import SymbolicControlModel

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------


def build_model() -> SymbolicControlModel:
    """DC motor with PID controller embedded in the ODE.

    The integral of the error is modeled as an augmented state
    variable 'error_int'. This lets the PID law appear in the
    state equations without requiring a separate transfer function.
    """
    # PID: V = Kp*(ref-theta) + Ki*error_int + Kd*(0 - omega)
    # d(error_int)/dt = theta_ref - theta
    # Note: derivative term uses -omega (derivative of error = -omega
    # when theta_ref is constant)
    return SymbolicControlModel(
        name="DC Motor PID",
        states=[
            State(name="theta", initial=0.0),
            State(name="omega", initial=0.0),
        ],
        inputs=[
            Input(name="theta_ref"),
        ],
        sensors=[
            Sensor(name="position_sensor", observes=["theta"]),
        ],
        controllers=[
            Controller(
                name="pid_controller",
                reads=["position_sensor", "theta_ref"],
                drives=["theta", "omega"],
            ),
        ],
        state_equations=[
            StateEquation(state_name="theta", expr_str="omega"),
            StateEquation(
                state_name="omega",
                expr_str=(
                    f"-({b}/{J})*omega"
                    f" + ({K_t}/{J})*(Kp*(theta_ref - theta)"
                    f" + Ki*error_int"
                    f" + Kd*(0 - omega))"
                ),
            ),
        ],
        output_equations=[
            OutputEquation(sensor_name="position_sensor", expr_str="theta"),
        ],
        symbolic_params=["Kp", "Ki", "Kd", "error_int"],
        description="DC motor with PID position control",
    )


def get_plant_linearization():
    """Linearize the open-loop plant (no controller) at the origin.

    Returns LinearizedSystem with A, B, C, D for the 2-state motor.
    This is the PLANT only — no controller in the loop.
    """
    from gds_domains.symbolic.linearize import LinearizedSystem

    # Analytical state-space for the DC motor plant:
    #   A = [[0, 1], [0, -b/J]]
    #   B = [[0], [K_t/J]]
    #   C = [[1, 0]]  (position output)
    #   D = [[0]]
    return LinearizedSystem(
        A=[[0.0, 1.0], [0.0, -b / J]],
        B=[[0.0], [K_t / J]],
        C=[[1.0, 0.0]],
        D=[[0.0]],
        x0=[0.0, 0.0],
        u0=[0.0],
        state_names=["theta", "omega"],
        input_names=["V"],
        output_names=["theta_out"],
    )


def analyze_transfer_function():
    """Compute open-loop plant transfer function and properties.

    Returns (tf, plant_poles, plant_zeros, controllable, observable).
    """
    from gds_domains.symbolic.transfer import (
        is_controllable,
        is_observable,
        poles,
        ss_to_tf,
        zeros,
    )

    ls = get_plant_linearization()
    tf_mat = ss_to_tf(ls)
    tf = tf_mat.elements[0][0]

    return (
        tf,
        poles(tf),
        zeros(tf),
        is_controllable(ls),
        is_observable(ls),
    )


def simulate_pid(
    kp: float = 10.0,
    ki: float = 5.0,
    kd: float = 0.5,
    theta_ref: float = 1.0,
    t_end: float = 5.0,
) -> tuple[list[float], list[float]]:
    """Simulate PID-controlled motor.

    Uses a manually constructed ODE that includes the error integral
    as a third state variable (augmented system).
    """
    from gds_continuous import ODEModel, ODESimulation

    def pid_ode(t, y, params):
        theta, omega, err_int = y
        ref = params.get("theta_ref", 1.0)
        kp_ = params.get("Kp", 10.0)
        ki_ = params.get("Ki", 5.0)
        kd_ = params.get("Kd", 0.5)

        error = ref - theta
        v = kp_ * error + ki_ * err_int + kd_ * (0 - omega)

        dtheta = omega
        domega = -(b / J) * omega + (K_t / J) * v
        derr_int = error
        return [dtheta, domega, derr_int]

    ode_model = ODEModel(
        state_names=["theta", "omega", "error_int"],
        initial_state={"theta": 0.0, "omega": 0.0, "error_int": 0.0},
        rhs=pid_ode,
        params={
            "theta_ref": [theta_ref],
            "Kp": [kp],
            "Ki": [ki],
            "Kd": [kd],
        },
    )
    sim = ODESimulation(model=ode_model, t_span=(0.0, t_end), solver="RK45")
    results = sim.run()
    return results.times, results.state_array("theta")


if __name__ == "__main__":
    from gds_analysis.linear import eigenvalues, frequency_response, is_stable
    from gds_analysis.response import step_response_metrics

    print("=== Lesson 3: PID, Transfer Functions, Bode ===\n")

    # --- Plant linearization ---
    ls = get_plant_linearization()
    print("Plant state-space (open-loop):")
    print(f"  A = {ls.A}")
    print(f"  B = {ls.B}")
    print(f"  C = {ls.C}")
    print(f"  D = {ls.D}")

    eigs = eigenvalues(ls.A)
    print(f"  Eigenvalues: {[f'{e.real:.2f}' for e in eigs]}")
    print(f"  Open-loop stable: {is_stable(ls.A)}")

    # --- Transfer function ---
    tf, p, z, ctrl, obs = analyze_transfer_function()
    print(f"\nPlant TF: num={tf.num}, den={tf.den}")
    print(f"  Poles: {[f'{pi.real:.2f}+{pi.imag:.2f}j' for pi in p]}")
    print(f"  Zeros: {z}")
    print(f"  Controllable: {ctrl}")
    print(f"  Observable:   {obs}")

    # --- Frequency response ---
    omega, mag_db, phase_deg = frequency_response(ls.A, ls.B, ls.C, ls.D)
    print(f"\n  Bode data: {len(omega)} frequency points")

    # --- PID simulation ---
    print("\n--- PID step response (Kp=10, Ki=5, Kd=0.5) ---")
    times, theta = simulate_pid(kp=10.0, ki=5.0, kd=0.5)
    metrics = step_response_metrics(times, theta, setpoint=1.0)
    print(f"  Rise time:    {metrics.rise_time:.3f} s")
    print(f"  Settling:     {metrics.settling_time:.3f} s")
    print(f"  Overshoot:    {metrics.overshoot_pct:.1f}%")
    print(f"  SS error:     {metrics.steady_state_error:.4f}")
    print("  (Integral action eliminates steady-state error)")
