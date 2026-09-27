"""Deterministic action handlers.

Each handler performs exactly one `PlanStep.action` against the household
and media backends. Execution never uses an LLM: everything here is
ordinary, testable code that either succeeds, fails, or is skipped, and
says which.

Handlers are looked up by the plan step's `action` string. An action the
planner has never proposed (or a typo) simply has no handler, and the
executor turns that into a `FAILED` step rather than raising — a plan
partially failing is normal, and it is the executor/verifier's job to
decide what to do about it, not an individual handler's.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol

from haven.execution.results import StepExecutionResult, StepExecutionStatus
from haven.integrations.media import MediaService
from haven.models.plan import PlanStep

_QUOTED_TITLE = re.compile(r"'([^']+)'")


class HouseholdBackend(Protocol):
    """The subset of `HouseholdSimulatorService` action handlers depend on."""

    def get_device_state(self, device_id: str) -> dict | None: ...

    def set_device_state(
        self, device_id: str, *, state: dict | None = None, online: bool | None = None
    ) -> dict: ...


class ActionContext:
    """Bundles the backends an action handler needs to do its work."""

    def __init__(self, household: HouseholdBackend, media: MediaService) -> None:
        self.household = household
        self.media = media


ActionHandler = Callable[[PlanStep, ActionContext], StepExecutionResult]
"""Signature every action handler satisfies."""


def extract_quoted_title(*texts: str | None) -> str | None:
    """Return the first single-quoted substring found in `texts`, if any.

    `PlanStep` does not carry a structured `media_id` (see
    `docs/friction-log.md`); the planner's mock reasoner always phrases a
    selected title in single quotes (`"Select 'Interstellar' (169 min)..."`),
    so this recovers it well enough for Phase 2. This is a deliberately
    narrow, documented bridge — not a general NLP parser.
    """

    for text in texts:
        if not text:
            continue
        match = _QUOTED_TITLE.search(text)
        if match:
            return match.group(1)
    return None


def handle_select_media(step: PlanStep, context: ActionContext) -> StepExecutionResult:
    # A read-only step: the planner has already chosen a title. There is
    # nothing to change in the world, only something to record.

    title = extract_quoted_title(step.description, step.title)
    if title is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail="Could not determine which media title was selected.",
            error="no quoted title found in step text",
        )

    media_id = context.media.find_media_id_by_title(title)
    if media_id is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail=f"Selected title '{title}' was not found in the media catalog.",
            error="unknown media title",
        )

    return StepExecutionResult(
        step_id=step.id,
        action=step.action,
        status=StepExecutionStatus.SUCCEEDED,
        detail=f"Confirmed '{title}' as the selected media.",
        effect={"media_id": media_id, "title": title},
    )


def handle_prepare_media_session(step: PlanStep, context: ActionContext) -> StepExecutionResult:
    if step.device_id is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail="Step has no target device.",
            error="missing device_id",
        )

    title = extract_quoted_title(step.description, step.title)
    if title is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail="Could not determine which media title to prepare.",
            error="no quoted title found in step text",
        )

    media_id = context.media.find_media_id_by_title(title)
    if media_id is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail=f"'{title}' was not found in the media catalog.",
            error="unknown media title",
        )

    try:
        session = context.media.prepare_session(step.device_id, media_id)
    except KeyError as exc:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail=f"Could not prepare '{title}' on {step.device_id}.",
            error=str(exc),
        )

    return StepExecutionResult(
        step_id=step.id,
        action=step.action,
        status=StepExecutionStatus.SUCCEEDED,
        detail=f"Prepared '{session.title}' on {step.device_id}; not yet playing.",
        effect={
            "device_id": session.device_id,
            "media_id": session.media_id,
            "status": session.status.value,
        },
    )


def handle_start_media_session(step: PlanStep, context: ActionContext) -> StepExecutionResult:
    # Not currently proposed by the planner, but supported so a future
    # explicit "start playback" confirmation step has somewhere to go.

    if step.device_id is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail="Step has no target device.",
            error="missing device_id",
        )

    try:
        session = context.media.start_session(step.device_id)
    except KeyError as exc:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail=f"No prepared session to start on {step.device_id}.",
            error=str(exc),
        )

    return StepExecutionResult(
        step_id=step.id,
        action=step.action,
        status=StepExecutionStatus.SUCCEEDED,
        detail=f"Started '{session.title}' on {step.device_id}.",
        effect={
            "device_id": session.device_id,
            "media_id": session.media_id,
            "status": session.status.value,
        },
    )


def handle_dim_lights(step: PlanStep, context: ActionContext) -> StepExecutionResult:
    if step.device_id is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail="Step has no target device.",
            error="missing device_id",
        )

    current = context.household.get_device_state(step.device_id)
    if current is None:
        return StepExecutionResult(
            step_id=step.id,
            action=step.action,
            status=StepExecutionStatus.FAILED,
            detail=f"Unknown device: {step.device_id}.",
            error="device not found",
        )

    target_brightness = _viewing_brightness(current.get("state", {}).get("brightness"))

    updated = context.household.set_device_state(
        step.device_id,
        state={"power": "on", "brightness": target_brightness},
    )

    return StepExecutionResult(
        step_id=step.id,
        action=step.action,
        status=StepExecutionStatus.SUCCEEDED,
        detail=f"Dimmed {step.device_id} to {target_brightness}% for viewing.",
        effect={
            "device_id": step.device_id,
            "brightness": updated.get("state", {}).get("brightness"),
        },
    )


# A comfortable, fixed "movie night" viewing level. A future preference
# (`PreferenceKey`-style) could make this per-household; hardcoding it
# here keeps Phase 2 deterministic and simple.
_VIEWING_BRIGHTNESS = 20


def _viewing_brightness(_current: object) -> int:
    return _VIEWING_BRIGHTNESS


_HANDLERS: dict[str, ActionHandler] = {
    "select_media": handle_select_media,
    "prepare_media_session": handle_prepare_media_session,
    "start_media_session": handle_start_media_session,
    "dim_lights": handle_dim_lights,
}


def get_handler(action: str) -> ActionHandler | None:
    """Return the handler for `action`, or `None` if it is unsupported."""

    return _HANDLERS.get(action)


__all__ = [
    "ActionContext",
    "HouseholdBackend",
    "extract_quoted_title",
    "get_handler",
    "handle_select_media",
    "handle_prepare_media_session",
    "handle_start_media_session",
    "handle_dim_lights",
]
