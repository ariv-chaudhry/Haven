"""Application-facing memory facade.

    MemoryService
        -> PreferenceStore  (InMemoryPreferenceStore today, DynamoDB in Phase 3)
        -> ActivityStore    (InMemoryActivityStore today, DynamoDB in Phase 3)

Callers (planner, MCP, context) depend only on this class. Swapping storage
means passing different store implementations to the constructor.

`lookup_fact` matches the callback shape Person B's ``MemorySource`` expects
(``memory_lookup(fact_name, **kwargs)``) using the existing conventions
``preference:<key>`` and ``history:<activity_type>``. This module does not
import ``haven.context``.
"""

from __future__ import annotations

import logging
from typing import Any

from haven.memory.activity import (
    ActivityDetailValue,
    ActivityRecord,
    ActivityStore,
    ActivityType,
    InMemoryActivityStore,
)
from haven.memory.preferences import (
    InMemoryPreferenceStore,
    Preference,
    PreferenceStore,
    PreferenceValue,
    is_durable_preference_key,
)
from haven.models.plan import Plan

logger = logging.getLogger(__name__)

PREFERENCE_FACT_PREFIX = "preference:"
HISTORY_FACT_PREFIX = "history:"
DEFAULT_HISTORY_LIMIT = 10


class MemoryService:
    """Durable household memory: explicit preferences and activity history."""

    def __init__(
        self,
        *,
        preferences: PreferenceStore | None = None,
        activity: ActivityStore | None = None,
        default_household_id: str | None = None,
    ) -> None:
        self._preferences: PreferenceStore = preferences or InMemoryPreferenceStore()
        self._activity: ActivityStore = activity or InMemoryActivityStore()
        self._default_household_id = default_household_id

    # -- Preferences ------------------------------------------------------- #

    def save_preference(
        self,
        household_id: str,
        key: str,
        value: PreferenceValue,
        *,
        person_id: str | None = None,
    ) -> Preference:
        """Store (or intentionally overwrite) a durable preference.

        Raises `ValueError` for empty IDs/keys and for transient state keys
        such as ``room_occupied`` that must not become durable memory.
        """

        household_id = _require(household_id, "household_id")
        key = _require(key, "key").lower()
        if not is_durable_preference_key(key):
            raise ValueError(f"{key!r} describes temporary state and cannot be saved as memory")

        preference = Preference(
            household_id=household_id,
            key=key,
            value=value,
            person_id=_optional(person_id),
        )
        saved = self._preferences.save(preference)
        self.record_activity(
            household_id,
            ActivityType.PREFERENCE_CHANGED,
            f"Preference '{key}' updated",
            details={"key": key, "scope": saved.scope},
        )
        return saved

    def get_preference(
        self, household_id: str, key: str, *, person_id: str | None = None
    ) -> Preference | None:
        return self._preferences.get(
            _require(household_id, "household_id"),
            _require(key, "key").lower(),
            _optional(person_id),
        )

    def get_preferences(
        self, household_id: str, *, person_id: str | None = None
    ) -> list[Preference]:
        return self._preferences.list(_require(household_id, "household_id"), _optional(person_id))

    def delete_preference(
        self, household_id: str, key: str, *, person_id: str | None = None
    ) -> bool:
        household_id = _require(household_id, "household_id")
        key = _require(key, "key").lower()
        deleted = self._preferences.delete(household_id, key, _optional(person_id))
        if deleted:
            self.record_activity(
                household_id,
                ActivityType.PREFERENCE_DELETED,
                f"Preference '{key}' deleted",
                details={"key": key},
            )
        return deleted

    # -- Activity ---------------------------------------------------------- #

    def record_activity(
        self,
        household_id: str,
        activity_type: ActivityType,
        summary: str,
        *,
        details: dict[str, ActivityDetailValue] | None = None,
    ) -> ActivityRecord:
        record = ActivityRecord(
            household_id=_require(household_id, "household_id"),
            activity_type=activity_type,
            summary=_require(summary, "summary"),
            details=dict(details or {}),
        )
        return self._activity.record(record)

    def record_plan_proposed(self, household_id: str, plan: Plan) -> ActivityRecord:
        """Remember that a plan was proposed. Stores plan metadata, not context."""

        return self.record_activity(
            household_id,
            ActivityType.PLAN_PROPOSED,
            f"Proposed plan for: {plan.goal}",
            details={
                "plan_id": plan.id,
                "step_count": len(plan.steps),
                "requires_confirmation": plan.requires_confirmation,
            },
        )

    def list_activity(
        self,
        household_id: str,
        *,
        activity_type: ActivityType | None = None,
        limit: int | None = None,
    ) -> list[ActivityRecord]:
        return self._activity.list(
            _require(household_id, "household_id"), activity_type=activity_type, limit=limit
        )

    # -- Context-source callback ------------------------------------------- #

    def lookup_fact(self, fact_name: str, **kwargs: Any) -> Any | None:
        """Answer a memory fact for Person B's ``MemorySource``.

        ``preference:<key>``      -> preference value or None
        ``history:<activity_type>`` -> list of ActivityRecord (newest first) or None

        ``household_id`` and optional ``person_id`` / ``limit`` come from
        kwargs; ``household_id`` falls back to the service default. Any
        other fact name (including transient state) returns None.
        """

        household_id = kwargs.get("household_id") or self._default_household_id
        if not household_id:
            return None

        if fact_name.startswith(PREFERENCE_FACT_PREFIX):
            key = fact_name[len(PREFERENCE_FACT_PREFIX) :]
            if not key.strip():
                return None
            preference = self.get_preference(household_id, key, person_id=kwargs.get("person_id"))
            return None if preference is None else preference.value

        if fact_name.startswith(HISTORY_FACT_PREFIX):
            raw_type = fact_name[len(HISTORY_FACT_PREFIX) :]
            try:
                activity_type = ActivityType(raw_type)
            except ValueError:
                return None
            records = self.list_activity(
                household_id,
                activity_type=activity_type,
                limit=int(kwargs.get("limit", DEFAULT_HISTORY_LIMIT)),
            )
            return records or None

        return None


def _require(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
