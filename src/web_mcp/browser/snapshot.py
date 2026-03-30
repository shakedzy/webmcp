from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Locator, Page

INTERACTIVE_ROLES = frozenset({
    "button", "checkbox", "combobox", "link", "menuitem", "menuitemcheckbox",
    "menuitemradio", "option", "radio", "scrollbar", "searchbox", "slider",
    "spinbutton", "switch", "tab", "textbox", "treeitem",
})

NOTABLE_ROLES = frozenset({
    "heading", "img", "figure", "alert", "dialog", "table",
    "cell", "columnheader", "rowheader",
})

# Matches lines like: "  - role "name" [attrs]:" or "  - role:"
_NODE_RE = re.compile(r"^(\s*)-\s+(\w+)(?:\s+\"([^\"]*)\")?(.*?)$")


class SnapshotEngine:
    def __init__(self) -> None:
        self._ref_counter: int = 0
        self._ref_map: dict[int, dict[str, Any]] = {}
        self._role_occurrence: dict[tuple[str, str], int] = {}

    @property
    def has_refs(self) -> bool:
        return bool(self._ref_map)

    def take_snapshot(self, page: Page) -> str:
        """Take an ARIA accessibility snapshot and annotate interactive elements with ref numbers."""
        self._ref_counter = 0
        self._ref_map.clear()
        self._role_occurrence.clear()

        raw = page.locator(":root").aria_snapshot()
        if not raw:
            return "(empty page)"

        header = f"URL: {page.url}\nTitle: {page.title()}\n---"
        output_lines: list[str] = []

        for line in raw.split("\n"):
            m = _NODE_RE.match(line)
            if not m:
                output_lines.append(line)
                continue

            indent, role, name, rest = m.groups()
            name = name or ""

            should_ref = role in INTERACTIVE_ROLES or (role in NOTABLE_ROLES and name)

            if should_ref:
                self._ref_counter += 1
                ref = self._ref_counter

                key = (role, name)
                nth = self._role_occurrence.get(key, 0)
                self._role_occurrence[key] = nth + 1
                self._ref_map[ref] = {"role": role, "name": name, "nth": nth}

                name_part = f' "{name}"' if name else ""
                output_lines.append(f"{indent}- [{ref}] {role}{name_part}{rest}")
            else:
                output_lines.append(line)

        return header + "\n" + "\n".join(output_lines)

    def resolve_ref(self, page: Page, ref: int) -> Locator:
        if ref not in self._ref_map:
            raise ValueError(
                f"Unknown ref {ref}. Take a fresh snapshot with browser_snapshot first."
            )
        info = self._ref_map[ref]
        role: str = info["role"]
        name: str = info["name"]
        nth: int = info["nth"]

        kwargs: dict[str, Any] = {}
        if name:
            kwargs["name"] = name
            kwargs["exact"] = True

        locator = page.get_by_role(role, **kwargs)
        return locator.nth(nth)
