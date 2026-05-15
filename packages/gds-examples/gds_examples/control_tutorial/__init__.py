"""Classical Control Theory with GDS -- progressive tutorial.

A DC motor position controller serves as the running example across
eight lessons, each introducing new control theory concepts and the
GDS modules that implement them.

Lessons:
    1. lesson1_plant          -- Model the DC motor (SymbolicControlModel, ODE sim)
    2. lesson2_p_control      -- Proportional control and step response metrics
    3. lesson3_pid_transfer   -- PID, transfer functions, Bode analysis
    4. lesson4_disturbance    -- Disturbance rejection and sensitivity (Gang of Six)
    5. lesson5_delay          -- Sensor delay, Pade approximation, stability margins
    6. lesson6_lqr            -- LQR optimal control, Kalman filter, gain scheduling
    7. lesson7_discrete       -- Discretization and discrete-time simulation (gds-sim)
    8. lesson8_lyapunov       -- Lyapunov stability proof and passivity certificate
"""
