"""Lesson 8 -- Lyapunov Stability Proof and Passivity Certificate.

Move from numerical stability checks (eigenvalues) to formal symbolic
proofs. A Lyapunov function V(x) > 0 with dV/dt < 0 is the control
theorist's invariant — it guarantees that energy is always dissipating.
We find V for the closed-loop motor, verify it symbolically, and then
prove passivity: the motor dissipates more energy than it stores.

New concepts:
    - quadratic_lyapunov(P, A) -- verify V = x'Px via eigenvalue check
    - find_quadratic_lyapunov(A) -- solve Lyapunov equation A'P + PA = -Q
    - lyapunov_candidate(V, f) -- verify custom V(x) symbolically
    - passivity_certificate(V, s, f, h) -- energy dissipation proof
    - LyapunovResult / PassivityResult result types

GDS Decomposition:
    X  = (theta, omega)
    U  = theta_ref
    g  = lqr_controller
    f  = motor_dynamics (closed-loop: A_cl = A - B*K)
    Theta = {J, b, K_t, K_lqr}

The Lyapunov function V(x) = x'Px is the "generalized energy" of the
closed-loop system. If V always decreases, the system is stable.
"""

# ---------------------------------------------------------------------------
# Motor parameters
# ---------------------------------------------------------------------------

J = 0.01
b = 0.1
K_t = 0.01


# ---------------------------------------------------------------------------
# Closed-loop system
# ---------------------------------------------------------------------------


def get_closed_loop_A() -> list[list[float]]:
    """Compute closed-loop A_cl = A - B*K using LQR from Lesson 6.

    Returns the 2x2 closed-loop state matrix.
    """
    from gds_analysis.linear import lqr

    A = [[0.0, 1.0], [0.0, -b / J]]
    B = [[0.0], [K_t / J]]
    Q = [[100.0, 0.0], [0.0, 1.0]]
    R = [[1.0]]

    K, _P, _E = lqr(A, B, Q, R)

    # A_cl = A - B*K
    A_cl = [
        [A[0][0] - B[0][0] * K[0][0], A[0][1] - B[0][0] * K[0][1]],
        [A[1][0] - B[1][0] * K[0][0], A[1][1] - B[1][0] * K[0][1]],
    ]
    return A_cl


# ---------------------------------------------------------------------------
# Lyapunov analysis
# ---------------------------------------------------------------------------


def prove_quadratic_lyapunov():
    """Find and verify a quadratic Lyapunov function for the closed-loop motor.

    Returns (P, result) where P is the Lyapunov matrix and result
    is a LyapunovResult with status fields.
    """
    from gds_proof.analysis.lyapunov import find_quadratic_lyapunov

    A_cl = get_closed_loop_A()
    return find_quadratic_lyapunov(A_cl)


def verify_custom_lyapunov():
    """Verify V(x) = theta^2 + omega^2 as a Lyapunov candidate.

    This is a simple "energy-like" function (not the optimal one).
    It may or may not prove stable depending on the dynamics.

    Returns LyapunovResult.
    """
    from gds_proof.analysis.lyapunov import lyapunov_candidate

    A_cl = get_closed_loop_A()

    # Build state transition from closed-loop A
    # d(theta)/dt = A_cl[0][0]*theta + A_cl[0][1]*omega
    # d(omega)/dt = A_cl[1][0]*theta + A_cl[1][1]*omega
    return lyapunov_candidate(
        V_expr="theta**2 + omega**2",
        state_transition={
            "theta": f"{A_cl[0][0]}*theta + {A_cl[0][1]}*omega",
            "omega": f"{A_cl[1][0]}*theta + {A_cl[1][1]}*omega",
        },
        state_symbols=["theta", "omega"],
        continuous=True,
    )


def prove_passivity():
    """Prove passivity of the open-loop motor plant.

    Storage function: V = 0.5 * J * omega^2  (kinetic energy)
    Supply rate:      s = K_t * V_input * omega  (torque times velocity = power in)
    Dynamics:         d(omega)/dt = -(b/J)*omega + (K_t/J)*V_input

    dV/dt = J * omega * domega/dt = -b*omega^2 + K_t*V_input*omega
    Dissipation: dV/dt - s = -b*omega^2 <= 0
    The damping term b*omega^2 is always non-negative, so the motor
    is passive (it dissipates energy through friction).

    Returns PassivityResult.
    """
    from gds_proof.analysis.lyapunov import passivity_certificate

    return passivity_certificate(
        V_expr=f"{J}/2 * omega**2",
        supply_rate=f"{K_t} * V_input * omega",
        state_transition={
            "omega": f"-({b}/{J})*omega + ({K_t}/{J})*V_input",
        },
        output_map={"y_omega": "omega"},
        state_symbols=["omega"],
        input_symbols=["V_input"],
    )


if __name__ == "__main__":
    from gds_analysis.linear import eigenvalues

    print("=== Lesson 8: Lyapunov Stability Proof ===\n")

    # --- Closed-loop system ---
    A_cl = get_closed_loop_A()
    eigs = eigenvalues(A_cl)
    print("Closed-loop A_cl:")
    print(f"  [{A_cl[0][0]:8.4f}, {A_cl[0][1]:8.4f}]")
    print(f"  [{A_cl[1][0]:8.4f}, {A_cl[1][1]:8.4f}]")
    print(f"  Eigenvalues: {[f'{e.real:.4f}' for e in eigs]}")

    # --- Find quadratic Lyapunov ---
    print("\n--- Quadratic Lyapunov (find P s.t. A'P + PA = -I) ---")
    result = prove_quadratic_lyapunov()
    if result is not None:
        P, lyap = result
        print(f"  P = [[{P[0][0]:.4f}, {P[0][1]:.4f}],")
        print(f"       [{P[1][0]:.4f}, {P[1][1]:.4f}]]")
        print(f"  Positive definite: {lyap.positive_definite}")
        print(f"  Decreasing:        {lyap.decreasing}")
        print(f"  STABLE:            {lyap.stable}")
    else:
        print("  Failed to find P (system may be unstable)")

    # --- Custom Lyapunov candidate ---
    print("\n--- Custom candidate: V = theta^2 + omega^2 ---")
    custom = verify_custom_lyapunov()
    print(f"  Positive definite: {custom.positive_definite}")
    print(f"  Decreasing:        {custom.decreasing}")
    print(f"  Stable:            {custom.stable}")
    if custom.dV_expr is not None:
        print(f"  dV/dt = {custom.dV_expr}")

    # --- Passivity ---
    print("\n--- Passivity certificate (open-loop motor) ---")
    passivity = prove_passivity()
    print(f"  Storage:     V = {passivity.storage_function}")
    print(f"  Supply rate: s = {passivity.supply_rate}")
    print(f"  Dissipation: {passivity.dissipation_proved}")
    print(f"  Passive:     {passivity.passive}")
    print("\n  Proof trace:")
    for line in passivity.details:
        print(f"    {line}")

    print("\n  The motor is passive: friction dissipates energy.")
    print("  Any passive controller guarantees closed-loop stability,")
    print("  even with unmodeled dynamics (passivity theorem).")
