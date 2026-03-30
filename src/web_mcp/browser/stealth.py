from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext


ENGINE_NAMES = ("playwright", "camoufox", "cloakbrowser")
BROWSER_TYPES = ("chromium", "firefox", "webkit")


@dataclass
class BrowserConfig:
    engine: Literal["playwright", "camoufox", "cloakbrowser"] = "playwright"
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    proxy: dict[str, str] | None = None
    geoip: bool | str = False
    humanize: bool | float = False
    locale: str | None = None
    viewport: dict[str, int] | None = None
    user_agent: str | None = None
    extra_args: list[str] = field(default_factory=list)


def launch_engine(config: BrowserConfig, exit_stack: ExitStack) -> BrowserContext:
    launchers = {
        "playwright": _launch_playwright,
        "camoufox": _launch_camoufox,
        "cloakbrowser": _launch_cloakbrowser,
    }
    launcher = launchers.get(config.engine)
    if launcher is None:
        raise ValueError(f"Unknown engine: {config.engine!r}. Choose from {ENGINE_NAMES}")
    return launcher(config, exit_stack)


def _launch_playwright(config: BrowserConfig, exit_stack: ExitStack) -> BrowserContext:
    from playwright.sync_api import sync_playwright

    pw = exit_stack.enter_context(sync_playwright())
    engine = getattr(pw, config.browser_type)

    launch_kwargs: dict[str, Any] = {"headless": config.headless}
    if config.proxy:
        launch_kwargs["proxy"] = config.proxy
    if config.extra_args:
        launch_kwargs["args"] = config.extra_args

    browser = engine.launch(**launch_kwargs)
    exit_stack.callback(browser.close)

    ctx_kwargs: dict[str, Any] = {}
    if config.viewport:
        ctx_kwargs["viewport"] = config.viewport
    if config.user_agent:
        ctx_kwargs["user_agent"] = config.user_agent
    if config.locale:
        ctx_kwargs["locale"] = config.locale

    context = browser.new_context(**ctx_kwargs)
    exit_stack.callback(context.close)
    return context


def _launch_camoufox(config: BrowserConfig, exit_stack: ExitStack) -> BrowserContext:
    from camoufox.sync_api import Camoufox

    kwargs: dict[str, Any] = {"headless": config.headless}
    if config.proxy:
        kwargs["proxy"] = config.proxy
    if config.geoip:
        kwargs["geoip"] = config.geoip
    if config.humanize:
        kwargs["humanize"] = config.humanize
    if config.locale:
        kwargs["locale"] = config.locale
    if config.viewport:
        kwargs["window"] = (config.viewport["width"], config.viewport["height"])
    if config.extra_args:
        kwargs["args"] = config.extra_args

    context = exit_stack.enter_context(Camoufox(**kwargs))
    return context


def _launch_cloakbrowser(config: BrowserConfig, exit_stack: ExitStack) -> BrowserContext:
    from cloakbrowser import launch

    launch_kwargs: dict[str, Any] = {"headless": config.headless}
    if config.proxy:
        server = config.proxy.get("server", "")
        username = config.proxy.get("username")
        if username:
            password = config.proxy.get("password", "")
            scheme, rest = server.split("://", 1)
            server = f"{scheme}://{username}:{password}@{rest}"
        launch_kwargs["proxy"] = server
    if config.humanize:
        launch_kwargs["humanize"] = True

    browser = launch(**launch_kwargs)
    exit_stack.callback(browser.close)

    ctx_kwargs: dict[str, Any] = {}
    if config.viewport:
        ctx_kwargs["viewport"] = config.viewport
    if config.locale:
        ctx_kwargs["locale"] = config.locale

    context = browser.new_context(**ctx_kwargs)
    exit_stack.callback(context.close)
    return context
