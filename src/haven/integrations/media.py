"""Media integration abstraction.

Phase 2 is backed by the in-memory media simulator; no external
streaming/Fire TV API is called. The interface answers the questions
Haven actually needs: what's available to watch, and how to queue,
start, stop and check a playback session.

`MediaService.list_media_items` returns the shared `MediaItem` contract
type directly, so `haven.context.resolver.resolve_context` can pass its
result straight through as `media_options` without any extra mapping.
This module does not import `haven.context` or `haven.execution`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from haven.models.context import MediaItem


class MediaSessionStatus(StrEnum):
    """Lifecycle of a simulated (or, later, real) playback session."""

    READY = "ready"
    PLAYING = "playing"
    STOPPED = "stopped"


class MediaSession(BaseModel):
    """A device's current playback session, as reported by the backend."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    media_id: str
    title: str
    duration_minutes: int | None = Field(default=None, ge=0)
    status: MediaSessionStatus


class MediaCatalogEntry(BaseModel):
    """A catalog title with the extra detail (genres) `MediaItem` doesn't
    carry, for callers that need to rank or filter by genre — currently
    `haven.mcp.tools.recommendations`. `MediaItem` (the planning contract)
    intentionally stays minimal; this is additive, not a replacement.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    duration_minutes: int
    genres: list[str] = Field(default_factory=list)
    is_available: bool = True


class MediaBackend(Protocol):
    """The subset of `MediaSimulatorService` this integration depends on.

    A real Fire TV / streaming integration can satisfy this same shape
    later without `MediaService` or its callers changing.
    """

    def list_media(self) -> list[dict]: ...

    def get_media(self, media_id: str) -> dict | None: ...

    def prepare_session(self, device_id: str, media_id: str) -> dict: ...

    def start_session(self, device_id: str) -> dict: ...

    def stop_session(self, device_id: str) -> dict | None: ...

    def get_session_state(self, device_id: str) -> dict | None: ...


class MediaService:
    """Application-facing facade over a media backend (simulator today)."""

    def __init__(self, backend: MediaBackend) -> None:
        self._backend = backend

    # -- Catalog, shaped for planning ---------------------------------------- #

    def list_media_items(self) -> list[MediaItem]:
        """Return the catalog as the shared `MediaItem` planning contract.

        Every catalog entry is currently treated as available; the
        planner's own constraints filter by remaining time.
        """

        return [
            MediaItem(
                id=item["media_id"],
                title=item["title"],
                duration_minutes=item["duration_minutes"],
                is_available=True,
            )
            for item in self._backend.list_media()
        ]

    def list_catalog_entries(self) -> list[MediaCatalogEntry]:
        """Return the catalog with genres, for genre-aware recommendations.

        `resolve_context`/planning should keep using `list_media_items`
        (the stable planning contract); this is for callers that need the
        extra detail.
        """

        return [
            MediaCatalogEntry(
                id=item["media_id"],
                title=item["title"],
                duration_minutes=item["duration_minutes"],
                genres=list(item.get("genres", [])),
                is_available=True,
            )
            for item in self._backend.list_media()
        ]

    def get_duration_minutes(self, media_id: str) -> int | None:
        media = self._backend.get_media(media_id)
        return None if media is None else media.get("duration_minutes")

    def find_media_id_by_title(self, title: str) -> str | None:
        """Best-effort lookup used by the executor.

        `PlanStep` does not currently carry a structured `media_id` (see
        `docs/friction-log.md`), so the executor recovers the intended
        title from step text and resolves it here by exact, then
        case-insensitive, title match.
        """

        for item in self._backend.list_media():
            if item.get("title") == title:
                return item.get("media_id")

        lowered = title.strip().lower()
        for item in self._backend.list_media():
            if item.get("title", "").strip().lower() == lowered:
                return item.get("media_id")

        return None

    # -- Sessions ------------------------------------------------------------ #

    def prepare_session(self, device_id: str, media_id: str) -> MediaSession:
        """Queue a title on a device without starting playback."""

        raw = self._backend.prepare_session(device_id, media_id)
        return _to_session(raw)

    def start_session(self, device_id: str) -> MediaSession:
        """Start playback for a previously prepared session."""

        raw = self._backend.start_session(device_id)
        return _to_session(raw)

    def stop_session(self, device_id: str) -> MediaSession | None:
        """Stop and clear a session on a device, if one exists."""

        raw = self._backend.stop_session(device_id)
        return None if raw is None else _to_session(raw)

    def get_session_state(self, device_id: str) -> MediaSession | None:
        """Return a device's current session, if any."""

        raw = self._backend.get_session_state(device_id)
        return None if raw is None else _to_session(raw)


def _to_session(raw: dict) -> MediaSession:
    return MediaSession(
        device_id=raw["device_id"],
        media_id=raw["media_id"],
        title=raw["title"],
        duration_minutes=raw.get("duration_minutes"),
        status=MediaSessionStatus(raw["status"]),
    )


__all__ = [
    "MediaSessionStatus",
    "MediaSession",
    "MediaCatalogEntry",
    "MediaBackend",
    "MediaService",
]
