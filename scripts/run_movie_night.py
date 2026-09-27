"""Person B end-to-end workflow harness: goal -> context -> plan -> execution -> verification.

Runs the full local "Movie Night" vertical slice against the household
and media simulators:

    resolve_context()          Person B
        -> create_household_plan()   Person A
            -> execute_plan()        Person B
                -> verify_plan()     Person B

Nothing here talks to Alexa+, MCP, or AWS. Person A's `scripts/test_workflow.py`
covers planning alone with a hand-built context; this script is the
complement — it exercises Person B's full local pipeline, context
resolution through verification, with the household/media simulators
standing in for real devices.

Usage:
    python scripts/run_movie_night.py
    python scripts/run_movie_night.py --goal "Get movie night ready"
    python scripts/run_movie_night.py --backend mock

Requires the package to be installed (``pip install -e .``).
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from haven.config import SUPPORTED_PLANNER_BACKENDS, HavenConfig, get_config
from haven.context.resolver import resolve_context
from haven.context.sources import (
    ConnectedServiceSource,
    ContextSource,
    DeviceStateSource,
    MemorySource,
    SensorSource,
    UserStatementSource,
)
from haven.execution.executor import execute_plan
from haven.execution.results import ExecutionResult
from haven.integrations.calendar import demo_calendar
from haven.integrations.media import MediaService
from haven.memory.preferences import PreferenceKey
from haven.memory.service import MemoryService
from haven.models.context import HouseholdContext
from haven.models.plan import Plan
from haven.planning.plan_service import create_household_plan
from haven.verification.verifier import VerificationResult, verify_plan

from simulator.household.service import HouseholdSimulatorService
from simulator.media.service import MediaSimulatorService

DEFAULT_GOAL = "Get movie night ready"


def build_sources(
    household_service: HouseholdSimulatorService,
    memory: MemoryService,
    calendar,
) -> list[ContextSource]:
    """Assemble the approved context sources, in no particular order.

    `resolve_context` applies its own priority ordering internally.
    """

    return [
        UserStatementSource(),
        DeviceStateSource(household_service),
        SensorSource(household_service),
        MemorySource(memory.lookup_fact),
        ConnectedServiceSource(calendar.lookup_fact),
    ]


def seed_demo_preferences(memory: MemoryService, household_id: str) -> None:
    """Store a couple of durable preferences so the resolver has
    something realistic to find, mirroring what a household would have
    told Haven previously.
    """

    memory.save_preference(household_id, PreferenceKey.PREFERRED_GENRES.value, ["sci-fi", "comedy"])


def print_context(context: HouseholdContext) -> None:
    print("Resolved household context:")
    print(f"  Household:        {context.household_id}")
    print(f"  People home:      {[p.display_name for p in context.people if p.presence.value == 'PRESENT']}")
    print(f"  Rooms:            {[r.name for r in context.rooms]}")
    print(f"  Devices:          {[d.name for d in context.devices]}")
    print(f"  Available media:  {[m.title for m in context.media_options]}")
    print(f"  Available time:   {context.available_minutes} min")
    print(f"  Preferred room:   {context.preferred_room_id}")
    print(f"  Preferred genres: {context.preferred_genres}")
    print()


def print_plan(plan: Plan) -> None:
    print(f"Plan ID: {plan.id}")
    print(f"Status:  {plan.status.value}")
    print(f"Summary: {plan.summary}")
    print("Steps:")
    for step in plan.steps:
        confirm = "confirmation required" if step.requires_confirmation else "no confirmation"
        print(f"  {step.order}. {step.title}  [{step.risk.value}; {confirm}]")
        print(f"     {step.description}")
    print()


def print_execution(result: ExecutionResult) -> None:
    print(f"Execution status: {result.status.value}")
    for step_result in result.step_results:
        print(f"  - {step_result.action}: {step_result.status.value} — {step_result.detail}")
        if step_result.error:
            print(f"      error: {step_result.error}")
    print()


def print_verification(result: VerificationResult) -> None:
    print(f"Verification status: {result.status.value}")
    for verification in result.step_verifications:
        print(f"  - {verification.action}: {verification.status.value} — {verification.detail}")
    print()


def run(goal: str, backend: str | None) -> int:
    base = get_config()
    config = (
        HavenConfig(
            planner_backend=backend,
            max_plan_steps=base.max_plan_steps,
            log_level=base.log_level,
        )
        if backend
        else base
    )
    logging.basicConfig(level=config.log_level, format="%(levelname)s %(name)s: %(message)s")

    household_service = HouseholdSimulatorService()
    media_backend = MediaSimulatorService()
    media_service = MediaService(media_backend)
    memory = MemoryService()
    calendar = demo_calendar()

    household = household_service.get_snapshot()
    seed_demo_preferences(memory, household.household_id)
    sources = build_sources(household_service, memory, calendar)

    print(f"Goal: {goal}")
    print()

    try:
        context = resolve_context(goal, household, media_service.list_media_items(), sources)
    except Exception as exc:  # ClarificationNeeded or ValueError
        print(f"Context resolution failed: {exc}", file=sys.stderr)
        return 1

    print_context(context)

    try:
        plan = create_household_plan(goal, context, config=config)
    except Exception as exc:
        print(f"Planning failed: {exc}", file=sys.stderr)
        return 2

    print_plan(plan)

    execution_result = execute_plan(
        plan,
        household=household_service,
        media=media_service,
        household_id=context.household_id,
        memory=memory,
    )
    print_execution(execution_result)

    verification_result = verify_plan(
        plan,
        execution_result,
        household=household_service,
        media=media_service,
    )
    print_verification(verification_result)

    history = memory.lookup_fact("history:movie_night_prepared", household_id=context.household_id)
    print(f"Memory: {len(history or [])} movie night(s) recorded this session (in-memory only).")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Haven's full local movie-night workflow (context -> plan -> execute -> verify)."
    )
    parser.add_argument("--goal", default=DEFAULT_GOAL, help=f"Goal text (default: {DEFAULT_GOAL!r}).")
    parser.add_argument(
        "--backend",
        choices=sorted(SUPPORTED_PLANNER_BACKENDS),
        default=None,
        help="Planner backend (default: HAVEN_PLANNER_BACKEND or mock).",
    )
    args = parser.parse_args(argv)
    return run(args.goal, args.backend)


if __name__ == "__main__":
    sys.exit(main())
