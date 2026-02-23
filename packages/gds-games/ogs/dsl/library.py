"""Reusable component factories for the Reactive Decision Pattern.

Each factory returns a pre-configured atomic game with the correct signature,
encoding the shared structure found across negotiation and coalition patterns.

The Reactive Decision Pattern implements a decision-with-learning cycle
triggered by environmental events. The order of operations is:

1. Trigger Detection — sensors detect events (network, timer, market signals)
2. Context Building — event processor transforms triggers + resources into
   an observation x in X and feasible decision set Y' ⊆ Y
3. Reactive Decision — agent selects action y in Y' given observation, policy,
   and continuation context k: Y → R
4. Outcome Evaluation — action evaluated against external world → utility r in R
5. Learning — experience (coutility s in S) fed back to update policy and history

State evolution per step:
  g_0: X_T × X_C × P → U        action decider (context + policy → action)
  g_1: H × U × R × P → P        policy update (history + outcome → new policy)
  g_2: P × U × R × H → H        history update (append (policy, action, outcome))
  g_3: X_T × X_C × U → X_T × X_C  trigger/resource update
"""

from __future__ import annotations

from functools import reduce
from typing import Literal, overload

from gds.ir.models import FlowDirection

from ogs.dsl.base import OpenGame
from ogs.dsl.composition import (
    FeedbackFlow,
    FeedbackLoop,
    Flow,
    ParallelComposition,
    SequentialComposition,
)
from ogs.dsl.games import CovariantFunction, DecisionGame
from ogs.dsl.types import Signature, port


def context_builder(
    name: str = "Context Builder", tags: dict[str, str] | None = None
) -> CovariantFunction:
    """Context Builder — aggregates environmental inputs into a unified observation.

    Observes trigger events from the outside world (x_T) and available
    resources/constraints (x_C), then builds a unified observation x in X
    together with the feasible decision set Y' = U(x_T, x_C) ⊆ Y. Also
    constructs the continuation context k: Y → R that the Reactive Decision
    game uses to evaluate candidate actions. This is a covariant lifting —
    a pure function with no utility or coutility.
    """
    game = CovariantFunction(
        name=name,
        signature=Signature(
            x=(port("Event"), port("Constraint"), port("Primitive")),
            y=(port("Observation, Context"),),
        ),
        logic=(
            "Aggregate trigger events (x_T) and resource constraints (x_C) "
            "into observation x and feasible decision set Y' = U(x_T, x_C) ⊆ Y. "
            "Construct continuation context k: Y → R for downstream decision."
        ),
        color_code=1,
    )
    if tags:
        for key, value in tags.items():
            game = game.with_tag(key, value)
    return game


def history(name: str = "History", tags: dict[str, str] | None = None) -> DecisionGame:
    """History — accumulates past observations and decisions over time.

    Maintains an append-only record of (policy, action, outcome) tuples.
    Initialized from h_0 and updated via the contravariant History Update
    port: h' = g_2(p, u, r, h) := (h, (p, u, r)). The latest history is
    forwarded to the Policy game so it can condition its strategy selection
    on past experience.
    """
    game = DecisionGame(
        name=name,
        signature=Signature(
            x=(port("Primitive"),),
            y=(port("Latest History"),),
            r=(port("History Update"),),
        ),
        logic=(
            "Append-only record of (policy, action, outcome) tuples. "
            "Initialized from h_0 in H, updated each round via "
            "h' = g_2(p, u, r, h) := (h, (p, u, r)). "
            "Forwards latest history to Policy for strategy conditioning."
        ),
        color_code=1,
    )
    if tags:
        for key, value in tags.items():
            game = game.with_tag(key, value)
    return game


def policy(name: str = "Policy", tags: dict[str, str] | None = None) -> DecisionGame:
    """Policy — maps history to a strategy (policy function ``p ∈ P``).

    Selects a strategy σ: X → Y from the policy space P, conditioned on
    the accumulated history. Receives experience feedback (coutility)
    from the Reactive Decision game and uses it to update the policy:
    p' = g_1(h, u, r; p). Emits a History Update (coutility s) back
    to the History game so the record includes the latest round.
    Initialized from p_0 (e.g., uniform over actions).
    """
    game = DecisionGame(
        name=name,
        signature=Signature(
            x=(port("Latest History"), port("Primitive")),
            y=(port("Latest Policy"),),
            r=(port("Experience"),),
            s=(port("History Update"),),
        ),
        logic=(
            "Select strategy σ: X → Y from policy space P given "
            "history. Update policy via p' = g_1(h, u, r; p) using "
            "experience feedback. Emit history update s to record "
            "the latest (policy, action, outcome) tuple."
        ),
        color_code=1,
    )
    if tags:
        for key, value in tags.items():
            game = game.with_tag(key, value)
    return game


