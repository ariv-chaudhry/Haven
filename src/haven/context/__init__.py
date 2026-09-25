# __init__.py
# Haven Context Package

# Implements Haven's Context Resolver: the subsystem that gathers only
# the facts required for the user's current goal, from a small set of
# approved sources, and asks the user directly when a fact cannot be
# confidently obtained rather than guessing or continuously monitoring
# the household

# Modules
# facts    - Helpers for creating and storing individual ContextFacts
#            during a single resolution pass
# sources  - The approved context sources (user input, connected
#            services, device state, low-resolution sensors, memory)
#            and the common interface they implement
# expiry   - Rules for how long a gathered fact remains trustworthy
#            before it must be re-resolved
# resolver - The main resolve_context() entry point used by the
#            planner

# Public Classes / Functions
# resolve_context      - Resolves the facts required for a goal
# ClarificationNeeded   - Raised when a required fact needs user input
# FactRequest           - Describes a single fact the planner needs
# FactStore             - Holds facts gathered during one resolution
# ContextSource         - Base interface for an approved context source

from haven.context.resolver import (
    ClarificationNeeded,
    FactRequest,
    resolve_context,
)
from haven.context.facts import FactStore
from haven.context.sources import ContextSource

__all__ = [
    "resolve_context",
    "ClarificationNeeded",
    "FactRequest",
    "FactStore",
    "ContextSource",
]
