from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastmcp import Context

from web_mcp.server import mcp


@mcp.tool
async def web_search(
    query: str,
    max_results: int = 10,
    region: str = "wt-wt",
    safesearch: Literal["on", "moderate", "off"] = "moderate",
    backend: str = "auto",
    timelimit: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Search the web using DDGS (multi-backend metasearch: Bing, Brave, DuckDuckGo, Google, Yahoo, Wikipedia).

    Args:
        query: Search query.
        max_results: Number of results (default 10).
        region: Region code (default "wt-wt" for worldwide). Examples: "us-en", "uk-en", "de-de".
        safesearch: Content filter level.
        backend: Search backend — "auto", "bing", "brave", "duckduckgo", "google", "yahoo", "wikipedia".
        timelimit: Time filter — "d" (day), "w" (week), "m" (month), "y" (year), or None.
    """

    def _search():
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

    results = await asyncio.to_thread(_search)
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

    def _search():
        from ddgs import DDGS

        with DDGS() as ddgs:
            return ddgs.news(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
            )

    results = await asyncio.to_thread(_search)
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

    def _search():
        from ddgs import DDGS

        with DDGS() as ddgs:
            return ddgs.images(
                query,
                max_results=max_results,
                region=region,
                safesearch=safesearch,
            )

    results = await asyncio.to_thread(_search)
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
