"""Household activity history.

Records meaningful events Haven took part in (a plan was proposed, a
preference changed). Not conversation transcripts, not sensor streams.
Timestamps are timezone-aware UTC.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

ActivityDetailValue = str | int | float | bool


class ActivityType(StrEnum):
    PLAN_PROPOSED = "plan_proposed"
    MOVIE_NIGHT_PREPARED = "movie_night_prepared"
    PREFERENCE_CHANGED = "preference_changed"
    PREFERENCE_DELETED = "preference_deleted"


class ActivityRecord(BaseModel):
    """One remembered household event."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"activity-{uuid.uuid4()}")
    household_id: str
    activity_type: ActivityType
    summary: str
    details: dict[str, ActivityDetailValue] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActivityStore(Protocol):
    """Storage contract for activity history (in-memory now, DynamoDB later)."""

    def record(self, activity: ActivityRecord) -> ActivityRecord: ...

    def list(
        self,
        household_id: str,
        *,
        activity_type: ActivityType | None = None,
        limit: int | None = None,
    ) -> list[ActivityRecord]: ...


class InMemoryActivityStore:
    """Process-local `ActivityStore`, newest first on read."""

    def __init__(self) -> None:
        self._records: list[ActivityRecord] = []

    def record(self, activity: ActivityRecord) -> ActivityRecord:
        self._records.append(activity)
        return activity

    def list(
        self,
        household_id: str,
        *,
        activity_type: ActivityType | None = None,
        limit: int | None = None,
    ) -> list[ActivityRecord]:
        matches = [
            record
            for record in self._records
            if record.household_id == household_id
            and (activity_type is None or record.activity_type == activity_type)
        ]
        matches.sort(key=lambda record: record.occurred_at, reverse=True)
        if limit is not None:
            matches = matches[:limit]
        return matches
