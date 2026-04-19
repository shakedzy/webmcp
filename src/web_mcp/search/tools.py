from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from ddgs.exceptions import DDGSException
from fastmcp import Context

from web_mcp.server import mcp

# DDGS `backend="auto"` for text hits Wikipedia/Grokipedia first; their APIs often throw
# transient ConnectError, which becomes DDGSException before other engines return results.
_DEFAULT_TEXT_BACKENDS = "duckduckgo,bing,brave,google,yahoo"

T = TypeVar("T")


async def _ddgs_to_thread_with_retries(fn: Callable[[], T], *, attempts: int = 3) -> T:
    delay = 0.35
    last: DDGSException | None = None
    for i in range(attempts):
        try:
            return await asyncio.to_thread(fn)
        except DDGSException as e:
            last = e
            if i == attempts - 1:
                raise
            await asyncio.sleep(delay + random.random() * 0.2)
            delay *= 1.75
    raise AssertionError("unreachable") from last


@mcp.tool
async def web_search(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
    safesearch: Literal["on", "moderate", "off"] = "moderate",
    backend: str = _DEFAULT_TEXT_BACKENDS,
    timelimit: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Search the web using DDGS (multi-backend metasearch: Bing, Brave, DuckDuckGo, Google, Yahoo, Wikipedia).

    Args:
        query: Search query.
        max_results: Number of results (default 10).
        region: Region code (default "wt-wt" for worldwide). Examples: "us-en", "uk-en", "de-de".
        safesearch: Content filter level.
        backend: Comma-separated engines, or "auto" (Wikipedia-first; can flake on wiki HTTP errors).
            Default omits Wikipedia-first ordering for reliability.
        timelimit: Time filter — "d" (day), "w" (week), "m" (month), "y" (year), or None.
    """

    def _search() -> list[dict[str, Any]]:
        from ddgs import DDGS

        with DDGS() as ddgs:
            return ddgs.text(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
                backend=backend,
                timelimit=timelimit,
            )

    results = await _ddgs_to_thread_with_retries(_search)
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"**{r.get('title', '')}**")
        lines.append(r.get("href", ""))
        lines.append(r.get("body", ""))
        lines.append("")
    return "\n".join(lines)


@mcp.tool
async def news_search(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
    safesearch: Literal["on", "moderate", "off"] = "moderate",
    timelimit: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Search for recent news articles.

    Args:
        query: Search query.
        max_results: Number of results.
        region: Region code.
        safesearch: Content filter level.
        timelimit: Time filter — "d" (day), "w" (week), "m" (month).
    """

    def _search() -> list[dict[str, Any]]:
        from ddgs import DDGS

        with DDGS() as ddgs:
            return ddgs.news(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
            )

    results = await _ddgs_to_thread_with_retries(_search)
    if not results:
        return "No news results found."
    lines = []
    for r in results:
        lines.append(f"**{r.get('title', '')}**")
        lines.append(f"Source: {r.get('source', '')} | Date: {r.get('date', '')}")
        lines.append(r.get("url", ""))
        lines.append(r.get("body", ""))
        lines.append("")
    return "\n".join(lines)


@mcp.tool
async def image_search(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
    safesearch: Literal["on", "moderate", "off"] = "moderate",
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Search for images.

    Returns image URLs with metadata (title, source, dimensions).
    """

    def _search() -> list[dict[str, Any]]:
        from ddgs import DDGS

        with DDGS() as ddgs:
            return ddgs.images(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
            )

    results = await _ddgs_to_thread_with_retries(_search)
    if not results:
        return "No image results found."
    lines = []
    for r in results:
        lines.append(f"**{r.get('title', '')}**")
        lines.append(f"Image: {r.get('image', '')}")
        dims = f"{r.get('width', '?')}x{r.get('height', '?')}"
        lines.append(f"Source: {r.get('source', '')} | Size: {dims}")
        lines.append("")
    return "\n".join(lines)
