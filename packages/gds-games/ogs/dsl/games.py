"""Concrete atomic game types for the DSL.

Atomic games are the leaf nodes of a composition tree -- they cannot be
decomposed further. Each type enforces structural constraints on its
signature via Pydantic validators.

Mathematical Foundation
-----------------------
An open game is represented as a 4-tuple::

    ? := (Sigma__?, ?_?, ?_?, ?_?)

Where:
- Sigma__?: Set of strategies (mappings sigma: X -> Y)
- ?_?: Play function (Sigma__? x X -> Y)
- ?_?: Coplay function (Sigma__? -> (X x R -> S))
- ?_?: Best response function (X x (Y -> R) -> (Sigma__? -> ?Sigma__?))

Information Flows
-----------------
Each game has four directed information flows::

    X -> ? -> Y        (covariant/forward)
    R <- ? <- S        (contravariant/feedback)

- X: Input observations (what the game observes)
- Y: Output choices (what the game decides)
- R: Input outcomes/utilities (what the game receives)
- S: Output valuations/coutilities (what the game transmits)

The internal logic selects choices from Y based on observations X and
context k: Y -> R (the mapping from choices to outcomes). This logic
defines the best response relation ?_?.

Order of Operations
-------------------
1. Input: Observation x  in  X provided to ?
2. Context: k: Y -> R provided within ? (internal logic)
3. Output: Choice y  in  Y selected by ? based on x and k
4. Evaluation: Outcome r  in  R provided to ? (depends on y)
5. Transmission: Valuation s  in  S provided by ? to upstream games

References
----------
- Specification Notes: "The Open Game Template" section
- Compositional Game Theory: Ghani et al. (2018)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gds.tagged import Tagged
from pydantic import Field, model_validator

from ogs.dsl.base import OpenGame
from ogs.dsl.errors import DSLTypeError
from ogs.dsl.types import GameType

if TYPE_CHECKING:
    from ogs.dsl.types import Signature


class AtomicGame(OpenGame, Tagged):
    """Base class for non-decomposable (leaf) games.

    Carries a ``game_type`` tag, optional ``logic``, a ``color_code``
    for visual grouping, and semantic ``tags`` for domain grouping.

    Tags are inert annotations (per GDS) -- they don't affect composition
    or verification but enable domain-grouped visualization.
    """

    game_type: GameType
    logic: str = ""
    color_code: int = 1
    tags: dict[str, str] = Field(default_factory=dict)

    def flatten(self) -> list[AtomicGame]:  # type: ignore[override]
        return [self]


class DecisionGame(AtomicGame):
    """A strategic decision game -- a player who chooses an action.

    Has all four port categories: X, Y, R, S.

    Mathematical Definition
    -----------------------
    A decision game has no transmission value s  in  S output--it simply outputs
    a choice y  in  Y based upon x  in  X and a context k, resulting in an outcome
    r  in  R::

        X -> ? -> Y
        R <- ?

    Where:
    - X: Set of input observations (may be empty, singleton, or multi-element)
    - Y: Set of output choices (may include "NO-OP", "NO ACTION", or other
      "non-choice" choices)
    - R: Set of input resolved outcomes/utilities (may be numbers, vectors, etc.)
    - S = {}: No coutility transmission (decision game endpoint)

    The decision game ? contains the logic for selecting a choice from Y
    (which may be the empty set). The logic defines Sigma__? (strategies),
    ?_? (play function), and ?_? (best response).

    Diagram
    -------
    ::

        X["Observations X"] --> D{"Decision ?"}
        D --> Y["Choices Y"]
        D ~~~ R["Utility R"]
            R -.-> D
            R ~~~ D

    Example
    -------
    A "Reactive Decision" game observes context and policy, then decides
    on an action that generates an outcome::

        DecisionGame(
            name="Reactive Decision",
            signature=Signature(
                x=(port("Observation, Context"), port("Latest Policy")),
                y=(port("Decision"),),
                r=(port("Outcome"),),
                s=(port("Experience"),),  # Coutility for learning
            ),
        )

    See Also
    --------
    Specification Notes: "Decision Open Game" section
    """

    game_type: GameType = GameType.DECISION

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            signature: Signature | None = None,
            logic: str = "",
            color_code: int = 1,
            tags: dict[str, str] | None = None,
        ) -> None: ...


class CovariantFunction(AtomicGame):
    """A pure deterministic function with only forward ports: X -> Y.

    Also known as a "lifting" in category theory. Has no utility r  in  R or
    transmission value s  in  S--it simply associates to an x  in  X a choice y  in  Y.

    Mathematical Definition
    -----------------------
    A covariant function (lifting) f: X -> Y::

        X -> f -> Y

    Where:
    - X: Domain (input observations)
    - Y: Codomain (output choices)
    - R = {}: No utility input
    - S = {}: No coutility output

    This is the simplest atomic game type--pure functional transformation
    without feedback or strategic choice.

    Diagram
    -------
    ::

        X["X"] --> D[/"Function f"\\]
        D --> Y["Y"]

    Example
    -------
    A "Context Builder" transforms trigger data into usable context::

        CovariantFunction(
            name="Context Builder",
            signature=Signature(
                x=(port("Event"), port("Constraint")),
                y=(port("Observation, Context"),),
            ),
        )

    Validation
    ----------
    Must have empty R and S ports (enforced by validator).

    See Also
    --------
    Specification Notes: "Function Open Game" section
    """

    game_type: GameType = GameType.FUNCTION_COVARIANT

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            signature: Signature | None = None,
            logic: str = "",
            color_code: int = 1,
            tags: dict[str, str] | None = None,
        ) -> None: ...

    @model_validator(mode="after")
    def _no_contravariant(self) -> Self:
        if self.signature.r or self.signature.s:
            raise DSLTypeError(
                f"CovariantFunction {self.name!r} cannot have contravariant ports "
                f"(R={self.signature.r}, S={self.signature.s})"
            )
        return self


class ContravariantFunction(AtomicGame):
    """A pure backward function with only contravariant ports: R -> S.

    The "dual" or contravariant lifting f*: R -> S. Associates a transmission
    value s in S with a utility r in R, with no observations
    x in X or choices y in Y.

    Mathematical Definition
    -----------------------
    A contravariant function (dual lifting) f*: R -> S::

        R <- f* <- S

    Or equivalently, reading right-to-left::

        S -> f* -> R

    Where:
    - R: Input utility/outcome
    - S: Output coutility/valuation
    - X = {}: No observation input
    - Y = {}: No choice output

    The f* notation indicates this relationship may be thought of as a 'dual'
    or 'inverse' of a covariant lifting f: S -> R, providing sufficient structure
    to create the standard open game via the tensor product of one covariant
    and one contravariant lifting.

    Diagram
    -------
    ::

        R["R"] -.-> D[/"Function f*"\\]
        D -.-> S["S"]

    Validation
    ----------
    Must have empty X and Y ports (enforced by validator).

    See Also
    --------
    Specification Notes: "Function Open Game" section (contravariant subsection)
    """

    game_type: GameType = GameType.FUNCTION_CONTRAVARIANT

    @model_validator(mode="after")
    def _no_covariant(self) -> Self:
        if self.signature.x or self.signature.y:
            raise DSLTypeError(
                f"ContravariantFunction {self.name!r} cannot have covariant ports "
                f"(X={self.signature.x}, Y={self.signature.y})"
            )
        return self


class DeletionGame(AtomicGame):
    """Discards an input channel: X -> {}. Y must be empty.

    A special function game where x  in  X is discarded, returning Y := {}.

    Mathematical Definition
    -----------------------
    A deletion game discards observations without producing choices::

        X -> f -> {}

    Where Y = {} (empty set). This represents intentional information
    loss or filtering--receiving input but producing no output.

    Diagram (Full)
    --------------
    ::

        X["X"] --> D[/"Function f"\\] --> Y["{}"]

    Diagram (Shorthand)
    -------------------
    ::

        X["X"] --> D@{shape: dbl-circ, label: " "}

    The double-circle shorthand is commonly used in string diagram notation
    to represent deletion (discarding) of information.

    Validation
    ----------
    Must have empty Y (enforced by validator).

    See Also
    --------
    Specification Notes: "Deletion Open Game" section
    """

    game_type: GameType = GameType.DELETION

    @model_validator(mode="after")
    def _y_must_be_empty(self) -> Self:
        if self.signature.y:
            raise DSLTypeError(
                f"DeletionGame {self.name!r} must have empty Y (got {self.signature.y})"
            )
        return self


class DuplicationGame(AtomicGame):
    """Copies an input to multiple outputs: X -> X x X. Y must have 2+ ports.

    A special function game where x  in  X is copied, returning Y := X x X.

    Mathematical Definition
    -----------------------
    A duplication game copies observations to multiple outputs::

        X -> f -> X x X

    Where Y = X x X (cartesian product). This represents information
    broadcasting--receiving input and sending copies to multiple downstream
    consumers.

    Has a natural contravariant counterpart when r  in  R is copied.

    Diagram (Full)
    --------------
    ::

        X["X"] --> D[/"Function f"\\] --> Y["X x X"]

    Diagram (Shorthand)
    -------------------
    ::

        X0["X"] --> X1["X"]
        X0 --> X2["X"]

    The fork shorthand is commonly used in string diagram notation
    to represent duplication (copying) of information.

    Contravariant Counterpart
    -------------------------
    When r  in  R is copied::

        R["R"] -.-> D[/"Function f*"\\] -.-> Y["R x R"]

    Or in shorthand::

        R0["R"] -.-> R1["R"]
        R0 -.-> R2["R"]

    Validation
    ----------
    Must have 2+ Y ports (enforced by validator).

    See Also
    --------
    Specification Notes: "Duplication Open Game" section
    """

    game_type: GameType = GameType.DUPLICATION

    @model_validator(mode="after")
    def _y_must_have_multiple_ports(self) -> Self:
        if len(self.signature.y) < 2:
            raise DSLTypeError(
                f"DuplicationGame {self.name!r} must have 2+ Y ports "
                f"(got {len(self.signature.y)})"
            )
        return self


class CounitGame(AtomicGame):
    """Future-conditioned observation: X -> {}, with S = X. Y and R must be empty.

    The counit open game is mainly used for technical purposes--to specify
    future data that may be important to a present decision-maker.

    Mathematical Definition
    -----------------------
    A counit game with special structure S = X and R = Y = {}::

        X -> ?
        ? -.-> X

    Where:
    - X: Input observations (also output as coutility)
    - Y = {}: No choices
    - R = {}: No utility input
    - S = X: Coutility equals observations

    This defines how a future piece of observational data x  in  X is able
    to be conditioned upon in the present time. The observation flows
    through but also becomes available as coutility for upstream games
    to access.

    Diagram (Full)
    --------------
    ::

        S["Coutility X"] ~~~ G
        G -.-> S
        G ~~~ S
        X["Observations X"] --> G["Open Game ?"]

    Diagram (Shorthand)
    -------------------
    ::

        S["Coutility X"] ~~~ X["Observations X"]
        X -.-> S
        X ~~~ S

    Use Cases
    ---------
    - Propagating context from downstream to upstream games
    - Making future observations available for present decisions
    - Creating feedback loops that carry state information

    Validation
    ----------
    Must have empty Y and R (enforced by validator).

    See Also
    --------
    Specification Notes: "Counit Open Game" section
    """

    game_type: GameType = GameType.COUNIT

    @model_validator(mode="after")
    def _validate_counit(self) -> Self:
        if self.signature.y:
            raise DSLTypeError(
                f"CounitGame {self.name!r} must have empty Y (got {self.signature.y})"
            )
        if self.signature.r:
            raise DSLTypeError(
                f"CounitGame {self.name!r} must have empty R (got {self.signature.r})"
            )
        return self
