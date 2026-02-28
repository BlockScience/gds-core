"""Shared compilation utilities for all business diagram types.

Extracted from the stockflow pattern: parallel tier building and
explicit inter-tier wiring construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gds.blocks.composition import StackComposition, Wiring

if TYPE_CHECKING:
    from gds.blocks.base import Block


def parallel_tier(blocks: list[Block]) -> Block:
    """Compose a list of blocks in parallel."""
    tier: Block = blocks[0]
    for b in blocks[1:]:
        tier = tier | b
    return tier


def build_inter_tier_wirings(
    first_tier_blocks: list[Block],
    second_tier_blocks: list[Block],
) -> list[Wiring]:
    """Build explicit wirings between two tiers based on port token overlap.

    For each output port in the first tier, find matching input ports in the
    second tier (by token intersection). This replaces auto-wiring so we can
    use explicit StackComposition and bypass the token overlap validator.
    """
    wirings: list[Wiring] = []
    for first_block in first_tier_blocks:
        for out_port in first_block.interface.forward_out:
            for second_block in second_tier_blocks:
                for in_port in second_block.interface.forward_in:
                    if out_port.type_tokens & in_port.type_tokens:
                        wirings.append(
                            Wiring(
                                source_block=first_block.name,
                                source_port=out_port.name,
                                target_block=second_block.name,
                                target_port=in_port.name,
                            )
                        )
    return wirings


def sequential_with_explicit_wiring(
    first: Block,
    second: Block,
    wiring: list[Wiring],
) -> Block:
    """Compose two tiers sequentially with explicit wiring.

    Uses StackComposition directly to bypass the auto-wire token overlap check.
    If no wirings found, falls back to auto-wiring via >>.
    """
    if wiring:
        return StackComposition(
            name=f"{first.name} >> {second.name}",
            first=first,
            second=second,
            wiring=wiring,
        )
    return first >> second
