"""Standalone visual prototype of the proposed Agents-tab node rail + zoom chrome.

Not SASE code: a Textual mock that approximates the real layout so the design
can be judged as pixels. Rendered through sase's own visual renderer.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from sase.ace.tui.visual_render import render_svg_to_png

SUP = str.maketrans("0123456789+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺")

GOLD = "#FFD700"
GREEN = "#5FD75F"
RED = "#FF5F5F"
PURPLE = "#AF87FF"
QBLUE = "#5F87FF"
ORANGE = "#FFAF00"
CLAN = "#D75FFF"
SESSION = "#00AFFF"
BANNER = "#5FAFFF"
TIER = ["#5FAFFF", "#5FD7AF", "#FFD75F", "#FF87AF"]

RAIL_CONTENT = 6
HINTS = False
HINT_ITER = iter("asdfghjklqwertyuiopzxcv")

# glyph, style
STATUS = {
    "running": ("▶", f"bold {GOLD}"),
    "starting": ("◐", "bold #87D7FF"),
    "queued": ("○", f"bold {QBLUE}"),
    "waiting": ("◷", f"bold {PURPLE}"),
    "ask": ("?", f"bold #1a1a1a on {ORANGE}"),
    "failed": ("✗", f"bold {RED}"),
    "done": ("✓", f"{GREEN}"),
    "done_read": ("✓", f"dim {GREEN}"),
    "stopped": ("Ø", "bold #8787AF"),
    "monitor": ("⚙", "bold #FFAF5F"),
    "gate": ("⋔", "bold #0BCDEC"),
    "proc": ("⚙", "bold #5FD7FF"),
    "step": ("❯", "#87D787"),
}


def node(
    kind: str,
    *,
    guides: list[tuple[str, str]] = (),
    count: int | None = None,
    count_style: str = f"dim {CLAN}",
    unread: bool = False,
    hint: str | None = None,
) -> Text:
    t = Text()
    for g, s in guides:
        t.append(g, style=s)
    glyph, style = STATUS[kind]
    if HINTS and hint is None:
        hint = next(HINT_ITER)
    if hint:
        t.append(hint, style="bold #1a1a1a on #FFFF00")
    else:
        t.append(glyph, style=style)
    if count is not None:
        t.append(str(count), style=count_style)
    pad = RAIL_CONTENT - 1 - t.cell_len
    t.append(" " * max(0, pad))
    t.append("•" if unread else " ", style=f"bold {GOLD}")
    return t


def banner(lead: str, lead_style: str, *, level: int = 0, folded: int | None = None) -> Text:
    t = Text()
    if folded is not None:
        t.append("▸", style=f"bold {GOLD}")
    t.append(lead, style=lead_style)
    rule = "━" if level == 0 else "─"
    tail = "" if folded is None else str(folded)
    n = RAIL_CONTENT - t.cell_len - len(tail)
    t.append(rule * n, style=f"{BANNER}" if level == 0 else "#87D7FF")
    if tail:
        t.append(tail, style=f"bold {GOLD}")
    return t


def blank() -> Text:
    return Text(" " * RAIL_CONTENT)


G1 = [("│", TIER[1])]
G1L = [("└", TIER[1])]
G2 = [("│", TIER[1]), ("└", TIER[2])]


def panels_by_project() -> list[tuple[str, str, list[Text | None], int | None, bool]]:
    """(title markup, border class, rows, highlighted index, focused)."""
    default_rows = [
        banner("s", f"bold {BANNER}"),
        node("ask"),
        node("running", count=3, count_style=f"dim {SESSION}"),
        node("failed", unread=True),
        node("done", unread=True),
        node("done_read"),
        blank(),
        banner("b", f"bold {BANNER}"),
        node("done", unread=True),
        node("done_read"),
    ]
    epic_rows = [
        banner("s", f"bold {BANNER}"),
        node("running", count=7),
        node("running", count=5, unread=True),
        banner("", "", level=1, folded=4),
    ]
    research_rows = [
        banner("s", f"bold {BANNER}"),
        node("running", count=7),
        node("running", guides=G1),
        node("running", guides=G1),
        node("running", guides=G1),
        node("done", guides=G1, unread=True),
        node("running", guides=G1),
        node("waiting", guides=G1),
        node("waiting", guides=G1L),
    ]
    job_rows: list[Text | None] = []
    return [
        ("[#87D7FF]⌂[/]", "", default_rows, None, False),
        ("[#AF87FF]▲[/]", "", epic_rows, None, False),
        ("[#5FD7AF]∴[/]", "-focused-panel", research_rows, 1, True),
        ("[#AFAFAF]▸[/][#FFAF5F]†[/]", "-collapsed", job_rows, None, False),
    ]


def _x(markup: str) -> Text:
    return Text.from_markup(markup)


def panels_expanded() -> list[tuple[str, str, list[Text | None], int | None, bool]]:
    """Same tree as ``panels_by_project`` rendered as (approximate) full rows."""
    B = f"[bold {BANNER}]"
    default_rows = [
        _x(f"{B}▌ sase[/] [{BANNER}]━━━━━━━━━━━━━━━━[/] [dim #5FAFFF]5 agents · 1 running[/]"),
        _x("[#87AFFF]\\[agent][/] [#00D7AF]planner[/] [dim]([/][dim]QUESTION[/][dim])[/] [#FFD75F]planner[/]      [#FFAF5F]✋[/]"),
        _x("[bold #FFD700](RUNNING)[/] [dim #00D7D7]×3[/] [#00AFFF]fix-flaky[/]        [#D7AF5F]🏃[/] [bold]4m[/]"),
        _x("[#87AFFF]\\[agent][/] [#00D7AF]visual-code[/] [dim]([/][bold #FF5F5F]FAILED[/][dim])[/] [#FFD75F]coder[/]   ❌"),
        _x("[#87AFFF]\\[agent][/] 🎭 [#00D7AF]sase[/] [dim]([/][bold #5FD75F]DONE[/][dim])[/] [dim #00D7D7]×5[/]       ✅"),
        _x("[#87AFFF]\\[agent][/] [#00D7AF]notes[/] [dim]([/][bold #5FD75F]DONE[/][dim])[/]          [dim]16:03 · 6m[/]"),
        _x(""),
        _x(f"{B}▌ bob-cli[/] [{BANNER}]━━━━━━━━━━━━━━━━━━━━━━━[/] [dim #5FAFFF]2 agents[/]"),
        _x("[#87AFFF]\\[agent][/] 🦋 [#00D7AF]bob-cli[/] [dim](TALE DONE)[/]          ✅"),
        _x("[#87AFFF]\\[agent][/] [#00D7AF]bob-docs[/] [dim]([/][bold #5FD75F]DONE[/][dim])[/]     [dim]13:49 · 25m[/]"),
    ]
    epic_rows = [
        _x(f"{B}▌ sase[/] [{BANNER}]━━━━━━━━━━━━━━━━━━[/] [dim #5FAFFF]16 agents · 2 running[/]"),
        _x("[bold #FFD700](TESTING)[/] [dim #00D7D7]×7[/] [dim][[/][bold #00D7AF]R1[/] [bold #AF87FF]W4[/] [bold #5FD7FF]D2[/][dim]][/] [#D75FFF]sase-1bf[/]  🏃 [bold]1h53m[/]"),
        _x("[bold #FFD700](RUNNING)[/] [dim #00D7D7]×5[/] [dim][[/][bold #00D7AF]R1[/] [bold #AF87FF]W1[/] [bold #1a1a1a on #FFD700]U1[/] [bold #5FD7FF]D2[/][dim]][/] [#D75FFF]sase-1bd[/] 🏃 [bold]11m[/]"),
        _x("[#87D7FF]▎ sase-1b9[/] [#87D7FF]──────────────────────[/] [dim #5FAFFF]4 agents[/]"),
    ]
    research_rows = [
        _x(f"{B}▌ sase[/] [{BANNER}]━━━━━━━━━━━━━━━━━━━━━━[/] [dim #5FAFFF]7 agents · 4 running[/]"),
        _x("[bold #FFD700](RUNNING)[/] [dim #00D7D7]×7[/] [dim][[/][bold #00D7AF]R4[/] [bold #AF87FF]W2[/] [bold #1a1a1a on #FFD700]U1[/][dim]][/] [#D75FFF]research.h[/] 🏃 [bold]8m[/]"),
        _x("[#5FD7AF]├─[/] 🤖 [#00D7AF].cdx[/] [dim]([/][bold #FFD700]RUNNING[/][dim])[/]             🏃 [bold]8m[/]"),
        _x("[#5FD7AF]├─[/] 🎭 [#00D7AF].cld[/] [dim]([/][bold #FFD700]RUNNING[/][dim])[/]             🏃 [bold]8m[/]"),
        _x("[#5FD7AF]├─[/] 🚀 [#00D7AF].grk[/] [dim]([/][bold #FFD700]RUNNING[/][dim])[/]             🏃 [bold]8m[/]"),
        _x("[#5FD7AF]├─[/] 🦋 [#00D7AF].mus[/] [dim]([/][bold #5FD75F]DONE[/][dim])[/]                ✅"),
        _x("[#5FD7AF]├─[/] 🪐 [#00D7AF].gem[/] [dim]([/][bold #FFD700]RUNNING[/][dim])[/]             🏃 [bold]8m[/]"),
        _x("[#5FD7AF]├─[/] [#00D7AF].final[/] [dim]([/][bold #AF87FF]WAITING[/] [bold #AF87FF]▶5[/][dim])[/]"),
        _x("[#5FD7AF]└─[/] [#00D7AF].image[/] [dim]([/][bold #AF87FF]WAITING[/] [bold #AF87FF]▶1[/][dim])[/]"),
    ]
    return [
        ("[#87D7FF]⌂ @default[/] [dim]· 9 [[/][bold #FFAF00]S1[/] [bold #00D7AF]R1[/] [bold #FF5F5F]F1[/] [bold #1a1a1a on #FFD700]U3[/] [bold #5FD7FF]D6[/][dim]][/]", "", default_rows, None, False),
        ("[#AF87FF]▲ @epic[/] [dim]· 16 [[/][bold #00D7AF]R2[/] [bold #AF87FF]W5[/] [bold #1a1a1a on #FFD700]U1[/] [bold #5FD7FF]D8[/][dim]][/]", "", epic_rows, None, False),
        ("[#5FD7AF]∴ @research[/] [dim]· 7 [[/][bold #00D7AF]R4[/] [bold #AF87FF]W2[/] [bold #1a1a1a on #FFD700]U1[/][dim]][/]", "-focused-panel", research_rows, 1, True),
        ("[#AFAFAF]▸[/] [#FFAF5F]† @job[/] [dim]· 2 [[/][bold #00D7AF]R1[/] [bold #AF87FF]W1[/][dim]][/]", "-collapsed", [], None, False),
    ]


CSS = """
Screen { background: #121212; layout: vertical; }
#rail.-expanded { width: 58; }
#rail.-expanded RailPanel { border-title-align: left; }
#rail.-expanded RailPanel > .option-list--option { padding: 0 1; }
#tabs { height: 1; background: #1e1e1e; }
#info { height: 1; background: #1e1e1e; }
#main { height: 1fr; }
#rail { width: 9; height: 100%; }
#rail.hidden { display: none; }
RailPanel {
    width: 100%;
    height: auto;
    border: solid #3a6ea5;
    border-title-align: center;
    padding: 0;
    scrollbar-size-vertical: 0;
    background: #1e1e1e;
    text-wrap: nowrap;
    text-overflow: clip;
}
RailPanel.fill { height: 1fr; }
RailPanel.-focused-panel { border: solid #FFD700; }
RailPanel.-collapsed { height: 2; border-bottom: none; }
RailPanel > .option-list--option { padding: 0 0 0 1; }
RailPanel > .option-list--option-highlighted {
    background: #5b4a80 60%;
    text-style: bold;
    border-left: thick #b48ead;
    padding: 0;
}
#detail { width: 1fr; height: 100%; }
#identity { height: 5; border: solid #b8a200; border-title-color: #FFD700; border-title-style: bold; padding: 0 1; }
#deck { height: 1fr; border: solid #2a9d8f; padding: 1 2; }
#deck.-zoomed { border: heavy #2a9d8f; }
#footer { height: 2; background: #1e1e1e; }
#rail-sep { width: 1; }
"""


class RailPanel(OptionList):
    pass


class Proto(App):
    CSS = CSS

    def __init__(self, scene: str) -> None:
        super().__init__()
        self.scene = scene

    def compose(self) -> ComposeResult:
        yield Static(
            Text.from_markup(
                " [bold #87D7FF]Agents[/]  [dim]│[/]  [dim]Artifacts[/]  [dim]│[/]  [dim]Services[/]"
            ),
            id="tabs",
        )
        yield Static(self._info_text(), id="info")
        with Horizontal(id="main"):
            rail_cls = {"zoom": "hidden", "expanded": "-expanded"}.get(self.scene, "")
            source = panels_expanded() if self.scene == "expanded" else panels_by_project()
            with Vertical(id="rail", classes=rail_cls):
                for i, (title, cls, rows, hl, _focused) in enumerate(source):
                    classes = cls
                    if i == 0:
                        classes += " fill"
                    panel = RailPanel(
                        *[Option(r) for r in rows], classes=classes.strip()
                    )
                    panel.border_title = Text.from_markup(title)
                    if i == 0 and self.scene != "expanded":
                        panel.border_subtitle = Text.from_markup("[dim]▾2[/]")
                    panel._proto_hl = hl
                    yield panel
            with Vertical(id="detail"):
                ident = Static(self._identity_text(), id="identity")
                ident.border_title = Text.from_markup("[bold #FFD700]CLAN[/]")
                ident.border_subtitle = Text.from_markup("[#b8a200]▾ d more[/]")
                yield ident
                deck = Static(self._deck_text(), id="deck")
                deck.border_title = self._deck_title()
                deck.border_subtitle = self._deck_subtitle()
                if self.scene == "zoom":
                    deck.add_class("-zoomed")
                yield deck
        yield Static(self._footer_text(), id="footer")

    def on_mount(self) -> None:
        for panel in self.query(RailPanel):
            hl = getattr(panel, "_proto_hl", None)
            panel.highlighted = hl

    def _info_text(self) -> Text:
        t = Text.from_markup(
            "[bold]22[/] [dim][[/][bold #00D7AF]6[/] [dim]running ·[/] [bold #AF87FF]7[/] [dim]waiting ·[/] "
            "[bold #1a1a1a on #FFD700]4 unread[/] [dim]·[/] [bold #5FD7FF]5[/] [dim]done][/]"
        )
        if self.scene == "zoom":
            t.append(" · ", style="dim")
            t.append(" ZOOM ", style=f"bold #1a1a1a on {GOLD}")
            t.append(" nodes ", style="dim")
            t.append("12/22", style="bold")
            t.append(" · Z", style="dim")
        t.append(" · group: ", style="dim")
        t.append("by project", style="bold #5FAFFF")
        t.append(" (o)", style="dim")
        return t

    def _identity_text(self) -> Text:
        return Text.from_markup(
            "[#D75FFF]research.h[/] [bold #FFD700]RUNNING[/] [dim][[/][bold #00D7AF]R4[/] [bold #AF87FF]W2[/] "
            "[bold #1a1a1a on #FFD700]U1[/][dim]][/]\n[bold #5FD7AF]@research[/] [dim]·[/] 7 agents [dim]·[/] [bold]8m22s[/]"
        )

    def _deck_title(self) -> Text:
        t = Text()
        if self.scene == "zoom":
            t.append(" ZOOM ", style=f"bold #1a1a1a on {GOLD}")
            t.append(" ")
        t.append("◆ ", style="#2a9d8f")
        t.append("MAIN", style="bold #2a9d8f")
        t.append(" spread", style="#2a9d8f")
        t.append(" · auto ", style="dim")
        t.append("┃ ", style="dim")
        t.append("Summary", style="bold #e0e0e0 on #1f5f58")
        return t

    def _deck_subtitle(self) -> Text:
        t = Text()
        if self.scene == "zoom":
            t.append("◧ 1 of 2 panels", style=f"{GOLD}")
            t.append(" · ", style="dim")
            t.append("Z", style=f"bold {GOLD}")
            t.append(" restore", style="dim")
            t.append("  ")
        t.append("main 1", style="bold #2a9d8f")
        t.append(" · files 0 · tools 0", style="dim #2a9d8f")
        return t

    def _deck_text(self) -> Text:
        return Text.from_markup(
            "[bold]RESEARCH PROMPT:[/] We currently support collapsing the nav sidebar on\n"
            'the "Agents" tab via the `<ctrl+s>` keymap.\n\n'
            "- We also support zooming in on a single deck using the `Z` keymap, in\n"
            "  which case the sidebar is also collapsed.\n"
            "- When the sidebar is collapsed, it is completely invisible currently.\n"
            "- Instead, every tribe, agent group (e.g. \"Running\"), and node should\n"
            "  be represented still, just in a collapsed, fixed width state.\n"
        )

    def _footer_text(self) -> Text:
        if self.scene == "zoom":
            return Text.from_markup(
                " [bold #00D7AF]Z[/] restore layout   [bold #00D7AF]Ctrl+S[/] restore layout   "
                "[bold #00D7AF]j/k[/] move selection   [bold #00D7AF]Ctrl+N/P[/] cycle decks"
            )
        return Text.from_markup(
            " [bold #00D7AF]Ctrl+S[/] expand nodes   [bold #00D7AF]Z[/] zoom deck   "
            "[bold #00D7AF]j/k[/] move   [bold #00D7AF]'[/] jump hints   [bold #00D7AF]\"[/] node finder"
        )


async def main(scene: str, out: Path, size: tuple[int, int]) -> None:
    app = Proto(scene)
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        await pilot.pause()
        svg = app.export_screenshot(title=f"PROTOTYPE · {scene}")
    out.write_bytes(render_svg_to_png(svg))
    print(out)


if __name__ == "__main__":
    scene = sys.argv[1]
    if scene == "hints":
        HINTS = True
        scene = "rail"
    out = Path(sys.argv[2])
    cols, rows = (int(x) for x in sys.argv[3].split("x")) if len(sys.argv) > 3 else (120, 40)
    asyncio.run(main(scene, out, (cols, rows)))
