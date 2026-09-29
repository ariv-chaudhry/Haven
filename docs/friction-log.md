# Haven Friction Log

This log tracks friction, surprises, and rough edges encountered while
building Haven with Alexa+, MCP, and AWS. Add an entry as soon as you hit
something worth noting — don't wait until submission week.

The hackathon submission requires product feedback for every tool, API,
or SDK used. This log is the raw material for that write-up, so be
specific: what you tried, what happened, and what you'd change.

## How to Add an Entry

Copy the template below into a new section, dated, with your initials.

```
### [YYYY-MM-DD] — Short title (Initials)

**Tool / API / SDK:**

**What we were trying to do:**

**What happened:**

**What worked well:**

**What didn't:**

**Workaround (if any):**

**Would we use it again?**
```

## Entries

### [Phase 3] — mcp SDK usage not verifiable offline (B)

**Tool / API / SDK:** `mcp` (the official MCP Python SDK), specifically
`mcp.server.fastmcp.FastMCP`

**What we were trying to do:** Build `haven/mcp/server.py` against the
documented FastMCP lifespan pattern: a `@dataclass AppContext`, an
`@asynccontextmanager async def app_lifespan(server) -> AsyncIterator[AppContext]`
passed to `FastMCP(name, lifespan=...)`, tools reading shared state via
`ctx.request_context.lifespan_context`, and `server.run(transport="streamable-http")`
for the Streamable HTTP transport Alexa+ requires.

**What happened:** This dev environment has no network access, so `mcp`
couldn't be `pip install`-ed to test against the real package. Everything
in `haven/mcp/` was built and verified against a small local stand-in
(matching just this usage) instead: `FastMCP(name, instructions=,
lifespan=, host=, port=)`, `@mcp.tool()`, `Context.request_context.lifespan_context`,
`server.run(transport=)`. All 6 tools were registered and called through
that stand-in — including the confirmation-gating path on a synthetic
high-impact plan — and behaved correctly.

**What worked well:** Keeping each tool's actual logic (the functions
`haven.mcp.tools.*` export alongside `register()`) as plain,
dependency-injected functions with no import of `mcp` at all meant the
business logic itself could be fully tested regardless. Only the
`register()` wrapper and the `Context`/`FastMCP` imports depend on the
real package.

**What didn't:** The exact FastMCP constructor kwargs (`host=`, `port=`
passed directly vs. set via `server.settings`) and the precise
`transport=` string for Streamable HTTP could plausibly differ by
installed version. This wasn't independently confirmed against a real
`mcp` install.

**Workaround (if any):** None needed yet — but this is the first thing
to check the moment `pip install -e .` succeeds with network access:
`python scripts/run_server.py` should start cleanly, and
`npx @modelcontextprotocol/inspector` (or curling the Streamable HTTP
endpoint) should list all 6 tools. If the constructor signature has
moved, it's isolated to `create_server()` in `haven/mcp/server.py` —
nothing else touches FastMCP directly.

**Would we use it again?** Yes, but flag this as the first thing to
smoke-test locally before wiring up the Alexa+ web simulator (Phase 4) —
don't assume this is 100% confirmed to work in the real environment yet.

### [Phase 2] — PlanStep has no structured media_id (B)

**Tool / API / SDK:** Internal contract — `haven.models.plan.PlanStep`

**What we were trying to do:** Have the executor's `prepare_media_session`
and `select_media` handlers read which title the planner selected
directly off the `PlanStep`, the same way they read `device_id` and
`room_id`.

**What happened:** `PlanStep` (owned by Person A) has no `media_id`
field, and `candidate_to_step` doesn't carry `ActionCandidate.media_id`
through to the step either — it's dropped at that boundary. The selected
title only survives in the free-text `title` / `description` strings
(e.g. `"Select 'Paddington 2' (103 min) ..."`).

**What worked well:** The phrasing is consistent enough (always a single
quoted title) that a small regex plus a title lookup against the media
catalog (`MediaService.find_media_id_by_title`) recovers it reliably for
the mock reasoner's output.

**What didn't:** This is fragile — it breaks if the phrasing in
`agents/planner.py` or the Bedrock reasoner's summary ever changes, and
it silently fails (a `FAILED` step, not a crash) if a title doesn't
match exactly.

**Workaround (if any):** `extract_quoted_title()` +
`MediaService.find_media_id_by_title()` in
`haven/execution/actions.py`, documented inline as a deliberate,
narrow bridge rather than a general parser.

**Would we use it again?** No — flagging for Person A: adding an
optional `media_id: str | None = None` field to `PlanStep` (and
threading `ActionCandidate.media_id` through `candidate_to_step`) would
remove the need for this entirely and make execution far more robust.
Worth doing before Phase 3 wires this up to MCP.

---

_Add new entries above this line, most recent first._
