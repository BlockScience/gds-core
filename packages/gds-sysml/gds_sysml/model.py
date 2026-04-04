"""SysML v2 intermediate model — parsed representation before RDF conversion.

These Pydantic models capture the structural elements of a SysML v2 textual
notation file with @GDS* metadata annotations. They are the output of the
parser layer and the input to the RDF conversion layer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GDSAnnotation(BaseModel, frozen=True):
    """A @GDS* metadata annotation on a SysML element.

    SysML v2 ``metadata def`` usage: ``@GDSMechanism``, ``@GDSStateVariable``,
    ``@GDSParameter``, etc.  These are valid SysML v2 and parsed as first-class
    elements by both SysON and the OMG Pilot.

    Attributes:
        kind: The annotation type without the ``@GDS`` prefix.
            Examples: ``"Mechanism"``, ``"Policy"``, ``"BoundaryAction"``,
            ``"StateVariable"``, ``"Parameter"``, ``"Dynamics"``.
        properties: Key-value metadata from the annotation body.
            For ``@GDSDynamics``: ``{"reads": ["x", "y"], "writes": ["z"]}``.
            For ``@GDSParameter``: ``{"units": "kg/m^2"}``.
    """

    kind: str
    properties: dict[str, str | list[str]] = Field(default_factory=dict)


class SysMLAttribute(BaseModel, frozen=True):
    """An ``attribute`` usage within a part or action definition.

    Attributes:
        name: Attribute name (e.g. ``"temperature"``).
        type_name: SysML type reference (e.g. ``"Real"``, ``"Boolean"``).
        default_value: Optional default value as string.
        annotations: @GDS* metadata attached to this attribute.
    """

    name: str
    type_name: str = ""
    default_value: str = ""
    annotations: list[GDSAnnotation] = Field(default_factory=list)


class SysMLPort(BaseModel, frozen=True):
    """A ``port`` definition/usage on a part or action.

    Attributes:
        name: Port name (e.g. ``"temperatureOut"``).
        direction: Port direction — ``"in"``, ``"out"``, or ``"inout"``.
        type_name: Port type reference (e.g. ``"Temperature"``).
    """

    name: str
    direction: str = ""
    type_name: str = ""


class SysMLAction(BaseModel, frozen=True):
    """An ``action def`` / ``action usage`` — maps to GDS blocks.

    The @GDS* annotation determines the GDS role:
    - ``@GDSBoundaryAction`` → BoundaryAction
    - ``@GDSPolicy`` → Policy
    - ``@GDSMechanism`` → Mechanism
    - ``@GDSControlAction`` → ControlAction
    - No annotation → defaults to Policy

    Attributes:
        name: Action name.
        annotations: @GDS* metadata (role, dynamics, etc.).
        ports: Ports declared on this action.
        attributes: Attributes declared within this action.
        nested_actions: Nested action usages (composition structure).
    """

    name: str
    annotations: list[GDSAnnotation] = Field(default_factory=list)
    ports: list[SysMLPort] = Field(default_factory=list)
    attributes: list[SysMLAttribute] = Field(default_factory=list)
    nested_actions: list[str] = Field(default_factory=list)


class SysMLPart(BaseModel, frozen=True):
    """A ``part def`` / ``part usage`` — maps to GDS entities.

    Attributes:
        name: Part name (e.g. ``"Spacecraft"``).
        annotations: @GDS* metadata.
        attributes: State variables and parameters declared on this part.
        ports: Ports declared on this part.
        nested_parts: Names of nested part usages.
    """

    name: str
    annotations: list[GDSAnnotation] = Field(default_factory=list)
    attributes: list[SysMLAttribute] = Field(default_factory=list)
    ports: list[SysMLPort] = Field(default_factory=list)
    nested_parts: list[str] = Field(default_factory=list)


class SysMLConnection(BaseModel, frozen=True):
    """A ``connection usage`` — maps to GDS wiring.

    Attributes:
        name: Optional connection name.
        source: Source endpoint (e.g. ``"sensor.temperatureOut"``).
        target: Target endpoint (e.g. ``"controller.temperatureIn"``).
    """

    name: str = ""
    source: str = ""
    target: str = ""


class SysMLModel(BaseModel):
    """Complete parsed SysML v2 model — the output of the parser layer.

    Captures all structural elements and @GDS* annotations needed to
    build a GDSSpec via the RDF pipeline.

    Attributes:
        name: Model/package name.
        parts: Part definitions (→ entities).
        actions: Action definitions (→ blocks).
        connections: Connection usages (→ wirings).
        metadata_defs: Raw ``metadata def`` declarations for @GDS* types.
    """

    name: str = ""
    parts: dict[str, SysMLPart] = Field(default_factory=dict)
    actions: dict[str, SysMLAction] = Field(default_factory=dict)
    connections: list[SysMLConnection] = Field(default_factory=list)
    metadata_defs: list[str] = Field(default_factory=list)
