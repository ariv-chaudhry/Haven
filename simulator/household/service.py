# service.py
# Haven Household Simulator Service

# Exposes household state (people, rooms, devices) without any real
# hardware, backed by the JSON demo data in simulator/household/data/.
# This lets both the Context Resolver and the executor be developed
# and demoed before any real device integration exists

# The simulator intentionally mirrors the shape of a real integration
# so that swapping it out later does not require changing callers

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path(__file__).parent / "data"


class HouseholdSimulatorService:
    # In-memory household simulator, loaded from local JSON fixtures

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self._data_dir = Path(data_dir)

        self._household: dict[str, Any] = {}
        self._people: list[dict[str, Any]] = []
        self._rooms: list[dict[str, Any]] = []

        self.reload()

    def reload(self) -> None:
        # Reloads all simulator state from disk, discarding any
        # in-memory changes made during the current run

        self._household = self._load_json("household.json")
        self._people = self._load_json("people.json")
        self._rooms = self._load_json("rooms.json")

    def _load_json(self, filename: str) -> Any:
        path = self._data_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"Simulator data file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    # -- Household -----------------------------------------------------

    def get_household(self) -> dict[str, Any]:
        # Returns the household record, including stored preferences

        return dict(self._household)

    def get_preference(self, key: str, default: Any = None) -> Any:
        # Returns a household-level preference by dotted key, e.g.
        # "media.preferred_genres"

        node: Any = self._household.get("preferences", {})

        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default

            node = node[part]

        return node

    # -- People ----------------------------------------------------------

    def get_people(self) -> list[dict[str, Any]]:
        # Returns every known person

        return [dict(person) for person in self._people]

    def get_person(self, person_id: str) -> dict[str, Any] | None:
        # Returns a single person by id, if present

        for person in self._people:
            if person.get("person_id") == person_id:
                return dict(person)

        return None

    def people_home(self) -> list[dict[str, Any]]:
        # Returns every person currently marked as home

        return [p for p in self.get_people() if p.get("presence") == "home"]

    def set_presence(self, person_id: str, presence: str) -> None:
        # Updates a person's presence for the remainder of this run

        for person in self._people:
            if person.get("person_id") == person_id:
                person["presence"] = presence
                return

        raise KeyError(f"Unknown person_id: {person_id}")

    # -- Rooms -----------------------------------------------------------

    def get_rooms(self) -> list[dict[str, Any]]:
        # Returns every known room

        return [dict(room) for room in self._rooms]

    def get_room_state(self, room_id: str) -> dict[str, Any] | None:
        # Returns a single room's state by id, if present

        for room in self._rooms:
            if room.get("room_id") == room_id:
                return dict(room)

        return None

    def set_room_occupied(self, room_id: str, occupied: bool) -> None:
        # Updates a room's occupancy for the remainder of this run

        for room in self._rooms:
            if room.get("room_id") == room_id:
                room["occupied"] = occupied
                return

        raise KeyError(f"Unknown room_id: {room_id}")

    # -- Devices -----------------------------------------------------------
    # Device state is served by the security simulator's data file, but
    # exposed here too since the Context Resolver only knows about one
    # "household" surface. This keeps the resolver's source interface
    # simple during early phases.

    def get_device_state(self, device_id: str) -> dict[str, Any] | None:
        # Returns a single device's state by id, if present, by reading
        # directly from the security simulator's shared fixture

        devices_path = self._data_dir.parent.parent / "security" / "data" / "devices.json"

        if not devices_path.exists():
            return None

        with devices_path.open("r", encoding="utf-8") as handle:
            devices = json.load(handle)

        for device in devices:
            if device.get("device_id") == device_id:
                return dict(device)

        return None


__all__ = [
    "HouseholdSimulatorService",
]
