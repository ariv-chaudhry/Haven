"""Calendar integration abstraction.

Phase 2 is backed by explicit demo events; no external calendar API is
called. The interface answers the questions Haven actually needs:

    What is the next event?
    How many minutes are available before it?

`CalendarService.lookup_fact` matches the callback shape Person B's
``ConnectedServiceSource`` expects (``calendar_lookup(fact_name, **kwargs)``)
for the fact names ``available_time_minutes`` and ``next_event_time``. This
module does not import ``haven.context``.

All datetimes are timezone-aware; naive values are rejected. UTC is used
internally.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

FACT_AVAILABLE_TIME_MINUTES = "available_time_minutes"
FACT_NEXT_EVENT_TIME = "next_event_time"
SUPPORTED_FACTS: frozenset[str] = frozenset({FACT_AVAILABLE_TIME_MINUTES, FACT_NEXT_EVENT_TIME})

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


class CalendarEvent(BaseModel):
    """A single scheduled event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def _aware(cls, value: datetime, info: Any) -> datetime:
        return _ensure_aware_utc(value, info.field_name)

    @model_validator(mode="after")
    def _ordered(self) -> CalendarEvent:
        if self.end <= self.start:
            raise ValueError("event end must be after start")
        if not self.id.strip():
            raise ValueError("event id must not be empty")
        return self

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class CalendarService:
    """Read-only calendar view over a fixed set of events.

    ``clock`` is injectable so tests and demos are deterministic.
    """

    def __init__(self, events: Sequence[CalendarEvent] = (), *, clock: Clock | None = None) -> None:
        self._events = sorted(events, key=lambda event: event.start)
        self._clock = clock or utc_now

    def now(self) -> datetime:
        return _ensure_aware_utc(self._clock(), "clock")

    def events(self) -> list[CalendarEvent]:
        return list(self._events)

    def next_event(self, now: datetime | None = None) -> CalendarEvent | None:
        """Return the first event that has not yet started, if any."""

        current = self._resolve_now(now)
        for event in self._events:
            if event.start > current:
                return event
        return None

    def current_event(self, now: datetime | None = None) -> CalendarEvent | None:
        """Return an event in progress at ``now``, if any."""

        current = self._resolve_now(now)
        for event in self._events:
            if event.start <= current < event.end:
                return event
        return None

    def available_minutes(self, now: datetime | None = None) -> int | None:
        """Whole minutes until the next event starts; None when nothing is upcoming.

        Returns 0 when an event is already in progress.
        """

        current = self._resolve_now(now)
        if self.current_event(current) is not None:
            return 0
        upcoming = self.next_event(current)
        if upcoming is None:
            return None
        return max(0, int((upcoming.start - current).total_seconds() // 60))

    def events_between(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        start_utc = _ensure_aware_utc(start, "start")
        end_utc = _ensure_aware_utc(end, "end")
        return [e for e in self._events if e.start < end_utc and e.end > start_utc]

    # -- Context-source callback ------------------------------------------- #

    def lookup_fact(self, fact_name: str, **kwargs: Any) -> Any | None:
        """Answer a connected-service fact for Person B's ``ConnectedServiceSource``.

        ``available_time_minutes`` -> int | None
        ``next_event_time``        -> datetime (UTC) | None

        ``now`` may be supplied via kwargs; otherwise the service clock is used.
        Unknown fact names return None.
        """

        now = kwargs.get("now")
        if fact_name == FACT_AVAILABLE_TIME_MINUTES:
            return self.available_minutes(now)
        if fact_name == FACT_NEXT_EVENT_TIME:
            upcoming = self.next_event(now)
            return None if upcoming is None else upcoming.start
        return None

    def _resolve_now(self, now: datetime | None) -> datetime:
        return self.now() if now is None else _ensure_aware_utc(now, "now")


def demo_calendar(now: datetime | None = None, *, clock: Clock | None = None) -> CalendarService:
    """A small deterministic calendar for local demos and the workflow harness.

    Events are placed relative to ``now`` (default: current UTC time): a
    2-hour free window, then a family call, then a late reminder.
    """

    anchor = _ensure_aware_utc(now, "now") if now is not None else utc_now()
    events = [
        CalendarEvent(
            id="evt-call",
            title="Family video call",
            start=anchor + timedelta(hours=2),
            end=anchor + timedelta(hours=2, minutes=30),
        ),
        CalendarEvent(
            id="evt-bedtime",
            title="Kids' bedtime",
            start=anchor + timedelta(hours=4),
            end=anchor + timedelta(hours=4, minutes=15),
        ),
    ]
    return CalendarService(events, clock=clock or (lambda: anchor))
