from __future__ import annotations

import asyncio

from fastmcp import Context

from web_mcp.server import mcp

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@mcp.tool
async def html_to_markdown(
    html: str,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Convert an HTML string to Markdown as-is (preserves the full page structure).

    This performs a faithful structural conversion — no content is stripped.
    Use extract_article instead if you want to pull just the article body.
    """

    def _convert():
        from markdownify import markdownify as md

        return md(html, heading_style="ATX", strip=["script", "style"])

    return await asyncio.to_thread(_convert)


@mcp.tool
async def extract_article(
    html: str,
    include_links: bool = True,
    include_images: bool = True,
    include_tables: bool = True,
    include_comments: bool = False,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Extract article content from HTML and convert to Markdown.

    Strips navigation, ads, sidebars, and other clutter. Returns clean Markdown
    plus metadata (title, author, date) when available.
    """

    def _extract():
        import trafilatura

        markdown = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=include_links,
            include_images=include_images,
            include_tables=include_tables,
            include_comments=include_comments,
            include_formatting=True,
        )
        metadata = trafilatura.bare_extraction(html)
        return markdown, metadata

    markdown, metadata = await asyncio.to_thread(_extract)

    if not markdown:
        return "No article content found on this page."

    parts: list[str] = []
    if metadata:
        title = getattr(metadata, "title", None)
        if title:
            parts.append(f"# {title}")
        meta_bits: list[str] = []
        if getattr(metadata, "author", None):
            meta_bits.append(f"Author: {metadata.author}")
        if getattr(metadata, "date", None):
            meta_bits.append(f"Date: {metadata.date}")
        if meta_bits:
            parts.append(" | ".join(meta_bits))
        if parts:
            parts.append("---")

    parts.append(markdown)
    return "\n\n".join(parts)


@mcp.tool
async def fetch_raw_page_as_html(
    url: str,
    headers: dict[str, str] | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Fetch a URL via HTTP and return the raw HTML. 
    [!] DO NOT use this tool unless you absolutely need the raw HTML. 
        In most cases, using `fetch_as_markdown` is the right way to go.
        The output of this tool may be extremely long, use it only when truly required.

    This is a lightweight fetch (no JavaScript rendering). For JS-heavy pages,
    use browser_navigate + browser_get_html instead.
    """
    import httpx

    merged = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers=merged)
        resp.raise_for_status()
        return resp.text


@mcp.tool
async def fetch_as_markdown(
    url: str,
    headers: dict[str, str] | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Fetch a URL and convert the full HTML to Markdown (as-is, no content filtering).

    Combines fetch_page + html_to_markdown in one call.
    """
    import httpx
    from markdownify import markdownify as md

    merged = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers=merged)
        resp.raise_for_status()
        html = resp.text

    return await asyncio.to_thread(
        md, html, heading_style="ATX", strip=["script", "style"]
    )


@mcp.tool
async def fetch_article(
    url: str,
    include_links: bool = True,
    include_images: bool = True,
    headers: dict[str, str] | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Fetch a URL and extract the article to Markdown.
    Use this tool when accessing news articles, blog-posts or similar content.
    In other cases it may return empty or partial results.

    Combines fetch_page + extract_article in one call. Returns clean Markdown
    with metadata.
    """
    import httpx
    import trafilatura

    merged = {**DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers=merged)
        resp.raise_for_status()
        html = resp.text

    def _extract():
        markdown = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=include_links,
            include_images=include_images,
            include_tables=True,
            include_formatting=True,
        )
        metadata = trafilatura.bare_extraction(html)
        return markdown, metadata

    markdown, metadata = await asyncio.to_thread(_extract)

    if not markdown:
        return f"No article content found at {url}"

    parts: list[str] = []
    if metadata:
        title = getattr(metadata, "title", None)
        if title:
            parts.append(f"# {title}")
        meta_bits: list[str] = []
        if getattr(metadata, "author", None):
            meta_bits.append(f"Author: {metadata.author}")
        if getattr(metadata, "date", None):
            meta_bits.append(f"Date: {metadata.date}")
        if meta_bits:
            parts.append(" | ".join(meta_bits))
        if parts:
            parts.append("---")

    parts.append(markdown)
    return "\n\n".join(parts)
