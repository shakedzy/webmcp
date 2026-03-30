from __future__ import annotations

import base64
from typing import Literal

from fastmcp import Context

from web_mcp.server import mcp


def _mgr(ctx: Context):
    return ctx.lifespan_context["browser_manager"]


@mcp.tool
async def browser_configure(
    engine: Literal["playwright", "camoufox", "cloakbrowser"] = "playwright",
    headless: bool = True,
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium",
    proxy_server: str | None = None,
    proxy_username: str | None = None,
    proxy_password: str | None = None,
    geoip: bool = False,
    humanize: bool = False,
    locale: str | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    user_agent: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Configure the browser engine and stealth options. Call before navigating.

    Engines:
      - playwright: vanilla Playwright (chromium/firefox/webkit). Set user_agent manually.
      - camoufox: Firefox stealth with auto-generated fingerprints. Use geoip=True with a proxy.
      - cloakbrowser: Chromium stealth (passes Cloudflare). Use humanize=True for human-like input.

    The browser launches automatically on the first navigation. Re-calling this closes the
    current browser and applies the new config.
    """
    mgr = _mgr(ctx)
    proxy = None
    if proxy_server:
        proxy = {"server": proxy_server}
        if proxy_username:
            proxy["username"] = proxy_username
            proxy["password"] = proxy_password or ""
    viewport = None
    if viewport_width and viewport_height:
        viewport = {"width": viewport_width, "height": viewport_height}

    return await mgr.execute(
        mgr.configure,
        engine=engine,
        headless=headless,
        browser_type=browser_type,
        proxy=proxy,
        geoip=geoip,
        humanize=humanize,
        locale=locale,
        viewport=viewport,
        user_agent=user_agent,
    )


@mcp.tool
async def browser_navigate(url: str, ctx: Context = None) -> str:  # type: ignore[assignment]
    """Navigate the browser to a URL. Launches the browser if not already running."""
    return await _mgr(ctx).execute(_mgr(ctx).navigate, url)


@mcp.tool
async def browser_navigate_back(ctx: Context = None) -> str:  # type: ignore[assignment]
    """Go back to the previous page in browser history."""
    return await _mgr(ctx).execute(_mgr(ctx).go_back)


@mcp.tool
async def browser_snapshot(ctx: Context = None) -> str:  # type: ignore[assignment]
    """Get an accessibility snapshot of the current page.

    Returns a text tree of page elements. Interactive elements are labeled with
    [ref] numbers that can be used in other browser tools (click, type, etc.).
    Always call this before interacting with elements.
    """
    return await _mgr(ctx).execute(_mgr(ctx).snapshot)


@mcp.tool
async def browser_take_screenshot(
    full_page: bool = False,
    ref: int | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Take a screenshot of the page or a specific element.

    Returns a base64-encoded PNG image.
    """
    mgr = _mgr(ctx)
    img = await mgr.execute(mgr.screenshot, full_page=full_page, ref=ref)
    encoded = base64.b64encode(img).decode()
    return f"data:image/png;base64,{encoded}"


@mcp.tool
async def browser_click(
    ref: int,
    button: Literal["left", "right", "middle"] = "left",
    double_click: bool = False,
    modifiers: list[str] | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Click a page element identified by its ref number from browser_snapshot.

    Modifiers can include 'Alt', 'Control', 'Meta', 'Shift'.
    """
    return await _mgr(ctx).execute(
        _mgr(ctx).click,
        ref=ref,
        button=button,
        double_click=double_click,
        modifiers=modifiers,
    )


@mcp.tool
async def browser_type(
    ref: int,
    text: str,
    submit: bool = False,
    slowly: bool = False,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Type text into a page element (appends to existing text).

    Set submit=True to press Enter after typing. Set slowly=True for human-like speed.
    """
    return await _mgr(ctx).execute(
        _mgr(ctx).type_text, ref=ref, text=text, submit=submit, slowly=slowly
    )


@mcp.tool
async def browser_fill_form(
    fields_json: str,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Fill multiple form fields at once.

    fields_json: a JSON array of objects, each with:
      - ref (int): element ref from browser_snapshot
      - value (str): value to set
      - type (str, optional): "textbox" | "checkbox" | "radio" | "combobox" | "slider"
        (defaults to "textbox")

    Example: [{"ref": 3, "value": "Alice"}, {"ref": 5, "value": "true", "type": "checkbox"}]
    """
    import json

    fields = json.loads(fields_json)
    return await _mgr(ctx).execute(_mgr(ctx).fill_form, fields)


@mcp.tool
async def browser_select_option(
    ref: int,
    values: list[str],
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Select one or more options in a <select> dropdown by their values."""
    return await _mgr(ctx).execute(_mgr(ctx).select_option, ref=ref, values=values)


@mcp.tool
async def browser_hover(ref: int, ctx: Context = None) -> str:  # type: ignore[assignment]
    """Hover over a page element identified by its ref number."""
    return await _mgr(ctx).execute(_mgr(ctx).hover, ref)


@mcp.tool
async def browser_drag(
    start_ref: int,
    end_ref: int,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Drag an element and drop it onto another element."""
    return await _mgr(ctx).execute(_mgr(ctx).drag, start_ref, end_ref)


@mcp.tool
async def browser_press_key(
    key: str, ctx: Context = None  # type: ignore[assignment]
) -> str:
    """Press a keyboard key (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown', 'a')."""
    return await _mgr(ctx).execute(_mgr(ctx).press_key, key)


@mcp.tool
async def browser_evaluate(
    expression: str,
    ref: int | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Execute JavaScript on the page and return the result.

    If ref is provided, the expression receives the element as its first argument
    (use `element => element.textContent` style arrow functions).
    """
    return await _mgr(ctx).execute(
        _mgr(ctx).evaluate, expression=expression, ref=ref
    )


@mcp.tool
async def browser_wait_for(
    time_seconds: float | None = None,
    text: str | None = None,
    selector: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Wait for a condition: a number of seconds, specific text to appear, or a CSS selector."""
    return await _mgr(ctx).execute(
        _mgr(ctx).wait_for,
        time_seconds=time_seconds,
        text=text,
        selector=selector,
    )


@mcp.tool
async def browser_tabs(
    action: Literal["list", "new", "close", "select"],
    index: int | None = None,
    url: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Manage browser tabs.

    Actions:
      - list: show all open tabs
      - new: open a new tab (optionally navigate to url)
      - close: close tab at index (default: active tab)
      - select: switch to tab at index
    """
    mgr = _mgr(ctx)
    if action == "list":
        return await mgr.execute(mgr.list_tabs)
    elif action == "new":
        return await mgr.execute(mgr.new_tab, url)
    elif action == "close":
        return await mgr.execute(mgr.close_tab, index)
    elif action == "select":
        if index is None:
            return "Error: index is required for 'select' action"
        return await mgr.execute(mgr.select_tab, index)
    return f"Unknown action: {action}"


@mcp.tool
async def browser_resize(
    width: int,
    height: int,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Resize the browser viewport."""
    return await _mgr(ctx).execute(_mgr(ctx).resize, width, height)


@mcp.tool
async def browser_file_upload(
    ref: int,
    paths: list[str],
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Upload file(s) to a file input element. Paths must be absolute."""
    return await _mgr(ctx).execute(_mgr(ctx).file_upload, ref, paths)


@mcp.tool
async def browser_handle_dialog(
    accept: bool,
    prompt_text: str | None = None,
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Set up a handler for the next browser dialog (alert/confirm/prompt).

    Call this BEFORE the action that triggers the dialog.
    """
    return await _mgr(ctx).execute(
        _mgr(ctx).handle_dialog, accept=accept, prompt_text=prompt_text
    )


@mcp.tool
async def browser_console_messages(
    level: Literal["error", "warning", "info", "debug"] = "info",
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Get console messages from the browser. Each level includes more severe levels."""
    return await _mgr(ctx).execute(_mgr(ctx).get_console_messages, level)


@mcp.tool
async def browser_network_requests(
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Get the network request log since the page was loaded."""
    return await _mgr(ctx).execute(_mgr(ctx).get_network_requests)


@mcp.tool
async def browser_get_html(
    ctx: Context = None,  # type: ignore[assignment]
) -> str:
    """Get the full HTML source of the current page."""
    return await _mgr(ctx).execute(_mgr(ctx).get_html)


@mcp.tool
async def browser_close(ctx: Context = None) -> str:  # type: ignore[assignment]
    """Close the browser and free resources. The browser can be re-launched by navigating again."""
    mgr = _mgr(ctx)
    if mgr._launched:
        await mgr.execute(mgr._close_browser)
    return "Browser closed."
