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
