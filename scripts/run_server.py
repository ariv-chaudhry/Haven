"""Run Haven's MCP server.

Usage:
    python scripts/run_server.py
    python scripts/run_server.py --transport stdio
    python scripts/run_server.py --host 0.0.0.0 --port 8787

Alexa+ requires Streamable HTTP (the default here); `--transport stdio`
is for local tools that speak MCP over stdio, such as the MCP Inspector,
which is worth running against this server before pointing the Alexa+
web simulator at it (see docs/mcp.md, once it exists — for now, the
inspector's own README covers `npx @modelcontextprotocol/inspector`).

Requires the package to be installed (`pip install -e .`).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from haven.mcp.server import create_server

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Haven's MCP server.")
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="streamable-http",
        help="MCP transport (default: streamable-http, required by Alexa+).",
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"Host to bind for streamable-http (default: {DEFAULT_HOST})."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind for streamable-http (default: {DEFAULT_PORT}).",
    )
    args = parser.parse_args(argv)

    if args.transport == "streamable-http":
        server = create_server(host=args.host, port=args.port)
        print(f"Haven MCP server: http://{args.host}:{args.port} (streamable-http)")
    else:
        server = create_server()
        print("Haven MCP server: stdio")

    server.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
