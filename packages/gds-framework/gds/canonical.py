"""Canonical GDS projection — derives the formal h = f ∘ g structure.

The canonical projection extracts the mathematical GDS decomposition
from a GDSSpec:

    h_θ : X → X  where θ ∈ Θ

    X = state space (product of entity variables)
    U = input space (BoundaryAction outputs)
    W = disturbance space (disturbance-tagged BoundaryAction outputs)
    U_c = controlled input space (Z minus W)
    D = decision space (Policy outputs)
    g = policy mapping: X x U_c → D
    f = state transition: X x D x W → X
    Θ = parameter space (ParameterSchema)

This is a **pure function** of GDSSpec — always derivable, never authoritative.
GDSSpec remains ground truth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from gds.blocks.roles import BoundaryAction, ControlAction, Mechanism, Policy
from gds.parameters import ParameterSchema

if TYPE_CHECKING:
    from gds.spec import GDSSpec


class CanonicalGDS(BaseModel):
    """Canonical projection of a GDSSpec to formal GDS structure.

    Pure derivation — always computable, never authoritative.
    GDSSpec remains ground truth.
    """

    model_config = ConfigDict(frozen=True)

    # State space X: entity.variable entries
    state_variables: tuple[tuple[str, str], ...] = ()

    # Parameter space Θ
    parameter_schema: ParameterSchema = Field(default_factory=ParameterSchema)

    # Controlled input space U_c: (block_name, port_name)
    # from non-disturbance BoundaryAction forward_out
    input_ports: tuple[tuple[str, str], ...] = ()

    # Disturbance space W: (block_name, port_name)
    # from disturbance-tagged BoundaryAction forward_out
    disturbance_ports: tuple[tuple[str, str], ...] = ()

    # Decision space D: (block_name, port_name) from Policy forward_out
    decision_ports: tuple[tuple[str, str], ...] = ()

    # Structural decomposition: block names by role
    boundary_blocks: tuple[str, ...] = ()
    control_blocks: tuple[str, ...] = ()
    policy_blocks: tuple[str, ...] = ()
    mechanism_blocks: tuple[str, ...] = ()

    # Mechanism update targets: (entity, variable) per mechanism
    update_map: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()

    # Admissibility deps: (constraint_name, ((entity, var), ...))
    admissibility_map: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()

    # Mechanism read deps: (mechanism_name, ((entity, var), ...))
    read_map: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()

    @property
    def has_parameters(self) -> bool:
        """True if the system has any parameters."""
        return len(self.parameter_schema) > 0

    @property
    def has_disturbances(self) -> bool:
        """True if the system has disturbance-tagged inputs."""
        return len(self.disturbance_ports) > 0

    def formula(self) -> str:
        """Render as mathematical formula string."""
        has_f = len(self.mechanism_blocks) > 0
        has_g = len(self.policy_blocks) > 0

        if has_f and has_g:
            decomp = "f ∘ g"
        elif has_g:
            decomp = "g"
        elif has_f:
            decomp = "f"
        else:
            decomp = "id"

        if self.has_parameters:
            decomp_theta = decomp.replace("f", "f_θ").replace("g", "g_θ")
            if self.has_disturbances:
                return f"h_θ : X → X  (h = {decomp_theta}, θ ∈ Θ); f : X x D x W → X"
            return f"h_θ : X → X  (h = {decomp_theta}, θ ∈ Θ)"

        if self.has_disturbances:
            return f"h : X → X  (h = {decomp}); f : X x D x W → X"
        return f"h : X → X  (h = {decomp})"


def project_canonical(spec: GDSSpec) -> CanonicalGDS:
    """Pure function: GDSSpec → CanonicalGDS.

    Deterministic, stateless. Never mutates the spec.
    """
    # 1. State space X: all entity variables
    state_variables: list[tuple[str, str]] = []
    for entity in spec.entities.values():
        for var_name in entity.variables:
            state_variables.append((entity.name, var_name))

    # 2. Parameter space Θ
    parameter_schema = spec.parameter_schema

    # 3. Classify blocks by role
    boundary_blocks: list[str] = []
    control_blocks: list[str] = []
    policy_blocks: list[str] = []
    mechanism_blocks: list[str] = []

    for bname, block in spec.blocks.items():
        if isinstance(block, BoundaryAction):
            boundary_blocks.append(bname)
        elif isinstance(block, ControlAction):
            control_blocks.append(bname)
        elif isinstance(block, Policy):
            policy_blocks.append(bname)
        elif isinstance(block, Mechanism):
            mechanism_blocks.append(bname)

    # 4. Partition BoundaryAction ports: controlled (U_c) vs disturbance (W)
    input_ports: list[tuple[str, str]] = []
    disturbance_ports: list[tuple[str, str]] = []
    for bname in boundary_blocks:
        block = spec.blocks[bname]
        is_disturbance = getattr(block, "tags", {}).get("role") == "disturbance"
        target = disturbance_ports if is_disturbance else input_ports
        for p in block.interface.forward_out:
            target.append((bname, p.name))

    # 5. Decision space D: Policy forward_out ports
    decision_ports: list[tuple[str, str]] = []
    for bname in policy_blocks:
        block = spec.blocks[bname]
        for p in block.interface.forward_out:
            decision_ports.append((bname, p.name))

    # 6. Mechanism update targets
    update_map: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for bname in mechanism_blocks:
        block = spec.blocks[bname]
        if isinstance(block, Mechanism):
            updates = tuple(tuple(pair) for pair in block.updates)
            update_map.append((bname, updates))  # type: ignore[arg-type]

    # 7. Admissibility dependencies
    admissibility_map: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for ac_name, ac in spec.admissibility_constraints.items():
        deps = tuple(tuple(pair) for pair in ac.depends_on)
        admissibility_map.append((ac_name, deps))  # type: ignore[arg-type]

    # 8. Transition read map
    read_map: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for mname, ts in spec.transition_signatures.items():
        reads = tuple(tuple(pair) for pair in ts.reads)
        read_map.append((mname, reads))  # type: ignore[arg-type]

    return CanonicalGDS(
        state_variables=tuple(state_variables),
        parameter_schema=parameter_schema,
        input_ports=tuple(input_ports),
        disturbance_ports=tuple(disturbance_ports),
        decision_ports=tuple(decision_ports),
        boundary_blocks=tuple(boundary_blocks),
        control_blocks=tuple(control_blocks),
        policy_blocks=tuple(policy_blocks),
        mechanism_blocks=tuple(mechanism_blocks),
        update_map=tuple(update_map),
        admissibility_map=tuple(admissibility_map),
        read_map=tuple(read_map),
    )
