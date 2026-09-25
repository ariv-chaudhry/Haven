# device.py
# Haven Device Model

# Defines a smart device tracked by Haven, such as a TV, light,
# thermostat, lock or sensor. Device state is stored as a small,
# explicit set of facts rather than a raw vendor payload, so that
# the rest of Haven never depends on a specific integration's shape

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceType(str, Enum):
    # The category of a tracked device

    TV = "tv"
    LIGHT = "light"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    SECURITY_SYSTEM = "security_system"
    OCCUPANCY_SENSOR = "occupancy_sensor"
    CONTACT_SENSOR = "contact_sensor"
    OTHER = "other"


@dataclass
class Device:
    # Represents a single smart device within the household

    device_id: str
    name: str
    device_type: DeviceType

    room_id: str | None = None
    online: bool = True

    state: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError("device_id cannot be empty.")

        if not self.name.strip():
            raise ValueError("name cannot be empty.")

    def set_online(self, online: bool) -> None:
        # Updates whether the device is currently reachable

        self.online = online

    def get_state(self, key: str, default: Any = None) -> Any:
        # Returns a single state value, or a default if unset

        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        # Updates a single state value for this device

        if not key.strip():
            raise ValueError("State key cannot be empty.")

        self.state[key] = value

    def to_dict(self) -> dict[str, Any]:
        # Converts the device into a serializable dictionary

        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "room_id": self.room_id,
            "online": self.online,
            "state": dict(self.state),
        }


__all__ = [
    "Device",
    "DeviceType",
]
