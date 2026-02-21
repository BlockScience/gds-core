"""Spec serialization — GDSSpec to dict/JSON.

Constraint functions are not serializable. JSON is an interchange format,
not the source of truth. This is by design.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from gds.blocks.roles import HasConstraints, HasOptions, HasParams, Mechanism

if TYPE_CHECKING:
    from gds.blocks.base import Block
    from gds.spec import GDSSpec


def spec_to_dict(spec: GDSSpec) -> dict[str, Any]:
    """Serialize a GDSSpec to a plain dict (JSON-compatible)."""
    return {
        "name": spec.name,
        "description": spec.description,
        "types": {
            name: {
                "name": t.name,
                "python_type": t.python_type.__name__,
                "description": t.description,
                "units": t.units,
            }
            for name, t in spec.types.items()
        },
        "spaces": {
            name: {
                "name": s.name,
                "schema": {fname: tdef.name for fname, tdef in s.fields.items()},
                "description": s.description,
            }
            for name, s in spec.spaces.items()
        },
        "entities": {
            name: {
                "name": e.name,
                "description": e.description,
                "variables": {
                    vname: {
                        "name": v.name,
                        "type": v.typedef.name,
                        "description": v.description,
                        "symbol": v.symbol,
                    }
                    for vname, v in e.variables.items()
                },
            }
            for name, e in spec.entities.items()
        },
        "blocks": {name: _block_to_dict(b) for name, b in spec.blocks.items()},
        "wirings": {
            name: {
                "name": w.name,
                "description": w.description,
                "blocks": list(w.block_names),
                "wires": [
                    {
                        "source": wire.source,
                        "target": wire.target,
                        "space": wire.space,
                        "optional": wire.optional,
                    }
                    for wire in w.wires
                ],
            }
            for name, w in spec.wirings.items()
        },
        "parameters": {
            name: {
                "name": p.name,
                "typedef": p.typedef.name,
                "python_type": p.typedef.python_type.__name__,
                "description": p.description,
                "bounds": list(p.bounds) if p.bounds is not None else None,
            }
            for name, p in spec.parameter_schema.parameters.items()
        },
    }


def _block_to_dict(b: Block) -> dict[str, Any]:
    """Serialize a single block to a dict."""
    d: dict[str, Any] = {
        "name": b.name,
        "kind": getattr(b, "kind", "generic"),
    }
    if isinstance(b, HasParams):
        d["params_used"] = list(b.params_used)
    if isinstance(b, HasConstraints):
        d["constraints"] = list(b.constraints)
    if isinstance(b, Mechanism):
        d["updates"] = [list(pair) for pair in b.updates]
    if isinstance(b, HasOptions):
        d["options"] = list(b.options)
    return d


def spec_to_json(spec: GDSSpec, indent: int = 2) -> str:
    """Serialize a GDSSpec to a JSON string."""
    return json.dumps(spec_to_dict(spec), indent=indent)
