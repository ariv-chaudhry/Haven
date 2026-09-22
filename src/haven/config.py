"""Runtime configuration for Haven planning.

Phase 1 supports only the local mock planner backend. Phase 2 may add a
Bedrock/Strands backend without changing the public planning interface.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MOCK_PLANNER_BACKEND = "mock"


@dataclass(frozen=True, slots=True)
class HavenConfig:
    """Process configuration for planning.

    No cloud credentials or AWS settings are stored here in Phase 1.
    """

    planner_backend: str = MOCK_PLANNER_BACKEND
    max_plan_steps: int = 12
    log_level: str = "INFO"


def get_config() -> HavenConfig:
    """Load planning configuration from process environment when present."""

    backend = (
        os.getenv("HAVEN_PLANNER_BACKEND", MOCK_PLANNER_BACKEND).strip() or MOCK_PLANNER_BACKEND
    )
    raw_max_steps = os.getenv("HAVEN_MAX_PLAN_STEPS", "").strip()
    raw_log_level = os.getenv("HAVEN_LOG_LEVEL", "").strip()

    max_plan_steps = int(raw_max_steps) if raw_max_steps else 12
    if max_plan_steps < 1:
        raise ValueError("HAVEN_MAX_PLAN_STEPS must be a positive integer")

    return HavenConfig(
        planner_backend=backend,
        max_plan_steps=max_plan_steps,
        log_level=raw_log_level or "INFO",
    )
