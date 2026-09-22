from __future__ import annotations

import pytest

from haven.agents.planner import create_plan
from haven.agents.prompts import PLANNER_SYSTEM_PROMPT, build_planning_prompt
from haven.models.context import HouseholdContext
from haven.models.plan import ActionRisk, Plan, PlanStatus, PlanStep
from haven.planning.plan_service import create_household_plan


def test_movie_night_plan_is_structured(movie_night_context: HouseholdContext) -> None:
    plan = create_plan("Get movie night ready", movie_night_context)

    assert isinstance(plan, Plan)
    assert plan.goal == "Get movie night ready"
    assert plan.status is PlanStatus.PROPOSED
    assert not plan.requires_confirmation
    assert [s.action for s in plan.steps] == ["select_media", "prepare_media_session", "dim_lights"]
    assert [s.order for s in plan.steps] == [1, 2, 3]
    assert all(isinstance(s, PlanStep) for s in plan.steps)
    assert plan.rejected_candidate_count == 0


def test_movie_night_respects_time_constraint(movie_night_context: HouseholdContext) -> None:
    plan = create_plan("Get movie night ready", movie_night_context)
    select = plan.steps[0]
    assert "Short Feature" in select.description
    assert "Long Epic" not in select.description


def test_movie_night_uses_only_existing_devices(movie_night_context: HouseholdContext) -> None:
    plan = create_plan("Get movie night ready", movie_night_context)
    device_ids = {d.id for d in movie_night_context.devices}
    for step in plan.steps:
        assert step.device_id is None or step.device_id in device_ids
        assert step.risk in (ActionRisk.READ, ActionRisk.REVERSIBLE_ACTION)
        assert step.requires_confirmation is False


def test_movie_night_without_lights_omits_dim_step(movie_night_context: HouseholdContext) -> None:
    ctx = movie_night_context.model_copy(
        update={"devices": [d for d in movie_night_context.devices if d.id != "lamp-1"]}
    )
    plan = create_plan("Get movie night ready", ctx)
    assert [s.action for s in plan.steps] == ["select_media", "prepare_media_session"]


def test_no_media_device_raises(movie_night_context: HouseholdContext) -> None:
    ctx = movie_night_context.model_copy(
        update={"devices": [d for d in movie_night_context.devices if d.id != "tv-1"]}
    )
    with pytest.raises(ValueError, match="media playback device"):
        create_plan("Get movie night ready", ctx)


def test_no_fitting_media_raises(movie_night_context: HouseholdContext) -> None:
    ctx = movie_night_context.model_copy(update={"available_minutes": 30})
    with pytest.raises(ValueError, match="available time"):
        create_plan("Get movie night ready", ctx)


def test_unknown_goal_raises(movie_night_context: HouseholdContext) -> None:
    with pytest.raises(ValueError):
        create_plan("Launch the rocket", movie_night_context)


@pytest.mark.parametrize("goal", ["", "   "])
def test_empty_goal_raises(goal: str, movie_night_context: HouseholdContext) -> None:
    with pytest.raises(ValueError, match="empty"):
        create_plan(goal, movie_night_context)


def test_invalid_context_raises() -> None:
    with pytest.raises(ValueError, match="HouseholdContext"):
        create_plan("Get movie night ready", None)  # type: ignore[arg-type]


def test_plan_service_returns_policy_valid_plan(movie_night_context: HouseholdContext) -> None:
    plan = create_household_plan("Get movie night ready", movie_night_context)
    assert isinstance(plan, Plan)
    assert plan.steps


def test_prompt_builder_includes_goal_and_context(movie_night_context: HouseholdContext) -> None:
    prompt = build_planning_prompt("Get movie night ready", movie_night_context)
    assert "Get movie night ready" in prompt
    assert "household-1" in prompt
    assert "HIGH_IMPACT_ACTION" in prompt
    assert "Do not execute" in PLANNER_SYSTEM_PROMPT or "not execute" in PLANNER_SYSTEM_PROMPT


def test_no_aws_or_alexa_modules_are_imported() -> None:
    import sys

    import haven.agents.planner  # noqa: F401
    import haven.planning.plan_service  # noqa: F401

    forbidden = {"boto3", "botocore", "strands", "ask_sdk_core"}
    assert not forbidden & set(sys.modules)