def outcome(name: str = "Outcome", tags: dict[str, str] | None = None) -> DecisionGame:
    """Outcome — evaluates decisions against the external world to compute payoff.

    Takes the agent's chosen action u and the external world state ¬u (the
    counterfactual — what would have happened under alternative actions) and
    computes the realized utility r = Q(u, ¬u). This outcome is fed back
    contravariantly to the Reactive Decision game as its resolved payoff,
    closing the decision-evaluation loop.
    """
    game = DecisionGame(
        name=name,
        signature=Signature(
            x=(port("Decision"), port("Primitive")),
            s=(port("Outcome"),),
        ),
        logic=(
            "Evaluate action u against external world state ¬u to compute "
            "realized utility r = Q(u, ¬u). Fed back contravariantly as the "
            "resolved outcome for the decision game."
        ),
        color_code=2,
    )
    if tags:
        for key, value in tags.items():
            game = game.with_tag(key, value)
    return game


def reactive_decision(
    name: str = "Reactive Decision", tags: dict[str, str] | None = None
) -> DecisionGame:
    """Reactive Decision — the core decision game where the agent chooses an action.

    The central decision point. Observes the context (x, Y', k) built by the
    Context Builder and the current policy p from the Policy game. Selects an
    action y = σ(x) from the feasible set Y' ⊆ Y according to strategy
    σ: X → Y parameterized by policy p. Receives resolved outcome r in R
    (utility) from the Outcome game. Transmits experience s in S (coutility)
    back to the Policy game for learning. The best-response function
    B(x, k) identifies which strategies are rational given the continuation.
    """
    game = DecisionGame(
        name=name,
        signature=Signature(
            x=(port("Observation, Context"), port("Latest Policy")),
            y=(port("Decision"),),
            r=(port("Outcome"),),
            s=(port("Experience"),),
        ),
        logic=(
            "Select action y = σ(x) from feasible set Y' ⊆ Y "
            "using policy p. Receive resolved outcome r (utility) "
            "from evaluation. Transmit experience s (coutility) "
            "for policy learning. Best-response B(x, k) identifies "
            "rational strategies given continuation k: Y → R."
        ),
        color_code=1,
    )
    if tags:
        for key, value in tags.items():
            game = game.with_tag(key, value)
    return game


# ---------------------------------------------------------------------------
# reactive_decision_agent — overloaded signatures
# ---------------------------------------------------------------------------


@overload
def reactive_decision_agent(
    name: str = ...,
    include_outcome: Literal[True] = ...,
    include_feedback: Literal[True] = ...,
) -> FeedbackLoop: ...


@overload
def reactive_decision_agent(
    name: str = ...,
    include_outcome: Literal[False] = ...,
    include_feedback: Literal[True] = ...,
) -> FeedbackLoop: ...


@overload
def reactive_decision_agent(
    name: str = ...,
    include_outcome: bool = ...,
    include_feedback: Literal[False] = ...,
) -> SequentialComposition: ...


