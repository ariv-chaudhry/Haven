"""Structured plan contracts produced by Haven's planner.

These types are the planning/execution boundary. Phase 1 only *proposes*
plans; it never executes steps or verifies device effects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActionRisk(StrEnum):
    """Risk category for a proposed household action."""

    READ = "READ"
    REVERSIBLE_ACTION = "REVERSIBLE_ACTION"
    HIGH_IMPACT_ACTION = "HIGH_IMPACT_ACTION"


class PlanStatus(StrEnum):
    """Lifecycle status for a proposed plan.

    Planning produces PROPOSED or AWAITING_CONFIRMATION. Execution states
    are reserved for later phases and are not set by the planner.
    """

    PROPOSED = "PROPOSED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"


class PlanStep(BaseModel):
    """A single explicit, understandable step in a proposed household plan."""

    model_config = ConfigDict(extra="forbid")

    id: str
    order: int = Field(ge=1)
    action: str
    title: str
    description: str
    risk: ActionRisk
    requires_confirmation: bool
    device_id: str | None = None
    room_id: str | None = None
    capability: str | None = None
    expected_effect: str | None = None


class Plan(BaseModel):
    """Structured household plan returned by `create_plan`."""

    model_config = ConfigDict(extra="forbid")

    id: str
    goal: str
    status: PlanStatus
    summary: str
    steps: list[PlanStep]
    requires_confirmation: bool
    clarification_needed: bool = False
    clarification_prompt: str | None = None
    rejected_candidate_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
