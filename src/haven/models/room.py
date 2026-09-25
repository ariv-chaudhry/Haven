# room.py
# Haven Room Model

# Defines a physical room within the household. Occupancy is tracked
# only as a simple boolean fact, sourced from low-resolution sensors
# or user statements. Haven never stores camera or video data here

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Room:
    # Represents a single room within the household

    room_id: str
    name: str

    occupied: bool = False
    current_activity: str | None = None

    device_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.room_id.strip():
            raise ValueError("room_id cannot be empty.")

        if not self.name.strip():
            raise ValueError("name cannot be empty.")

    def set_occupied(self, occupied: bool) -> None:
        # Updates whether the room is currently occupied

        self.occupied = occupied

    def set_activity(self, activity: str | None) -> None:
        # Updates the room's current activity, if known

        self.current_activity = activity

    def add_device(self, device_id: str) -> None:
        # Associates a device id with this room

        if not device_id.strip():
            raise ValueError("device_id cannot be empty.")

        if device_id not in self.device_ids:
            self.device_ids.append(device_id)

    @property
    def is_available(self) -> bool:
        # Returns whether the room is free for a new activity

        return not self.occupied

    def to_dict(self) -> dict[str, Any]:
        # Converts the room into a serializable dictionary

        return {
            "room_id": self.room_id,
            "name": self.name,
            "occupied": self.occupied,
            "current_activity": self.current_activity,
            "device_ids": list(self.device_ids),
        }


__all__ = [
    "Room",
]
