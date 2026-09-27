"""Recovery strategy for a step that failed execution or verification.

Haven's Layer 4 (verification) is only useful if something sensible
happens after a mismatch is found. This module answers "what should
happen next?" for a single step — it does not itself retry, skip, or
abort anything; callers (the executor, MCP layer, or a future
orchestrator) decide whether and how to act on the recommendation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from haven.execution.results import StepExecutionResult, StepExecutionStatus
from haven.verification.verifier import StepVerification, StepVerificationStatus


class RecoveryAction(StrEnum):
    """What Haven should consider doing about one step's outcome."""

    CONTINUE = "CONTINUE"
    """The step succeeded and was verified; proceed to the next step."""

    RETRY = "RETRY"
    """The failure looks transient; trying the same step again may help."""

    SKIP = "SKIP"
    """Leave this step's effect as-is and continue with the rest of the plan."""

    ASK_USER = "ASK_USER"
    """Haven needs a decision it should not make on its own."""

    ABORT = "ABORT"
    """Retrying will not help; stop and surface the problem."""


# Failures that indicate the request itself cannot succeed as given
# (wrong id, missing target, unsupported action) — retrying identically
# will not change the outcome.
_NON_RETRYABLE_ERRORS = frozenset(
    {
        "unsupported action",
        "unknown media title",
        "device not found",
        "missing device_id",
        "no quoted title found in step text",
    }
)


def recommend_recovery_for_execution(step_result: StepExecutionResult) -> RecoveryAction:
    """Recommend what to do about a single executed step's outcome."""

    if step_result.status is StepExecutionStatus.SUCCEEDED:
        return RecoveryAction.CONTINUE

    if step_result.status is StepExecutionStatus.SKIPPED:
        # Skipped almost always means "awaiting confirmation" today.
        return RecoveryAction.ASK_USER

    # FAILED
    if step_result.error in _NON_RETRYABLE_ERRORS:
        return RecoveryAction.ABORT

    return RecoveryAction.RETRY


def recommend_recovery_for_verification(verification: StepVerification) -> RecoveryAction:
    """Recommend what to do about a single step's verification outcome."""

    if verification.status is StepVerificationStatus.VERIFIED:
        return RecoveryAction.CONTINUE

    if verification.status is StepVerificationStatus.SKIPPED:
        return RecoveryAction.ASK_USER

    if verification.status is StepVerificationStatus.UNVERIFIABLE:
        # Haven can't confirm the effect, but it also has no evidence
        # anything is wrong. Move on rather than blocking on a check
        # that was never going to succeed.
        return RecoveryAction.SKIP

    # MISMATCH: the device didn't end up where the plan expected. A
    # single retry is worth attempting (the device may have been
    # momentarily unavailable); a caller that already retried should
    # treat a second mismatch as ABORT rather than calling this again.
    return RecoveryAction.RETRY


def retry_step(
    step: Any,
    context: Any,
    handler: Any,
    *,
    max_attempts: int = 2,
) -> StepExecutionResult:
    """Re-run `handler` for `step` up to `max_attempts` times.

    Stops as soon as a `SUCCEEDED` result is produced. Returns the final
    attempt's result (success or otherwise) when every attempt fails.
    Exceptions from `handler` are not caught here — callers that need
    the executor's crash-safety should call through
    `haven.execution.executor.execute_plan` instead of this helper
    directly for anything beyond a single manual retry.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    result: StepExecutionResult | None = None

    for _attempt in range(max_attempts):
        result = handler(step, context)
        if result.status is StepExecutionStatus.SUCCEEDED:
            return result

    assert result is not None  # loop runs at least once
    return result


__all__ = [
    "RecoveryAction",
    "recommend_recovery_for_execution",
    "recommend_recovery_for_verification",
    "retry_step",
]
