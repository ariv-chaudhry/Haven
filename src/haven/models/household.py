# household.py
# Haven Household Model

# Defines the top-level Household domain object. A Household is the
# root container for everything Haven's Context Resolver can reason
# about: the people who live there, the rooms in the home, and the
# devices connected to it

# This module is intentionally free of any planning, execution or
# MCP logic. It only describes household data, making it easy to
# test in isolation and safe for both developers to depend on

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from haven.models.person import Person
from haven.models.room import Room
from haven.models.device import Device


@dataclass
class Household:
    # Represents a single household tracked by Haven

    household_id: str
    name: str
    timezone: str = "UTC"

    people: list[Person] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)

    preferences: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.household_id.strip():
            raise ValueError("household_id cannot be empty.")

        if not self.name.strip():
            raise ValueError("name cannot be empty.")

    def get_person(self, person_id: str) -> Person | None:
        # Returns the person with the given id, if present

        for person in self.people:
            if person.person_id == person_id:
                return person

        return None

    def get_room(self, room_id: str) -> Room | None:
        # Returns the room with the given id, if present

        for room in self.rooms:
            if room.room_id == room_id:
                return room

        return None

    def get_device(self, device_id: str) -> Device | None:
        # Returns the device with the given id, if present

        for device in self.devices:
            if device.device_id == device_id:
                return device

        return None

    def devices_in_room(self, room_id: str) -> list[Device]:
        # Returns every device located in the given room

        return [device for device in self.devices if device.room_id == room_id]

    @property
    def people_home(self) -> list[Person]:
        # Returns every person currently marked as home

        return [person for person in self.people if person.is_home]

    @property
    def anyone_home(self) -> bool:
        # Returns whether at least one person is currently home

        return len(self.people_home) > 0

    def to_dict(self) -> dict[str, Any]:
        # Converts the household into a serializable dictionary

        return {
            "household_id": self.household_id,
            "name": self.name,
            "timezone": self.timezone,
            "people": [person.to_dict() for person in self.people],
            "rooms": [room.to_dict() for room in self.rooms],
            "devices": [device.to_dict() for device in self.devices],
            "preferences": dict(self.preferences),
        }


__all__ = [
    "Household",
]
