# person.py
# Haven Person Model

# Defines an individual member of a household. Presence, name and
# per-person preferences live here. Nothing in this module knows
# about planning, execution or MCP

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PresenceStatus(str, Enum):
    # Where a person is understood to currently be

    HOME = "home"
    AWAY = "away"
    UNKNOWN = "unknown"


@dataclass
class Person:
    # Represents a single member of the household

    person_id: str
    name: str

    presence: PresenceStatus = PresenceStatus.UNKNOWN
    preferences: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.person_id.strip():
            raise ValueError("person_id cannot be empty.")

        if not self.name.strip():
            raise ValueError("name cannot be empty.")

    def set_presence(self, presence: PresenceStatus) -> None:
        # Updates the person's presence status

        self.presence = presence

    def get_preference(self, key: str, default: Any = None) -> Any:
        # Returns a stored preference, or a default if unset

        return self.preferences.get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        # Stores or updates a preference for this person

        if not key.strip():
            raise ValueError("Preference key cannot be empty.")

        self.preferences[key] = value

    @property
    def is_home(self) -> bool:
        # Returns whether this person is currently home

        return self.presence == PresenceStatus.HOME

    def to_dict(self) -> dict[str, Any]:
        # Converts the person into a serializable dictionary

        return {
            "person_id": self.person_id,
            "name": self.name,
            "presence": self.presence.value,
            "preferences": dict(self.preferences),
        }


__all__ = [
    "Person",
    "PresenceStatus",
]
