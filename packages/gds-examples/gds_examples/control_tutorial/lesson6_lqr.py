"""Lesson 6 -- LQR Optimal Control vs PID.

Replace the hand-tuned PID with a Linear Quadratic Regulator (LQR).
LQR computes the optimal gain matrix K by minimizing a cost function
J = integral(x'Qx + u'Ru) dt, balancing state error against control
effort. We compare step responses, design a Kalman observer, and
compute a gain schedule for varying load inertia.

New concepts:
    - lqr() -> (K, P, E) from gds_analysis.linear
    - kalman() -> (L, P) for observer design
    - gain_schedule() for multiple operating points
    - Q/R cost matrix design philosophy
    - compare_responses() for LQR vs PID

GDS Decomposition:
    X  = (theta, omega)
    U  = theta_ref
    g  = lqr_controller:  V = -K @ [theta - theta_ref, omega]
    f  = motor_dynamics
    Theta = {J, b, K_t, Q, R}

Composition:
    (reference | sensor) >> lqr_controller >> motor_dynamics
        .loop(dynamics -> sensor)
"""

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Plant linearization (analytical, matching Lesson 3)
# ---------------------------------------------------------------------------


def get_plant_ss() -> tuple[
    list[list[float]],
    list[list[float]],
    list[list[float]],
    list[list[float]],
]:
    """Return (A, B, C, D) for the open-loop DC motor plant."""
    A = [[0.0, 1.0], [0.0, -b / J]]
    B = [[0.0], [K_t / J]]
    C = [[1.0, 0.0]]
    D = [[0.0]]
    return A, B, C, D


# ---------------------------------------------------------------------------
# LQR design
# ---------------------------------------------------------------------------


def design_lqr(
    q_diag: tuple[float, float] = (100.0, 1.0),
    r_val: float = 1.0,
) -> tuple[list[list[float]], list[list[float]], list[complex]]:
    """Design LQR gains for the DC motor.

    Args:
        q_diag: Diagonal of Q (position error weight, velocity error weight).
        r_val: Control effort weight R.

    Returns (K, P, E): gain, Riccati solution, closed-loop eigenvalues.
    """
    from gds_analysis.linear import lqr

    A, B, _, _ = get_plant_ss()
    Q = [[q_diag[0], 0.0], [0.0, q_diag[1]]]
    R = [[r_val]]
    return lqr(A, B, Q, R)


def design_kalman() -> tuple[list[list[float]], list[list[float]]]:
    """Design Kalman observer for the DC motor.

    Returns (L, P): observer gain, error covariance.
    """
    from gds_analysis.linear import kalman

    A, _, C, _ = get_plant_ss()
    Q_process = [[0.01, 0.0], [0.0, 0.1]]  # process noise covariance
    R_measurement = [[0.001]]  # measurement noise covariance
    return kalman(A, C, Q_process, R_measurement)


def simulate_lqr(
    K: list[list[float]],
    theta_ref: float = 1.0,
    t_end: float = 3.0,
) -> tuple[list[float], list[float]]:
    """Simulate LQR-controlled motor: V = -K @ [theta - ref, omega].

    Returns (times, theta_values).
    """
    from gds_continuous import ODEModel, ODESimulation

    k1, k2 = K[0][0], K[0][1]

    def lqr_ode(t, y, params):
        theta, omega = y
        ref = params.get("theta_ref", 1.0)
        v = -k1 * (theta - ref) - k2 * omega
        dtheta = omega
        domega = -(b / J) * omega + (K_t / J) * v
        return [dtheta, domega]

    ode_model = ODEModel(
        state_names=["theta", "omega"],
        initial_state={"theta": 0.0, "omega": 0.0},
        rhs=lqr_ode,
        params={"theta_ref": [theta_ref]},
    )
    sim = ODESimulation(model=ode_model, t_span=(0.0, t_end), solver="RK45")
    results = sim.run()
    return results.times, results.state_array("theta")


def run_gain_schedule() -> list[tuple[dict, list[list[float]], list[complex]]]:
    """Compute LQR gains at 3 different load inertias.

    Simulates the motor with different payloads attached.
    """
    from gds_analysis.linear import gain_schedule

    def linearize_at_inertia(point):
        j = point["J"]
        A = [[0.0, 1.0], [0.0, -b / j]]
        B = [[0.0], [K_t / j]]
        C = [[1.0, 0.0]]
        D = [[0.0]]
        return A, B, C, D

    points = [{"J": 0.005}, {"J": 0.01}, {"J": 0.02}]
    Q = [[100.0, 0.0], [0.0, 1.0]]
    R = [[1.0]]

    return gain_schedule(linearize_at_inertia, points, Q, R)


if __name__ == "__main__":
    from gds_analysis.response import step_response_metrics

    print("=== Lesson 6: LQR Optimal Control ===\n")

    # --- LQR design ---
    K, P, E = design_lqr()
    print(f"LQR gain K = [{K[0][0]:.4f}, {K[0][1]:.4f}]")
    print(f"Riccati P diagonal = [{P[0][0]:.4f}, {P[1][1]:.4f}]")
    print("Closed-loop eigenvalues:")
    for e in E:
        print(f"  {e.real:.4f} + {e.imag:.4f}j")
    print(f"Closed-loop stable: {all(e.real < 0 for e in E)}")

    # --- LQR step response ---
    print("\n--- LQR step response ---")
    t_lqr, y_lqr = simulate_lqr(K)
    m_lqr = step_response_metrics(t_lqr, y_lqr, setpoint=1.0)
    print(f"  Rise time:   {m_lqr.rise_time:.3f} s")
    print(f"  Settling:    {m_lqr.settling_time:.3f} s")
    print(f"  Overshoot:   {m_lqr.overshoot_pct:.1f}%")

    # --- Compare with PID (from Lesson 3) ---
    from gds_examples.control_tutorial.lesson3_pid_transfer import simulate_pid

    t_pid, y_pid = simulate_pid(kp=10.0, ki=5.0, kd=0.5, t_end=3.0)
    m_pid = step_response_metrics(t_pid, y_pid, setpoint=1.0)

    print("\n--- LQR vs PID comparison ---")
    print(f"{'Metric':>15}  {'LQR':>8}  {'PID':>8}")
    print("-" * 36)
    print(f"{'Rise time':>15}  {m_lqr.rise_time:8.3f}  {m_pid.rise_time:8.3f}")
    print(f"{'Settling':>15}  {m_lqr.settling_time:8.3f}  {m_pid.settling_time:8.3f}")
    os_lqr, os_pid = m_lqr.overshoot_pct, m_pid.overshoot_pct
    print(f"{'Overshoot %':>15}  {os_lqr:8.1f}  {os_pid:8.1f}")

    # --- Kalman observer ---
    print("\n--- Kalman observer ---")
    L, P_obs = design_kalman()
    print(f"  Observer gain L = [{L[0][0]:.4f}, {L[1][0]:.4f}]'")

    # --- Gain schedule ---
    print("\n--- Gain schedule (varying inertia) ---")
    schedule = run_gain_schedule()
    print(f"{'J':>8}  {'K1':>10}  {'K2':>10}  {'eig1':>12}  {'eig2':>12}")
    print("-" * 58)
    for point, k, e in schedule:
        print(
            f"{point['J']:8.3f}  {k[0][0]:10.4f}  {k[0][1]:10.4f}"
            f"  {e[0].real:12.4f}  {e[1].real:12.4f}"
        )
    print("\n  Gains change with inertia — one K doesn't fit all loads.")
