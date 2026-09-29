"""Haven executor: structured `Plan` -> `ExecutionResult`.

    execute_plan(plan, household=..., media=...) -> ExecutionResult

Execution is deterministic. No LLM is involved: each step is dispatched
to a plain Python handler (`haven.execution.actions`) that either
succeeds, fails, or is skipped, and every outcome is recorded — a
partially failed plan is a normal, expected result, not an exception.

The executor does not resolve context, plan, or verify device effects.
It also refuses to run a plan that still requires confirmation unless
the caller explicitly says the user has confirmed it; Haven never
silently executes a high-impact action.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Protocol

from haven.execution.actions import ActionContext, HouseholdBackend, get_handler
from haven.execution.results import (
    ExecutionResult,
    ExecutionStatus,
    StepExecutionResult,
    StepExecutionStatus,
    status_for_results,
)
from haven.integrations.media import MediaService
from haven.memory.activity import ActivityType
from haven.models.plan import Plan, PlanStatus

logger = logging.getLogger(__name__)


class ActivityRecorder(Protocol):
    """The subset of `MemoryService` the executor optionally reports to."""

    def record_activity(
        self,
        household_id: str,
        activity_type: ActivityType,
        summary: str,
        *,
        details: dict | None = None,
    ) -> object: ...


_MOVIE_NIGHT_KEYWORDS = ("movie", "film", "cinema")


def execute_plan(
    plan: Plan,
    *,
    household: HouseholdBackend,
    media: MediaService,
    household_id: str | None = None,
    confirmed: bool = False,
    memory: ActivityRecorder | None = None,
) -> ExecutionResult:
    """Execute every step of `plan` in order and report what happened.

    ``confirmed`` must be ``True`` for a plan whose status is
    ``AWAITING_CONFIRMATION`` (i.e. it contains a `HIGH_IMPACT_ACTION`
    step); otherwise no step runs and the result's status is
    `ExecutionStatus.AWAITING_CONFIRMATION`. This mirrors the same
    policy the planner already encodes on the plan and steps
    (`haven.agents.policies`) — the executor enforces it again rather
    than trusting a caller not to skip it.

    ``memory``, if given, is used to record a `MOVIE_NIGHT_PREPARED`
    activity on a fully successful movie-night execution. A memory
    failure is logged and never fails execution.
    """

    started_at = datetime.now(UTC)

    if plan.status is PlanStatus.AWAITING_CONFIRMATION and not confirmed:
        logger.info("Plan %s awaits confirmation; not executing.", plan.id)
        return ExecutionResult(
            plan_id=plan.id,
            goal=plan.goal,
            status=ExecutionStatus.AWAITING_CONFIRMATION,
            step_results=[],
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )

    context = ActionContext(household=household, media=media)
    step_results: list[StepExecutionResult] = []

    for step in sorted(plan.steps, key=lambda s: s.order):
        if step.requires_confirmation and not confirmed:
            step_results.append(
                StepExecutionResult(
                    step_id=step.id,
                    action=step.action,
                    status=StepExecutionStatus.SKIPPED,
                    detail="Step requires confirmation, which was not given.",
                )
            )
            continue

        handler = get_handler(step.action)
        if handler is None:
            step_results.append(
                StepExecutionResult(
                    step_id=step.id,
                    action=step.action,
                    status=StepExecutionStatus.FAILED,
                    detail=f"No executor is registered for action '{step.action}'.",
                    error="unsupported action",
                )
            )
            continue

        try:
            result = handler(step, context)
        except Exception as exc:  # noqa: BLE001 - a handler bug must not crash the plan
            logger.exception("Handler for action '%s' raised unexpectedly.", step.action)
            result = StepExecutionResult(
                step_id=step.id,
                action=step.action,
                status=StepExecutionStatus.FAILED,
                detail=f"Executing '{step.title}' raised an unexpected error.",
                error=str(exc),
            )

        step_results.append(result)

    status = status_for_results(step_results)
    completed_at = datetime.now(UTC)

    logger.info(
        "Executed plan %s: status=%s succeeded=%s failed=%s",
        plan.id,
        status.value,
        sum(1 for r in step_results if r.status is StepExecutionStatus.SUCCEEDED),
        sum(1 for r in step_results if r.status is StepExecutionStatus.FAILED),
    )

    if memory is not None and status is ExecutionStatus.COMPLETED and household_id is not None:
        _record_completion(memory, household_id, plan, step_results)

    return ExecutionResult(
        plan_id=plan.id,
        goal=plan.goal,
        status=status,
        step_results=step_results,
        started_at=started_at,
        completed_at=completed_at,
    )


def _record_completion(
    memory: ActivityRecorder,
    household_id: str,
    plan: Plan,
    step_results: list[StepExecutionResult],
) -> None:
    if not _is_movie_night_goal(plan.goal):
        return

    details: dict[str, str | int | float | bool] = {
        "plan_id": plan.id,
        "step_count": len(plan.steps),
    }

    selected = next(
        (
            r
            for r in step_results
            if r.action == "select_media" and r.status is StepExecutionStatus.SUCCEEDED
        ),
        None,
    )
    if selected is not None:
        # Recorded so a future recommendation (haven.mcp.tools.recommendations)
        # can avoid re-suggesting whatever was just watched.
        media_id = selected.effect.get("media_id")
        title = selected.effect.get("title")
        if isinstance(media_id, str):
            details["media_id"] = media_id
        if isinstance(title, str):
            details["title"] = title

    try:
        memory.record_activity(
            household_id,
            ActivityType.MOVIE_NIGHT_PREPARED,
            f"Movie night prepared: {plan.summary}",
            details=details,
        )
    except Exception:  # noqa: BLE001 - memory is best-effort here
        logger.exception("Failed to record movie night activity for plan %s.", plan.id)


def _is_movie_night_goal(goal: str) -> bool:
    lowered = goal.lower()
    return any(keyword in lowered for keyword in _MOVIE_NIGHT_KEYWORDS)


__all__ = [
    "execute_plan",
    "ActivityRecorder",
]