def reactive_decision_agent(
    name: str = "Reactive Decision Agent",
    include_outcome: bool = True,
    include_feedback: bool = True,
) -> FeedbackLoop | SequentialComposition:
    """Reactive decision agent — configurable single-agent decision loop.

    Builds a Reactive Decision Pattern chain from atomic games.  The two
    boolean flags control which components are included:

    +------------------+------------------+------------------------------+
    | ``include_outcome`` | ``include_feedback`` | Returns                   |
    +==================+==================+==============================+
    | ``True`` (default)  | ``True`` (default)  | ``FeedbackLoop`` — full    |
    |                  |                  | 5-game loop (CB→Hist→Pol    |
    |                  |                  | →RD→Out + 3 feedback flows) |
    +------------------+------------------+------------------------------+
    | ``False``           | ``True``            | ``FeedbackLoop`` — 4-game  |
    |                  |                  | loop without Outcome game   |
    +------------------+------------------+------------------------------+
    | ``True``            | ``False``           | ``SequentialComposition``   |
    |                  |                  | — 5-game open chain,        |
    |                  |                  | no feedback wrap            |
    +------------------+------------------+------------------------------+
    | ``False``           | ``False``           | ``SequentialComposition``   |
    |                  |                  | — 4-game open-loop chain    |
    |                  |                  | (CB→Hist→Pol→RD), suited    |
    |                  |                  | for multi-agent patterns    |
    |                  |                  | where Outcome and feedback  |
    |                  |                  | are wired at pattern level  |
    +------------------+------------------+------------------------------+

    Args:
        name: Base name for the agent; used as the composition/loop name and
              as the domain tag on each atomic game (``{"domain": name}``).
        include_outcome: When ``True`` (default), appends the ``Outcome`` game
            and wires ``Reactive Decision → Outcome``.  When ``False``, the
            chain stops at ``Reactive Decision`` — useful in multi-agent
            patterns where a shared Decision Router owns the Outcome game.
        include_feedback: When ``True`` (default), wraps the sequential chain
            in a ``FeedbackLoop`` with contravariant flows for outcome,
            experience, and history-update feedback.  When ``False``, returns
            the raw ``SequentialComposition`` chain.

    Returns:
        ``FeedbackLoop`` when ``include_feedback=True``,
        ``SequentialComposition`` when ``include_feedback=False``.
    """
    tags = {"domain": name}
    cb = context_builder(tags=tags)
    hist = history(tags=tags)
    pol = policy(tags=tags)
    rd = reactive_decision(tags=tags)

    # innermost: Policy >> Reactive Decision
    pol_rd = SequentialComposition(
        name=f"{name} Policy+RD",
        first=pol,
        second=rd,
        wiring=[
            Flow(
                source_game=pol,
                source_port="Latest Policy",
                target_game=rd,
                target_port="Latest Policy",
            ),
        ],
    )

    # History >> (Policy >> RD)
    hist_pol_rd = SequentialComposition(
        name=f"{name} Core",
        first=hist,
        second=pol_rd,
        wiring=[
            Flow(
                source_game=hist,
                source_port="Latest History",
                target_game=pol,
                target_port="Latest History",
            ),
        ],
    )

    if include_outcome:
        out = outcome(tags=tags)

        # (Policy >> RD) >> Outcome — reuse pol_rd as first
        rd_out = SequentialComposition(
            name=f"{name} RD+Outcome",
            first=rd,
            second=out,
            wiring=[
                Flow(
                    source_game=rd,
                    source_port="Decision",
                    target_game=out,
                    target_port="Decision",
                ),
            ],
        )

        # History >> (Policy >> RD >> Outcome)
        hist_chain = SequentialComposition(
            name=f"{name} Core",
            first=hist,
            second=SequentialComposition(
                name=f"{name} Policy+RD+Outcome",
                first=pol,
                second=rd_out,
                wiring=[
                    Flow(
                        source_game=pol,
                        source_port="Latest Policy",
                        target_game=rd,
                        target_port="Latest Policy",
                    ),
                ],
            ),
            wiring=[
                Flow(
                    source_game=hist,
                    source_port="Latest History",
                    target_game=pol,
                    target_port="Latest History",
                ),
            ],
        )

        chain = SequentialComposition(
            name=name,
            first=cb,
            second=hist_chain,
            wiring=[
                Flow(
                    source_game=cb,
                    source_port="Observation, Context",
                    target_game=rd,
                    target_port="Observation, Context",
                ),
            ],
        )

        if not include_feedback:
            return chain

        return FeedbackLoop(
            name=name,
            inner=chain,
            feedback_wiring=[
                FeedbackFlow(
                    source_game=out,
                    source_port="Outcome",
                    target_game=rd,
                    target_port="Outcome",
                ),
                FeedbackFlow(
                    source_game=rd,
                    source_port="Experience",
                    target_game=pol,
                    target_port="Experience",
                ),
                FeedbackFlow(
                    source_game=pol,
                    source_port="History Update",
                    target_game=hist,
                    target_port="History Update",
                ),
            ],
            signature=Signature(),
        )

    # include_outcome=False — 4-game chain: CB >> Hist >> Pol >> RD
    chain = SequentialComposition(
        name=name,
        first=cb,
        second=hist_pol_rd,
        wiring=[
            Flow(
                source_game=cb,
                source_port="Observation, Context",
                target_game=rd,
                target_port="Observation, Context",
            ),
        ],
    )

    if not include_feedback:
        return chain

    # include_outcome=False, include_feedback=True — wrap 4-game chain
    return FeedbackLoop(
        name=name,
        inner=chain,
        feedback_wiring=[
            FeedbackFlow(
                source_game=rd,
                source_port="Experience",
                target_game=pol,
                target_port="Experience",
            ),
            FeedbackFlow(
                source_game=pol,
                source_port="History Update",
                target_game=hist,
                target_port="History Update",
            ),
        ],
        signature=Signature(),
    )


