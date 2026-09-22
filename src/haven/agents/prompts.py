"""Central planning prompts and instructions for Haven.

Phase 1 does not call a model. These strings are the single source of
planning instructions so Phase 2 can pass them to Strands + Bedrock
without collecting prompt text from planner or plan-service code.
"""

from __future__ import annotations

from haven.models.context import HouseholdContext
from haven.models.plan import ActionRisk, PlanStatus

PLANNER_SYSTEM_PROMPT = """You are Haven, a household planning agent.

Your job is planning only. Do not execute device actions, do not verify
effects, and do not persist or deploy anything. Produce an explicit
structured plan made of understandable steps.

Planning rules:
- Use only the supplied household context.
- Use the minimum household context required for the user's request.
- Do not invent unavailable devices, people, rooms, media, preferences, or other facts.
- If required information is missing, prefer clarification over guessing.
- Respect deterministic constraints already applied to candidate actions.
  If ordinary rules have rejected an option, do not revive it.
- Respect action-risk policy:
  READ does not require confirmation.
  REVERSIBLE_ACTION may proceed automatically under current policy.
  HIGH_IMPACT_ACTION always requires explicit user confirmation.
- Treat high-impact actions conservatively. Include them only when the
  user's goal clearly requires them, and mark them as requiring confirmation.
- Keep steps concrete, minimal, and understandable.
- Distinguish planning from execution and verification. Never claim that
  a step has already been performed.
"""


def build_planning_prompt(goal: str, context: HouseholdContext) -> str:
    """Build the user-turn planning prompt for a goal and resolved context."""

    context_json = context.model_dump_json(indent=2)
    return (
        "Create a structured household plan for the following request.\n\n"
        f"Goal:\n{goal}\n\n"
        "Resolved household context (JSON). Use only these facts:\n"
        f"{context_json}\n\n"
        "Allowed action risk values:\n"
        f"{', '.join(risk.value for risk in ActionRisk)}\n\n"
        "Allowed plan status values for a newly proposed plan:\n"
        f"{PlanStatus.PROPOSED.value}, {PlanStatus.AWAITING_CONFIRMATION.value}\n\n"
        "Return a plan with explicit steps. Do not execute anything."
    )
