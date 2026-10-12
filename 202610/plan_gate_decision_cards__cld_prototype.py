"""Prototype: card-based Decisions rail swapped into the real PlanApprovalModal.

Usage: proto.py WIDTH HEIGHT OUT.png [--changed] [keys...]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

import sase.ace.tui.modals.plan_approval_modal_controls as controls_mod
import sase.ace.tui.modals.plan_approval_modal_view as view_mod
from sase.ace.tui.modals.plan_approval_modal import PlanApprovalModal
from sase.ace.tui.visual_render import render_svg_to_png
from textual.app import App

import os as _os
PLAN = Path(_os.environ.get("PROTO_PLAN", str(Path.home() / ".sase/plans/202610/retire_syncthing_and_relocate_sync_tree.md")))
DEFS = json.loads(
    PLAN.with_suffix("").with_suffix(".plan-decisions.json").read_text()
)["definitions"]

GOLD = "#FFD700"
ACCENT = "#5FD7FF"
MUTED = "#8A8A8A"


def _value_chip(row: dict[str, Any], *, focused: bool) -> Text:
    kind = str(row.get("kind", ""))
    value = row.get("value")
    changed = bool(row.get("changed"))
    chip = Text(no_wrap=True, justify="right")
    if focused:
        chip.append("‹ ", style=MUTED)
    if kind == "toggle":
        chip.append("☑ yes" if value is True else "☐ no", style="bold")
    else:
        chip.append(str(value), style=f"bold {GOLD}" if changed else "bold")
    chip.append(" ●" if changed else " ★", style=GOLD if changed else MUTED)
    if focused:
        chip.append(" ›", style=MUTED)
    return chip


def _header(row: dict[str, Any], *, focused: bool) -> Table:
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
    grid.add_column(justify="right", no_wrap=True)
    name = Text(no_wrap=True, overflow="ellipsis")
    if isinstance(row.get("memory"), dict):
        name.append("🧠 ")
    name.append(str(row.get("id", "")), style=f"bold {ACCENT}" if focused else "bold")
    grid.add_row(name, _value_chip(row, focused=focused))
    return grid


def collapsed(row: dict[str, Any], *, lines: int = 2, width: int = 0) -> Group:
    parts: list[Any] = [_header(row, focused=False)]
    if lines > 0:
        import textwrap
        ask = str(row.get("ask", "")).strip()
        wrapped = textwrap.wrap(ask, max(10, width)) if width else [ask]
        shown = wrapped[:lines]
        if len(wrapped) > lines:
            shown[-1] = shown[-1][: max(0, width - 1)].rstrip() + "…"
        parts.append(Text("\n".join(shown), style=MUTED, no_wrap=True, overflow="ellipsis"))
    return Group(*parts)


_PROV = {
    "asked": "on ★ — you asked",
    "not_asked": "off ★ — you did not ask for this edit",
    "quote_not_found": "off: the quoted request was not found",
    "inherited": "approved in the epic",
    "correction": "corrects the note",
}


def expanded_memory(row: dict[str, Any]) -> Group:
    parts: list[Any] = [_header(row, focused=True)]
    parts.append(Text(str(row.get("ask", "")).strip()))
    memory = row.get("memory") or {}
    resolved = [r for r in (memory.get("resolved") or []) if isinstance(r, dict)]
    grid = Table.grid(padding=(0, 2, 0, 0))
    grid.add_column(no_wrap=True)
    grid.add_column(ratio=1)
    for rec in resolved or [{"selector": s} for s in memory.get("selectors", [])]:
        target = Text(str(rec.get("selector", "")), style="bold")
        kind = str(rec.get("type") or rec.get("kind") or "")
        bits = [b for b in ("web strand" if kind in ("strand", "web") else kind,
                            str(rec.get("scope", "")),
                            "new" if rec.get("exists") is False else "edit") if b]
        target.append("  " + " · ".join(bits), style=MUTED)
        grid.add_row(Text("  edits", style=MUTED), target)
    prov = str(memory.get("provenance") or "")
    quote = memory.get("quote")
    why = Text(_PROV.get(prov, prov), style=f"italic {MUTED}")
    if prov == "asked" and isinstance(quote, str) and quote.strip():
        why.append(f': "{quote.strip()}"', style=f"italic {MUTED}")
    if prov == "quote_not_found":
        why.stylize("yellow")
    grid.add_row(Text("  default", style=f"italic {MUTED}"), why)
    parts.append(grid)
    return Group(*parts)


def expanded(row: dict[str, Any], width: int = 0) -> Group:
    if isinstance(row.get("memory"), dict) and str(row.get("kind")) == "toggle":
        return expanded_memory(row)
    if width and width < 60:
        return expanded_stacked(row)
    return expanded_grid(row)


def expanded_stacked(row: dict[str, Any]) -> Group:
    parts: list[Any] = [_header(row, focused=True)]
    parts.append(Text(str(row.get("ask", "")).strip()))
    value = row.get("value")
    default = row.get("default")
    kind = str(row.get("kind", ""))
    options = [
        (str(c.get("key", "")), str(c.get("label", "")))
        for c in row.get("choices", []) if isinstance(c, dict)
    ] if kind == "choice" else [("yes", ""), ("no", "")]
    for key, label in options:
        selected = (str(value) == key) if kind == "choice" else ((value is True) == (key == "yes"))
        is_default = (str(default) == key) if kind == "choice" else ((default is True) == (key == "yes"))
        grid = Table.grid(padding=0)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1)
        mark = Text("◉" if selected else "○", style=f"bold {ACCENT}" if selected else MUTED)
        head = Text()
        head.append(key, style="bold" if selected else MUTED)
        if is_default:
            head.append(" ★", style=MUTED)
        grid.add_row(mark, head)
        if label:
            grid.add_row(Text(""), Text(label, style="" if selected else MUTED))
        parts.append(grid)
    why = row.get("why")
    if isinstance(why, str) and why.strip():
        grid = Table.grid(padding=0)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1)
        grid.add_row(Text("★", style=MUTED), Text(f"why: {why.strip()}", style=f"italic {MUTED}"))
        parts.append(grid)
    return Group(*parts)


def expanded_grid(row: dict[str, Any]) -> Group:
    parts: list[Any] = [_header(row, focused=True)]
    parts.append(Text(str(row.get("ask", "")).strip()))
    parts.append(Text(""))
    grid = Table.grid(padding=(0, 2, 0, 0))
    grid.add_column(no_wrap=True)
    grid.add_column(ratio=1)
    value = row.get("value")
    default = row.get("default")
    kind = str(row.get("kind", ""))
    if kind == "choice":
        options = [
            (str(c.get("key", "")), str(c.get("label", "")))
            for c in row.get("choices", []) if isinstance(c, dict)
        ]
    else:
        options = [("yes", ""), ("no", "")]
    for key, label in options:
        selected = (str(value) == key) if kind == "choice" else (
            (value is True) == (key == "yes"))
        is_default = (str(default) == key) if kind == "choice" else (
            (default is True) == (key == "yes"))
        mark = Text(no_wrap=True)
        mark.append("◉ " if selected else "○ ", style=f"bold {ACCENT}" if selected else MUTED)
        mark.append(key, style="bold" if selected else MUTED)
        if is_default:
            mark.append(" ★", style=MUTED)
        grid.add_row(mark, Text(label, style="" if selected else MUTED))
    why = row.get("why")
    if isinstance(why, str) and why.strip():
        grid.add_row(Text(""), Text(""))
        grid.add_row(Text("  why ★", style=f"italic {MUTED}"),
                     Text(why.strip(), style=f"italic {MUTED}"))
    parts.append(grid)
    return Group(*parts)


class DecisionCard(Static, can_focus=True):
    DEFAULT_CSS = ""

    def on_resize(self) -> None:
        parent = self.parent
        if isinstance(parent, ProtoDecisionRows):
            parent.refresh_rows()


class ProtoDecisionRows(VerticalScroll):
    """Same interface as PlanDecisionRows; cards instead of Buttons."""

    collapsed_lines = 2

    def __init__(self, sheet_rows, definitions=None, *, id=None, classes=None):
        super().__init__(id=id, classes=classes)
        self._rows = list(sheet_rows)
        self._definitions = list(definitions or [])
        self._focused_index = 0 if self._rows else -1

    @property
    def focused_index(self) -> int:
        return self._focused_index

    @property
    def focused_id(self):
        if 0 <= self._focused_index < len(self._rows):
            return str(self._rows[self._focused_index].get("id", ""))
        return None

    def compose(self):
        for index, row in enumerate(self._rows):
            yield DecisionCard(self._render_row(index, row),
                               id=f"plan-decision-{index}", classes="decision-card")

    def _render_row(self, index, row):
        width = 0
        try:
            width = self.query_one(f"#plan-decision-{index}").content_size.width
        except Exception:
            width = 0
        if index == self._focused_index or ZOOM:
            return expanded(row, width)
        lines = self.collapsed_lines
        if self.app.size.width < 100 or COMPACT:
            lines = 0
        return collapsed(row, lines=lines, width=width)

    def refresh_rows(self) -> None:
        for index, row in enumerate(self._rows):
            try:
                card = self.query_one(f"#plan-decision-{index}", DecisionCard)
            except Exception:
                continue
            card.update(self._render_row(index, row))
            card.set_class(index == self._focused_index, "-current")
        try:
            self.query_one(f"#plan-decision-{self._focused_index}").scroll_visible(animate=False)
        except Exception:
            pass

    def on_mount(self) -> None:
        self.refresh_rows()

    def update_rows(self, sheet_rows) -> None:
        self._rows = list(sheet_rows)
        if self.is_mounted:
            self.refresh_rows()

    def rebuild(self, sheet_rows, definitions) -> None:
        self.update_rows(sheet_rows)

    def set_focused_index(self, index: int) -> None:
        if not self._rows:
            return
        self._focused_index = max(0, min(index, len(self._rows) - 1))
        if self.is_mounted:
            self.refresh_rows()

    def visible_control_ids(self):
        return [f"plan-decision-{index}" for index in range(len(self._rows))]


ZOOM = False
COMPACT = False

NARROW_CSS = """
PlanApprovalModal.-gate-review-narrow .gate-review-body > .gate-review-actions {
    height: 62%;
}
PlanApprovalModal .decision-card { margin: 0; }
"""

ZOOM_CSS = """
PlanApprovalModal .gate-review-body > .gate-review-actions--decisions {
    width: 100%;
    height: 1fr;
    dock: none;
}
PlanApprovalModal #plan-approval-scroll { display: none; }
PlanApprovalModal .decision-card { margin: 0 0 1 0; }
"""

PROTO_CSS = """
PlanApprovalModal .gate-review-body > .gate-review-actions--decisions {
    width: RAILW;
}
PlanApprovalModal .gate-review-actions--decisions {
    scrollbar-size-vertical: 1;
}
PlanApprovalModal #plan-decision-rows {
    height: 1fr;
    max-height: 100%;
    scrollbar-size-vertical: 1;
    scrollbar-gutter: auto;
}
PlanApprovalModal .decision-card {
    height: auto;
    width: 1fr;
    padding: 0 1 0 1;
    margin: 0 0 1 0;
    border-left: blank;
}
PlanApprovalModal .decision-card.-current {
    border-left: outer #3A6F80;
    background: #5FD7FF 6%;
    padding: 0 1 0 1;
}
PlanApprovalModal .decision-card.-current:focus {
    border-left: outer #5FD7FF;
    background: #5FD7FF 10%;
}
PlanApprovalModal .decision-card:focus {
    text-style: none;
}
"""


def rail_width(width: int) -> int:
    inner = int(width * 0.98) - 4
    return max(50, min(84, inner - 1 - 98))


class Harness(App):
    CSS_PATH = str(Path(view_mod.__file__).parents[1] / "styles.tcss")

    def __init__(self, rail: int, values: dict | None) -> None:
        css = PROTO_CSS.replace("RAILW", str(rail))
        if COMPACT:
            css += NARROW_CSS
        if ZOOM:
            css += ZOOM_CSS
        self.CSS = css
        super().__init__()
        self.values = values

    def on_mount(self) -> None:
        modal = PlanApprovalModal(str(PLAN), default_choice="tale", decision_definitions=DEFS)
        if self.values:
            for k, v in self.values.items():
                modal._decision_draft.set_value(k, v)
        self.push_screen(modal)


def _proto_header(self) -> str:
    total = len(self._decision_definitions)
    memos = sum(1 for d in self._decision_definitions if d.get("memory") is not None)
    try:
        changed = int(self._decision_draft.sheet().get("changed_count", 0))
    except Exception:
        changed = 0
    parts = [f"Decisions · {total}"]
    if changed:
        parts.append(f"{changed} changed ●")
    if memos:
        parts.append(f"🧠 {memos}")
    return "  ".join([parts[0], " · ".join(parts[1:])]).rstrip(" ·") if len(parts) > 1 else parts[0]


async def main(width: int, height: int, out: str, presses: list[str], values, title) -> None:
    view_mod.PlanApprovalViewMixin._decisions_header = _proto_header
    view_mod.PlanDecisionRows = ProtoDecisionRows
    controls_mod.PlanDecisionRows = ProtoDecisionRows
    app = Harness(rail_width(width), values)
    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause(0.5)
        for key in presses:
            await pilot.press(key)
            await pilot.pause(0.1)
        await pilot.pause(0.3)
        svg = app.export_screenshot(title=title or f"proposed {width}x{height}")
    Path(out).write_bytes(render_svg_to_png(svg))
    print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    values = None
    title = None
    if "--changed" in args:
        args.remove("--changed")
        values = {"root": "legacy"}
    if "--zoom" in args:
        args.remove("--zoom")
        ZOOM = True
    if "--compact" in args:
        args.remove("--compact")
        COMPACT = True
    if "--title" in args:
        i = args.index("--title")
        title = args[i + 1]
        del args[i:i + 2]
    w, h, out, *presses = args
    asyncio.run(main(int(w), int(h), out, presses, values, title))
