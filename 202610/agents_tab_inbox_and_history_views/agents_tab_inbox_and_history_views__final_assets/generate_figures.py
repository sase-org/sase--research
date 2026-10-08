#!/usr/bin/env python3
"""Regenerate the figures for agents_tab_inbox_and_history_views__final.md.

The TUI mockups are character grids exported to SVG by Rich and rasterized by
the same hermetic renderer `sase screenshot` uses
(`sase.ace.tui.visual_render.render_svg_to_png`, bundled Fira Code). Run it
with a sase checkout's virtualenv so that module and Rich are importable:

    <sase-checkout>/.venv/bin/python -I generate_figures.py [OUT_DIR]

Row names, counts, and day/month totals in the History mock come from athena's
dismissed-bundle index on 2026-10-08. Reply text and link targets are
illustrative.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.terminal_theme import TerminalTheme
from rich.text import Text

from sase.ace.tui.visual_render import render_svg_to_png

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent

# --- palette (approximates the live ACE theme) ------------------------------
BG = "#161616"
FG = "#d0d0d0"
DIM = "#7a7a7a"
FAINT = "#555555"
WHITE = "#ececec"
AMBER = "#d7af5f"  # the one History accent
AMBER_BG = "#3a3122"
TEAL = "#5fd7af"
DECK = "#00af87"
BLUE = "#3f6fb5"
CYAN = "#5fafff"
YELLOW = "#ffd75f"
GREEN = "#87d75f"
DGREEN = "#6faa5f"
RED = "#ff5f5f"
DRED = "#d75f5f"
VIOLET = "#8787af"
MAGENTA = "#d75fd7"
ORANGE = "#ff8700"
EPIC = "#d7af00"
SEL = "#4b3d5c"
KEY = "#5fd75f"

THEME = TerminalTheme(
    (22, 22, 22),
    (208, 208, 208),
    [
        (0, 0, 0),
        (205, 49, 49),
        (13, 188, 121),
        (229, 229, 16),
        (36, 114, 200),
        (188, 63, 188),
        (17, 168, 205),
        (229, 229, 229),
    ],
)

# Codepoints Fira Code lacks; they render from the bundled fallback faces, so
# each one is emitted as its own SVG text run to keep the row grid aligned.
FALLBACK = set("✗↺⇡▸▾⋮⊘⚠✔⇄★◈⬡❯◂")


class Canvas:
    """A fixed character grid with per-cell foreground and background styles."""

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.ch = [[" "] * w for _ in range(h)]
        self.st = [[""] * w for _ in range(h)]
        self.bgc = [[""] * w for _ in range(h)]

    def put(self, x: int, y: int, s: str, style: str = "") -> int:
        if 0 <= y < self.h:
            for c in s:
                if 0 <= x < self.w:
                    self.ch[y][x] = c
                    self.st[y][x] = style
                x += 1
        else:
            x += len(s)
        return x

    def runs(self, x: int, y: int, parts) -> int:
        for item in parts:
            text, style = item if isinstance(item, tuple) else (item, "")
            x = self.put(x, y, text, style)
        return x

    def rput(self, right: int, y: int, parts) -> int:
        """Right-align parts so the last cell lands at column ``right``."""
        width = sum(len(p[0] if isinstance(p, tuple) else p) for p in parts)
        return self.runs(right - width + 1, y, parts)

    def shade(self, x: int, y: int, w: int, color: str) -> None:
        for i in range(max(x, 0), min(x + w, self.w)):
            self.bgc[y][i] = color

    def box(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: str,
        title=None,
        title_right=None,
        bottom_left=None,
        bottom_right=None,
        round_=False,
    ) -> None:
        tl, tr, bl, br = ("╭", "╮", "╰", "╯") if round_ else ("┌", "┐", "└", "┘")
        self.put(x, y, tl + "─" * (w - 2) + tr, color)
        if h > 1:
            self.put(x, y + h - 1, bl + "─" * (w - 2) + br, color)
        for yy in range(y + 1, y + h - 1):
            self.put(x, yy, "│", color)
            self.put(x + w - 1, yy, "│", color)
        if title:
            self.runs(x + 2, y, [" "] + list(title) + [" "])
        if title_right:
            self.rput(x + w - 3, y, [" "] + list(title_right) + [" "])
        if bottom_left:
            self.runs(x + 2, y + h - 1, [" "] + list(bottom_left) + [" "])
        if bottom_right:
            self.rput(x + w - 3, y + h - 1, [" "] + list(bottom_right) + [" "])

    def rule(self, x: int, y: int, w: int, color: str = BLUE) -> None:
        self.put(x, y, "─" * w, color)

    def lines(self) -> list[Text]:
        out = []
        for y in range(self.h):
            text = Text(no_wrap=True, overflow="crop")
            run, run_style = "", None
            for x in range(self.w):
                style = self.st[y][x]
                if self.bgc[y][x]:
                    style = f"{style} on {self.bgc[y][x]}".strip()
                char = self.ch[y][x]
                if char in FALLBACK:
                    if run:
                        text.append(run, run_style or None)
                    # A distinct (no-op) style keeps the glyph in its own run.
                    text.append(char, f"{style} not strike".strip())
                    run, run_style = "", None
                    continue
                if style != run_style and run:
                    text.append(run, run_style or None)
                    run = ""
                run_style = style
                run += char
            if run:
                text.append(run, run_style or None)
            out.append(text)
        return out


def save(canvas: Canvas, name: str, title: str, scale: float = 2.0) -> None:
    console = Console(
        record=True,
        width=canvas.w,
        file=io.StringIO(),
        force_terminal=True,
        color_system="truecolor",
    )
    for line in canvas.lines():
        console.print(line, no_wrap=True, overflow="crop", soft_wrap=False)
    svg = console.export_svg(title=title, theme=THEME, unique_id=name.replace("-", "_"))
    match = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if match:
        vw, vh = float(match.group(1)), float(match.group(2))
        svg = svg.replace(
            match.group(0),
            f'{match.group(0)} width="{vw * scale:.0f}" height="{vh * scale:.0f}"',
            1,
        )
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    (OUT / f"{name}.png").write_bytes(render_svg_to_png(svg))
    print("wrote", name)


def chip(text: str, fg: str = "black", bg: str = AMBER, bold: bool = True):
    return (text, f"{'bold ' if bold else ''}{fg} on {bg}")


def footer(c: Canvas, y: int, items) -> None:
    x = 1
    for key, label in items:
        x = c.runs(x, y, [(key, f"bold {KEY}"), (" " + label, FG)]) + 3


def outcome_parts(kind: str, word: str):
    if kind == "done":
        return [("√ ", f"bold {GREEN}"), (word, DGREEN)]
    if kind == "failed":
        return [("✗ ", f"bold {RED}"), (word, DRED)]
    if kind == "was":
        return [("○ ", VIOLET), ("WAS " + word, VIOLET)]
    if kind == "live":
        return [("● ", f"bold {YELLOW}"), (word, f"bold {YELLOW}")]
    raise ValueError(kind)


def history_row(c, y, time, kind, word, name, model, runtime, chip_=None, start_only=False, selected=False, x0=2, name_w=28):
    time_style = f"italic {FAINT}" if start_only else DIM
    c.put(x0 + 2, y, time, time_style)
    c.runs(x0 + 8, y, outcome_parts(kind, word))
    name_style = f"bold {WHITE}" if selected else WHITE
    if kind == "was":
        name_style = f"{VIOLET}"
    c.put(x0 + 24, y, name[:name_w], name_style)
    c.put(x0 + 24 + name_w + 1, y, model, "#5fafd7")
    c.put(x0 + 24 + name_w + 8, y, runtime.rjust(5), DIM)
    if chip_:
        c.runs(x0 + 24 + name_w + 15, y, chip_)
    if selected:
        c.shade(x0 + 1, y, 75, SEL)


def banner(c, y, label, count, open_=True, x0=2, right=76, color=CYAN):
    glyph = "▼ " if open_ else "▶ "
    x = c.runs(x0, y, [(glyph, color), (label, f"bold {color}")])
    tail = f" {count} runs"
    c.put(x + 1, y, "─" * (right - x - len(tail) - 1), BLUE)
    c.put(right - len(tail) + 1, y, tail, CYAN)


# =============================================================================
# Figure 1: the History view (merged design)
# =============================================================================


def fig_history_view() -> None:
    c = Canvas(160, 46)
    # top tab bar: History marker on the Agents tab label (grk)
    c.runs(1, 0, [("Agents", f"bold {TEAL}"), (" ◷", f"bold {AMBER}"), ("  │  ", FAINT), ("Artifacts", DIM), ("  │  ", FAINT), ("Services", DIM)])
    c.rput(158, 0, [("load: ", DIM), ("6.25/8", f"bold {RED}"), (" · model: ", DIM), ("gpt-6.1-sol@xhigh", GREEN), (" · project: ", DIM), ("+sase", f"bold {ORANGE}")])
    # info row
    c.runs(0, 1, [chip(" ◷ HISTORY "), (" 11,061", f"bold {WHITE}"), (" runs (144 live)", DIM), (" · filter: ", DIM), chip(" in:local ", "black", "#af875f"), (" (/)", DIM), (" · group: ", DIM), ("by day", f"bold {YELLOW}"), (" (o)", DIM), (" · ", DIM), ("newest activity first", FG)])
    c.rput(158, 1, [("✓ searched all local history", DGREEN), ("  ·  ", DIM), (",a", f"bold black on {AMBER}"), (" inbox", DIM)])
    # source strip replaces the agent-tab strip
    c.runs(0, 2, [(" source ", DIM), chip(" ◷ This machine 11.1k "), ("  │  ", FAINT), ("↑ Published", DIM), (" (epic 2)", FAINT), ("  │  ", FAINT), ("∪ Combined", DIM), (" (epic 2)", FAINT)])
    c.rput(158, 2, [("agent tabs and tribe panels belong to the inbox", f"italic {FAINT}")])

    # ---- left column ----
    c.box(0, 3, 80, 2, BLUE, title=[("▶ ", CYAN), ("⌂ Inbox", f"bold {CYAN}"), (" · 147 [", DIM), ("R10", f"bold {YELLOW}"), (" Q5", f"bold {CYAN}"), (" W35", f"bold {VIOLET}"), (" ", DIM), ("U1", "bold black on #ffd700"), (" D96", f"bold {GREEN}"), ("] · ", DIM), ("1 needs you", f"bold {MAGENTA}")], bottom_right=[(",a", f"bold black on {AMBER}")])
    c.box(0, 5, 80, 38, AMBER, title=[("◷ History", f"bold {AMBER}"), (" · this machine · newest activity first", DIM)], bottom_left=[("italic time", f"italic {FAINT}"), (" = start only; end not recorded", FAINT)], bottom_right=[("7/11,061", DIM)])
    y = 6
    banner(c, y, "Today · Thu Oct 8", 33)
    rows = [
        ("19:52", "live", "RUNNING", "research.45 ×6", "mixed", "1h40", [("⌂ inbox", f"bold {CYAN}")], False),
        ("19:18", "was", "RUNNING", "0yn", "opus", "—", None, True),
        ("18:32", "done", "EPIC CREATED", "research.43.linker.w0--plan", "opus", "35m", None, False),
        ("15:07", "done", "TALE DONE", "0yh--plan", "opus", "49m", None, False),
        ("13:04", "done", "DONE", "0yf--0", "muse", "20m", None, False),
        ("12:22", "failed", "FAILED", "toobig-7e ×7", "muse", "—", None, True),
        ("12:06", "done", "DONE", "bob-cli-5p.4", "muse", "1h00", None, False),
        ("11:55", "done", "DONE", "bob-cli-5p.3", "muse", "49m", None, False),
        ("11:40", "done", "DONE", "bob-cli-5p.2", "muse", "34m", None, False),
        ("11:03", "done", "EPIC CREATED", "0yb--plan", "opus", "29m", None, False),
        ("01:38", "done", "DONE", "sase-1h7.land", "opus", "31h18", [("from Oct 6", FAINT)], False),
    ]
    for i, (t, k, w, n, m, r, ch, so) in enumerate(rows):
        y += 1
        history_row(c, y, t, k, w, n, m, r, ch, start_only=so, selected=(n == "bob-cli-5p.4"))
    y += 1
    c.runs(6, y, [("⋮ ", DIM), ("22 more", FG), (" · l expands · rows stream in as you scroll", DIM)])
    y += 2
    banner(c, y, "Yesterday · Wed Oct 7", 133)
    for t, k, w, n, m, r in [
        ("23:42", "done", "DONE", "sase-1hf.land", "opus", "8h54"),
        ("22:15", "done", "TALE DONE", "bob-cli-5k.land--plan", "opus", "7h34"),
        ("20:51", "done", "DONE", "sase-1h7.10--plan", "muse", "26h31"),
        ("20:49", "done", "DONE", "bob-cli-5k.7.1.land", "grok", "3h10"),
    ]:
        y += 1
        history_row(c, y, t, k, w, n, m, r)
    y += 1
    c.runs(6, y, [("⋮ ", DIM), ("129 more", FG), (" · l expands", DIM)])
    y += 2
    for label, count in [
        ("Tue Oct 6", 123),
        ("Mon Oct 5", 88),
        ("Sun Oct 4", 87),
        ("Last week · Sep 28 – Oct 3", 825),
        ("Earlier in September 2026", "2,952"),
        ("August 2026", "3,622"),
        ("July 2026", "3,055"),
    ]:
        banner(c, y, label, count, open_=False)
        y += 1

    # ---- right column ----
    rx = 81
    c.box(rx, 3, 79, 5, MAGENTA, title=[("AGENT", f"bold {MAGENTA}"), (" · ", DIM), ("◷ ARCHIVED", f"bold {AMBER}"), (" · read-only", DIM)])
    c.runs(rx + 2, 4, [("bob-cli-5p.4", f"bold {WHITE}"), (" · ", DIM), ("MUSE", f"bold {MAGENTA}"), ("(muse-spark-1.3-contributor)", MAGENTA), (" · ", DIM), ("√ DONE", f"bold {GREEN}"), (" · ", DIM), ("+bob-cli", f"bold {ORANGE}")])
    c.runs(rx + 2, 5, [("ended today 12:06", FG), (" · ran 11:06 → 12:06 (1h00) · dismissed 12:06", DIM)])
    c.runs(rx + 2, 6, [("⏎", f"bold {KEY}"), (" restore · fork · copy…", FG), ("   live-only keys (x s W A R n N) are off here", FAINT)])

    c.box(rx, 8, 79, 28, DECK, title=[("◆ ", DECK), ("MAIN", f"bold {DECK}"), (" spread · auto", DIM), (" │ ", FAINT), ("Context", FG), ("  ", ""), (" Reply ", f"bold black on {DECK}")], bottom_right=[("main 2", f"bold {DECK}"), (" · files 6 · tools 58 · final 3 · ", DIM), ("record 4", f"bold {AMBER}")])
    yy = 9
    c.runs(rx + 2, yy, [("── ", DECK), ("Reply", f"bold {DECK}"), (" · from the retained chat", DIM), (" " + "─" * 40, FAINT)])
    yy += 1
    c.put(rx + 2, yy, "Bead bob-cli-5p.4 is closed. Rollout is complete and verified.", f"bold {WHITE}")
    yy += 2
    c.put(rx + 2, yy, "What was done:", FG)
    for line in [
        [("• Installed ", FG), ("bob", f"bold {YELLOW}"), (" from master (", FG), ("just install", f"bold {YELLOW}"), ("); ", FG), ("bob freshness list", f"bold {YELLOW}")],
        [("  now reports schema 11.", FG)],
        [("• Live check passed: all four census overdue rows walk in", FG)],
        [("  RECURRING with exact dates.", FG)],
        [("• Deployed plugins with ", FG), ("bob plugins sync", f"bold {YELLOW}"), ("; deployed main.js", FG)],
        [("  files are byte-identical to the repo.", FG)],
        [("• ", FG), ("just check", f"bold {YELLOW}"), (" passes.", FG)],
    ]:
        yy += 1
        c.runs(rx + 2, yy, line)
    yy += 2
    c.runs(rx + 2, yy, [("── ", DECK), ("Context", f"bold {DECK}"), (" " + "─" * 55, FAINT)])
    yy += 1
    c.runs(rx + 2, yy, [("PROMPT", f"bold {DIM}"), (" full text, never cut at 4,000 chars", DIM), ("  %p copies it", FAINT)])
    yy += 1
    c.put(rx + 4, yy, "Can you complete the work for bead bob-cli-5p.4? The bead is", FG)
    yy += 1
    c.put(rx + 4, yy, "already reserved for you…", FG)
    yy += 2
    c.put(rx + 2, yy, "Every card reads the dismissed bundle and the retained chat.", f"italic {AMBER}")
    yy += 1
    c.put(rx + 2, yy, "Nothing is revived and nothing is written.", f"italic {AMBER}")
    yy += 2
    c.runs(rx + 2, yy, [("Files", f"bold {DIM}"), (" 6 diffs retained   ", DIM), ("Tools", f"bold {DIM}"), (" 58 calls   ", DIM), ("FINAL", f"bold {DIM}"), (" commit + close", DIM)])

    c.box(rx, 36, 79, 7, EPIC, title=[("JUMP", f"bold {EPIC}"), (" · ", DIM), ("CLAN", f"bold {MAGENTA}"), (" bob-cli-5p", MAGENTA), (" 01-04", FAINT), (" · RELATIONS", DIM)])
    x = rx + 2
    for i in range(1, 5):
        x = c.runs(x, 37, [(f"0{i}", f"bold black on {MAGENTA}"), (f" .{i} ", FG), ("√", GREEN), ("   ", "")])
    c.runs(x, 37, [("◂ you", f"bold {WHITE}")])
    c.runs(rx + 2, 39, [("parent ", DIM), ("bob-cli-5p", MAGENTA), ("  ·  retry chain —  ·  links 3: ", DIM), ("plan · bead · stitch", f"underline {CYAN}")])
    c.runs(rx + 2, 40, [("p r", f"bold {KEY}"), (" opens the Record deck: lifecycle · provenance · relations · links", DIM)])

    footer(c, 44, [("⏎", "restore / fork / copy…"), ("p r", "record"), ("y", "copy @agent ref"), ("e", "open chat"), ("m", "mark"), ("u", "clear marks"), (",a", "inbox"), ("^", "previous filter")])
    c.runs(1, 45, [("Archived rows never feed unread, attention, load:, runner slots, or bulk x / X / s.", f"italic {FAINT}")])
    save(c, "fig_history_view", "Proposed: Agents ▸ History view (merged design, mock)")


# =============================================================================
# Figure 2: the act chooser and what restore does
# =============================================================================


def fig_act_and_restore() -> None:
    c = Canvas(160, 31)
    c.runs(1, 0, [("① ", f"bold {AMBER}"), ("⏎ on an archived row opens the Agents chooser, with a HISTORY section", f"bold {WHITE}")])
    c.runs(82, 0, [("② ", f"bold {AMBER}"), ("⏎ r restores and you stay in History", f"bold {WHITE}")])

    # dimmed list behind the modal
    for i, (t, w, name) in enumerate([("13:04", "√ DONE  ", "0yf--0"), ("12:22", "✗ FAILED", "toobig-7e ×7"), ("12:06", "√ DONE  ", "bob-cli-5p.4")]):
        c.put(3, 2 + i, f"{t}  {w}      {name}", FAINT)
    c.box(4, 6, 74, 21, AMBER, title=[("Act on ", f"bold {WHITE}"), ("bob-cli-5p.4", f"bold {AMBER}"), (" · archived · √ DONE", DIM)], round_=True)
    y = 7
    c.put(7, y, "HISTORY", f"bold {AMBER}")
    opts = [
        ("r", "Restore to inbox", "shows it again · starts no new run", True),
        ("g", "Restore and show it", "same, then jumps to it in the inbox", False),
        ("F", "Fork into a new agent", "new run from this prompt + chat", False),
    ]
    for key, label, detail, sel in opts:
        y += 1
        c.runs(7, y, [(f" {key} ", f"bold black on {KEY}"), ("  " + label.ljust(24), f"bold {WHITE}" if sel else WHITE), (detail, DIM)])
        if sel:
            c.shade(6, y, 70, SEL)
    y += 2
    c.put(7, y, "READ AND REFER", f"bold {CYAN}")
    for key, label, detail in [
        ("e", "Open chat in $EDITOR", "read-only copy"),
        ("y", "Copy @agent reference", "same as y on the row"),
        ("%", "More copy targets…", "link · json · handoff · prompt"),
    ]:
        y += 1
        c.runs(7, y, [(f" {key} ", f"bold black on {CYAN}"), ("  " + label.ljust(24), WHITE), (detail, DIM)])
    y += 2
    c.put(7, y, "PATCH", f"bold {MAGENTA}")
    y += 1
    c.runs(7, y, [(" p ", f"bold black on {MAGENTA}"), ("  " + "Go to Patch".ljust(24), WHITE), ("existing section, unchanged", DIM)])
    y += 2
    c.runs(7, y, [("With marks: ", DIM), ("⏎ Restore 4 marked", f"bold {WHITE}"), (" · skips 1 (no bundle) and says why", DIM)])
    y += 1
    c.put(7, y, "Up/Down or j/k move - Enter select - Esc cancel", FAINT)
    c.runs(4, 28, [("There is no bare revive key: ", DIM), ("w", f"bold {KEY}"), (" stays reword and ", DIM), ("r", f"bold {KEY}"), (" stays refresh on the Agents tab.", DIM)])

    # right panel: after restore
    rx = 82
    c.box(rx, 2, 78, 2, BLUE, title=[("▶ ", CYAN), ("⌂ Inbox", f"bold {CYAN}"), (" · ", DIM), ("148", f"bold {WHITE}"), (" [R10 Q5 W35 U1 D", DIM), ("97", f"bold {GREEN}"), ("] · 1 needs you", DIM)], bottom_right=[("+1", f"bold {GREEN}")])
    c.box(rx, 4, 78, 10, AMBER, title=[("◷ History", f"bold {AMBER}"), (" · this machine", DIM)])
    hx = rx
    rows = [
        ("13:04", "done", "DONE", "0yf--0", "muse", "20m", None, False),
        ("12:22", "failed", "FAILED", "toobig-7e ×7", "muse", "—", None, True),
        ("12:06", "done", "DONE", "bob-cli-5p.4", "muse", "1h00", [("⌂ inbox", f"bold {CYAN}")], False),
        ("11:55", "done", "DONE", "bob-cli-5p.3", "muse", "49m", None, False),
        ("11:40", "done", "DONE", "bob-cli-5p.2", "muse", "34m", None, False),
    ]
    for i, (t, k, w, n, m, r, ch, so) in enumerate(rows):
        history_row(c, 6 + i, t, k, w, n, m, r, ch, start_only=so, selected=(n == "bob-cli-5p.4"), x0=hx + 1, name_w=22)
    c.runs(rx + 3, 12, [("the row stays put; its chip flips to ", DIM), ("⌂ inbox", f"bold {CYAN}")])
    c.box(rx + 6, 15, 70, 6, AMBER, title=[("⟳ restored", f"bold {AMBER}")], round_=True)
    c.runs(rx + 8, 16, [("bob-cli-5p.4", f"bold {WHITE}"), (" is back in the inbox. No new run started.", FG)])
    c.runs(rx + 8, 17, [("The inbox filter would hide it: ", DIM), ("status:RUNNING", YELLOW)])
    c.runs(rx + 8, 19, [("g", f"bold {KEY}"), (" show it in the inbox", FG), ("   ", ""), (",a", f"bold {KEY}"), (" back to where you were", FG)])
    rules = [
        "• Restore never switches views on its own, so bulk restores stay in place.",
        "• g reveals the agent in the inbox (clearing a hiding filter, ^ undoes) and",
        "  records one Ctrl+O hop; ,a returns to the parked inbox exactly as it was.",
        "• With dismissed:true in the filter the row leaves the results and the",
        "  highlight moves to the next row instead of jumping.",
        "• The pulse counts it at once; History never touches unread or attention.",
    ]
    for i, line in enumerate(rules):
        c.put(rx + 2, 22 + i, line, FG if line.startswith("•") else FG)
    save(c, "fig_act_and_restore", "Proposed: acting on an archived run (mock)")


# =============================================================================
# Figure 3: one tab, two views, and every road in
# =============================================================================


def fig_two_views_map() -> None:
    c = Canvas(160, 40)
    c.runs(1, 0, [("One Agents tab, two views, one reader", f"bold {WHITE}"), ("   ·   the inbox you work in, and the history you read, one keystroke apart", DIM)])

    # Inbox mini-screen
    c.box(1, 2, 60, 24, CYAN, title=[("⌂ INBOX view", f"bold {CYAN}"), (" · default · every startup", DIM)], round_=True)
    c.runs(3, 3, [("147", f"bold {WHITE}"), (" [R10 Q5 W35 ", DIM), ("U1", "bold black on #ffd700"), (" D96] · group: by status (o)", DIM)])
    c.runs(3, 4, [(" ⌂ athena 144 ", f"bold black on {TEAL}"), ("  ", ""), ("⌨ apollo 74", CYAN), ("   ← agent tabs: inbox-only", FAINT)])
    c.box(3, 5, 56, 5, BLUE, title=[("⌂ @default", f"bold {CYAN}"), (" · 17", DIM)])
    c.runs(5, 6, [("▶ Running", f"bold {YELLOW}")])
    c.runs(7, 7, [("sase (EPIC APPROVED) ×7 research.43.linker.w0", FG)])
    c.runs(5, 8, [("√ Done", f"bold {GREEN}"), ("   sase (DONE) 0yq", FG)])
    c.box(3, 10, 56, 5, EPIC, title=[("▲ @epic", f"bold {CYAN}"), (" · 66 [R5 Q2 W23 D35]", DIM)])
    c.runs(5, 11, [("▶ Running", f"bold {YELLOW}")])
    c.runs(7, 12, [("sase (RUNNING) ×9 [R3 W2 D3] sase-1h8.13.1", FG)])
    c.runs(7, 13, [("sase (RUNNING) ×7 [R1 W2 D4] sase-1id", FG)])
    c.box(3, 15, 56, 2, BLUE, title=[("▶ ∴ @research", f"bold {CYAN}"), (" · 32 [R5 W5 D21]", DIM)])
    c.box(3, 17, 56, 2, BLUE, title=[("▶ † @job", f"bold {CYAN}"), (" · 23 [Q1 W3 D18]", DIM)])
    c.box(3, 21, 56, 2, AMBER, title=[("▶ ", AMBER), ("◷ History", f"bold {AMBER}"), (" · ", DIM), ("10,917", f"bold {WHITE}"), (" archived · ", DIM), ("+3 just now", f"bold {GREEN}")], bottom_right=[(",a", f"bold black on {AMBER}")])
    c.runs(4, 23, [("↑ ", f"bold {AMBER}"), ("History shelf", f"bold {AMBER}"), (": one line, no rows. With a filter it", DIM)])
    c.runs(4, 24, [("  reads ", DIM), ("◷ History · 7 matches for this filter", AMBER), (".", DIM)])

    # History mini-screen
    c.box(99, 2, 60, 24, AMBER, title=[("◷ HISTORY view", f"bold {AMBER}"), (" · in:local", DIM)], round_=True)
    c.runs(101, 3, [(" ◷ HISTORY ", f"bold black on {AMBER}"), (" 11,061 runs · ", DIM), (" in:local ", "bold black on #af875f"), (" · by day", DIM)])
    c.runs(101, 4, [(" ◷ This machine ", f"bold black on {AMBER}"), (" │ ↑ Published │ ∪ Combined", FAINT)])
    c.box(101, 5, 56, 2, BLUE, title=[("▶ ", CYAN), ("⌂ Inbox", f"bold {CYAN}"), (" · 147 [R10 W35 ", DIM), ("U1", "bold black on #ffd700"), ("] · ", DIM), ("1 needs you", f"bold {MAGENTA}")], bottom_right=[(",a", f"bold black on {AMBER}")])
    c.runs(102, 7, [("↑ ", f"bold {CYAN}"), ("Inbox pulse", f"bold {CYAN}"), (": live counts while you browse", DIM)])
    c.box(101, 8, 56, 13, AMBER, title=[("◷ History", f"bold {AMBER}"), (" · newest activity first", DIM)])
    banner(c, 9, "Today · Thu Oct 8", 33, x0=103, right=154)
    mini = [
        ("19:52", "live", "RUNNING", "research.45 ×6", [("⌂ inbox", f"bold {CYAN}")], False),
        ("19:18", "was", "RUNNING", "0yn", None, True),
        ("12:22", "failed", "FAILED", "toobig-7e ×7", None, True),
        ("12:06", "done", "DONE", "bob-cli-5p.4", None, False),
    ]
    for i, (t, k, w, n, ch, so) in enumerate(mini):
        yy = 10 + i
        c.put(104, yy, t, f"italic {FAINT}" if so else DIM)
        c.runs(110, yy, outcome_parts(k, w))
        c.put(126, yy, n, VIOLET if k == "was" else (f"bold {WHITE}" if n == "bob-cli-5p.4" else WHITE))
        if ch:
            c.runs(144, yy, ch)
        if n == "bob-cli-5p.4":
            c.shade(103, yy, 53, SEL)
    banner(c, 15, "Yesterday · Wed Oct 7", 133, open_=False, x0=103, right=154)
    banner(c, 16, "Tue Oct 6", 123, open_=False, x0=103, right=154)
    banner(c, 17, "Last week · Sep 28 – Oct 3", 825, open_=False, x0=103, right=154)
    banner(c, 18, "Earlier in September 2026", "2,952", open_=False, x0=103, right=154)
    c.runs(102, 22, [("No agent tabs, no tribe panels, no fold tree.", DIM)])
    c.runs(102, 23, [("Past-tense outcomes: ", DIM), ("√ DONE", GREEN), ("  ", ""), ("✗ FAILED", DRED), ("  ", ""), ("○ WAS RUNNING", VIOLET)])

    # the switch, in the middle
    mid = 63
    c.runs(mid, 8, [("────────── ", AMBER), (",a", f"bold black on {AMBER}"), (" ──────────▶", AMBER)])
    c.runs(mid + 1, 9, [("⏎ on the shelf · ⏎ on a bridge hit", DIM)])
    c.runs(mid + 1, 10, [("carries your filter; drops what", DIM)])
    c.runs(mid + 1, 11, [("History can't answer, and says so", DIM)])
    c.runs(mid, 14, [("◀────────── ", CYAN), (",a", f"bold black on {AMBER}"), (" ──────────", CYAN)])
    c.runs(mid + 1, 15, [("⏎ on the pulse · ^ after a jump", DIM)])
    c.runs(mid + 1, 16, [("restores the inbox exactly: filter,", DIM)])
    c.runs(mid + 1, 17, [("selection, folds, agent tab, tribe", DIM)])
    c.runs(mid, 20, [("filter names ", DIM), ("dismissed: outcome:", YELLOW)])
    c.runs(mid, 21, [("──▶ History, with a toast · ^ undoes", AMBER)])

    # shared reader
    c.box(1, 27, 158, 5, DECK, title=[("◆ THE SAME READER FOR BOTH VIEWS", f"bold {DECK}")], round_=True)
    c.runs(3, 28, [("Main", f"bold {DECK}"), (" (Context · Reply)  ·  ", DIM), ("Files", f"bold {DECK}"), ("  ·  ", DIM), ("Tools", f"bold {DECK}"), ("  ·  ", DIM), ("FINAL", f"bold {DECK}"), ("  ·  ", DIM), ("Record", f"bold {AMBER}"), (" (new, p r: lifecycle · provenance · relations · links)", DIM)])
    c.runs(3, 29, [("Inbox rows: live data.  ", FG), ("History rows: hydrated from the dismissed bundle and retained chat after a 150 ms debounce, off the event loop.", DIM)])
    c.runs(3, 30, [("Reading never revives.  Missing files show a titled ", FG), ("not retained", f"italic {AMBER}"), (" card, never an empty deck.", FG)])

    # arrivals
    c.put(1, 33, "ARRIVALS", f"bold {WHITE}")
    c.runs(1, 34, [("TUI start", f"bold {CYAN}"), (" ─▶ Inbox (always)        ", DIM), ("agent: link, run is live", f"bold {CYAN}"), (" ─▶ Inbox; if the filter hides it, commit name:\"X\" (^ restores)", DIM)])
    c.runs(1, 35, [("agent: link, not in the inbox", f"bold {AMBER}"), (" ─▶ History, in:local name:\"X\", row selected, toast says why (\"dismissed Aug 13\")", DIM)])
    c.runs(1, 36, [("!R ▸ Search History for restorable runs…", f"bold {AMBER}"), ("   ", ""), ("\" Node Finder ▸ In History", f"bold {AMBER}"), ("   ", ""), ("zero-result bridge", f"bold {AMBER}"), ("   ", ""), ("dismiss toast", f"bold {AMBER}")])
    c.runs(1, 37, [("Artifacts: a legacy \"Agent pane\" command or keymap", f"bold {AMBER}"), (" ─▶ History    ", DIM), ("a persisted agents sub-tab", f"bold {FG}"), (" ─▶ Stitch + a one-time \"moved\" toast", DIM)])
    c.runs(1, 39, [("Every road ends on the Agents tab. None opens Artifacts. None creates local agent state just to read.", f"italic {FAINT}")])
    save(c, "fig_two_views_map", "Recommended: one Agents tab, two views (diagram)")


# =============================================================================
# Figure 4: where the five researchers landed, and the resolution
# =============================================================================

AGREE, PART, DIFF, NONE = "agree", "part", "diff", "none"
CELL_STYLE = {AGREE: TEAL, PART: AMBER, DIFF: DRED, NONE: FAINT}
CELL_MARK = {AGREE: "● ", PART: "◐ ", DIFF: "○ ", NONE: "  "}

MATRIX = [
    ("Where history lives", [(AGREE, "Inbox│History"), (AGREE, "view + bridges"), (AGREE, "History lens"), (AGREE, "History mode"), (AGREE, "History mode")], "Second Agents-tab view"),
    (",a behavior", [(AGREE, "toggle 2 views"), (AGREE, "toggle"), (DIFF, "cycle 4 scopes"), (DIFF, "cycle 3 scopes"), (DIFF, "cycle 3 scopes")], "Toggle; sources are chips"),
    ("Visible way in", [(PART, "Inbox│History tabs"), (AGREE, "History shelf"), (PART, "in: inbox chip"), (PART, "zero-result hint"), (PART, "zero-result hint")], "Shelf + zero-result bridge"),
    ("Live attention in History", [(NONE, "—"), (AGREE, "Inbox pulse"), (PART, "Agents* marker"), (NONE, "—"), (NONE, "—")], "Pulse + ◷ on tab label"),
    ("Archive field typed in Inbox", [(DIFF, "suggest only"), (AGREE, "widen + toast"), (AGREE, "widen + toast"), (AGREE, "widen"), (AGREE, "widen + label")], "Widen to local, toast, ^"),
    ("Default grouping", [(AGREE, "date"), (AGREE, "day"), (DIFF, "session"), (DIFF, "session"), (AGREE, "date")], "Day banners"),
    ("Row time", [(AGREE, "last activity"), (PART, "end time"), (NONE, "—"), (NONE, "—"), (DIFF, "start time")], "Activity; start-only marked"),
    ("Stale stored status", [(PART, "status ≠ presence"), (AGREE, "WAS RUNNING"), (DIFF, "DISMISSED"), (DIFF, "ARCHIVED"), (NONE, "—")], "○ WAS <status>"),
    ("Revive entry point", [(AGREE, "⏎ chooser"), (AGREE, "⏎ chooser"), (DIFF, "w in History"), (AGREE, "⏎ chooser"), (DIFF, "⏎ + bare r")], "⏎ chooser only"),
    ("Chooser default", [(DIFF, "a read action"), (AGREE, "revive"), (AGREE, "revive"), (AGREE, "revive"), (AGREE, "revive")], "Restore (stay in History)"),
    ("Action label", [(AGREE, "Restore to inbox"), (PART, "Revive"), (PART, "Revive"), (PART, "Revive"), (PART, "Revive")], "Restore to inbox"),
    ("Pane metadata + relations", [(PART, "identity detail"), (AGREE, "Record deck"), (NONE, "—"), (NONE, "—"), (NONE, "—")], "Record deck (p r)"),
    ("Old Artifacts entry points", [(AGREE, "split by intent"), (PART, "→ Stitch"), (PART, "→ History"), (PART, "→ Stitch"), (PART, "→ Stitch")], "State→Stitch, cmd→History"),
    ("Startup with History query", [(DIFF, "restore it"), (AGREE, "never"), (DIFF, "inbox, then fill"), (DIFF, "inbox, then fill"), (NONE, "—")], "Always the inbox"),
    ("History list data source", [(PART, "catalog, bounded"), (AGREE, "core SQL index"), (DIFF, "catalog rows"), (PART, "catalog rows"), (AGREE, "SQLite index")], "sase-core SQL projection"),
    ("Restorable chip", [(PART, "when bundle valid"), (PART, "↺ on every row"), (PART, "revivable green"), (NONE, "—"), (PART, "metric")], "Only the exceptions"),
]


def fig_consensus() -> None:
    c = Canvas(160, 4 + 2 * len(MATRIX) + 4)
    col0, colw = 29, 20
    xs = [1, 1 + col0]
    for _ in range(5):
        xs.append(xs[-1] + colw)
    c.runs(1, 0, [("Where the five researchers landed, and how this report resolves each question", f"bold {WHITE}")])
    c.runs(xs[0], 2, [("DECISION", f"bold {DIM}")])
    for i, name in enumerate(["cdx", "cld", "grk", "mus", "gem"]):
        c.put(xs[i + 1] + 2, 2, name, f"bold {WHITE}")
    c.put(xs[6] + 1, 2, "RESOLUTION", f"bold {AMBER}")
    c.put(0, 3, "─" * 160, FAINT)
    y = 4
    for label, cells, final in MATRIX:
        c.put(xs[0], y, label, WHITE)
        for i, (kind, text) in enumerate(cells):
            c.runs(xs[i + 1], y, [(CELL_MARK[kind], CELL_STYLE[kind]), (text[: colw - 3], CELL_STYLE[kind] if kind != AGREE else FG)])
        c.put(xs[6], y, "▶ " + final, f"bold {AMBER}")
        y += 2
    c.put(0, y - 1, "─" * 160, FAINT)
    c.runs(1, y, [("● ", TEAL), ("matches the resolution   ", DIM), ("◐ ", AMBER), ("partly matches   ", DIM), ("○ ", DRED), ("differs   ", DIM), ("— ", FAINT), ("not addressed", DIM)])
    c.runs(1, y + 1, [("Cell text is a paraphrase; each report's own section has the reasoning. The resolution column is the lead's call (see §4).", f"italic {FAINT}")])
    save(c, "fig_consensus", "Researcher positions and the consolidated resolution")


# =============================================================================
# Figure 5: what athena's archive rows can truthfully say (hand-built SVG chart)
# =============================================================================


def fig_archive_truth() -> None:
    surface, ink, ink2, muted, grid = "#1a1a19", "#ffffff", "#c3c2b7", "#898781", "#383835"
    ok, flag = "#3987e5", "#c98500"  # validated pair (dataviz validator, dark mode)
    total = 10917
    bars = [
        ("Stored status", [(9237, "terminal: done or failed", ok), (1680, "non-terminal on an archived row", flag)],
         "Show the outcome in the past tense: ○ WAS RUNNING, never a live RUNNING."),
        ("Time fields", [(7621, "end or dismissal time recorded", ok), (3296, "start time only", flag)],
         "Sort by last activity; mark start-only times instead of mixing them silently."),
        ("Restorable flag", [(10917, "durably_revivable = true", ok)],
         "A chip on every row says nothing. Badge only the rows that cannot be restored."),
    ]
    W, left, barw, barh = 1400, 250, 1050, 34
    rows_y0, gap = 130, 128
    H = 760
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f'<rect width="{W}" height="{H}" fill="{surface}"/>',
        f'<text x="40" y="52" fill="{ink}" font-size="26" font-weight="bold" font-family="Fira Code">What athena\'s 10,917 archived top-level runs can truthfully say</text>',
        f'<text x="40" y="86" fill="{ink2}" font-size="17" font-family="Fira Code">Share of rows in ~/.sase/dismissed_bundles/index.sqlite, 2026-10-08 (workflow children excluded)</text>',
    ]
    for i, (label, segs, note) in enumerate(bars):
        y = rows_y0 + i * gap
        parts.append(f'<text x="40" y="{y + 24}" fill="{ink}" font-size="19" font-weight="bold" font-family="Fira Code">{label}</text>')
        x = left
        note_y = y + barh + 26
        for j, (n, seg_label, color) in enumerate(segs):
            w = barw * n / total
            draw_w = w - (2 if j < len(segs) - 1 else 0)
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{draw_w:.1f}" height="{barh}" rx="4" fill="{color}"/>')
            text = f"{100 * n / total:.1f}% · {n:,} · {seg_label}"
            if w > 520:
                parts.append(f'<text x="{x + 12:.1f}" y="{y + 23}" fill="#0b0b0b" font-size="16" font-weight="bold" font-family="Fira Code">{text}</text>')
            else:
                parts.append(f'<text x="{left + barw:.1f}" y="{note_y}" text-anchor="end" fill="{ink2}" font-size="16" font-family="Fira Code"><tspan fill="{color}">■</tspan> {text}</text>')
                note_y += 26
            x += w
        parts.append(f'<text x="{left}" y="{note_y}" fill="{muted}" font-size="15" font-family="Fira Code">{note}</text>')
    by = rows_y0 + gap * (len(bars) - 1) + barh + 56
    parts.append(f'<line x1="{left}" y1="{by}" x2="{left + barw}" y2="{by}" stroke="{grid}" stroke-width="1"/>')
    for k in range(0, 101, 25):
        tx = left + barw * k / 100
        parts.append(f'<line x1="{tx:.1f}" y1="{by}" x2="{tx:.1f}" y2="{by + 6}" stroke="{grid}" stroke-width="1"/>')
        parts.append(f'<text x="{tx:.1f}" y="{by + 24}" text-anchor="middle" fill="{muted}" font-size="14" font-family="Fira Code">{k}%</text>')
    hy = by + 72
    parts.append(f'<text x="40" y="{hy}" fill="{ink}" font-size="19" font-weight="bold" font-family="Fira Code">Cost to list the newest 100 archived runs</text>')
    tiles = [
        ("11.1 s", "Python catalog build", "sase agent search -l 0 (cld)"),
        ("12–90 s", "Artifacts ▸ Agent first rows", "settled vs during startup (cld)"),
        ("16–31 ms", "one SQL window, no time index", "dismissed_bundle_summaries (lead)"),
    ]
    ty = hy + 22
    for i, (big, what, src) in enumerate(tiles):
        tx = 40 + i * 400
        parts.append(f'<rect x="{tx}" y="{ty}" width="380" height="96" rx="6" fill="#222221" stroke="{grid}"/>')
        parts.append(f'<text x="{tx + 18}" y="{ty + 40}" fill="{ink}" font-size="30" font-weight="bold" font-family="Fira Code">{big}</text>')
        parts.append(f'<text x="{tx + 18}" y="{ty + 66}" fill="{ink2}" font-size="15" font-family="Fira Code">{what}</text>')
        parts.append(f'<text x="{tx + 18}" y="{ty + 86}" fill="{muted}" font-size="13" font-family="Fira Code">{src}</text>')
    parts.append(f'<text x="40" y="{H - 22}" fill="{muted}" font-size="14" font-family="Fira Code">Blue = can be shown as stored · amber = needs a translation in the History view. The data table is under the figure.</text>')
    parts.append("</svg>")
    svg = "\n".join(parts)
    (OUT / "fig_archive_truth.svg").write_text(svg, encoding="utf-8")
    (OUT / "fig_archive_truth.png").write_bytes(render_svg_to_png(svg))
    print("wrote fig_archive_truth")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig_history_view()
    fig_act_and_restore()
    fig_two_views_map()
    fig_consensus()
    fig_archive_truth()
