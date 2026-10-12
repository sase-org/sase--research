"""Lead-researcher variant of cld's card prototype: pin every decision.

The current card scrolls inside its own slot whose max-height leaves one
line per other decision, so no decision id ever leaves the rail.
Usage: pinned_index_proto.py CLD_PROTO_PATH WIDTH HEIGHT OUT.png [keys...]
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

from textual.containers import VerticalScroll

spec = importlib.util.spec_from_file_location("cldproto", sys.argv[1])
cld = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cld)


class PinnedRows(cld.ProtoDecisionRows):
    def compose(self):
        for index, row in enumerate(self._rows):
            with VerticalScroll(id=f"plan-decision-slot-{index}", classes="decision-slot"):
                yield cld.DecisionCard(
                    self._render_row(index, row),
                    id=f"plan-decision-{index}",
                    classes="decision-card",
                )

    def _render_row(self, index, row):
        width = 0
        try:
            width = self.query_one(f"#plan-decision-{index}").content_size.width
        except Exception:
            width = 0
        if index == self._focused_index:
            return cld.expanded(row, width)
        return cld.collapsed(row, lines=0, width=width)

    def refresh_rows(self) -> None:
        super().refresh_rows()
        avail = self.size.height
        others = max(0, len(self._rows) - 1)
        for index in range(len(self._rows)):
            try:
                slot = self.query_one(f"#plan-decision-slot-{index}")
            except Exception:
                continue
            if index == self._focused_index and avail:
                slot.styles.max_height = max(4, avail - others)
            else:
                slot.styles.max_height = None

    def on_resize(self) -> None:
        self.refresh_rows()


EXTRA_CSS = """
PlanApprovalModal .decision-slot { height: auto; scrollbar-size-vertical: 1; }
PlanApprovalModal .decision-card { margin: 0; }
PlanApprovalModal.-gate-review-narrow .gate-review-body > .gate-review-actions { height: 62%; }
"""


async def main(width: int, height: int, out: str, presses: list[str]) -> None:
    cld.view_mod.PlanApprovalViewMixin._decisions_header = cld._proto_header
    cld.view_mod.PlanDecisionRows = PinnedRows
    cld.controls_mod.PlanDecisionRows = PinnedRows
    app = cld.Harness(cld.rail_width(width), None)
    app.CSS += EXTRA_CSS
    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause(0.5)
        for key in presses:
            await pilot.press(key)
            await pilot.pause(0.1)
        await pilot.pause(0.3)
        screen = app.screen
        rows = screen.query_one("#plan-decision-rows")
        visible = []
        for i in range(len(rows._rows)):
            slot = screen.query_one(f"#plan-decision-slot-{i}")
            region = slot.region.intersection(rows.region)
            visible.append((rows._rows[i]["id"], region.height))
        print(width, height, "list h", rows.region.height, "visible slot heights", visible)
        svg = app.export_screenshot(title=f"lead variant {width}x{height} · every decision pinned")
    Path(out).write_bytes(cld.render_svg_to_png(svg))
    print(out)


if __name__ == "__main__":
    _, _, w, h, out, *keys = sys.argv
    asyncio.run(main(int(w), int(h), out, keys))
