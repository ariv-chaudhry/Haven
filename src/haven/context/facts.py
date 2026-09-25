# facts.py
# Haven Context Facts

# Handles individual facts gathered by the Context Resolver: what was
# learned, where it came from, how confident Haven is in it, and when
# it stops being trustworthy

# This module builds on the shared ContextFact contract defined in
# haven.models.context (owned by Person A). It does not redefine that
# contract — it provides the helpers the resolver needs to create,
# store, and query facts consistently while a goal is being resolved

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from haven.models.context import ContextFact
from haven.context.sources import ContextSourceType


def make_fact(
    fact_name: str,
    value: Any,
    source: ContextSourceType,
    confidence: float = 1.0,
    expires_at: datetime | None = None,
) -> ContextFact:
    # Builds a ContextFact with consistent defaults

    if not fact_name.strip():
        raise ValueError("fact_name cannot be empty.")

    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence must be between 0.0 and 1.0.")

    return ContextFact(
        fact_name=fact_name,
        value=value,
        source=source.value,
        confidence=confidence,
        retrieved_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )


@dataclass
class FactStore:
    # Holds every fact gathered so far during a single context
    # resolution pass. Scoped to one resolve_context() call — it is
    # not a long-lived cache. Durable facts belong in memory/service.py
    # once that layer exists

    facts: dict[str, ContextFact] = field(default_factory=dict)

    def add(self, fact: ContextFact) -> None:
        # Stores or replaces a fact by name

        self.facts[fact.fact_name] = fact

    def get(self, fact_name: str) -> ContextFact | None:
        # Returns a fact by name, if it has been gathered

        return self.facts.get(fact_name)

    def has(self, fact_name: str) -> bool:
        # Returns whether a fact has been gathered

        return fact_name in self.facts

    def missing(self, required_fact_names: list[str]) -> list[str]:
        # Returns which of the required facts have not been gathered

        return [name for name in required_fact_names if name not in self.facts]

    def values(self) -> dict[str, Any]:
        # Returns a plain dict of fact_name -> value, useful for
        # assembling a HouseholdContext

        return {name: fact.value for name, fact in self.facts.items()}

    def as_list(self) -> list[ContextFact]:
        # Returns every gathered fact as a list

        return list(self.facts.values())


__all__ = [
    "make_fact",
    "FactStore",
]
