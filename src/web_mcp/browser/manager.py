from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from typing import Any

from playwright.sync_api import BrowserContext, Page

from web_mcp.browser.snapshot import SnapshotEngine
from web_mcp.browser.stealth import BrowserConfig, launch_engine


class BrowserManager:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")
        self._exit_stack = ExitStack()
        self._context: BrowserContext | None = None
        self._pages: list[Page] = []
        self._active_tab: int = 0
        self._snapshot = SnapshotEngine()
        self._config = BrowserConfig()
        self._launched = False
        self._console_messages: list[dict[str, str]] = []
        self._network_requests: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # Async bridge — all sync Playwright calls go through this executor
    # ------------------------------------------------------------------

    async def execute(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, functools.partial(fn, *args, **kwargs)
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, **kwargs: Any) -> str:
        if self._launched:
            self._close_browser()

        for key, value in kwargs.items():
            if value is None:
                continue
            if not hasattr(self._config, key):
                raise ValueError(f"Unknown config option: {key}")
            setattr(self._config, key, value)

        return (
            f"Browser configured: engine={self._config.engine}, "
            f"headless={self._config.headless}"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def ensure_browser(self) -> Page:
        if not self._launched:
            self._launch()
        return self._active_page()

    def _launch(self) -> None:
        self._context = launch_engine(self._config, self._exit_stack)
        self._console_messages.clear()
        self._network_requests.clear()

        page = self._context.new_page()
        self._attach_listeners(page)
        self._pages.append(page)
        self._active_tab = 0
        self._launched = True

    def _attach_listeners(self, page: Page) -> None:
        page.on(
            "console",
            lambda msg: self._console_messages.append(
                {"level": msg.type, "text": msg.text}
            ),
        )
        page.on(
            "request",
            lambda req: self._network_requests.append(
                {"method": req.method, "url": req.url, "resource_type": req.resource_type}
            ),
        )

    def _active_page(self) -> Page:
        if not self._pages:
            raise RuntimeError("No pages open. Call browser_navigate first.")
        return self._pages[self._active_tab]

    async def shutdown(self) -> None:
        """Async shutdown: close browser on executor thread, then shut down executor."""
        if self._launched:
            await self.execute(self._close_browser)
        self._executor.shutdown(wait=True)

    def close(self) -> None:
        """Sync close — only call from the same thread that launched the browser."""
        if self._launched:
            self._close_browser()
        self._executor.shutdown(wait=False)

    def _close_browser(self) -> None:
        self._exit_stack.close()
        self._exit_stack = ExitStack()
        self._context = None
        self._pages.clear()
        self._active_tab = 0
        self._console_messages.clear()
        self._network_requests.clear()
        self._snapshot = SnapshotEngine()
        self._launched = False

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, url: str) -> str:
        page = self.ensure_browser()
        resp = page.goto(url, wait_until="domcontentloaded")
        status = resp.status if resp else "unknown"
        return f"Navigated to {url} (status: {status})\nTitle: {page.title()}"

    def go_back(self) -> str:
        page = self.ensure_browser()
        page.go_back(wait_until="domcontentloaded")
        return f"Navigated back\nURL: {page.url}\nTitle: {page.title()}"

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> str:
        page = self.ensure_browser()
        return self._snapshot.take_snapshot(page)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, full_page: bool = False, ref: int | None = None) -> bytes:
        page = self.ensure_browser()
        if ref is not None:
            elem = self._snapshot.resolve_ref(page, ref)
            return elem.screenshot()
        return page.screenshot(full_page=full_page)

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def click(
        self,
        ref: int,
        button: str = "left",
        double_click: bool = False,
        modifiers: list[str] | None = None,
    ) -> str:
        page = self.ensure_browser()
        locator = self._snapshot.resolve_ref(page, ref)
        kw: dict[str, Any] = {"button": button}
        if modifiers:
            kw["modifiers"] = modifiers
        if double_click:
            locator.dblclick(**kw)
        else:
            locator.click(**kw)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        return f"Clicked ref={ref}\nURL: {page.url}\nTitle: {page.title()}"

    def type_text(
        self, ref: int, text: str, submit: bool = False, slowly: bool = False
    ) -> str:
        page = self.ensure_browser()
        locator = self._snapshot.resolve_ref(page, ref)
        delay = 50 if slowly else 0
        locator.press_sequentially(text, delay=delay)
        if submit:
            locator.press("Enter")
        return f"Typed into ref={ref}"

    def fill_form(self, fields: list[dict[str, Any]]) -> str:
        page = self.ensure_browser()
        filled: list[str] = []
        for f in fields:
            locator = self._snapshot.resolve_ref(page, f["ref"])
            ftype = f.get("type", "textbox")
            value = f["value"]

            if ftype in ("textbox", "searchbox"):
                locator.fill(value)
            elif ftype == "checkbox":
                locator.check() if value else locator.uncheck()
            elif ftype == "radio":
                locator.check()
            elif ftype == "combobox":
                locator.select_option(value)
            elif ftype == "slider":
                locator.fill(str(value))

            filled.append(f"ref={f['ref']} ({ftype})")

        return f"Filled {len(filled)} fields: {', '.join(filled)}"

    def select_option(self, ref: int, values: list[str]) -> str:
        page = self.ensure_browser()
        locator = self._snapshot.resolve_ref(page, ref)
        locator.select_option(values)
        return f"Selected {values} on ref={ref}"

    def hover(self, ref: int) -> str:
        page = self.ensure_browser()
        self._snapshot.resolve_ref(page, ref).hover()
        return f"Hovering over ref={ref}"

    def drag(self, start_ref: int, end_ref: int) -> str:
        page = self.ensure_browser()
        src = self._snapshot.resolve_ref(page, start_ref)
        dst = self._snapshot.resolve_ref(page, end_ref)
        src.drag_to(dst)
        return f"Dragged ref={start_ref} -> ref={end_ref}"

    def press_key(self, key: str) -> str:
        page = self.ensure_browser()
        page.keyboard.press(key)
        return f"Pressed key: {key}"

    def evaluate(self, expression: str, ref: int | None = None) -> str:
        page = self.ensure_browser()
        if ref is not None:
            result = self._snapshot.resolve_ref(page, ref).evaluate(expression)
        else:
            result = page.evaluate(expression)
        return str(result)

    def wait_for(
        self,
        time_seconds: float | None = None,
        text: str | None = None,
        selector: str | None = None,
    ) -> str:
        page = self.ensure_browser()
        if time_seconds is not None:
            page.wait_for_timeout(int(time_seconds * 1000))
            return f"Waited {time_seconds}s"
        if text is not None:
            page.get_by_text(text).wait_for(state="visible", timeout=30_000)
            return f"Text appeared: {text!r}"
        if selector is not None:
            page.wait_for_selector(selector, timeout=30_000)
            return f"Selector matched: {selector}"
        return "Nothing to wait for (provide time_seconds, text, or selector)."

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def list_tabs(self) -> str:
        lines: list[str] = []
        for i, page in enumerate(self._pages):
            marker = " (active)" if i == self._active_tab else ""
            lines.append(f"[{i}] {page.title()} — {page.url}{marker}")
        return "\n".join(lines) or "(no tabs)"

    def new_tab(self, url: str | None = None) -> str:
        self.ensure_browser()
        assert self._context is not None
        page = self._context.new_page()
        self._attach_listeners(page)
        self._pages.append(page)
        self._active_tab = len(self._pages) - 1
        if url:
            page.goto(url, wait_until="domcontentloaded")
        return f"Opened tab [{self._active_tab}]"

    def close_tab(self, index: int | None = None) -> str:
        idx = index if index is not None else self._active_tab
        if not (0 <= idx < len(self._pages)):
            return f"Invalid tab index: {idx}"
        self._pages[idx].close()
        self._pages.pop(idx)
        if self._active_tab >= len(self._pages):
            self._active_tab = max(0, len(self._pages) - 1)
        return f"Closed tab [{idx}]. Active tab: [{self._active_tab}]"

    def select_tab(self, index: int) -> str:
        if not (0 <= index < len(self._pages)):
            return f"Invalid tab index: {index}"
        self._active_tab = index
        p = self._pages[index]
        return f"Switched to tab [{index}]: {p.title()} — {p.url}"

    # ------------------------------------------------------------------
    # Viewport / Upload / Dialog
    # ------------------------------------------------------------------

    def resize(self, width: int, height: int) -> str:
        page = self.ensure_browser()
        page.set_viewport_size({"width": width, "height": height})
        return f"Resized viewport to {width}x{height}"

    def file_upload(self, ref: int, paths: list[str]) -> str:
        page = self.ensure_browser()
        locator = self._snapshot.resolve_ref(page, ref)
        locator.set_input_files(paths)
        return f"Uploaded {len(paths)} file(s) to ref={ref}"

    def handle_dialog(self, accept: bool, prompt_text: str | None = None) -> str:
        page = self.ensure_browser()

        def _handler(dialog: Any) -> None:
            if accept:
                dialog.accept(prompt_text or "")
            else:
                dialog.dismiss()
            page.remove_listener("dialog", _handler)

        page.on("dialog", _handler)
        return f"Dialog handler set: will {'accept' if accept else 'dismiss'} next dialog"

    # ------------------------------------------------------------------
    # Console / Network / HTML
    # ------------------------------------------------------------------

    def get_console_messages(self, level: str = "info") -> str:
        severity = {"error": 0, "warning": 1, "log": 2, "info": 2, "debug": 3}
        threshold = severity.get(level, 2)
        filtered = [
            m for m in self._console_messages if severity.get(m["level"], 3) <= threshold
        ]
        if not filtered:
            return "(no console messages)"
        return "\n".join(f"[{m['level']}] {m['text']}" for m in filtered[-200:])

    def get_network_requests(self) -> str:
        if not self._network_requests:
            return "(no network requests)"
        return "\n".join(
            f"{r['method']} {r['url']} ({r['resource_type']})"
            for r in self._network_requests[-200:]
        )

    def get_html(self) -> str:
        page = self.ensure_browser()
        return page.content()
