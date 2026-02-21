"""Generic compilation pipeline: Block tree → flat SystemIR."""

from gds.compiler.compile import (
    StructuralWiring,
    WiringOrigin,
    compile_system,
    extract_hierarchy,
    extract_wirings,
    flatten_blocks,
)

__all__ = [
    "StructuralWiring",
    "WiringOrigin",
    "compile_system",
    "extract_hierarchy",
    "extract_wirings",
    "flatten_blocks",
]
