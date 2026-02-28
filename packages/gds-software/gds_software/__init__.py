"""Software architecture DSL over GDS semantics.

Declare software architecture diagrams — DFDs, state machines, component diagrams,
C4 models, ERDs, and dependency graphs — as typed compositional specifications.
The compiler maps them to GDS role blocks, entities, and composition trees.
All downstream GDS tooling works immediately — canonical projection,
semantic checks, SpecQuery, serialization, gds-viz.
"""

__version__ = "0.1.0"

# ── Common ─────────────────────────────────────────────────
from gds_software.common.errors import SWCompilationError, SWError, SWValidationError
from gds_software.common.types import DiagramKind

# ── DFD ────────────────────────────────────────────────────
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process
from gds_software.dfd.model import DFDModel
from gds_software.dfd.compile import (
    ContentType,
    ContentSpace,
    DataType,
    DataSpace,
    SignalType,
    SignalSpace,
    compile_dfd,
    compile_dfd_to_system,
)
from gds_software.dfd.checks import (
    ALL_DFD_CHECKS,
    check_dfd001_process_connectivity,
    check_dfd002_flow_validity,
    check_dfd003_no_ext_to_ext,
    check_dfd004_store_connectivity,
    check_dfd005_process_output,
)

# ── State Machine ──────────────────────────────────────────
from gds_software.statemachine.elements import (
    Event,
    Guard,
    Region,
    State,
    Transition,
)
from gds_software.statemachine.model import StateMachineModel
from gds_software.statemachine.compile import (
    EventType,
    EventSpace,
    StateType,
    StateSpace,
    compile_sm,
    compile_sm_to_system,
)
from gds_software.statemachine.checks import (
    ALL_SM_CHECKS,
    check_sm001_initial_state,
    check_sm002_reachability,
    check_sm003_determinism,
    check_sm004_guard_completeness,
    check_sm005_region_partition,
    check_sm006_transition_validity,
)

# ── Component ──────────────────────────────────────────────
from gds_software.component.elements import Component, Connector, InterfaceDef
from gds_software.component.model import ComponentModel
from gds_software.component.compile import (
    compile_component,
    compile_component_to_system,
)
from gds_software.component.checks import (
    ALL_CP_CHECKS,
    check_cp001_interface_satisfaction,
    check_cp002_connector_validity,
    check_cp003_dangling_interfaces,
    check_cp004_component_naming,
)

# ── C4 ─────────────────────────────────────────────────────
from gds_software.c4.elements import (
    C4Component,
    C4Relationship,
    Container,
    ExternalSystem,
    Person,
)
from gds_software.c4.model import C4Model
from gds_software.c4.compile import compile_c4, compile_c4_to_system
from gds_software.c4.checks import (
    ALL_C4_CHECKS,
    check_c4001_relationship_validity,
    check_c4002_container_hierarchy,
    check_c4003_external_connectivity,
    check_c4004_level_consistency,
)

# ── ERD ────────────────────────────────────────────────────
from gds_software.erd.elements import (
    Attribute,
    Cardinality,
    ERDEntity,
    ERDRelationship,
)
from gds_software.erd.model import ERDModel
from gds_software.erd.compile import compile_erd, compile_erd_to_system
from gds_software.erd.checks import (
    ALL_ER_CHECKS,
    check_er001_relationship_validity,
    check_er002_pk_existence,
    check_er003_attribute_uniqueness,
    check_er004_relationship_naming,
)

# ── Dependency ─────────────────────────────────────────────
from gds_software.dependency.elements import Dep, Layer, Module
from gds_software.dependency.model import DependencyModel
from gds_software.dependency.compile import compile_dep, compile_dep_to_system
from gds_software.dependency.checks import (
    ALL_DG_CHECKS,
    check_dg001_dep_validity,
    check_dg002_acyclicity,
    check_dg003_layer_ordering,
    check_dg004_module_connectivity,
)

# ── Verification ───────────────────────────────────────────
from gds_software.verification.engine import verify

# ── Re-exports from gds-framework ─────────────────────────
from gds.verification.findings import Finding, Severity, VerificationReport

__all__ = [
    # Common
    "DiagramKind",
    "SWError",
    "SWValidationError",
    "SWCompilationError",
    # DFD
    "ExternalEntity",
    "Process",
    "DataStore",
    "DataFlow",
    "DFDModel",
    "compile_dfd",
    "compile_dfd_to_system",
    "ContentType",
    "ContentSpace",
    "DataType",
    "DataSpace",
    "SignalType",
    "SignalSpace",
    "ALL_DFD_CHECKS",
    "check_dfd001_process_connectivity",
    "check_dfd002_flow_validity",
    "check_dfd003_no_ext_to_ext",
    "check_dfd004_store_connectivity",
    "check_dfd005_process_output",
    # State Machine
    "State",
    "Event",
    "Transition",
    "Guard",
    "Region",
    "StateMachineModel",
    "compile_sm",
    "compile_sm_to_system",
    "EventType",
    "EventSpace",
    "StateType",
    "StateSpace",
    "ALL_SM_CHECKS",
    "check_sm001_initial_state",
    "check_sm002_reachability",
    "check_sm003_determinism",
    "check_sm004_guard_completeness",
    "check_sm005_region_partition",
    "check_sm006_transition_validity",
    # Component
    "Component",
    "Connector",
    "InterfaceDef",
    "ComponentModel",
    "compile_component",
    "compile_component_to_system",
    "ALL_CP_CHECKS",
    "check_cp001_interface_satisfaction",
    "check_cp002_connector_validity",
    "check_cp003_dangling_interfaces",
    "check_cp004_component_naming",
    # C4
    "Person",
    "ExternalSystem",
    "Container",
    "C4Component",
    "C4Relationship",
    "C4Model",
    "compile_c4",
    "compile_c4_to_system",
    "ALL_C4_CHECKS",
    "check_c4001_relationship_validity",
    "check_c4002_container_hierarchy",
    "check_c4003_external_connectivity",
    "check_c4004_level_consistency",
    # ERD
    "ERDEntity",
    "Attribute",
    "ERDRelationship",
    "Cardinality",
    "ERDModel",
    "compile_erd",
    "compile_erd_to_system",
    "ALL_ER_CHECKS",
    "check_er001_relationship_validity",
    "check_er002_pk_existence",
    "check_er003_attribute_uniqueness",
    "check_er004_relationship_naming",
    # Dependency
    "Module",
    "Dep",
    "Layer",
    "DependencyModel",
    "compile_dep",
    "compile_dep_to_system",
    "ALL_DG_CHECKS",
    "check_dg001_dep_validity",
    "check_dg002_acyclicity",
    "check_dg003_layer_ordering",
    "check_dg004_module_connectivity",
    # Verification
    "verify",
    # Re-exports
    "Finding",
    "Severity",
    "VerificationReport",
]
