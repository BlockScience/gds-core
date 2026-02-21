"""GDS specification registry — the {h, X} pair.

GDSSpec is the central object that ties types, spaces, entities, blocks,
wirings, and parameters into a single validated specification. It handles
registration and structural validation only — no rendering, simulation,
or export.

Unlike MSML's MathSpec (a 1000+ line god-object), GDSSpec separates
concerns cleanly: registration and validation live here; everything else
is handled by separate modules.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from gds.blocks.base import Block
from gds.blocks.roles import HasParams, Mechanism
from gds.parameters import ParameterDef, ParameterSchema
from gds.spaces import Space
from gds.state import Entity
from gds.tagged import Tagged
from gds.types.typedef import TypeDef


class Wire(BaseModel, frozen=True):
    """A connection between two blocks within a wiring."""

    source: str
    target: str
    space: str = ""
    optional: bool = False


class SpecWiring(BaseModel, frozen=True):
    """A named composition of blocks connected by wires."""

    name: str
    block_names: list[str] = Field(default_factory=list)
    wires: list[Wire] = Field(default_factory=list)
    description: str = ""


class GDSSpec(Tagged):
    """Complete Generalized Dynamical System specification.

    Mathematically: GDS = {h, X} where
        X = state space (product of entity states)
        h = transition map (composed from wirings)

    Registration methods are chainable:
        spec.register_type(t).register_space(s).register_entity(e)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str = ""
    types: dict[str, TypeDef] = Field(default_factory=dict)
    spaces: dict[str, Space] = Field(default_factory=dict)
    entities: dict[str, Entity] = Field(default_factory=dict)
    blocks: dict[str, Block] = Field(default_factory=dict)
    wirings: dict[str, SpecWiring] = Field(default_factory=dict)
    parameter_schema: ParameterSchema = Field(default_factory=ParameterSchema)

    # ── Registration ────────────────────────────────────────

    def register_type(self, t: TypeDef) -> GDSSpec:
        """Register a TypeDef. Raises if name already registered."""
        if t.name in self.types:
            raise ValueError(f"Type '{t.name}' already registered")
        self.types[t.name] = t
        return self

    def register_space(self, s: Space) -> GDSSpec:
        """Register a Space. Raises if name already registered."""
        if s.name in self.spaces:
            raise ValueError(f"Space '{s.name}' already registered")
        self.spaces[s.name] = s
        return self

    def register_entity(self, e: Entity) -> GDSSpec:
        """Register an Entity. Raises if name already registered."""
        if e.name in self.entities:
            raise ValueError(f"Entity '{e.name}' already registered")
        self.entities[e.name] = e
        return self

    def register_block(self, b: Block) -> GDSSpec:
        """Register a Block. Raises if name already registered."""
        if b.name in self.blocks:
            raise ValueError(f"Block '{b.name}' already registered")
        self.blocks[b.name] = b
        return self

    def register_wiring(self, w: SpecWiring) -> GDSSpec:
        """Register a SpecWiring. Raises if name already registered."""
        if w.name in self.wirings:
            raise ValueError(f"Wiring '{w.name}' already registered")
        self.wirings[w.name] = w
        return self

    def register_parameter(
        self, param_or_name: ParameterDef | str, typedef: TypeDef | None = None
    ) -> GDSSpec:
        """Register a parameter definition.

        Accepts either:
            spec.register_parameter(ParameterDef(name="rate", typedef=Rate))
            spec.register_parameter("rate", Rate)  # legacy convenience
        """
        if isinstance(param_or_name, str):
            if typedef is None:
                raise ValueError("typedef is required when registering by name string")
            param = ParameterDef(name=param_or_name, typedef=typedef)
        else:
            param = param_or_name
        self.parameter_schema = self.parameter_schema.add(param)
        return self

    @property
    def parameters(self) -> dict[str, TypeDef]:
        """Legacy access: parameter name → TypeDef mapping."""
        return {name: p.typedef for name, p in self.parameter_schema.parameters.items()}

    # ── Bulk registration ─────────────────────────────────

    def collect(
        self, *objects: TypeDef | Space | Entity | Block | ParameterDef
    ) -> GDSSpec:
        """Register multiple objects by type-dispatching each.

        Accepts any mix of TypeDef, Space, Entity, Block, and
        ParameterDef instances. Does not handle SpecWiring or
        (name, typedef) parameter shorthand --- those stay explicit
        via ``register_wiring()`` and ``register_parameter()``.

        Raises TypeError for unrecognized types.
        """
        for obj in objects:
            if isinstance(obj, TypeDef):
                self.register_type(obj)
            elif isinstance(obj, Space):
                self.register_space(obj)
            elif isinstance(obj, Entity):
                self.register_entity(obj)
            elif isinstance(obj, ParameterDef):
                self.register_parameter(obj)
            elif isinstance(obj, Block):
                self.register_block(obj)
            else:
                raise TypeError(
                    f"collect() does not accept {type(obj).__name__!r}; "
                    f"expected TypeDef, Space, Entity, Block, or ParameterDef"
                )
        return self

    # ── Validation ──────────────────────────────────────────

    def validate_spec(self) -> list[str]:
        """Full structural validation. Returns list of error strings."""
        errors: list[str] = []
        errors += self._validate_space_types()
        errors += self._validate_wiring_blocks()
        errors += self._validate_mechanism_updates()
        errors += self._validate_param_references()
        return errors

    def _validate_space_types(self) -> list[str]:
        """Every TypeDef used in a Space is registered."""
        errors: list[str] = []
        for space in self.spaces.values():
            for field_name, typedef in space.fields.items():
                if typedef.name not in self.types:
                    errors.append(
                        f"Space '{space.name}' field '{field_name}' uses "
                        f"unregistered type '{typedef.name}'"
                    )
        return errors

    def _validate_wiring_blocks(self) -> list[str]:
        """Every block referenced in a wiring is registered."""
        errors: list[str] = []
        for wiring in self.wirings.values():
            for bname in wiring.block_names:
                if bname not in self.blocks:
                    errors.append(
                        f"Wiring '{wiring.name}' references "
                        f"unregistered block '{bname}'"
                    )
            for wire in wiring.wires:
                if wire.source not in self.blocks:
                    errors.append(
                        f"Wiring '{wiring.name}' wire source "
                        f"'{wire.source}' not in registered blocks"
                    )
                if wire.target not in self.blocks:
                    errors.append(
                        f"Wiring '{wiring.name}' wire target "
                        f"'{wire.target}' not in registered blocks"
                    )
                if wire.space and wire.space not in self.spaces:
                    errors.append(
                        f"Wiring '{wiring.name}' wire references "
                        f"unregistered space '{wire.space}'"
                    )
        return errors

    def _validate_mechanism_updates(self) -> list[str]:
        """Mechanisms only update existing entity variables."""
        errors: list[str] = []
        for block in self.blocks.values():
            if isinstance(block, Mechanism):
                for entity_name, var_name in block.updates:
                    if entity_name not in self.entities:
                        errors.append(
                            f"Mechanism '{block.name}' updates "
                            f"unknown entity '{entity_name}'"
                        )
                    elif var_name not in self.entities[entity_name].variables:
                        errors.append(
                            f"Mechanism '{block.name}' updates "
                            f"unknown variable '{entity_name}.{var_name}'"
                        )
        return errors

    def _validate_param_references(self) -> list[str]:
        """All parameter references in blocks are registered."""
        errors: list[str] = []
        param_names = self.parameter_schema.names()
        for block in self.blocks.values():
            if isinstance(block, HasParams):
                for param in block.params_used:
                    if param not in param_names:
                        errors.append(
                            f"Block '{block.name}' references "
                            f"unregistered parameter '{param}'"
                        )
        return errors
