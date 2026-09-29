"""MCP tool: `get_household_context`.

Resolves Haven's current household context for a goal — the same
`resolve_context` call `scripts/run_movie_night.py` makes locally — and
returns it in the stable MCP-facing shape from `haven.mcp.schemas`.

`build_sources` is shared with `haven.mcp.tools.planning` and
`haven.mcp.tools.recommendations`, since every tool that needs a
`HouseholdContext` assembles the same approved sources the same way.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from haven.context.resolver import resolve_context
from haven.context.sources import (
    ConnectedServiceSource,
    ContextSource,
    DeviceStateSource,
    MemorySource,
    SensorSource,
    UserStatementSource,
)
from haven.mcp.schemas import HouseholdContextSummary, context_to_summary


def build_sources(app) -> list[ContextSource]:
    """Assemble the approved context sources for `app`'s current runtime.

    `app` is a `haven.mcp.server.AppContext`, accessed structurally here
    (not imported by type) to avoid importing `haven.mcp.server` at
    module load time — see that module's `create_server` for why.
    """

    return [
        UserStatementSource(),
        DeviceStateSource(app.household),
        SensorSource(app.household),
        MemorySource(app.memory.lookup_fact),
        ConnectedServiceSource(app.calendar.lookup_fact),
    ]


def get_household_context(app, goal: str) -> HouseholdContextSummary:
    """Resolve the current household context for `goal`.

    Raises `ValueError` for an empty goal, and
    `haven.context.resolver.ClarificationNeeded` if a required fact this
    goal needs cannot be resolved from any approved source (not currently
    reachable through this tool's own required facts, but preserved for
    goals added later that request one via `extra_facts`).
    """

    if not goal or not goal.strip():
        raise ValueError("goal must not be empty")

    household = app.household.get_snapshot()
    media_options = app.media.list_media_items()
    sources = build_sources(app)

    context = resolve_context(goal, household, media_options, sources)
    return context_to_summary(context)


def register(mcp) -> None:
    from haven.mcp.server import get_app

    @mcp.tool()
    def get_household_context_tool(goal: str, ctx: Context) -> HouseholdContextSummary:
        """Resolve and return Haven's current understanding of the
        household for a stated goal: who's home, which rooms and devices
        are available, what media is on hand, how much time is available,
        and any saved preferences relevant to that goal.
        """

        return get_household_context(get_app(ctx), goal)


__all__ = ["build_sources", "get_household_context", "register"]
