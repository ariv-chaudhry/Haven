"""Haven MCP server.

    Alexa+  --MCP (Streamable HTTP)-->  Haven MCP Server  --calls-->  Haven
        (context resolution / planning / execution / verification / memory)

This module wires the transport and shared runtime state together. The
actual tool logic lives in `haven.mcp.tools.*` as plain,
dependency-injected functions that don't import the `mcp` package at all
(see the module docstrings there) — this file's `register(mcp)` calls are
the only place those functions get wrapped as `@mcp.tool()`.

Phase 3 runs Haven's own simulators and in-memory stores directly, the
same way `scripts/run_movie_night.py` does; there is no AWS dependency
here yet. Person A's DynamoDB-backed `MemoryService` (Phase 3) is a
drop-in swap for the `MemoryService()` constructed below — nothing here
needs to change when that lands, only `app_lifespan`'s construction.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from mcp.server.fastmcp import Context, FastMCP

from haven.config import HavenConfig, get_config
from haven.execution.results import ExecutionResult
from haven.integrations.calendar import CalendarService, demo_calendar
from haven.integrations.media import MediaService
from haven.memory.service import MemoryService
from haven.models.plan import Plan
from haven.verification.verifier import VerificationResult

from simulator.household.service import HouseholdSimulatorService
from simulator.media.service import MediaSimulatorService

logger = logging.getLogger(__name__)

SERVER_NAME = "haven"
SERVER_INSTRUCTIONS = (
    "Haven is a household agent. Ask for the current household context, "
    "propose a plan for a goal like 'get movie night ready', execute a "
    "previously proposed plan (confirming when it includes a high-impact "
    "step), save a durable household preference, or ask what to do "
    "tonight for a quick recommendation."
)


@dataclass
class StoredPlan:
    """A previously proposed plan, plus whatever has happened to it since."""

    plan: Plan
    household_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    execution: ExecutionResult | None = None
    verification: VerificationResult | None = None


class PlanStore:
    """Process-local registry of plans proposed through this MCP server.

    Scoped to the server process — a real deployment would back this with
    `aws.dynamodb`, the same way `MemoryService` will, so a plan survives
    a restart and can be looked up across server instances. That's future
    work; nothing in `haven.mcp.tools` depends on this being in-memory.
    """

    def __init__(self) -> None:
        self._plans: dict[str, StoredPlan] = {}

    def save(self, plan: Plan, household_id: str) -> StoredPlan:
        stored = StoredPlan(plan=plan, household_id=household_id)
        self._plans[plan.id] = stored
        return stored

    def get(self, plan_id: str) -> StoredPlan | None:
        return self._plans.get(plan_id)

    def record_execution(
        self,
        plan_id: str,
        execution: ExecutionResult,
        verification: VerificationResult,
    ) -> StoredPlan:
        stored = self._plans.get(plan_id)
        if stored is None:
            raise KeyError(f"Unknown plan_id: {plan_id}")
        stored.execution = execution
        stored.verification = verification
        return stored


@dataclass
class AppContext:
    """Shared runtime state every MCP tool call can reach.

    `household_id` is fixed for this Phase 3 server — Haven runs against
    one demo household per process, matching the simulators. Routing a
    real Alexa+ account/session to a specific household is future work
    (Phase 4+), once there's an actual account to route from.
    """

    household: HouseholdSimulatorService
    media: MediaService
    memory: MemoryService
    calendar: CalendarService
    plans: PlanStore
    config: HavenConfig
    household_id: str


def get_app(ctx: Context) -> AppContext:
    """Fetch the shared `AppContext` from an MCP tool call's request context."""

    return ctx.request_context.lifespan_context


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Build Haven's runtime dependencies once per server process."""

    config = get_config()
    logging.basicConfig(level=config.log_level, format="%(levelname)s %(name)s: %(message)s")

    household_service = HouseholdSimulatorService()
    household_id = household_service.get_snapshot().household_id

    media_service = MediaService(MediaSimulatorService())
    memory_service = MemoryService(default_household_id=household_id)
    calendar_service = demo_calendar()

    logger.info("Haven MCP server starting for household_id=%s", household_id)

    try:
        yield AppContext(
            household=household_service,
            media=media_service,
            memory=memory_service,
            calendar=calendar_service,
            plans=PlanStore(),
            config=config,
            household_id=household_id,
        )
    finally:
        logger.info("Haven MCP server shutting down")


def create_server(host: str | None = None, port: int | None = None) -> FastMCP:
    """Build and fully wire the Haven MCP server. Does not start it —
    call `.run(transport=...)` on the result (see `scripts/run_server.py`).
    """

    kwargs: dict[str, object] = {}
    if host is not None:
        kwargs["host"] = host
    if port is not None:
        kwargs["port"] = port

    mcp = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS, lifespan=app_lifespan, **kwargs)

    # Deferred imports: these modules only need `create_server`/`get_app`
    # *after* this function starts running, by which point this module's
    # own top-level names (get_app, AppContext, ...) already exist. An
    # eager, module-level import here would deadlock: importing
    # `haven.mcp.tools.context` would re-enter this partially-initialized
    # module before `get_app` was defined.
    from haven.mcp.tools import context as context_tool
    from haven.mcp.tools import execution as execution_tool
    from haven.mcp.tools import planning as planning_tool
    from haven.mcp.tools import preferences as preferences_tool
    from haven.mcp.tools import recommendations as recommendations_tool

    context_tool.register(mcp)
    planning_tool.register(mcp)
    execution_tool.register(mcp)
    preferences_tool.register(mcp)
    recommendations_tool.register(mcp)

    return mcp


__all__ = [
    "AppContext",
    "PlanStore",
    "StoredPlan",
    "get_app",
    "app_lifespan",
    "create_server",
]
