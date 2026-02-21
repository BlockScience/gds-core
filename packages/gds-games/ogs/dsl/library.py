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

from gds.ir.models import FlowDirection

from ogs.dsl.composition import FeedbackLoop, Flow, SequentialComposition
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


def reactive_decision_agent(name: str = "Reactive Decision Agent") -> FeedbackLoop:
    """Complete reactive decision agent — the canonical single-agent decision loop."""
    cb = context_builder(tags={"domain": "Observation"})
    hist = history(tags={"domain": "State"})
    pol = policy(tags={"domain": "Learning"})
    rd = reactive_decision(tags={"domain": "Decision"})
    out = outcome(tags={"domain": "Outcome"})

    # Build the inner composite with explicit wiring
    inner = SequentialComposition(
        name=name,
        first=cb,
        second=SequentialComposition(
            name="History >> Policy >> RD >> Outcome",
            first=hist,
            second=SequentialComposition(
                name="Policy >> RD >> Outcome",
                first=pol,
                second=SequentialComposition(
                    name="RD >> Outcome",
                    first=rd,
                    second=out,
                    wiring=[
                        Flow(
                            source_game="Reactive Decision",
                            source_port="Decision",
                            target_game="Outcome",
                            target_port="Decision",
                        ),
                    ],
                ),
                wiring=[
                    Flow(
                        source_game="Policy",
                        source_port="Latest Policy",
                        target_game="Reactive Decision",
                        target_port="Latest Policy",
                    ),
                ],
            ),
            wiring=[
                Flow(
                    source_game="History",
                    source_port="Latest History",
                    target_game="Policy",
                    target_port="Latest History",
                ),
            ],
        ),
        wiring=[
            Flow(
                source_game="Context Builder",
                source_port="Observation, Context",
                target_game="Reactive Decision",
                target_port="Observation, Context",
            ),
        ],
    )

    # Wrap with feedback loops
    return FeedbackLoop(
        name=name,
        inner=inner,
        feedback_wiring=[
            # Outcome → Reactive Decision: utility feedback
            Flow(
                source_game="Outcome",
                source_port="Outcome",
                target_game="Reactive Decision",
                target_port="Outcome",
                direction=FlowDirection.CONTRAVARIANT,
            ),
            # Reactive Decision → Policy: experience feedback
            Flow(
                source_game="Reactive Decision",
                source_port="Experience",
                target_game="Policy",
                target_port="Experience",
                direction=FlowDirection.CONTRAVARIANT,
            ),
            # Policy → History: history update feedback
            Flow(
                source_game="Policy",
                source_port="History Update",
                target_game="History",
                target_port="History Update",
                direction=FlowDirection.CONTRAVARIANT,
            ),
        ],
        signature=Signature(),  # computed by validator
    )
