"""Composition operators: sequential, parallel, feedback, and corecursive.

These operators combine open games into larger composite games. Each extends
the corresponding GDS composition operator with game-theory naming:

- ``SequentialComposition`` extends ``StackComposition``
- ``ParallelComposition`` extends GDS ``ParallelComposition``
- ``FeedbackLoop`` extends GDS ``FeedbackLoop``
- ``CorecursiveLoop`` extends ``TemporalLoop``

This means ``isinstance(seq, StackComposition)`` is True, enabling the GDS
compiler and generic verification to work on OGS compositions directly.

Mathematical Foundation
-----------------------
Open games theory defines four fundamental composition operators that form
a symmetric monoidal category with feedback:

+-------------------+---------------+---------------------------+-------------------+
| Math              | DSL           | Meaning                   | Information Flow  |
+===================+===============+===========================+===================+
| G1 ; G2           | g1 >> g2      | Sequential: output of G1  | Y1 -> X2          |
|                   |               | feeds input of G2         | (covariant)       |
+-------------------+---------------+---------------------------+-------------------+
| G1 || G2          | g1 | g2       | Parallel: independent,    | No shared wires   |
|                   |               | no shared wires           |                   |
+-------------------+---------------+---------------------------+-------------------+
| feedback(G)       | g.feedback()  | Feedback: S->R within     | S -> R            |
|                   |               | single timestep           | (contravariant)   |
+-------------------+---------------+---------------------------+-------------------+
| corec(G)          | g.corecursive | Corecursive: Y->X across  | Y -> X            |
|                   |               | timesteps                 | (temporal)        |
+-------------------+---------------+---------------------------+-------------------+

Category Theory Structure
-------------------------
These operators form a symmetric monoidal category where:
- Objects are interfaces (X, Y, R, S port signatures)
- Morphisms are open games G: (X, R) -> (Y, S)
- Sequential (;) is morphism composition
- Parallel (||) is tensor product
- Feedback provides the compact closed structure

Covariant vs Contravariant
--------------------------
- **Covariant flows** (solid arrows): X -> Y, left-to-right
  Carry observations forward to choices
- **Contravariant flows** (dashed arrows): R <- S, right-to-left
  Carry utilities backward as coutilities

These terms derive from category theory: functors preserve the flow
direction when covariant, and reverse domain/range when contravariant.

Composition Order
-----------------
For sequential composition G1 ; G2 (g1 >> g2):
1. G1 receives observation x in X1, produces choice y in Y1
2. y becomes observation x' in X2 (via type matching)
3. G2 receives x', produces choice y' in Y2
4. Result outcome r in R2 feeds back to S2 (coutility)
5. S2 coutility propagates through feedback wiring to R1
6. G1 receives r in R1, produces coutility s in S1

References
----------
- Specification Notes: "Design Pattern Fundamentals" section
- Ghani et al. (2018): Compositional Game Theory
- Fong & Spivak: Seven Sketches in Compositionality
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gds.blocks.composition import FeedbackLoop as _GDSFeedbackLoop
from gds.blocks.composition import ParallelComposition as _GDSParallelComposition
from gds.blocks.composition import StackComposition, TemporalLoop
from gds.ir.models import FlowDirection
from pydantic import BaseModel, Field, model_validator

from ogs.dsl.base import OpenGame

if TYPE_CHECKING:
    from ogs.dsl.games import AtomicGame
    from ogs.dsl.types import Signature


class Flow(BaseModel, frozen=True):
    """An explicit wiring between two games.

    Uses game-theory naming (``source_game``/``target_game``). Provides
    ``source_block``/``target_block`` properties for GDS interop (GDS
    composition validators access these attributes).

    ``source_game`` and ``target_game`` accept either a ``str`` (game name)
    or an ``OpenGame`` instance. When an ``OpenGame`` is provided it is
    coerced to ``game.name`` immediately at construction time, so the IR
    and verifier always receive plain strings.
    """

    source_game: str
    source_port: str
    target_game: str
    target_port: str
    direction: FlowDirection = FlowDirection.COVARIANT

    @model_validator(mode="before")
    @classmethod
    def _resolve_game_refs(cls, data: Any) -> Any:
        """Coerce OpenGame instances to their name strings."""
        if not isinstance(data, dict):
            return data
        for field in ("source_game", "target_game"):
            val = data.get(field)
            if isinstance(val, OpenGame):
                data[field] = val.name
        return data

    @property
    def source_block(self) -> str:
        """GDS-compatible alias for ``source_game``."""
        return self.source_game

    @property
    def target_block(self) -> str:
        """GDS-compatible alias for ``target_game``."""
        return self.target_game


class FeedbackFlow(Flow):
    """A ``Flow`` with ``direction`` defaulting to ``CONTRAVARIANT``.

    Use this inside ``FeedbackLoop.feedback_wiring`` to avoid repeating
    ``direction=FlowDirection.CONTRAVARIANT`` on every flow::

        FeedbackLoop(
            name="...",
            inner=chain,
            feedback_wiring=[
                FeedbackFlow(source_game="Outcome", source_port="Outcome",
                             target_game="Reactive Decision", target_port="Outcome"),
                FeedbackFlow(source_game="Reactive Decision", source_port="Experience",
                             target_game="Policy", target_port="Experience"),
            ],
        )

    Equivalent to ``Flow(..., direction=FlowDirection.CONTRAVARIANT)`` for
    each entry, but without the repetition. Also accepts ``OpenGame`` objects
    for ``source_game``/``target_game`` (inherited from ``Flow``).
    """

    direction: FlowDirection = FlowDirection.CONTRAVARIANT


class SequentialComposition(StackComposition, OpenGame):
    """``g1 >> g2`` — sequential composition where output of g1 feeds input of g2.

    Extends GDS ``StackComposition`` so ``isinstance(seq, StackComposition)``
    is True. GDS's validator handles token-overlap checking and interface
    computation. The ``OpenGame.signature`` property provides x/y/r/s access.

    Mathematical Notation
    ---------------------
    In category theory, written as G1 ; G2 (semicolon denotes composition).
    The output Y1 of the first game becomes the input X2 of the second::

        X1 -> G1 -> Y1 = X2 -> G2 -> Y2

    Or as a composite::

        X1 -> (G1 ; G2) -> Y2

    With contravariant feedback::

        R1 <- G1 <- S1 = R2 <- G2 <- S2

    Signature Transformation
    -------------------------
    - X = X1 + X2 (observations from both games)
    - Y = Y1 + Y2 (choices from both games)
    - R = R1 + R2 (utilities to both games)
    - S = S1 + S2 (coutilities from both games)

    Type Matching
    -------------
    Sequential composition requires type compatibility between Y1 and X2.
    If no explicit wiring is provided, the validator checks that the
    type tokens of Y1 overlap with X2 (at least one shared token).

    Example
    -------
    A policy game feeding into a decision game::

        policy >> decision

    Where Policy.Y = "Latest Policy" and Decision.X = "Latest Policy"
    (automatic wiring via type token matching).

    See Also
    --------
    Specification Notes: Sequential composition via type matching
    """

    first: OpenGame  # type: ignore[assignment]  # narrower than Block
    second: OpenGame  # type: ignore[assignment]  # narrower than Block
    wiring: list[Flow] = Field(default_factory=list)  # type: ignore[assignment]  # narrower than list[Wiring]

    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        return self.first.flatten() + self.second.flatten()


class ParallelComposition(_GDSParallelComposition, OpenGame):
    """``g1 | g2`` — parallel (tensor) composition: games run independently.

    Extends GDS ``ParallelComposition`` so ``isinstance(par, GDSParallelComposition)``
    is True. GDS's validator handles interface computation.

    Mathematical Notation
    ---------------------
    In category theory, written as G1 || G2 (parallel bar denotes tensor product).
    Games run side-by-side with no shared information flows::

        X1 -> G1 -> Y1
        X2 -> G2 -> Y2

    As a composite::

        (X1 x X2) -> (G1 || G2) -> (Y1 x Y2)

    Signature Transformation
    -------------------------
    - X = X1 + X2 (concatenated observations)
    - Y = Y1 + Y2 (concatenated choices)
    - R = R1 + R2 (concatenated utilities)
    - S = S1 + S2 (concatenated coutilities)

    Independence
    ------------
    No game-to-game flows allowed between left and right components.
    Each game operates independently with separate observations, choices,
    utilities, and coutilities.

    Example
    -------
    Two agents acting in parallel::

        agent1 | agent2

    Each agent has its own context builder, policy, and decision game.
    Their outputs feed into a shared decision router via separate wires.

    See Also
    --------
    Specification Notes: Parallel composition for multi-agent patterns
    """

    left: OpenGame  # type: ignore[assignment]  # narrower than Block
    right: OpenGame  # type: ignore[assignment]  # narrower than Block

    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        return self.left.flatten() + self.right.flatten()

    @classmethod
    def from_list(
        cls,
        games: list[OpenGame],
        name: str | None = None,
    ) -> ParallelComposition:
        """Compose a list of games in parallel.

        Equivalent to ``games[0] | games[1] | ... | games[N-1]`` but
        accepts a dynamic list, enabling N-agent patterns without
        manually enumerating the ``|`` chain.

        Args:
            games: At least 2 ``OpenGame`` instances.
            name: Optional name override for the resulting composition.
                  Defaults to ``" | ".join(g.name for g in games)``.

        Raises:
            ValueError: If fewer than 2 games are provided.

        Example::

            agents = [reactive_decision_agent(f"Agent {i}") for i in range(1, 4)]
            agents_parallel = ParallelComposition.from_list(agents)
        """
        if len(games) < 2:
            raise ValueError(
                f"ParallelComposition.from_list() requires at least 2 games, got {len(games)}"
            )
        result: ParallelComposition = games[0] | games[1]  # type: ignore[assignment]
        for g in games[2:]:
            result = result | g  # type: ignore[assignment]
        if name is not None:
            result = result.model_copy(update={"name": name})
        return result


class FeedbackLoop(_GDSFeedbackLoop, OpenGame):
    """Wraps a game with contravariant S->R feedback within a single timestep.

    Extends GDS ``FeedbackLoop`` so ``isinstance(fb, GDSFeedbackLoop)``
    is True. GDS's validator sets the interface.

    Mathematical Notation
    ---------------------
    In category theory, written as feedback(G) or with a feedback loop symbol.
    Creates backward information flow within a single game execution::

        X -> G -> Y
              ^
              | (feedback)
              v
        R <- S

    The coutility S of the inner game feeds back as utility R within
    the same timestep (before the game "completes").

    Information Flow
    ----------------
    Contravariant (dashed arrows): S -> R
    - S: Coutility produced by inner game
    - R: Utility received by inner game
    - Direction: Right-to-left (backward)

    This enables learning within a single decision cycle:
    1. Inner game produces choice Y
    2. Choice generates outcome (external)
    3. Outcome feeds back as utility R
    4. Inner game produces coutility S (experience)
    5. S feeds back to R via feedback_wiring

    Example
    -------
    A reactive decision agent with learning::

        agent = (cb >> hist >> pol >> rd >> out).feedback([
            Flow("Outcome", "Outcome", "Reactive Decision", "Outcome", CONTRAVARIANT),
            Flow("Experience", "Experience", "Policy", "Experience", CONTRAVARIANT),
            Flow(
                "History Update", "History Update",
                "History", "History Update", CONTRAVARIANT,
            ),
        ])

    See Also
    --------
    Specification Notes: Feedback within Reactive Decision Pattern
    """

    inner: OpenGame  # type: ignore[assignment]  # narrower than Block
    feedback_wiring: list[Flow]  # type: ignore[assignment]  # narrower than list[Wiring]

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            inner: OpenGame,
            feedback_wiring: list[Flow],
            signature: Signature | None = None,
        ) -> None: ...

    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        return self.inner.flatten()


class CorecursiveLoop(TemporalLoop, OpenGame):
    """Wraps a game with temporal corecursion: covariant Y->X across timesteps.

    Extends GDS ``TemporalLoop`` so ``isinstance(cl, TemporalLoop)``
    is True. Accepts ``corecursive_wiring`` as an alias for ``temporal_wiring``.
    GDS's validator enforces COVARIANT-only wiring and sets the interface.

    Mathematical Notation
    ---------------------
    In category theory, written as corec(G) or with a temporal loop symbol.
    Creates forward information flow across multiple timesteps (iterations)::

        X -> G -> Y
             ^   |
             |   | (corecursive)
             |   v
             ---(loop)

    The choice Y of one iteration becomes the observation X of the next
    iteration. This creates a temporal loop that continues until an
    exit_condition is satisfied.

    Information Flow
    ----------------
    Covariant (solid arrows): Y -> X
    - Y: Choice produced by inner game in iteration n
    - X: Observation received by inner game in iteration n+1
    - Direction: Forward across time

    All corecursive_wiring must be COVARIANT direction.
    CONTRAVARIANT wiring in corecursive loops is prohibited.

    Temporal Structure
    ------------------
    1. Iteration n: Inner game observes X_n, produces Y_n
    2. Y_n propagates through corecursive_wiring to become X_{n+1}
    3. Iteration n+1: Inner game observes X_{n+1} (= Y_n), produces Y_{n+1}
    4. Loop continues until exit_condition is True

    Exit Conditions
    ---------------
    The exit_condition is a string description of when the loop terminates.
    Common conditions:
    - "Agreement reached" (bilateral negotiation)
    - "Consensus threshold met" (multi-party agreement)
    - "Maximum iterations exceeded" (timeout)
    - "Both agents reject" (failure state)

    Example
    -------
    Bilateral negotiation with corecursive message passing::

        negotiation = feedback_loop.corecursive(
            wiring=[
                Flow("Decision", "Decision", "Agent 2 Context Builder", "Decision"),
                Flow("Decision", "Decision", "Agent 1 Context Builder", "Decision"),
            ],
            exit_condition="Agreement reached or timeout",
        )

    See Also
    --------
    Specification Notes: Corecursive loops in Cyclic Interaction Pattern
    """

    inner: OpenGame  # type: ignore[assignment]  # narrower than Block
    temporal_wiring: list[Flow]  # type: ignore[assignment]  # narrower than list[Wiring]

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            inner: OpenGame,
            corecursive_wiring: list[Flow] | None = None,
            temporal_wiring: list[Flow] | None = None,
            exit_condition: str = "",
        ) -> None: ...

    @model_validator(mode="before")
    @classmethod
    def _map_corecursive_to_temporal(cls, data: dict) -> dict:
        """Accept corecursive_wiring as alias for temporal_wiring."""
        if isinstance(data, dict) and "corecursive_wiring" in data:
            data["temporal_wiring"] = data.pop("corecursive_wiring")
        return data

    @property
    def corecursive_wiring(self) -> list[Flow]:
        """Game-theory alias for ``temporal_wiring``."""
        return self.temporal_wiring

    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        return self.inner.flatten()
