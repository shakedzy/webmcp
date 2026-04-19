"""Comprehensive test for web-mcp: browser, search, and content tools."""

import asyncio
import sys
import traceback

from web_mcp.browser.manager import BrowserManager

PASS = 0
FAIL = 0


def result(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))


async def test_browser():
    print("\n=== Browser Tools ===")
    mgr = BrowserManager()
    try:
        # 1. Configure
        r = await mgr.execute(mgr.configure, engine="playwright", headless=True)
        result("configure", "configured" in r.lower(), r)

        # 2. Navigate
        r = await mgr.execute(mgr.navigate, "https://example.com")
        result("navigate", "Example Domain" in r, r.split("\n")[0])

        # 3. Snapshot with refs
        snap = await mgr.execute(mgr.snapshot)
        has_refs = "[1]" in snap and "[2]" in snap
        result("snapshot", has_refs, f"{snap.count('[')//2} refs found")

        # 4. Click (ref 2 = Learn more)
        r = await mgr.execute(mgr.click, ref=2)
        result("click", "iana.org" in r.lower(), r.split("\n")[0])

        # 5. Go back
        r = await mgr.execute(mgr.go_back)
        result("go_back", "example.com" in r.lower(), r.split("\n")[0])

        # 6. Re-snapshot after going back
        snap2 = await mgr.execute(mgr.snapshot)
        result("snapshot_after_back", "Example Domain" in snap2)

        # 7. Evaluate JS
        r = await mgr.execute(mgr.evaluate, "document.title")
        result("evaluate", "Example Domain" in r, f"title={r}")

        # 8. Get HTML
        html = await mgr.execute(mgr.get_html)
        result("get_html", "<html" in html.lower(), f"{len(html)} chars")

        # 9. Screenshot
        img = await mgr.execute(mgr.screenshot, full_page=False)
        result("screenshot", len(img) > 1000, f"{len(img)} bytes PNG")

        # 10. Tabs — new
        r = await mgr.execute(mgr.new_tab, "https://example.com")
        result("new_tab", "tab" in r.lower(), r)

        # 11. Tabs — list
        r = await mgr.execute(mgr.list_tabs)
        result("list_tabs", r.count("[") >= 2, f"{r.count(chr(10))+1} tabs")

        # 12. Tabs — select
        r = await mgr.execute(mgr.select_tab, 0)
        result("select_tab", "tab" in r.lower(), r)

        # 13. Tabs — close
        r = await mgr.execute(mgr.close_tab, 1)
        result("close_tab", "closed" in r.lower(), r)

        # 14. Resize
        r = await mgr.execute(mgr.resize, 800, 600)
        result("resize", "800" in r, r)

        # 15. Press key
        r = await mgr.execute(mgr.press_key, "Tab")
        result("press_key", "Tab" in r, r)

        # 16. Wait
        r = await mgr.execute(mgr.wait_for, time_seconds=0.5)
        result("wait_for", "waited" in r.lower(), r)

        # 17. Console messages
        r = await mgr.execute(mgr.get_console_messages, "info")
        result("console_messages", True, r[:60])

        # 18. Network requests
        r = await mgr.execute(mgr.get_network_requests)
        result("network_requests", True, f"{r.count(chr(10))+1} entries")

        # 19. Navigate to a form page to test type
        await mgr.execute(
            mgr.evaluate,
            """document.body.innerHTML = '<input id="q" type="text" aria-label="Search"><button>Go</button>'""",
        )
        snap3 = await mgr.execute(mgr.snapshot)
        result("inject_form", "textbox" in snap3.lower(), "form injected")

        # 20. Type into the search box (ref 1 should be the textbox)
        r = await mgr.execute(mgr.type_text, ref=1, text="hello", submit=False)
        result("type_text", "typed" in r.lower(), r)

        # 21. Close/relaunch cycle
        await mgr.execute(mgr._close_browser)
        r = await mgr.execute(mgr.navigate, "https://example.com")
        result("close_relaunch", "Example Domain" in r, "browser relaunched OK")

    except Exception as e:
        result("BROWSER_ERROR", False, f"{e}")
        traceback.print_exc()
    finally:
        await mgr.shutdown()


async def test_search():
    print("\n=== Search Tools ===")
    from ddgs import DDGS

    backends = ["duckduckgo", "bing", "brave", "google"]
    for backend in backends:
        try:
            with DDGS() as ddgs:
                results = ddgs.text("python programming", max_results=3, backend=backend)
            ok = len(results) > 0
            result(f"web_search ({backend})", ok, f"{len(results)} results")
            if ok:
                break
        except Exception as e:
            result(f"web_search ({backend})", False, str(e)[:80])

    # News search
    try:
        with DDGS() as ddgs:
            results = ddgs.news("technology", max_results=3)
        result("news_search", len(results) > 0, f"{len(results)} results")
    except Exception as e:
        result("news_search", False, str(e)[:80])

    # Image search
    try:
        with DDGS() as ddgs:
            results = ddgs.images("sunset", max_results=3)
        result("image_search", len(results) > 0, f"{len(results)} results")
    except Exception as e:
        result("image_search", False, str(e)[:80])


