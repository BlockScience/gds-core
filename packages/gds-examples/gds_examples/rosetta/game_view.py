"""Resource Pool — Game Theory View.

Models the same resource pool as a two-player extraction game using the
OGS (Open Games) DSL. Two agents simultaneously decide how much to extract
from a shared resource. Each agent's payoff depends on how much resource
remains after both extractions -- a classic common-pool resource dilemma.

This is a stateless strategic interaction: no persistent state updates,
pure policy computation. The canonical projection yields h = g (no f),
which is semantically correct for compositional game theory.

GDS Decomposition (via compile_pattern_to_spec):
    X  = {}  (no persistent state -- games are stateless)
    U  = (Resource Availability)  -- exogenous resource signal
    g  = (Agent 1 Extraction, Agent 2 Extraction, Payoff Computation)
    f  = {}  (no mechanisms)
    Theta = {}

Composition:
    resource_signal >> (agent1_extraction | agent2_extraction) >> payoff
"""

from gds.canonical import CanonicalGDS, project_canonical
from gds.spec import GDSSpec
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.dsl.pattern import Pattern, PatternInput
from ogs.dsl.spec_bridge import compile_pattern_to_spec
from ogs.dsl.types import InputType, Signature, port


def build_pattern() -> Pattern:
    """Declare the resource extraction game as an OGS Pattern.

    Structure:
    - One exogenous input: Resource Availability (how much is in the pool)
    - Two decision games: Agent 1 and Agent 2 each choose extraction amount
    - One covariant function: Payoff Computation determines allocation

    The two agents act in parallel (simultaneous decisions), then their
    choices feed into a payoff computation that determines the outcome.
    """
    # Exogenous resource availability signal
    resource_input = PatternInput(
        name="Resource Availability",
        input_type=InputType.RESOURCE,
        schema_hint="float >= 0",
        target_game="Agent 1 Extraction",
        flow_label="Resource Signal",
    )

    # Agent 1: observes resource availability, decides extraction amount
    agent1 = DecisionGame(
        name="Agent 1 Extraction",
        signature=Signature(
            x=(port("Resource Signal"),),
            y=(port("Agent 1 Decision"),),
            r=(port("Agent 1 Payoff"),),
        ),
        logic="Choose extraction amount based on resource availability",
        color_code=1,
        tags={"domain": "Agent 1"},
    )

    # Agent 2: observes resource availability, decides extraction amount
    agent2 = DecisionGame(
        name="Agent 2 Extraction",
        signature=Signature(
            x=(port("Resource Signal"),),
            y=(port("Agent 2 Decision"),),
            r=(port("Agent 2 Payoff"),),
        ),
        logic="Choose extraction amount based on resource availability",
        color_code=2,
        tags={"domain": "Agent 2"},
    )

    # Payoff computation: takes both decisions, computes allocation
    payoff = CovariantFunction(
        name="Payoff Computation",
        signature=Signature(
            x=(port("Agent 1 Decision"), port("Agent 2 Decision")),
            y=(port("Allocation Result"),),
        ),
        logic="Compute payoffs based on total extraction vs available resource",
        color_code=3,
        tags={"domain": "Environment"},
    )

    # Compose: agents decide in parallel, then payoff computation
    agents = agent1 | agent2
    game_tree = agents >> payoff

    return Pattern(
        name="Resource Pool (Game)",
        game=game_tree,
        inputs=[resource_input],
    )


def build_spec() -> GDSSpec:
    """Compile the OGS Pattern into a GDSSpec for canonical projection."""
    return compile_pattern_to_spec(build_pattern())


def build_canonical() -> CanonicalGDS:
    """Project the canonical h = f . g decomposition.

    For a game-theoretic model:
        |X| = 0  (no persistent state)
        |U| = 1  (resource availability input)
        |g| = 3  (2 decision games + 1 payoff function)
        |f| = 0  (no mechanisms)

    The system is pure policy: h = g.
    """
    return project_canonical(build_spec())
