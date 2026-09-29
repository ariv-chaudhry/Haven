# __init__.py
# Haven MCP Package

# Haven's MCP surface: the Streamable HTTP server and tools Alexa+ (or
# any MCP client) calls to read household context, propose and execute
# plans, save preferences, and get activity recommendations

# Modules
# server  - Builds the FastMCP server: shared runtime state
#           (household/media/memory/calendar simulators plus an
#           in-memory plan registry) via a lifespan context manager,
#           and wires up every tool module
# schemas - The MCP-facing request/response contracts and the
#           functions that map Haven's internal models onto them
# tools   - One module per MCP tool group: context, planning,
#           execution, preferences, recommendations

# Public Functions
# create_server - Builds a fully wired FastMCP server (not yet running)

from haven.mcp.server import create_server

__all__ = [
    "create_server",
]
