"""Application-facing planning orchestration.

    Goal + HouseholdContext
        -> planner (constraints + reasoning)
        -> policy validation
        -> final proposed Plan

This service does not resolve context, execute actions, verify device
state, call Alexa, serve MCP, or touch AWS.
"""

from __future__ import annotations

import logging

from haven.agents.planner import create_plan
from haven.agents.policies import validate_plan_policy
from haven.config import HavenConfig, get_config
from haven.models.context import HouseholdContext
from haven.models.plan import Plan

logger = logging.getLogger(__name__)


def create_household_plan(
    goal: str,
    context: HouseholdContext,
    *,
    config: HavenConfig | None = None,
) -> Plan:
    """Produce a policy-validated proposed plan for a household goal.

    Raises `ValueError` when input is invalid, the planner cannot produce
    steps, the plan exceeds configured size, or policy validation fails.
    """

    settings = config or get_config()

    plan = create_plan(goal, context)

    if len(plan.steps) > settings.max_plan_steps:
        raise ValueError(f"plan has {len(plan.steps)} steps; limit is {settings.max_plan_steps}")

    policy = validate_plan_policy(plan)
    if not policy.valid:
        detail = "; ".join(issue.message for issue in policy.issues)
        raise ValueError(f"plan violates action policy: {detail}")

    logger.info(
        "Created plan %s with %s step(s); requires_confirmation=%s",
        plan.id,
        len(plan.steps),
        plan.requires_confirmation,
    )
    return plan
