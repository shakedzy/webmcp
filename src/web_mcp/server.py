from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware


@asynccontextmanager
async def _lifespan(server: FastMCP):
    from web_mcp.browser.manager import BrowserManager

    manager = BrowserManager()
    try:
        yield {"browser_manager": manager}
    finally:
        await manager.shutdown()


mcp = FastMCP(name="web-mcp", lifespan=_lifespan)

import web_mcp.browser.tools as _bt  # noqa: E402, F401
import web_mcp.content.tools as _ct  # noqa: E402, F401
import web_mcp.search.tools as _st  # noqa: E402, F401


def main() -> None:
    parser = argparse.ArgumentParser(description="Web MCP — browser, search, and fetch tools.")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve MCP over HTTP (streamable) for clients that need a server URL (e.g. llama.cpp).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("WEB_MCP_HOST", "127.0.0.1"),
        help="HTTP bind host (default: 127.0.0.1 or WEB_MCP_HOST).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("WEB_MCP_PORT", "9000")),
        help="HTTP bind port (default: 9000 or WEB_MCP_PORT).",
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("WEB_MCP_PATH", "/mcp"),
        help="HTTP path for the MCP endpoint (default: /mcp).",
    )
    args, _unknown = parser.parse_known_args()

    if args.http:
        # Browser clients (e.g. llama.cpp web UI): OPTIONS preflight, and
        # Streamable HTTP requires echoing `mcp-session-id` on every POST after
        # initialize. JS can only read that response header if it is listed in
        # Access-Control-Expose-Headers (defaults would hide it).
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            path=args.path,
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["*"],
                    allow_headers=["*"],
                    expose_headers=["mcp-session-id", "mcp-protocol-version"],
                ),
            ],
        )
    else:
        mcp.run()