async def test_content():
    print("\n=== Content Tools ===")

    sample_html = """<!DOCTYPE html><html><head><title>Test Article</title>
    <meta name="author" content="Jane Doe"></head>
    <body>
    <nav><a href="/">Home</a> | <a href="/about">About</a></nav>
    <article>
    <h1>The Future of AI in 2026</h1>
    <p>Published by Jane Doe on March 29, 2026.</p>
    <p>Artificial intelligence continues to reshape industries worldwide.
    From healthcare to finance, the impact is profound.</p>
    <p>Key developments include:</p>
    <ul>
    <li>Large language models becoming more capable</li>
    <li>AI-assisted coding tools reaching mainstream adoption</li>
    <li>Autonomous systems gaining regulatory approval</li>
    </ul>
    <p>Read the <a href="https://example.com/full">full report</a> for details.</p>
    <img src="https://example.com/ai.jpg" alt="AI illustration">
    </article>
    <footer>Copyright 2026</footer>
    </body></html>"""

    # 1. html_to_markdown (markdownify)
    try:
        from markdownify import markdownify as md

        r = await asyncio.to_thread(md, sample_html, heading_style="ATX", strip=["script", "style"])
        ok = "# The Future" in r and "* Large language" in r or "- Large language" in r
        result("html_to_markdown", ok, f"{len(r)} chars, has heading + list")
    except Exception as e:
        result("html_to_markdown", False, str(e)[:80])

    # 2. extract_article (trafilatura)
    try:
        import trafilatura

        r = await asyncio.to_thread(
            trafilatura.extract,
            sample_html,
            output_format="markdown",
            include_links=True,
            include_formatting=True,
        )
        ok = r is not None and "AI" in r
        result("extract_article", ok, f"{len(r) if r else 0} chars")
    except Exception as e:
        result("extract_article", False, str(e)[:80])

    # 3. bare_extraction (metadata)
    try:
        import trafilatura

        meta = await asyncio.to_thread(trafilatura.bare_extraction, sample_html)
        title = getattr(meta, "title", None)
        result("bare_extraction", meta is not None, f"title={title}")
    except Exception as e:
        result("bare_extraction", False, str(e)[:80])

    # 4. fetch_page via httpx (verify=False due to env SSL issue)
    try:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=15, verify=False) as client:
            resp = await client.get("https://example.com")
        ok = resp.status_code == 200 and "<html" in resp.text.lower()
        result("fetch_page (httpx)", ok, f"status={resp.status_code}, {len(resp.text)} chars")
    except Exception as e:
        result("fetch_page (httpx)", False, str(e)[:80])

    # 5. fetch + markdownify (as-is)
    try:
        import httpx
        from markdownify import markdownify as md

        async with httpx.AsyncClient(follow_redirects=True, timeout=15, verify=False) as client:
            resp = await client.get("https://example.com")
        r = await asyncio.to_thread(md, resp.text, heading_style="ATX", strip=["script", "style"])
        ok = "Example Domain" in r
        result("fetch_as_markdown", ok, f"{len(r)} chars")
    except Exception as e:
        result("fetch_as_markdown", False, str(e)[:80])

    # 6. fetch + trafilatura (article extraction)
    try:
        import httpx
        import trafilatura

        async with httpx.AsyncClient(follow_redirects=True, timeout=15, verify=False) as client:
            resp = await client.get("https://example.com")
        r = await asyncio.to_thread(
            trafilatura.extract, resp.text, output_format="markdown", include_links=True
        )
        result("fetch_article", r is not None, f"{len(r) if r else 0} chars")
    except Exception as e:
        result("fetch_article", False, str(e)[:80])


async def test_mcp_registration():
    print("\n=== MCP Server Registration ===")
    from web_mcp.server import mcp

    tools = await mcp.list_tools()
    tool_names = sorted(t.name for t in tools)

    expected_browser = [
        "browser_click", "browser_close", "browser_configure", "browser_console_messages",
        "browser_drag", "browser_evaluate", "browser_fill_form", "browser_get_as_markdown",
        "browser_get_html",
        "browser_handle_dialog", "browser_hover", "browser_navigate", "browser_navigate_back",
        "browser_network_requests", "browser_press_key", "browser_resize",
        "browser_select_option", "browser_snapshot", "browser_tabs",
        "browser_take_screenshot", "browser_type", "browser_wait_for", "browser_file_upload",
    ]
    expected_search = ["web_search", "news_search", "image_search"]
    expected_content = ["html_to_markdown", "extract_article", "fetch_page", "fetch_as_markdown", "fetch_article"]
    all_expected = expected_browser + expected_search + expected_content

    result("total_tool_count", len(tools) == 31, f"{len(tools)} tools")

    missing = [t for t in all_expected if t not in tool_names]
    result("all_tools_present", len(missing) == 0, f"missing: {missing}" if missing else "all present")

    for t in tools:
        has_desc = bool(t.description and len(t.description) > 10)
        if not has_desc:
            result(f"description({t.name})", False, "missing or short description")
            break
    else:
        result("all_descriptions", True, "all tools have descriptions")


async def main():
    await test_mcp_registration()
    await test_browser()
    await test_search()
    await test_content()

    print(f"\n{'='*50}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
    print(f"{'='*50}")
    return FAIL


if __name__ == "__main__":
    fails = asyncio.run(main())
    sys.exit(min(fails, 1))
