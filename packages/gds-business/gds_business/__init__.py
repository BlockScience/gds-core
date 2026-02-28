"""Business dynamics DSL over GDS semantics.

Declare business dynamics diagrams — causal loop diagrams, supply chain networks,
and value stream maps — as typed compositional specifications.
The compiler maps them to GDS role blocks, entities, and composition trees.
All downstream GDS tooling works immediately — canonical projection,
semantic checks, SpecQuery, serialization, gds-viz.
"""

__version__ = "0.1.0"

# ── Common ─────────────────────────────────────────────────
from gds_business.common.errors import BizCompilationError, BizError, BizValidationError
from gds_business.common.types import BusinessDiagramKind

# ── CLD ────────────────────────────────────────────────────
from gds_business.cld.elements import CausalLink, Variable
from gds_business.cld.model import CausalLoopModel
from gds_business.cld.compile import (
    SignalType,
    SignalSpace,
    compile_cld,
    compile_cld_to_system,
)
from gds_business.cld.checks import (
    ALL_CLD_CHECKS,
    check_cld001_loop_polarity,
    check_cld002_variable_reachability,
    check_cld003_no_self_loops,
)

# ── Supply Chain ───────────────────────────────────────────
from gds_business.supplychain.elements import (
    DemandSource,
    OrderPolicy,
    Shipment,
    SupplyNode,
)
from gds_business.supplychain.model import SupplyChainModel
from gds_business.supplychain.compile import (
    DemandSpace,
    DemandType,
    InventorySpace,
    InventoryType,
    ShipmentRateSpace,
    ShipmentRateType,
    compile_scn,
    compile_scn_to_system,
)
from gds_business.supplychain.checks import (
    ALL_SCN_CHECKS,
    check_scn001_network_connectivity,
    check_scn002_shipment_node_validity,
    check_scn003_demand_target_validity,
    check_scn004_no_orphan_nodes,
)

# ── VSM ────────────────────────────────────────────────────
from gds_business.vsm.elements import (
    Customer,
    InformationFlow,
    InventoryBuffer,
    MaterialFlow,
    ProcessStep,
    Supplier,
)
from gds_business.vsm.model import ValueStreamModel
from gds_business.vsm.compile import (
    MaterialSpace,
    MaterialType,
    ProcessSignalSpace,
    ProcessSignalType,
    compile_vsm,
    compile_vsm_to_system,
)
from gds_business.vsm.checks import (
    ALL_VSM_CHECKS,
    check_vsm001_linear_process_flow,
    check_vsm002_push_pull_boundary,
    check_vsm003_flow_reference_validity,
    check_vsm004_bottleneck_vs_takt,
)

# ── Verification ───────────────────────────────────────────
from gds_business.verification.engine import verify

# ── Re-exports from gds-framework ─────────────────────────
from gds.verification.findings import Finding, Severity, VerificationReport

__all__ = [
    # Common
    "BusinessDiagramKind",
    "BizError",
    "BizValidationError",
    "BizCompilationError",
    # CLD
    "Variable",
    "CausalLink",
    "CausalLoopModel",
    "compile_cld",
    "compile_cld_to_system",
    "SignalType",
    "SignalSpace",
    "ALL_CLD_CHECKS",
    "check_cld001_loop_polarity",
    "check_cld002_variable_reachability",
    "check_cld003_no_self_loops",
    # Supply Chain
    "SupplyNode",
    "Shipment",
    "DemandSource",
    "OrderPolicy",
    "SupplyChainModel",
    "compile_scn",
    "compile_scn_to_system",
    "InventoryType",
    "InventorySpace",
    "ShipmentRateType",
    "ShipmentRateSpace",
    "DemandType",
    "DemandSpace",
    "ALL_SCN_CHECKS",
    "check_scn001_network_connectivity",
    "check_scn002_shipment_node_validity",
    "check_scn003_demand_target_validity",
    "check_scn004_no_orphan_nodes",
    # VSM
    "ProcessStep",
    "InventoryBuffer",
    "Supplier",
    "Customer",
    "MaterialFlow",
    "InformationFlow",
    "ValueStreamModel",
    "compile_vsm",
    "compile_vsm_to_system",
    "MaterialType",
    "MaterialSpace",
    "ProcessSignalType",
    "ProcessSignalSpace",
    "ALL_VSM_CHECKS",
    "check_vsm001_linear_process_flow",
    "check_vsm002_push_pull_boundary",
    "check_vsm003_flow_reference_validity",
    "check_vsm004_bottleneck_vs_takt",
    # Verification
    "verify",
    # Re-exports
    "Finding",
    "Severity",
    "VerificationReport",
]
