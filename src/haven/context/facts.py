"""Internal bookkeeping for facts gathered during context resolution.

Person A's shared planning contract (``haven.models.context``) does not
define a durable "ContextFact" type: ``HouseholdContext`` is a directly
constructible snapshot (people/rooms/devices/media already resolved), not
a bag of named facts. See ``haven/models/context.py`` for the contract
and ``haven/context/resolver.py`` for how it gets built.

``GatheredFact`` here is therefore private to this package. It exists only
to give ``resolve_context`` a consistent way to try several sources for a
handful of scalar facts (available time, preferences, per-person presence
overrides) before folding the result into the final ``HouseholdContext``.
It never crosses the planning boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from haven.context.sources import ContextSourceType


@dataclass(frozen=True)
class GatheredFact:
    """A single fact resolved from one approved context source."""

    fact_name: str
    value: Any
    source: ContextSourceType
    confidence: float = 1.0
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


def make_fact(
    fact_name: str,
    value: Any,
    source: ContextSourceType,
    confidence: float = 1.0,
    expires_at: datetime | None = None,
) -> GatheredFact:
    """Build a `GatheredFact` with consistent validation and defaults."""

    if not fact_name.strip():
        raise ValueError("fact_name cannot be empty.")

    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0.")

    return GatheredFact(
        fact_name=fact_name,
        value=value,
        source=source,
        confidence=confidence,
        retrieved_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )


@dataclass
class FactStore:
    """Facts gathered so far during a single `resolve_context` call.

    Scoped to one resolution pass — it is not a long-lived cache. Durable
    facts belong in `haven.memory.service.MemoryService`.
    """

    facts: dict[str, GatheredFact] = field(default_factory=dict)

    def add(self, fact: GatheredFact) -> None:
        """Store or replace a fact by name."""

        self.facts[fact.fact_name] = fact

    def get(self, fact_name: str) -> GatheredFact | None:
        """Return a fact by name, if it has been gathered."""

        return self.facts.get(fact_name)

    def has(self, fact_name: str) -> bool:
        """Return whether a fact has been gathered."""

        return fact_name in self.facts

    def missing(self, required_fact_names: list[str]) -> list[str]:
        """Return which of the required facts have not been gathered."""

        return [name for name in required_fact_names if name not in self.facts]

    def values(self) -> dict[str, Any]:
        """Return a plain dict of fact_name -> value."""

        return {name: fact.value for name, fact in self.facts.items()}

    def as_list(self) -> list[GatheredFact]:
        """Return every gathered fact as a list."""

        return list(self.facts.values())


__all__ = [
    "GatheredFact",
    "make_fact",
    "FactStore",
]
