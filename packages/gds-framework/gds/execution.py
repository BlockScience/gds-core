"""ExecutionContract -- DSL-layer declaration of time model semantics.

The core algebra is temporally agnostic: blocks, composition operators, and
the compiler carry no intrinsic notion of time.  ExecutionContract is how
DSLs declare what "temporal boundary" means for their domain.

A GDSSpec without an ExecutionContract is valid for structural verification
but carries no execution semantics -- it cannot be connected to a simulator
without one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ExecutionContract:
    """Declares the time model for a GDS specification.

    Attached to GDSSpec as an optional field.  Absent means the spec
    is valid structurally but carries no time model commitment.

    Fields:
        time_domain: What kind of temporal boundary the DSL declares.
        synchrony: For discrete only -- synchronous or asynchronous updates.
        observation_delay: For discrete only -- 0 = Moore (output depends on
            current state only), 1 = one-step delay.
        update_ordering: For discrete only -- Moore or Mealy machine semantics.
    """

    time_domain: Literal["discrete", "continuous", "event", "atemporal"]
    synchrony: Literal["synchronous", "asynchronous"] = "synchronous"
    observation_delay: int = 0
    update_ordering: Literal["Moore", "Mealy"] = "Moore"

    def __post_init__(self) -> None:
        if self.time_domain != "discrete":
            if self.synchrony != "synchronous":
                raise ValueError(
                    f"synchrony is only meaningful for discrete time_domain, "
                    f"got time_domain={self.time_domain!r}"
                )
            if self.observation_delay != 0:
                raise ValueError(
                    f"observation_delay is only meaningful for discrete time_domain, "
                    f"got time_domain={self.time_domain!r}"
                )
            if self.update_ordering != "Moore":
                raise ValueError(
                    f"update_ordering is only meaningful for discrete time_domain, "
                    f"got time_domain={self.time_domain!r}"
                )

    def is_compatible_with(self, other: ExecutionContract) -> bool:
        """Check if two contracts can be composed.

        Compatible means: same time_domain, or one is atemporal (universal donor).
        """
        if self.time_domain == "atemporal" or other.time_domain == "atemporal":
            return True
        return self.time_domain == other.time_domain