# ---------------------------------------------------------------------------
# parallel — N-agent parallel composition helper (#6)
# ---------------------------------------------------------------------------


def parallel(games: list[OpenGame], name: str | None = None) -> ParallelComposition:
    """Compose a list of games in parallel.

    Convenience wrapper for ``ParallelComposition.from_list()``.  Use this
    when building N-agent patterns where the number of agents may vary::

        agents = [
            reactive_decision_agent(f"Agent {i}", include_outcome=False, include_feedback=False)
            for i in range(1, n + 1)
        ]
        agents_parallel = parallel(agents)

    Args:
        games: At least 2 ``OpenGame`` instances.
        name: Optional name override. Defaults to ``" | ".join(g.name for g in games)``.

    Raises:
        ValueError: If fewer than 2 games are provided.
    """
    return ParallelComposition.from_list(games, name=name)


# ---------------------------------------------------------------------------
# multi_agent_composition — parallel agents + router + auto-generated feedback (#2)
# ---------------------------------------------------------------------------


def multi_agent_composition(
    agents: list[OpenGame],
    router: OpenGame,
    feedback_port_map: dict[str, tuple[str, str]],
    wiring: list[Flow] | None = None,
    name: str | None = None,
) -> FeedbackLoop:
    """Compose N open-loop agents in parallel, wire them into a router, and
    generate all feedback flows automatically.

    This helper encodes the three-step structure that every multi-agent pattern
    follows:

    1. **Parallel composition** — all agents run side-by-side
    2. **Sequential composition** — agents feed into the shared ``router``
    3. **FeedbackLoop** — ``N × K`` contravariant flows (one per agent per
       feedback channel) route the router's outputs back into each agent

    Args:
        agents: Open-loop agent games (typically built with
            ``reactive_decision_agent(..., include_outcome=False,
            include_feedback=False)``).  Must contain at least 2 agents.
        router: The shared game that receives all agent decisions and produces
            per-agent outcomes/feedback signals (e.g. a Decision Router).
        feedback_port_map: Maps a semantic label to a
            ``(source_port, target_port)`` pair.  For each entry and each
            agent, a ``FeedbackFlow`` is generated from
            ``router.source_port`` → ``agent.target_port``.  Port names are
            used verbatim; they are NOT prefixed with the agent name.

            Example::

                feedback_port_map={
                    "outcome":    ("Outcome",        "Outcome"),
                    "experience": ("Experience",     "Experience"),
                    "history":    ("History Update", "History Update"),
                }

        wiring: Optional explicit ``Flow`` overrides for the sequential
            composition step (agents_parallel >> router).  If omitted, relies
            on token-overlap auto-wiring.
        name: Name for the resulting ``FeedbackLoop``.  Defaults to
            ``f"{router.name} [multi-agent feedback]"``.

    Returns:
        A ``FeedbackLoop`` wrapping ``(agents_parallel >> router)`` with all
        ``len(agents) × len(feedback_port_map)`` contravariant flows.

    Raises:
        ValueError: If fewer than 2 agents are provided.

    Example::

        agent1 = reactive_decision_agent("Agent 1", include_outcome=False, include_feedback=False)
        agent2 = reactive_decision_agent("Agent 2", include_outcome=False, include_feedback=False)
        router = my_decision_router()

        game = multi_agent_composition(
            agents=[agent1, agent2],
            router=router,
            feedback_port_map={
                "outcome":    ("Outcome",        "Outcome"),
                "experience": ("Experience",     "Experience"),
                "history":    ("History Update", "History Update"),
            },
        )
    """
    if len(agents) < 2:
        raise ValueError(
            f"multi_agent_composition() requires at least 2 agents, got {len(agents)}"
        )

    # Step 1: parallel composition of all agents
    agents_parallel = ParallelComposition.from_list(agents)

    # Step 2: sequential into router
    inner = SequentialComposition(
        name=f"{agents_parallel.name} >> {router.name}",
        first=agents_parallel,
        second=router,
        wiring=wiring or [],
    )

    # Step 3: generate N × K contravariant feedback flows
    feedback_wiring: list[Flow] = []
    for agent in agents:
        for _label, (source_port, target_port) in feedback_port_map.items():
            feedback_wiring.append(
                FeedbackFlow(
                    source_game=router,
                    source_port=source_port,
                    target_game=agent,
                    target_port=target_port,
                )
            )

    loop_name = name or f"{router.name} [multi-agent feedback]"
    return FeedbackLoop(
        name=loop_name,
        inner=inner,
        feedback_wiring=feedback_wiring,
        signature=Signature(),
    )
