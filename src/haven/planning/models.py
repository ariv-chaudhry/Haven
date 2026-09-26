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
    """Structured output every planner reasoner (mock or Bedrock) returns.

    Steps are always built by application code from accepted candidates;
    a model never constructs `PlanStep` objects directly.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str
    steps: list[PlanStep]
    clarification_needed: bool = False
    clarification_prompt: str | None = None


class OfferedCandidate(BaseModel):
    """What the model is shown for one accepted candidate.

    The `candidate_id` is a temporary, per-request handle used only to map
    the model's selection back to the trusted `ActionCandidate`. It is never
    exposed in the public `Plan`.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    action: str
    title: str
    description: str
    risk: ActionRisk
    device_id: str | None = None
    room_id: str | None = None
    media_id: str | None = None

    @classmethod
    def from_candidate(cls, candidate_id: str, candidate: ActionCandidate) -> OfferedCandidate:
        return cls(
            candidate_id=candidate_id,
            action=candidate.action,
            title=candidate.title,
            description=candidate.description,
            risk=candidate.risk,
            device_id=candidate.required_device_id,
            room_id=candidate.room_id,
            media_id=candidate.media_id,
        )


class ModelPlanDecision(BaseModel):
    """Structured decision a model returns: a selection among offered candidates.

    This is the only shape the model may produce. It cannot carry device
    IDs, risk classes, or new actions; those come from the trusted candidates
    referenced by `selected_candidate_ids`.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        description="One or two plain sentences describing the proposed plan for the user."
    )
    selected_candidate_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Candidate IDs to include, in execution order. Use only IDs from the offered "
            "candidates. Leave empty only when clarification_needed is true."
        ),
    )
    clarification_needed: bool = Field(
        default=False,
        description="True when the goal cannot be planned from the offered candidates.",
    )
    clarification_prompt: str | None = Field(
        default=None,
        description="The question to ask the user when clarification_needed is true.",
    )
