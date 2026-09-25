# sources.py
# Haven Context Sources

# Defines the approved places the Context Resolver is allowed to pull
# facts from, and the common interface every source implements. Haven
# never infers context from anywhere outside this list, and it never
# uses cameras or continuous video

# Per household member request, sources are intentionally narrow:
# - user input        (stated directly by the person)
# - connected service  (calendar, reminders, schedules)
# - device state       (TV, lights, thermostat, locks, security)
# - low-resolution sensor (motion / occupancy / contact, no video)
# - saved preference/history (Haven's own memory)
#
# If none of these can confidently answer a required fact, the
# resolver asks the user directly rather than guessing

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ContextSourceType(str, Enum):
    # Every approved origin for a context fact

    USER_INPUT = "user_input"
    CONNECTED_SERVICE = "connected_service"
    DEVICE_STATE = "device_state"
    SENSOR = "sensor"
    MEMORY = "memory"
    CLARIFICATION = "clarification"


class ContextSource(ABC):
    # Common interface every context source implements. Concrete
    # sources may be backed by the household simulator today and by
    # real integrations later, without the resolver's logic changing

    source_type: ContextSourceType

    @abstractmethod
    def supports(self, fact_name: str) -> bool:
        # Returns whether this source is able to answer the given fact

        raise NotImplementedError

    @abstractmethod
    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        # Attempts to fetch a fact's value. Returns None if the value
        # could not be confidently obtained, rather than guessing

        raise NotImplementedError


class UserStatementSource(ContextSource):
    # Facts the user has stated directly in the current conversation,
    # such as "we're all home" or "I have 45 minutes"

    source_type = ContextSourceType.USER_INPUT

    def __init__(self, statements: dict[str, Any] | None = None) -> None:
        self._statements = dict(statements or {})

    def supports(self, fact_name: str) -> bool:
        return fact_name in self._statements

    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        return self._statements.get(fact_name)


class DeviceStateSource(ContextSource):
    # Facts backed by a device's current state, via the household
    # simulator in development and a real device integration later

    source_type = ContextSourceType.DEVICE_STATE

    SUPPORTED_FACTS = {"device_state", "tv_state", "lock_state", "security_armed"}

    def __init__(self, household_service: Any) -> None:
        self._household_service = household_service

    def supports(self, fact_name: str) -> bool:
        return fact_name in self.SUPPORTED_FACTS

    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        device_id = kwargs.get("device_id")

        if device_id is None:
            return None

        return self._household_service.get_device_state(device_id)


class SensorSource(ContextSource):
    # Low-resolution sensor facts such as room occupancy. Never backed
    # by cameras or video, only simple boolean/contact-style facts

    source_type = ContextSourceType.SENSOR

    SUPPORTED_FACTS = {"room_occupied"}

    def __init__(self, household_service: Any) -> None:
        self._household_service = household_service

    def supports(self, fact_name: str) -> bool:
        return fact_name in self.SUPPORTED_FACTS

    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        room_id = kwargs.get("room_id")

        if room_id is None:
            return None

        room_state = self._household_service.get_room_state(room_id)

        if room_state is None:
            return None

        return room_state.get("occupied")


class MemorySource(ContextSource):
    # Saved preferences and history that Haven has intentionally
    # remembered. Backed by an in-memory store during early phases and
    # by src/haven/memory/service.py (Person A) once DynamoDB lands

    source_type = ContextSourceType.MEMORY

    def __init__(self, memory_lookup: Any | None = None) -> None:
        self._memory_lookup = memory_lookup

    def supports(self, fact_name: str) -> bool:
        return fact_name.startswith("preference:") or fact_name.startswith("history:")

    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        if self._memory_lookup is None:
            return None

        return self._memory_lookup(fact_name, **kwargs)


class ConnectedServiceSource(ContextSource):
    # Facts backed by an explicitly connected external service, such
    # as a calendar. During early phases this is satisfied by demo
    # data behind the same interface (owned by Person A in
    # src/haven/integrations/calendar.py)

    source_type = ContextSourceType.CONNECTED_SERVICE

    SUPPORTED_FACTS = {"available_time_minutes", "next_event_time"}

    def __init__(self, calendar_lookup: Any | None = None) -> None:
        self._calendar_lookup = calendar_lookup

    def supports(self, fact_name: str) -> bool:
        return fact_name in self.SUPPORTED_FACTS

    def fetch(self, fact_name: str, **kwargs: Any) -> Any | None:
        if self._calendar_lookup is None:
            return None

        return self._calendar_lookup(fact_name, **kwargs)


__all__ = [
    "ContextSourceType",
    "ContextSource",
    "UserStatementSource",
    "DeviceStateSource",
    "SensorSource",
    "MemorySource",
    "ConnectedServiceSource",
]
