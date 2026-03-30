from __future__ import annotations

from contextlib import asynccontextmanager

from fastmcp import FastMCP


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


def main():
    mcp.run()
