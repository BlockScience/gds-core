"""Lesson 7 -- Discretization and Discrete-Time Simulation.

Continuous-time controllers run on digital microcontrollers that update
at fixed sample rates. We convert the plant and LQR controller from
continuous to discrete time using Tustin and ZOH methods, verify
discrete stability (eigenvalues inside the unit circle), and simulate
in gds-sim's discrete-time engine.

New concepts:
    - discretize() with Tustin / ZOH methods (from gds_analysis.linear)
    - is_stable(A, continuous=False) for discrete stability
    - dlqr() for discrete-time LQR
    - gds_sim Model / Simulation for timestep-based execution
    - Sample rate sweep: effect of dt on performance

GDS Decomposition:
    X[k]  = (theta[k], omega[k])
    U[k]  = theta_ref
    g[k]  = discrete_lqr: V[k] = -K_d @ (X[k] - X_ref)
    f[k]  = X[k+1] = Ad @ X[k] + Bd @ V[k]
    Theta = {Ad, Bd, K_d, dt}

Composition:
    reference >> discrete_controller >> discrete_dynamics
        .loop(dynamics -> sensor)   [temporal, COVARIANT]
"""

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Discretization
# ---------------------------------------------------------------------------


def discretize_plant(
    dt: float = 0.01,
    method: str = "tustin",
) -> tuple[
    list[list[float]],
    list[list[float]],
    list[list[float]],
    list[list[float]],
]:
    """Discretize the DC motor plant at sample period dt.

    Returns (Ad, Bd, Cd, Dd).
    """
    from gds_analysis.linear import discretize

    A = [[0.0, 1.0], [0.0, -b / J]]
    B = [[0.0], [K_t / J]]
    C = [[1.0, 0.0]]
    D = [[0.0]]
    return discretize(A, B, C, D, dt, method=method)


def design_dlqr(
    dt: float = 0.01,
    q_diag: tuple[float, float] = (100.0, 1.0),
    r_val: float = 1.0,
) -> tuple[list[list[float]], list[list[float]], list[complex]]:
    """Design discrete-time LQR for the discretized plant.

    Returns (Kd, Pd, Ed): discrete gain, Riccati solution, eigenvalues.
    """
    from gds_analysis.linear import dlqr

    Ad, Bd, _Cd, _Dd = discretize_plant(dt, method="zoh")
    Q = [[q_diag[0], 0.0], [0.0, q_diag[1]]]
    R = [[r_val]]
    return dlqr(Ad, Bd, Q, R)


# ---------------------------------------------------------------------------
# Discrete simulation via gds-sim
# ---------------------------------------------------------------------------


def simulate_discrete(
    dt: float = 0.01,
    theta_ref: float = 1.0,
    n_steps: int = 300,
) -> tuple[list[float], list[float]]:
    """Simulate discrete-time LQR control using gds-sim.

    Returns (times, theta_values).
    """
    from gds_sim import Model, Simulation

    Ad, Bd, _Cd, _Dd = discretize_plant(dt, method="zoh")
    Kd, _Pd, _Ed = design_dlqr(dt)

    k1, k2 = Kd[0][0], Kd[0][1]

    def controller_policy(_params, _substep, _history, state):
        theta = state["theta"]
        omega = state["omega"]
        v = -k1 * (theta - theta_ref) - k2 * omega
        return {"voltage": v}

    def theta_suf(_params, _substep, _history, state, signal):
        theta = state["theta"]
        omega = state["omega"]
        v = signal["voltage"]
        theta_next = Ad[0][0] * theta + Ad[0][1] * omega + Bd[0][0] * v
        return ("theta", theta_next)

    def omega_suf(_params, _substep, _history, state, signal):
        theta = state["theta"]
        omega = state["omega"]
        v = signal["voltage"]
        omega_next = Ad[1][0] * theta + Ad[1][1] * omega + Bd[1][0] * v
        return ("omega", omega_next)

    model = Model(
        initial_state={"theta": 0.0, "omega": 0.0},
        state_update_blocks=[
            {
                "policies": {"controller": controller_policy},
                "variables": {"theta": theta_suf, "omega": omega_suf},
            },
        ],
        params={},
    )

    sim = Simulation(model=model, timesteps=n_steps, runs=1)
    results = sim.run()
    rows = results.to_list()

    times = [i * dt for i in range(len(rows))]
    theta_vals = [row["theta"] for row in rows]

    return times, theta_vals


# ---------------------------------------------------------------------------
# Sample rate sweep
# ---------------------------------------------------------------------------


def sample_rate_sweep(
    rates: list[float] | None = None,
) -> list[dict]:
    """Sweep sample rates and collect settling time metrics.

    Returns list of dicts with keys: dt, settling_time, overshoot_pct, stable.
    """
    from gds_analysis.linear import is_stable
    from gds_analysis.response import step_response_metrics

    if rates is None:
        rates = [0.001, 0.005, 0.01, 0.02, 0.05]

    results = []
    for dt in rates:
        Ad, _Bd, _Cd, _Dd = discretize_plant(dt, method="zoh")
        stable = is_stable(Ad, continuous=False)

        times, theta = simulate_discrete(dt=dt, n_steps=int(3.0 / dt))
        metrics = step_response_metrics(times, theta, setpoint=1.0)

        results.append(
            {
                "dt": dt,
                "settling_time": metrics.settling_time,
                "overshoot_pct": metrics.overshoot_pct,
                "stable": stable,
            }
        )
    return results


if __name__ == "__main__":
    from gds_analysis.linear import eigenvalues

    print("=== Lesson 7: Discretization + gds-sim ===\n")

    # --- Discretize ---
    dt = 0.01
    Ad, Bd, Cd, Dd = discretize_plant(dt, method="zoh")
    print(f"Discrete plant (ZOH, dt={dt}s):")
    print(f"  Ad = {Ad}")
    print(f"  Bd = {Bd}")

    eigs = eigenvalues(Ad)
    print(f"  Eigenvalues: {[f'{abs(e):.6f}' for e in eigs]}")
    print(f"  |lambda| < 1: {all(abs(e) < 1.0 for e in eigs)}")

    # --- Discrete LQR ---
    Kd, _Pd, Ed = design_dlqr(dt)
    print(f"\nDiscrete LQR gain Kd = [{Kd[0][0]:.4f}, {Kd[0][1]:.4f}]")
    print(f"  Closed-loop |lambda|: {[f'{abs(e):.6f}' for e in Ed]}")

    # --- Discrete simulation ---
    print(f"\n--- Discrete simulation (dt={dt}s, 300 steps) ---")
    times, theta = simulate_discrete(dt=dt)
    from gds_analysis.response import step_response_metrics

    m = step_response_metrics(times, theta, setpoint=1.0)
    print(f"  Rise time:   {m.rise_time:.3f} s")
    print(f"  Settling:    {m.settling_time:.3f} s")
    print(f"  Overshoot:   {m.overshoot_pct:.1f}%")

    # --- Sample rate sweep ---
    print("\n--- Sample rate sweep ---")
    print(f"{'dt':>8}  {'Settle':>8}  {'OS%':>8}  {'Stable':>8}")
    print("-" * 38)
    for r in sample_rate_sweep():
        print(
            f"{r['dt']:8.3f}  {r['settling_time']:8.3f}  "
            f"{r['overshoot_pct']:8.1f}  {'yes' if r['stable'] else 'NO':>8}"
        )
    print("\n  Slower sample rate -> worse performance, eventually unstable.")
