# resolver.py
# Haven Context Resolver

# Implements the core context-gathering flow:
#
#   User gives Haven a goal
#           |
#   Haven determines what information is required
#           |
#   Context Resolver searches approved sources
#           |
#   Required information available?
#          / \
#        Yes  No
#         |    |
#       Use   Ask user
#         \    /
#          |
#      Create plan
#
# The resolver never tries to know everything happening in the home.
# It only gathers the facts a specific goal requires, in priority
# order across the approved sources, and raises ClarificationNeeded
# when a required fact cannot be confidently obtained from any of
# them. It is the planner's (Person A's) job to decide what to do with
# that — typically, ask the user the returned question directly

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from haven.models.context import HouseholdContext
from haven.context.expiry import default_expiry_for, is_expired
from haven.context.facts import FactStore, make_fact
from haven.context.sources import ContextSource

# The order sources are tried in for any fact that more than one
# source could plausibly answer. Earlier sources are preferred because
# they are more direct/reliable for the fact in question.
DEFAULT_SOURCE_PRIORITY = [
    "user_input",
    "device_state",
    "connected_service",
    "sensor",
    "memory",
]


@dataclass
class FactRequest:
    # Describes a single fact the planner needs resolved, plus any
    # extra parameters a source needs to look it up (e.g. which
    # room_id or device_id the fact applies to)

    fact_name: str
    required: bool = True
    params: dict = field(default_factory=dict)


class ClarificationNeeded(Exception):
    # Raised when a required fact could not be confidently obtained
    # from any approved source. Carries the question Haven should ask
    # the user, and which fact it corresponds to

    def __init__(self, fact_name: str, question: str) -> None:
        self.fact_name = fact_name
        self.question = question

        super().__init__(question)


def resolve_context(
    goal: str,
    required_facts: list[FactRequest],
    sources: list[ContextSource],
    household_id: str,
    source_priority: list[str] | None = None,
) -> HouseholdContext:
    # Resolves every required fact for a goal, using the given sources
    # in priority order, and assembles a HouseholdContext.
    #
    # Raises ClarificationNeeded on the first required fact that no
    # source can confidently answer. Optional facts that can't be
    # resolved are simply omitted.

    priority = source_priority or DEFAULT_SOURCE_PRIORITY
    ordered_sources = _order_sources(sources, priority)

    store = FactStore()

    for request in required_facts:
        fact = _resolve_single_fact(request, ordered_sources, store)

        if fact is not None:
            store.add(fact)
            continue

        if request.required:
            raise ClarificationNeeded(
                fact_name=request.fact_name,
                question=_default_clarifying_question(request.fact_name),
            )

    return HouseholdContext(
        household_id=household_id,
        goal=goal,
        facts=store.as_list(),
        generated_at=datetime.now(timezone.utc),
    )


def apply_user_clarification(
    fact_name: str,
    value: object,
    store: FactStore,
) -> None:
    # Records a fact the user supplied directly in response to a
    # clarifying question, so resolution can continue without asking
    # again for the remainder of the session

    from haven.context.sources import ContextSourceType

    fact = make_fact(
        fact_name=fact_name,
        value=value,
        source=ContextSourceType.CLARIFICATION,
        confidence=1.0,
        expires_at=default_expiry_for(fact_name),
    )

    store.add(fact)


def _resolve_single_fact(
    request: FactRequest,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> object | None:
    # Tries each source in priority order until one confidently
    # answers the requested fact, reusing an existing unexpired fact
    # if already gathered this session

    existing = store.get(request.fact_name)

    if existing is not None and not is_expired(existing):
        return existing

    for source in ordered_sources:
        if not source.supports(request.fact_name):
            continue

        value = source.fetch(request.fact_name, **request.params)

        if value is None:
            continue

        return make_fact(
            fact_name=request.fact_name,
            value=value,
            source=source.source_type,
            expires_at=default_expiry_for(request.fact_name),
        )

    return None


def _order_sources(
    sources: list[ContextSource],
    priority: list[str],
) -> list[ContextSource]:
    # Sorts sources according to the priority list, with any source
    # type not listed placed at the end in its original order

    def sort_key(source: ContextSource) -> int:
        try:
            return priority.index(source.source_type.value)
        except ValueError:
            return len(priority)

    return sorted(sources, key=sort_key)


def _default_clarifying_question(fact_name: str) -> str:
    # Produces a reasonable fallback question when no more specific
    # phrasing has been configured for a fact. Callers (the planner)
    # are free to use their own phrasing instead

    readable = fact_name.replace("_", " ").replace(":", " ")

    return f"Could you tell me {readable}?"


__all__ = [
    "FactRequest",
    "ClarificationNeeded",
    "resolve_context",
    "apply_user_clarification",
    "DEFAULT_SOURCE_PRIORITY",
]
