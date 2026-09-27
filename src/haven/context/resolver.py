"""Haven Context Resolver.

Implements the core context-gathering flow used before planning:

    User gives Haven a goal
            |
    Haven determines what information is required
            |
    Context Resolver searches approved sources
            |
    Required information available?
           / \\
         Yes  No
          |    |
        Use   Ask user
          \\    /
           |
       Create plan

The resolver never tries to know everything happening in the home. Most
of a `HouseholdContext` is mapped directly from the household's current
domain snapshot (people, rooms, devices — already reflecting whatever the
household simulator or a real integration currently reports). Only a
small number of scalar facts that genuinely need to be resolved across
several possible sources go through the source-priority engine below:

    - available_minutes      (a connected calendar service)
    - preferred_room_id      (Haven's saved preferences)
    - preferred_genres       (Haven's saved preferences)
    - per-person presence overrides (an explicit user statement, e.g.
      "Sam is staying behind", overriding the household's default record)

`resolve_context` raises `ClarificationNeeded` only for facts explicitly
requested as required and left unresolved by every source. It is the
planner's (Person A's) job to decide what to do with that — typically,
surface the question to the user directly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from haven.context.expiry import default_expiry_for, is_expired
from haven.context.facts import FactStore, GatheredFact, make_fact
from haven.context.sources import ContextSource, ContextSourceType
from haven.models.context import (
    DeviceCapability,
    DeviceContext,
    HouseholdContext,
    MediaItem,
    PersonContext,
    PresenceState,
    RoomContext,
)
from haven.models.device import Device, DeviceType
from haven.models.household import Household
from haven.models.person import Person, PresenceStatus

# The order sources are tried in for any fact more than one source could
# plausibly answer. Earlier sources are preferred because they are more
# direct/reliable for the fact in question.
DEFAULT_SOURCE_PRIORITY = [
    ContextSourceType.USER_INPUT.value,
    ContextSourceType.DEVICE_STATE.value,
    ContextSourceType.CONNECTED_SERVICE.value,
    ContextSourceType.SENSOR.value,
    ContextSourceType.MEMORY.value,
]

# How a household domain DeviceType maps onto the capability strings the
# planner understands. A device with no listed capability (a sensor, for
# instance) simply offers nothing actionable to the planner yet.
_DEVICE_CAPABILITY_MAP: dict[DeviceType, list[str]] = {
    DeviceType.TV: [DeviceCapability.MEDIA_PLAYBACK, DeviceCapability.DISPLAY],
    DeviceType.LIGHT: [DeviceCapability.LIGHTING],
    DeviceType.THERMOSTAT: [DeviceCapability.THERMOSTAT],
    DeviceType.LOCK: [DeviceCapability.LOCK],
    DeviceType.SECURITY_SYSTEM: [DeviceCapability.SECURITY],
    DeviceType.OCCUPANCY_SENSOR: [],
    DeviceType.CONTACT_SENSOR: [],
    DeviceType.OTHER: [],
}

_PRESENCE_MAP: dict[PresenceStatus, PresenceState] = {
    PresenceStatus.HOME: PresenceState.PRESENT,
    PresenceStatus.AWAY: PresenceState.AWAY,
    PresenceStatus.UNKNOWN: PresenceState.UNKNOWN,
}

FACT_AVAILABLE_TIME_MINUTES = "available_time_minutes"
FACT_PREFERRED_ROOM = "preference:preferred_room"
FACT_PREFERRED_GENRES = "preference:preferred_genres"


@dataclass
class FactRequest:
    """Describes a single fact the caller needs resolved.

    ``params`` are passed through to whichever source answers the fact
    (for example ``household_id`` for a memory/calendar lookup, or
    ``device_id`` / ``room_id`` for a device or sensor lookup).
    """

    fact_name: str
    required: bool = True
    params: dict = field(default_factory=dict)


class ClarificationNeeded(Exception):
    """A required fact could not be confidently obtained from any source.

    Carries the question Haven should ask the user, and which fact it
    corresponds to.
    """

    def __init__(self, fact_name: str, question: str) -> None:
        self.fact_name = fact_name
        self.question = question

        super().__init__(question)


def resolve_context(
    goal: str,
    household: Household,
    media_options: Sequence[MediaItem],
    sources: list[ContextSource],
    *,
    extra_facts: list[FactRequest] | None = None,
    source_priority: list[str] | None = None,
) -> HouseholdContext:
    """Resolve a `HouseholdContext` snapshot for `goal`.

    ``household`` is Person B's current domain snapshot (typically read
    from the household simulator). Its people, rooms and devices are
    mapped directly into the planning contract; ``sources`` are consulted
    only for the handful of facts that genuinely vary by source
    (available time, preferences, presence overrides).

    ``extra_facts`` lets a caller resolve additional facts this goal
    needs that are not part of the `HouseholdContext` contract itself
    (for example, a future "Leaving Home" workflow's "is everyone
    leaving?" check). They are resolved and validated here — raising
    `ClarificationNeeded` if required and unresolved — but are not folded
    into the returned context.

    Raises `ClarificationNeeded` when a required fact cannot be obtained
    from any approved source. `ValueError` for invalid input.
    """

    _validate_goal(goal)
    _validate_household(household)

    priority = source_priority or DEFAULT_SOURCE_PRIORITY
    ordered_sources = _order_sources(sources, priority)
    store = FactStore()

    people = [_resolve_person(person, ordered_sources, store) for person in household.people]
    rooms = [RoomContext(id=room.room_id, name=room.name) for room in household.rooms]
    devices = [_map_device(device) for device in household.devices]

    available_minutes = _resolve_available_minutes(household, ordered_sources, store)
    preferred_room_id = _resolve_preferred_room(household, ordered_sources, store)
    preferred_genres = _resolve_preferred_genres(household, ordered_sources, store)

    for request in extra_facts or []:
        fact = _resolve_single_fact(request, ordered_sources, store)
        if fact is not None:
            store.add(fact)
        elif request.required:
            raise ClarificationNeeded(
                fact_name=request.fact_name,
                question=_default_clarifying_question(request.fact_name),
            )

    return HouseholdContext(
        household_id=household.household_id,
        people=people,
        rooms=rooms,
        devices=devices,
        media_options=list(media_options),
        available_minutes=available_minutes,
        preferred_room_id=preferred_room_id,
        preferred_genres=preferred_genres,
    )


def apply_user_clarification(fact_name: str, value: object, store: FactStore) -> None:
    """Record a fact the user supplied in response to a clarifying question.

    Lets a caller continue a resolution attempt without asking again for
    the remainder of the session.
    """

    fact = make_fact(
        fact_name=fact_name,
        value=value,
        source=ContextSourceType.CLARIFICATION,
        confidence=1.0,
        expires_at=default_expiry_for(fact_name),
    )

    store.add(fact)


# --------------------------------------------------------------------------- #
# Domain -> planning-contract mapping
# --------------------------------------------------------------------------- #


def _resolve_person(
    person: Person,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> PersonContext:
    """Map a household `Person` to a `PersonContext`, honoring a fresher
    user-stated presence override (e.g. "Sam is staying behind") when one
    has been supplied.
    """

    fact_name = f"person_home:{person.person_id}"
    fact = _resolve_single_fact(FactRequest(fact_name, required=False), ordered_sources, store)

    if fact is not None:
        store.add(fact)
        presence = PresenceState.PRESENT if bool(fact.value) else PresenceState.AWAY
    else:
        presence = _PRESENCE_MAP.get(person.presence, PresenceState.UNKNOWN)

    return PersonContext(id=person.person_id, display_name=person.name, presence=presence)


def _map_device(device: Device) -> DeviceContext:
    """Map a household `Device` to a `DeviceContext`."""

    return DeviceContext(
        id=device.device_id,
        name=device.name,
        room_id=device.room_id,
        capabilities=list(_DEVICE_CAPABILITY_MAP.get(device.device_type, [])),
        is_available=device.online,
    )


def _resolve_available_minutes(
    household: Household,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> int | None:
    request = FactRequest(
        FACT_AVAILABLE_TIME_MINUTES,
        required=False,
        params={"household_id": household.household_id},
    )
    fact = _resolve_single_fact(request, ordered_sources, store)
    if fact is None:
        return None

    store.add(fact)
    try:
        return int(fact.value)
    except (TypeError, ValueError):
        return None


def _resolve_preferred_room(
    household: Household,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> str | None:
    request = FactRequest(
        FACT_PREFERRED_ROOM,
        required=False,
        params={"household_id": household.household_id},
    )
    fact = _resolve_single_fact(request, ordered_sources, store)
    if fact is None or not isinstance(fact.value, str):
        return None

    store.add(fact)
    room_id = fact.value
    if any(room.room_id == room_id for room in household.rooms):
        return room_id
    return None


def _resolve_preferred_genres(
    household: Household,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> list[str]:
    request = FactRequest(
        FACT_PREFERRED_GENRES,
        required=False,
        params={"household_id": household.household_id},
    )
    fact = _resolve_single_fact(request, ordered_sources, store)
    if fact is None:
        return []

    store.add(fact)
    value = fact.value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return []


# --------------------------------------------------------------------------- #
# Source-resolution engine
# --------------------------------------------------------------------------- #


def _resolve_single_fact(
    request: FactRequest,
    ordered_sources: list[ContextSource],
    store: FactStore,
) -> GatheredFact | None:
    """Try each source in priority order until one confidently answers
    the requested fact, reusing an existing unexpired fact if already
    gathered this session.
    """

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


def _order_sources(sources: list[ContextSource], priority: list[str]) -> list[ContextSource]:
    """Sort sources by priority, with unlisted source types placed last."""

    def sort_key(source: ContextSource) -> int:
        try:
            return priority.index(source.source_type.value)
        except ValueError:
            return len(priority)

    return sorted(sources, key=sort_key)


def _default_clarifying_question(fact_name: str) -> str:
    """Fallback question when no more specific phrasing has been configured."""

    readable = fact_name.replace("_", " ").replace(":", " ")
    return f"Could you tell me {readable}?"


def _validate_goal(goal: str) -> None:
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("goal must be a non-empty string")


def _validate_household(household: Household) -> None:
    if not isinstance(household, Household):
        raise ValueError("household must be a Household")


__all__ = [
    "FactRequest",
    "ClarificationNeeded",
    "resolve_context",
    "apply_user_clarification",
    "DEFAULT_SOURCE_PRIORITY",
]
