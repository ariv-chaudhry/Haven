"""Haven planner: goal + resolved context -> structured proposed Plan.

Public contract (stable across Phase 1 mock and Phase 2 Bedrock/Strands):

    create_plan(goal: str, context: HouseholdContext) -> Plan

The planner does not resolve context, execute devices, verify effects,
call Alexa, or access AWS. Only the private reasoning function changes
when a model-backed planner is introduced.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Sequence
from typing import TypeVar

from haven.agents.policies import (
    confirmation_required_for_step,
    plan_status_for_steps,
    requires_confirmation,
)
from haven.agents.prompts import PLANNER_SYSTEM_PROMPT, build_planning_prompt
from haven.models.context import DeviceCapability, HouseholdContext
from haven.models.plan import ActionRisk, Plan, PlanStep
from haven.planning.constraints import (
    apply_constraints,
    filter_available_devices,
    filter_available_options,
)
from haven.planning.models import ActionCandidate, ReasonedPlan

logger = logging.getLogger(__name__)

T = TypeVar("T")

Reasoner = Callable[[str, HouseholdContext, Sequence[ActionCandidate]], ReasonedPlan]
"""Signature a Phase 2 model-backed reasoner must satisfy."""

_MOVIE_NIGHT_KEYWORDS = ("movie", "film", "cinema")


def create_plan(goal: str, context: HouseholdContext) -> Plan:
    """Create a structured proposed plan for `goal` using resolved `context`.

    Raises `ValueError` for an empty goal, a missing/invalid context, or when
    no valid plan step can be produced without clarification.
    """

    normalized_goal = _validate_goal(goal)
    _validate_context(context)

    candidates = generate_candidates(normalized_goal, context)
    constrained = apply_constraints(normalized_goal, context, candidates)

    reasoned = _reason(normalized_goal, context, constrained.accepted)
    return assemble_plan(
        normalized_goal,
        reasoned,
        rejected_candidate_count=len(constrained.rejected),
    )


def generate_candidates(goal: str, context: HouseholdContext) -> list[ActionCandidate]:
    """Enumerate candidate actions for a goal from what the context offers.

    Candidates are proposals only. Deterministic constraints and policy
    decide which survive. Nothing is fabricated: each candidate references
    devices, rooms, or media present in `context`.
    """

    if _is_movie_night_goal(goal):
        return _movie_night_candidates(context)
    return []


def assemble_plan(goal: str, reasoned: ReasonedPlan, *, rejected_candidate_count: int = 0) -> Plan:
    """Turn a reasoner's structured output into a public `Plan`.

    Confirmation flags are normalized from policy so a reasoner cannot
    downgrade a high-impact action.
    """

    if reasoned.clarification_needed:
        raise ValueError(
            reasoned.clarification_prompt
            or "planner needs clarification before it can produce a plan"
        )
    if not reasoned.steps:
        raise ValueError("planner was unable to produce any valid steps")

    steps = [
        step.model_copy(
            update={
                "order": index,
                "requires_confirmation": confirmation_required_for_step(step),
            }
        )
        for index, step in enumerate(reasoned.steps, start=1)
    ]

    return Plan(
        id=f"plan-{uuid.uuid4()}",
        goal=goal,
        status=plan_status_for_steps(steps),
        summary=reasoned.summary,
        steps=steps,
        requires_confirmation=any(step.requires_confirmation for step in steps),
        rejected_candidate_count=rejected_candidate_count,
    )


# --------------------------------------------------------------------------- #
# Reasoning backend
# --------------------------------------------------------------------------- #


def _reason(
    goal: str,
    context: HouseholdContext,
    candidates: Sequence[ActionCandidate],
) -> ReasonedPlan:
    """Select the reasoning backend.

    Phase 2 replaces this body with a Strands + Bedrock reasoner that consumes
    `PLANNER_SYSTEM_PROMPT` and `build_planning_prompt(goal, context)` and
    returns a `ReasonedPlan`. Nothing else in this module should change.
    """

    return _mock_reasoner(goal, context, candidates)


def _mock_reasoner(
    goal: str,
    context: HouseholdContext,
    candidates: Sequence[ActionCandidate],
) -> ReasonedPlan:
    """Deterministic stand-in for model reasoning.

    Builds the prompt so the same inputs Phase 2 will send are exercised, but
    does not send them anywhere.
    """

    _ = PLANNER_SYSTEM_PROMPT
    _ = build_planning_prompt(goal, context)

    if not candidates:
        return ReasonedPlan(
            summary="",
            steps=[],
            clarification_needed=True,
            clarification_prompt=_clarification_prompt(goal, context),
        )

    steps = [_candidate_to_step(candidate, index) for index, candidate in enumerate(candidates, 1)]
    return ReasonedPlan(summary=_summarize(goal, steps), steps=steps)


def _candidate_to_step(candidate: ActionCandidate, order: int) -> PlanStep:
    return PlanStep(
        id=f"step-{order}",
        order=order,
        action=candidate.action,
        title=candidate.title,
        description=candidate.description,
        risk=candidate.risk,
        requires_confirmation=requires_confirmation(candidate.risk),
        device_id=candidate.required_device_id,
        room_id=candidate.room_id,
        capability=candidate.required_capabilities[0] if candidate.required_capabilities else None,
        expected_effect=candidate.expected_effect,
    )


def _summarize(goal: str, steps: Sequence[PlanStep]) -> str:
    return f"Proposed {len(steps)} step(s) for: {goal}"


def _clarification_prompt(goal: str, context: HouseholdContext) -> str:
    if _is_movie_night_goal(goal):
        if not filter_available_options(
            context.media_options, available_minutes=context.available_minutes
        ):
            return (
                "No available media option fits the household's available time. "
                "Which title should be prepared, or how much time is available?"
            )
        return "No available media playback device was found. Which device should be used?"
    return "Haven does not yet know how to plan this request. Please describe the goal differently."


# --------------------------------------------------------------------------- #
# Movie night prototype
# --------------------------------------------------------------------------- #


def _is_movie_night_goal(goal: str) -> bool:
    lowered = goal.lower()
    return any(keyword in lowered for keyword in _MOVIE_NIGHT_KEYWORDS)


def _movie_night_candidates(context: HouseholdContext) -> list[ActionCandidate]:
    room_id = _select_room(context)
    media_device = _first(
        filter_available_devices(
            context, capability=DeviceCapability.MEDIA_PLAYBACK, room_id=room_id
        )
    ) or _first(filter_available_devices(context, capability=DeviceCapability.MEDIA_PLAYBACK))
    if media_device is None:
        return []

    effective_room_id = media_device.room_id or room_id
    candidates: list[ActionCandidate] = []

    media_options = filter_available_options(
        context.media_options, available_minutes=context.available_minutes
    )
    selected = media_options[0] if media_options else None
    if selected is None:
        return []

    candidates.append(
        ActionCandidate(
            action="select_media",
            title="Choose a media option",
            description=(
                f"Select '{selected.title}' ({selected.duration_minutes} min) from available "
                "media that fits the household's time."
            ),
            risk=ActionRisk.READ,
            media_id=selected.id,
            duration_minutes=selected.duration_minutes,
            expected_effect="A single media title is chosen for the session.",
        )
    )
    candidates.append(
        ActionCandidate(
            action="prepare_media_session",
            title=f"Prepare playback on {media_device.name}",
            description=f"Queue '{selected.title}' on {media_device.name} without starting playback.",
            risk=ActionRisk.REVERSIBLE_ACTION,
            required_capabilities=[DeviceCapability.MEDIA_PLAYBACK],
            required_device_id=media_device.id,
            room_id=effective_room_id,
            media_id=selected.id,
            expected_effect="The media session is ready to start on request.",
        )
    )

    light = _first(
        filter_available_devices(
            context, capability=DeviceCapability.LIGHTING, room_id=effective_room_id
        )
    )
    if light is not None:
        candidates.append(
            ActionCandidate(
                action="dim_lights",
                title=f"Dim {light.name}",
                description=f"Lower {light.name} to a viewing level in the selected room.",
                risk=ActionRisk.REVERSIBLE_ACTION,
                required_capabilities=[DeviceCapability.LIGHTING],
                required_device_id=light.id,
                room_id=effective_room_id,
                expected_effect="Room lighting is dimmed for viewing.",
            )
        )

    return candidates


def _select_room(context: HouseholdContext) -> str | None:
    if context.preferred_room_id and any(r.id == context.preferred_room_id for r in context.rooms):
        return context.preferred_room_id
    return None


def _first(items: Sequence[T]) -> T | None:
    return items[0] if items else None


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def _validate_goal(goal: str) -> str:
    if not isinstance(goal, str):
        raise ValueError("goal must be a string")
    normalized = goal.strip()
    if not normalized:
        raise ValueError("goal must not be empty")
    return normalized


def _validate_context(context: HouseholdContext) -> None:
    if not isinstance(context, HouseholdContext):
        raise ValueError("context must be a HouseholdContext")
    if not context.household_id.strip():
        raise ValueError("context.household_id must not be empty")
