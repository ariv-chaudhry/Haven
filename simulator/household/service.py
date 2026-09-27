# service.py
# Haven Household Simulator Service

# Exposes household state (people, rooms, devices) without any real
# hardware, backed by the JSON demo data in simulator/household/data/
# and simulator/security/data/devices.json. This lets the Context
# Resolver, executor, and verifier all be developed and demoed before
# any real device integration exists.

# Phase 2 change: device records are now loaded into memory once (like
# people and rooms already were) instead of being re-read from disk on
# every call, and can be mutated via set_device_state(). This is what
# lets the executor actually turn a "dim the lights" step into an
# observable state change the verifier can check afterwards.

# The simulator intentionally mirrors the shape of a real integration
# so that swapping it out later does not require changing callers.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from haven.models.device import Device, DeviceType
from haven.models.household import Household
from haven.models.person import Person, PresenceStatus
from haven.models.room import Room

DEFAULT_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_DEVICES_PATH = Path(__file__).parent.parent / "security" / "data" / "devices.json"


class HouseholdSimulatorService:
    # In-memory household simulator, loaded from local JSON fixtures

    def __init__(
        self,
        data_dir: Path | str = DEFAULT_DATA_DIR,
        devices_path: Path | str = DEFAULT_DEVICES_PATH,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._devices_path = Path(devices_path)

        self._household: dict[str, Any] = {}
        self._people: list[dict[str, Any]] = []
        self._rooms: list[dict[str, Any]] = []
        self._devices: list[dict[str, Any]] = []

        self.reload()

    def reload(self) -> None:
        # Reloads all simulator state from disk, discarding any
        # in-memory changes made during the current run

        self._household = self._load_json(self._data_dir / "household.json")
        self._people = self._load_json(self._data_dir / "people.json")
        self._rooms = self._load_json(self._data_dir / "rooms.json")
        self._devices = self._load_json(self._devices_path)

    @staticmethod
    def _load_json(path: Path) -> Any:
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

    def get_devices(self) -> list[dict[str, Any]]:
        # Returns every known device

        return [dict(device) for device in self._devices]

    def get_device_state(self, device_id: str) -> dict[str, Any] | None:
        # Returns a single device's record by id, if present

        for device in self._devices:
            if device.get("device_id") == device_id:
                return dict(device)

        return None

    def set_device_state(
        self,
        device_id: str,
        *,
        state: dict[str, Any] | None = None,
        online: bool | None = None,
    ) -> dict[str, Any]:
        # Updates a device's state for the remainder of this run.
        #
        # `state` is merged into the device's existing state dict (only
        # the given keys change); `online` replaces the device's
        # reachability flag when provided. Returns the updated device
        # record.

        for device in self._devices:
            if device.get("device_id") != device_id:
                continue

            if state:
                device.setdefault("state", {}).update(state)

            if online is not None:
                device["online"] = online

            return dict(device)

        raise KeyError(f"Unknown device_id: {device_id}")

    # -- Domain snapshot -----------------------------------------------------

    def get_snapshot(self) -> Household:
        # Builds a fully populated `Household` domain object from the
        # simulator's current in-memory state. This is what the Context
        # Resolver maps into the planning-facing HouseholdContext.

        people = [
            Person(
                person_id=p["person_id"],
                name=p["name"],
                presence=PresenceStatus(p.get("presence", "unknown")),
                preferences=dict(p.get("preferences", {})),
            )
            for p in self._people
        ]

        rooms = [
            Room(
                room_id=r["room_id"],
                name=r["name"],
                occupied=bool(r.get("occupied", False)),
                current_activity=r.get("current_activity"),
                device_ids=list(r.get("device_ids", [])),
            )
            for r in self._rooms
        ]

        devices = [
            Device(
                device_id=d["device_id"],
                name=d["name"],
                device_type=DeviceType(d.get("device_type", "other")),
                room_id=d.get("room_id"),
                online=bool(d.get("online", True)),
                state=dict(d.get("state", {})),
            )
            for d in self._devices
        ]

        return Household(
            household_id=self._household["household_id"],
            name=self._household["name"],
            timezone=self._household.get("timezone", "UTC"),
            people=people,
            rooms=rooms,
            devices=devices,
            preferences=dict(self._household.get("preferences", {})),
        )


__all__ = [
    "HouseholdSimulatorService",
]
