"""Planning-specific models that are not part of the public Plan contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from haven.models.plan import ActionRisk, PlanStep


class ActionCandidate(BaseModel):
    """A possible plan step before deterministic constraints and policy."""

    model_config = ConfigDict(extra="forbid")

    action: str
    title: str
    description: str
    risk: ActionRisk
    required_capabilities: list[str] = Field(default_factory=list)
    required_device_id: str | None = None
    room_id: str | None = None
    media_id: str | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    expected_effect: str | None = None


class RejectedCandidate(BaseModel):
    """A candidate removed by a deterministic constraint."""

    model_config = ConfigDict(extra="forbid")

    candidate: ActionCandidate
    reason: str


class ConstraintResult(BaseModel):
    """Outcome of applying deterministic planning constraints."""

    model_config = ConfigDict(extra="forbid")

    accepted: list[ActionCandidate] = Field(default_factory=list)
    rejected: list[RejectedCandidate] = Field(default_factory=list)


class PolicyIssue(BaseModel):
    """A single policy violation found in a proposed plan."""

    model_config = ConfigDict(extra="forbid")

    step_id: str | None = None
    message: str


class PolicyValidationResult(BaseModel):
    """Result of checking a plan against Haven action policy."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    issues: list[PolicyIssue] = Field(default_factory=list)
    requires_confirmation: bool = False


class ReasonedPlan(BaseModel):
    """Structured output expected from a planner reasoner.

    Phase 1 uses a mock reasoner. Phase 2 should produce the same shape
    from Strands + Bedrock so `create_plan` does not change.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    steps: list[PlanStep]
    clarification_needed: bool = False
    clarification_prompt: str | None = None
