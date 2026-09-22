"""Planning-facing household snapshot.

This is the resolved-context contract consumed by planning:

    resolve_context(...) -> HouseholdContext   # Person B
    create_plan(goal, context) -> Plan         # Person A

Person B owns context collection and household/person/room/device *domain*
models. Those domain objects should be mapped into this snapshot before
planning. The planner never resolves, collects, or fetches context itself.

The snapshot is intentionally constructible by hand so planning can be
developed and tested with mock data while the resolver is incomplete.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DeviceCapability:
    """Well-known capability names used by planning constraints.

    Stored as strings on devices so Person B can introduce additional
    capabilities without a planning-package change.
    """

    MEDIA_PLAYBACK = "media_playback"
    DISPLAY = "display"
    LIGHTING = "lighting"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    SECURITY = "security"


class PresenceState(StrEnum):
    PRESENT = "PRESENT"
    AWAY = "AWAY"
    UNKNOWN = "UNKNOWN"


class PersonContext(BaseModel):
    """Person facts available to planning. Not a full household domain model."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    presence: PresenceState = PresenceState.UNKNOWN


class RoomContext(BaseModel):
    """Room facts available to planning. Not a full household domain model."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class DeviceContext(BaseModel):
    """Device facts available to planning. Not a full household domain model."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    room_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    is_available: bool = True


class MediaItem(BaseModel):
    """A media option the household can currently offer."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    duration_minutes: int = Field(ge=0)
    is_available: bool = True


class HouseholdContext(BaseModel):
    """Resolved household state used as planner input."""

    model_config = ConfigDict(extra="forbid")

    household_id: str
    people: list[PersonContext] = Field(default_factory=list)
    rooms: list[RoomContext] = Field(default_factory=list)
    devices: list[DeviceContext] = Field(default_factory=list)
    media_options: list[MediaItem] = Field(default_factory=list)
    available_minutes: int | None = Field(default=None, ge=0)
    preferred_room_id: str | None = None
    preferred_genres: list[str] = Field(default_factory=list)
