# __init__.py
# Haven MCP Tools Package

# One module per MCP tool group. Each module exposes a plain,
# dependency-injected function that does the actual work (independently
# testable without the `mcp` package) and a register(mcp) function that
# wraps it as an @mcp.tool() for haven.mcp.server.create_server to call

# Modules
# context         - get_household_context
# planning        - propose_household_plan, get_plan_status
# execution       - execute_household_plan
# preferences     - save_household_preference
# recommendations - get_activity_recommendations

# Intentionally empty of submodule imports: haven.mcp.server imports
# these modules individually, deferred inside create_server(), and an
# eager aggregate import here would run at the same time as that
# function's own module is still initializing. See haven/mcp/server.py's
# create_server() docstring for the full explanation.

__all__: list[str] = []
