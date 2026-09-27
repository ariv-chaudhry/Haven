"""Expiry rules for facts gathered during context resolution.

Determines how long a gathered fact should be trusted before it needs to
be re-resolved. A motion/occupancy observation goes stale in seconds. A
saved genre preference does not go stale at all. Getting this right is
what lets Haven avoid re-asking the user things it already confidently
knows, without acting on stale information.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from haven.context.facts import GatheredFact


class FactVolatility(str, Enum):
    """How quickly a fact category is expected to become unreliable."""

    INSTANT = "instant"  # valid only for the current request
    TRANSIENT = "transient"  # valid for a short window (sensors, presence)
    SESSION = "session"  # valid for the current conversation/session
    DURABLE = "durable"  # valid until explicitly changed (preferences)


# Default volatility per fact name. Facts not listed here default to
# TRANSIENT, which is the safer assumption.
DEFAULT_VOLATILITY: dict[str, FactVolatility] = {
    "room_occupied": FactVolatility.TRANSIENT,
    "device_state": FactVolatility.TRANSIENT,
    "tv_state": FactVolatility.TRANSIENT,
    "lock_state": FactVolatility.TRANSIENT,
    "security_armed": FactVolatility.TRANSIENT,
    "available_time_minutes": FactVolatility.SESSION,
    "next_event_time": FactVolatility.SESSION,
}


def _is_person_home_fact(fact_name: str) -> bool:
    return fact_name.startswith("person_home:")


# How long each volatility level remains valid, from the moment the fact
# was retrieved.
DEFAULT_TTL: dict[FactVolatility, timedelta] = {
    FactVolatility.INSTANT: timedelta(seconds=0),
    FactVolatility.TRANSIENT: timedelta(minutes=2),
    FactVolatility.SESSION: timedelta(minutes=30),
    FactVolatility.DURABLE: timedelta(days=3650),
}


def volatility_for(fact_name: str) -> FactVolatility:
    """Return the expected volatility for a fact name."""

    if fact_name.startswith("preference:") or fact_name.startswith("history:"):
        return FactVolatility.DURABLE

    if _is_person_home_fact(fact_name):
        return FactVolatility.TRANSIENT

    return DEFAULT_VOLATILITY.get(fact_name, FactVolatility.TRANSIENT)


def default_expiry_for(fact_name: str, retrieved_at: datetime | None = None) -> datetime:
    """Compute the default expiry timestamp for a newly gathered fact."""

    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    ttl = DEFAULT_TTL[volatility_for(fact_name)]

    return retrieved_at + ttl


def is_expired(fact: GatheredFact, now: datetime | None = None) -> bool:
    """Return whether a previously gathered fact should be treated as stale."""

    if fact.expires_at is None:
        return False

    now = now or datetime.now(timezone.utc)

    return now >= fact.expires_at


__all__ = [
    "FactVolatility",
    "volatility_for",
    "default_expiry_for",
    "is_expired",
]
