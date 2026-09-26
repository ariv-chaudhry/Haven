"""Runtime configuration for Haven planning.

Backend selection is explicit and deterministic:

    HAVEN_PLANNER_BACKEND=mock     offline deterministic reasoner (default)
    HAVEN_PLANNER_BACKEND=bedrock  Strands Agent -> Amazon Bedrock

Haven never switches to Bedrock merely because AWS credentials exist, and it
never silently falls back to the mock when Bedrock is selected and fails.
Bedrock connection settings live in ``aws.bedrock.config``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MOCK_PLANNER_BACKEND = "mock"
BEDROCK_PLANNER_BACKEND = "bedrock"
SUPPORTED_PLANNER_BACKENDS: frozenset[str] = frozenset(
    {MOCK_PLANNER_BACKEND, BEDROCK_PLANNER_BACKEND}
)

ENV_PLANNER_BACKEND = "HAVEN_PLANNER_BACKEND"
ENV_MAX_PLAN_STEPS = "HAVEN_MAX_PLAN_STEPS"
ENV_LOG_LEVEL = "HAVEN_LOG_LEVEL"


@dataclass(frozen=True, slots=True)
class HavenConfig:
    """Process configuration for planning. Contains no cloud credentials."""

    planner_backend: str = MOCK_PLANNER_BACKEND
    max_plan_steps: int = 12
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        object.__setattr__(self, "planner_backend", normalize_backend(self.planner_backend))
        if self.max_plan_steps < 1:
            raise ValueError(f"{ENV_MAX_PLAN_STEPS} must be a positive integer")


def normalize_backend(value: str) -> str:
    """Return a canonical backend name or raise `ValueError` if unsupported."""

    backend = (value or "").strip().lower()
    if backend not in SUPPORTED_PLANNER_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_PLANNER_BACKENDS))
        raise ValueError(f"unsupported planner backend {value!r}; expected one of: {supported}")
    return backend


def get_config() -> HavenConfig:
    """Load planning configuration from the process environment."""

    backend = os.getenv(ENV_PLANNER_BACKEND, MOCK_PLANNER_BACKEND).strip() or MOCK_PLANNER_BACKEND
    raw_max_steps = os.getenv(ENV_MAX_PLAN_STEPS, "").strip()
    raw_log_level = os.getenv(ENV_LOG_LEVEL, "").strip()

    if raw_max_steps:
        try:
            max_plan_steps = int(raw_max_steps)
        except ValueError as exc:
            raise ValueError(f"{ENV_MAX_PLAN_STEPS} must be an integer") from exc
    else:
        max_plan_steps = 12

    return HavenConfig(
        planner_backend=backend,
        max_plan_steps=max_plan_steps,
        log_level=raw_log_level or "INFO",
    )
