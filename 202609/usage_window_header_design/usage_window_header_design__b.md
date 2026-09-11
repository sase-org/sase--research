# Usage-Window Indicator Presentation (Researcher B)

**Date:** 2026-09-11
**Scope:** Presentation only — separators, spacing, grouping structure, field layout,
emphasis (weight), disclosure ladder, and placement in the ACE top bar.
**Explicitly out of scope (per request):** hues, icons/glyphs, and *which* values are
shown. Anything in this report that brushes those is quarantined in
[§8 Out of scope](#8-out-of-scope-observations-not-part-of-the-recommendation) and is
**not** part of the recommendation.

---

## 1. What ships today (verified, not remembered)

### 1.1 Code under review

| File | Role |
| --- | --- |
| `src/sase/ace/tui/widgets/_provider_usage_indicator.py` | Grouping + segment assembly + disclosure ladder |
| `src/sase/ace/tui/widgets/_usage_indicator_format.py` | Percent / countdown / compact-name text |
| `src/sase/ace/tui/widgets/_usage_indicator_palette.py` | Badge surface, gap surface, weight/color styles |
| `src/sase/ace/tui/widgets/provider_disables_indicator.py` | Host widget (routing pills **+** usage), budget, click, tooltip |
| `src/sase/ace/tui/_app_layout.py:68-84` | `#top-bar` child order |
| `src/sase/ace/tui/styles.tcss:9-64` | `width: auto` on every indicator, `1fr` on `#tab-bar` |

### 1.2 The rendered grammar

Constants in `_provider_usage_indicator.py:32-35`:

```python
_OUTER_PADDING    = "  "   # gap surface, both ends of the block
_PROVIDER_GAP     = "  "   # gap surface, between provider groups
_WINDOW_SEPARATOR = " | "  # badge surface, between windows inside one group
_DISCLOSURE_GAP   = "  "   # gap surface, before "+N"
```

Plus conditional `(` … `)` around a provider group **iff** it has ≥ 2 *visible* windows
(`_render_visible_windows`, `parenthesized = len(fragments) >= 2`).

I rendered the real code against a realistic steady state (Claude weekly-all + Claude
`fable`, Codex weekly, Grok weekly — which is what `default_config.yml` produces out of
the box, since `weekly_all: always` and `"weekly:claude-fable-5": always`):

```
'  🎭 (62% 3d4h | fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h  '
```

- Rich reports **61 cells**; a real terminal renders **62** (see §4.7).
- This matches the committed snapshot
  `tests/ace/tui/visual/snapshots/png/top_bar_usage_groups_real_projection_140x24.png`.

### 1.3 The measured disclosure ladder

Driving `build_usage_indicator_segment` across every budget from 61 down to 1:

| Budget | Rendered | Width | Waste |
| ---: | --- | ---: | ---: |
| 61 | `  🎭 (62% 3d4h \| fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h  ` | 61 | 0 |
| 60 | `  🎭 (62% 3d4h \| fable 100% 1d8h)  🤖 45% 2d5h  +1  ` | 52 | 8 |
| 51 | `  🎭 (62% 3d4h \| fable 100% 1d8h)  +2  ` | 39 | 12 |
| 38 | `  🎭 62% 3d4h  +3  ` | 19 | 19 |
| 18 | `  usage 4  ` | 11 | 7 |
| 10 | `  4  ` | 5 | 5 |
| 4 | ` 4 ` | 3 | 1 |
| 2 | `4` | 1 | 1 |

The "Waste" column is the point: at a budget of 38 cells the indicator paints 19 and
leaves 19 empty. Half the space it was granted goes unused because the only unit it can
drop is an entire window, and the cheapest droppable window costs 20 cells
(`fable 100% 1d8h` = 15, ` | ` = 3, `( )` = 2).

### 1.4 The top bar it lives in

```
#top-bar (Horizontal, max-height: 1)
  #tab-bar                     width: 1fr     <- the only flexible child
  #proc-indicator              width: auto
  #monitor-indicator           width: auto
  #updates-indicator           width: auto
  #llm-override-indicator      width: auto
  #alias-overrides-indicator   width: auto
  #provider-disables-indicator width: auto    <- routing pills AND usage block
  #current-project-indicator   width: auto
  #stashed-prompts-indicator   width: auto
  #notification-indicator      width: auto
```

Budget: `min(top_bar_width − routing − 1 − Σ(other siblings), top_bar_width // 2)`
(`provider_disables_indicator.py:227-244`). So at 120 columns the cap is 60; at 160 it
is 80.

---

## 2. The house grammar the usage block is violating

ACE already has a consistent, unwritten chip grammar. Three other widgets obey it; the
usage block is the only one that does not.

| Widget | Chip shape | Separator between chips | Overflow |
| --- | --- | --- | --- |
| `gear_chip` (proc / monitor) | `" {glyph} {count} "` — 1 cell pad inside the fill | n/a | n/a |
| `build_override_pill` | `" {subject}"` + `"@{effort}"` + `" {trailing} "` — 1 cell pad inside the accent | pills abut (no gap) | n/a |
| `NotificationIndicator` | `"{icon}{count}"` colored text | **one space, no punctuation** | `" +{n}"`, dim |
| **usage block** | `icon + " " + "(" + w + " \| " + w + ")"` | two spaces | `"  +{n}"` |

`NotificationIndicator`'s own docstring states the principle explicitly:

> "Each chip identifies itself, so the badge carries no `✉` anchor and **no separators**
> once it has chips to show."

That is exactly the right instinct, and the usage block is the one place it was not
applied. The usage block is also the only widget in the bar that uses parentheses or a
pipe at all.

---

## 3. Diagnosis

Ten concrete defects, ordered by how much they hurt a one-second glance.

### 3.1 The separator hierarchy is inverted

Within a provider, windows are separated by ` | ` — a full-height, high-contrast glyph.
Between providers — the *stronger* semantic boundary — the separator is two spaces,
i.e. nothing at all.

Gestalt proximity and common region both say the opposite: members of a group should be
*tighter* than the gap between groups, and the loudest divider should mark the
outermost boundary. Today the loudest mark sits at the innermost boundary. The eye
parses `62% 3d4h | fable 100% 1d8h` as two peers and `) 🤖` as continuation, which is
backwards.

### 3.2 Structure is conditional, so it cannot be learned

Parentheses appear only when a provider has ≥ 2 *visible* windows. They therefore:

- appear and disappear as windows cross their display policy thresholds,
- **disappear under truncation** — a group normally rendered `(a | b)` becomes a bare
  `a` plus `+1` when the budget tightens.

A user who learns "Claude is the one in parentheses" is wrong as soon as the terminal is
resized. Shape that flickers is shape you re-parse every time.

### 3.3 Every field looks identical, so nothing is the answer

`_entry_fragment` paints the compact name, the percent, and the countdown all with
`usage_value_style` = **bold + the same capacity color**, joined by single spaces:

```
fable 100% 1d8h      <- three bold tokens, one color, two identical spaces
```

Three different kinds of thing (a label, a quantity, a duration) with one visual weight.
The reader must lexically parse `%` versus `d`/`h`/`m` to tell the quantity from the
duration. Meanwhile the codebase's own `_PillPalette` already establishes the correct
pattern next door — *subject in primary, trailing state in a recessive secondary*
(`_override_pill.py:23-36`) — and the usage block simply does not use it.

### 3.4 Nothing is column-aligned, so the whole right side of the bar twitches

Both numeric fields are variable width:

- percent ∈ {`0%`, `<1%`, `62%`, `100%`} → 2–4 cells
- countdown, measured from the real `format_usage_countdown`:

  | seconds left | rendered | cells |
  | ---: | --- | ---: |
  | 540 | `0h9m` | 4 |
  | 600 | `0h10m` | 5 |
  | 3 540 | `0h59m` | 5 |
  | 3 600 | `1h0m` | 4 |
  | 36 000 | `10h0m` | 5 |
  | 86 340 | `23h59m` | 6 |
  | 86 400 | `1d0h` | 4 |

The countdown changes width **roughly twice an hour per window** (every time the minutes
field crosses 10, and again at the hour and day boundaries), and the widget repaints
every 30 s. With four windows that is on the order of eight width changes an hour.

Because `#tab-bar` is the sole `1fr` child and sits at position 0, a child's x-position
is `x_i = W_total − Σ_{j ≥ i} w_j`. Changing the usage block's width therefore shifts
**itself and every indicator to its left** — today that is `proc`, `monitor`, `updates`,
`llm-override`, and `alias-overrides`. Five unrelated badges slide sideways because a
countdown ticked from `3h10m` to `3h9m`. That is the single biggest reason the bar
"feels unfinished."

### 3.5 The click target is hijacked

`ProviderDisablesIndicator.on_click` takes no event and therefore has no click offset:

```python
async def on_click(self) -> None:
    if self._usage_open_provider:          # non-None whenever ANY window is displayed
        await self.app.run_action("open_provider_usage")
        return
    await self.app.run_action("open_models_panel")
```

`usage_indicator_open_provider` returns `groups[0].provider if groups else None`. So
whenever any usage window is displayed — which, with `weekly_all: always`, is
essentially always — clicking the `CLAUDE off ∞` disable pill opens Providers · Usage
instead of Launch settings. `docs/ace.md` promises "Clicking **rendered usage or
overflow** opens Providers · Usage"; one `Static` with one handler cannot honor that.
The same conflation gives both objects a single merged tooltip, which is why that
tooltip has grown to ~15 lines with two headings and its own notation legend.

### 3.6 The overflow marker collides with the project chip

At 80 columns the bar reads (verified from
`top_bar_usage_partial_group_overflow_80x24.png`):

```
🎭 62% 3d4h  +3   +sase
```

Two `+`-prefixed tokens, different meanings, three cells apart. `+3` means "3 hidden
usage windows"; `+sase` means "current project". Adjacency is the whole problem.

### 3.7 The chip rectangle hugs its glyphs, and is broken by the `0%` state

The badge surface (`#242830`) starts exactly at the icon and ends exactly at the last
character — no internal padding, unlike every other chip in the bar. The rectangle the
palette docstring promises ("a badge reads as a distinct rectangle") therefore reads as
a faint tint rather than a chip.

Worse, `usage_zero_value_style` inverts the **entire** `0% <countdown>` run. In the
three-window Claude group the chip contains three different background treatments in 30
cells:

```
🎭 (62% 3d4h | fable 0% 1d8h | 5h 18% 2h9m)
             ^^^^^^        ^^^^^^^^
             badge surface  inverted red block, 7 cells, mid-string
```

(committed as `top_bar_usage_claude_three_windows_140x24.png`). The alarm is correct;
its *extent* is what breaks the chip geometry.

### 3.8 The disclosure ladder wastes space, then discards the signal

Two separate problems:

1. **Granularity.** §1.3 shows up to 19 wasted cells because the smallest droppable unit
   is a whole window and there is no cheaper concession available (no spacing tier).
2. **Terminal state.** Below 18 cells the block becomes `usage 4` → `4` → `…`. The last
   thing standing is a *cardinality*. Nobody glances at this indicator to learn how many
   windows exist; they glance to learn whether they are about to run out.

### 3.9 Chips reorder themselves under stress

`usage_indicator_groups` sorts groups by `(-group_rank, provider)`, i.e. by attention
severity first. So when Grok drops into `very_low`, the Grok chip *moves to the front*
and Claude/Codex shift right. Position is the cheapest landmark a status bar has, and
this design spends it on a signal that color already carries — and destroys it at
exactly the moment (low capacity) when the user most needs to find a specific provider
fast.

The severity sort does buy one real thing: because truncation keeps a left prefix, the
most urgent window is the last to be hidden. The fix is to decouple the two (see §6, S5),
not to abandon either.

### 3.10 Two emoji are measured at half their rendered width

`_prefix_cell_widths` and the badge surface both measure via `Text(...).cell_len`:

```
🎭 claude   cell_len=2   (U+1F3AD, East-Asian Wide)
🤖 codex    cell_len=2
🛰️ grok     cell_len=1   (U+1F6F0 + U+FE0F — Neutral + Ambiguous)
♾️ muse     cell_len=1   (U+267E  + U+FE0F)
```

Every mainstream terminal renders both of those as 2 cells (emoji presentation forced by
the variation selector). Consequences for a Grok or Muse group: the painted rectangle
ends one cell short of the text, and the budget arithmetic under-counts by one per
group — so the "fits half the bar" calculation can overflow. This is a layout bug, not
an icon question; the icon itself stays exactly as it is.

---

## 4. Design space

I evaluated six presentations against five criteria: glance latency, positional
stability, cell cost, degradation quality, and consistency with the rest of the bar.

| Option | Glance | Stability | Cells | Degradation | Consistency |
| --- | --- | --- | --- | --- | --- |
| **A.** Status quo | poor | poor | 62 | cliffy | poor |
| **B.** Keep parens, quiet the pipe (` \| ` → ` · `) | fair | poor | 62 | cliffy | poor |
| **C.** Drop punctuation; chip = common region | good | poor | 58–60 | cliffy | **good** |
| **D.** C + weight hierarchy + field alignment | **best** | good | 60–69 | cliffy | good |
| **E.** D + spacing-tier disclosure ladder | **best** | **best** | 51–69 | **graceful** | good |
| **F.** Dedicated second row | best | best | n/a | n/a | n/a |

**Rejected — B.** A quieter mid-dot still leaves the inner boundary marked and the outer
boundary unmarked, keeps the conditional parentheses, and costs the same 3 cells. It
treats the symptom.

**Rejected — F (own row).** A second row is the only way to get a genuinely spacious
layout, and it would be positionally perfect. It is rejected because the request is
explicitly for something "very concise" that is "always shown at the top," and a
permanent row costs ~4 % of a 24-row terminal for information that is ambient. The
top bar already has `max-height: 1` and a Header above it; a third band would make the
chrome taller than the AXE dashboard header.

**Rejected — one chip for everything** (`[🎭 62% · 🤖 45% · 🛰 97%]`). Collapsing to a
single rectangle destroys per-provider common region and forces punctuation back in.

**Rejected — moving it out of the top bar** (footer, link rail). The request specifies
the top.

**Recommended — E**, specified in §6.

### 4.1 Why the chip is the right grouping device

The block already paints a per-group background. A painted region *is* the strongest
grouping cue available in a terminal — stronger than any punctuation, and it costs zero
extra cells because it is already being painted. Once the chip carries the grouping,
`(`, `)` and `|` are pure redundancy: 5 cells per multi-window group spent re-stating
something the background already says, and spent *conditionally* so it cannot be
learned.

### 4.2 Why weight, not color, is the emphasis lever here

The palette constraint ("don't mess with the colors") is not a limitation — it is the
right constraint. Color in this block is already fully committed to a semantic: the
ten-bucket capacity gradient. Overloading it with a second meaning (field role) would
be the wrong move even if it were permitted. **Weight** is the free axis, and it is
currently unused: everything is bold, so bold means nothing.

Making exactly one token per window bold — the percentage — gives each window a single
visual anchor. A four-window block then has exactly four heavy tokens, and you can count
and read the block without parsing any characters at all.

### 4.3 Why fixed-width fields, and why they should be the first thing sacrificed

Right-aligning the percent into 4 cells and the countdown into 5 removes intra-block
shimmer completely: the block's width then changes only when the *set* of windows
changes (rare), not on every tick. It also aligns the numbers into columns, which is
what makes a dense numeric strip scannable.

It costs ~9 cells for a four-window block. The resolution is to make that padding the
**first** concession in the disclosure ladder rather than a fixed tax: pad when there is
room, collapse when there is not. Wide terminals get a stable aligned strip; narrow ones
get more information instead of more whitespace.

### 4.4 Why placement is a stability decision, not a taste decision

From `x_i = W_total − Σ_{j ≥ i} w_j`: widening child *i* moves child *i* and every child
**left** of it, and leaves every child **right** of it untouched. The volatile widget
should therefore be as far **left** in the auto-width cluster as possible. Moving the
usage block to the first slot after `#tab-bar` makes it the *only* thing in the bar that
ever moves, and pins its own right edge (since everything to its right is fixed).

---

## 5. What "best possible" looks like

Current (real, 62 cells):

```
CODEX(model)  🎭 (62% 3d4h | fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h  +sase 🚩 ✉18
              └─── one long rectangle, punctuation-heavy ───┘
```

Proposed, **aligned tier** (≈ 69 cells, terminals ≥ ~140 columns) — `▒` marks the
painted chip surface, which is already there today:

```
▒ 🎭  62%  3d4h  fable 100%  1d8h ▒  ▒ 🤖  45%  2d5h ▒  ▒ 🛰️  97%  1d7h ▒
  └──┬──┘ └─┬─┘  └──┬──┘
   bold  normal   normal weight
```

Proposed, **relaxed tier** (60 cells — one cell *narrower* than today, and it shows the
same four windows that today's 62-cell render shows):

```
▒ 🎭 62% 3d4h  fable 100% 1d8h ▒ ▒ 🤖 45% 2d5h ▒ ▒ 🛰️ 97% 1d7h ▒
```

Proposed, **tight tier** (51 cells — where today's ladder has already dropped two
windows):

```
▒🎭 62% 3d4h fable 100% 1d8h▒ ▒🤖 45% 2d5h▒ ▒🛰️ 97% 1d7h▒
```

Top bar, before and after (140 columns):

```
before:  Agents │ Artifacts │ AXE      CODEX(model)  🎭 (62% 3d4h | fable 100% 1d8h)  🤖 45% 2d5h  🛰️ 97% 1d7h  +sase 🚩 ✉18
after:   Agents │ Artifacts │ AXE   ▒🎭 62% 3d4h  fable 100% 1d8h▒ ▒🤖 45% 2d5h▒ ▒🛰️ 97% 1d7h▒   CODEX(model)  +sase 🚩 ✉18
                                    └──────── only thing in the bar that ever moves ────────┘
```

---

## 6. Recommendation

Eight changes. S1–S4 are the presentation redesign proper; S5–S8 are the structural
fixes that make it hold still and behave.

### S1 — One chip per provider, zero punctuation

Delete `(`, `)`, and ` | `. Let the painted chip carry the grouping.

```
chip  ::= PAD ICON SP window (WSEP window)* PAD        # all on the badge surface
block ::= OUTER chip (GAP chip)* [GAP overflow] OUTER  # GAP/OUTER unpainted
overflow ::= PAD "+" N PAD                             # its own mini-chip
```

Spacing per tier:

| | `OUTER` | `GAP` | `PAD` | `WSEP` |
| --- | :-: | :-: | :-: | :-: |
| aligned | 1 | 2 | 1 | 2 |
| relaxed | 1 | 1 | 1 | 2 |
| tight | 0 | 1 | 0 | 1 |

Salience now increases strictly with the boundary's importance: *field* = 1 space, same
background → *window* = 2 spaces, same background → *provider* = padded chip edge +
unpainted gap (a background change) → *block* = unpainted margin against a differently
styled neighbor. And the structure is unconditional: a one-window chip and a
three-window chip are the same shape, and truncation never changes a chip's shape.

The `PAD` also brings the chip in line with `gear_chip` and `build_override_pill`, which
both already pad one cell inside their fill.

### S2 — One bold token per window

```
window ::= [name SP] [marker SP] percent SP countdown
           normal      bold-red    BOLD      normal
```

- `name`: normal weight, same capacity color as today (today: bold)
- `percent`: **bold**, same capacity color as today (unchanged)
- `countdown`: normal weight, same capacity color as today (today: bold)

No hue changes anywhere — this reassigns weight only, using styles that already exist
(`usage_value_style` for bold, a normal-weight sibling built from the same color). It
mirrors `_PillPalette.base_style` / `.secondary_style` exactly, so the usage block
finally speaks the same dialect as the pill sitting next to it.

Additionally: narrow the `0%` inversion from `0% <countdown>` to the **percent field
only**. Inverted red on a dark chip is maximally salient at 2–4 cells; extending it
across 7+ cells is what fractures the chip rectangle (§3.7). The alarm survives intact;
the geometry stops breaking.

### S3 — Fixed-width numeric fields (aligned tier)

- percent right-aligned into 4 cells — `100%`, ` 62%`, ` <1%`, `  0%`
- countdown right-aligned into 5 cells — ` 3d4h`, `10h5m`, ` 2h9m`

Padding carries the field's own style, so the `0%` alarm becomes a uniform 4-cell block
rather than a ragged 2–4. `23h59m` (6 cells) and `0h0m↻` are the two states that exceed
the field; they occur for about a minute a day per window, and are the accepted residual.

Result: the block's width is a pure function of *which* windows are displayed. A ticking
countdown never moves anything.

### S4 — Three-tier disclosure ladder

Replace "longest complete prefix that fits" with: **maximize windows shown; spend
leftover room on legibility.**

```
for keep in (N ... 1):
    for tier in (aligned, relaxed, tight):
        if width(keep, tier) <= budget:
            return render(keep, tier)
return fallback_ladder()
```

Measured widths for the default four-window steady state (all figures counting the Grok
emoji at its true 2 cells):

| windows kept | aligned | relaxed | tight | **today** |
| ---: | ---: | ---: | ---: | ---: |
| 4 | 69 | 60 | **51** | 62 |
| 3 | 58 | 51 | **42** | 52 |
| 2 | 41 | 37 | **30** | 39 |
| 1 | 23 | 20 | **14** | 19 |

What the user actually sees, by budget:

| budget | today | proposed |
| ---: | ---: | --- |
| 80 | 4 windows | 4 windows, aligned |
| 62 | 4 windows | 4 windows, relaxed |
| **60** | **3 windows** | **4 windows, relaxed** |
| **55** | **3 windows** | **4 windows, tight** |
| **51** | **2 windows** | **4 windows, tight** |
| **45** | **2 windows** | **3 windows, tight** |
| **36** | **1 window** | **2 windows, tight** |
| 25 | 1 window | 1 window, aligned |
| **14** | **`usage 4`** | **1 window, tight** |

At 120 columns the budget cap is exactly 60, so this change alone takes the default
configuration from three visible windows to four on a 120-column terminal — with no new
information and no extra cells.

Two riders:

- Add hysteresis on tier transitions (drop a tier only when short, regain only with ≥ 2
  cells spare) so an adjacent pill appearing cannot start a flip-flop.
- Render `+N` as its own padded mini-chip so it reads as "and N more of *these*" and is
  visually bound to the block rather than floating toward `+sase`.

### S5 — Stable chip order; severity drives *selection*, not *position*

Render provider chips in a stable order (registry order, or alphabetical). Keep severity
as the rule for deciding **which** windows get hidden when the budget bites. Position
becomes a learnable landmark; color keeps carrying urgency; the most urgent window is
still the last to go.

### S6 — Split the widget

Extract a `UsageWindowsIndicator(Static)` from `ProviderDisablesIndicator`, with its own
`id`, its own tooltip, and its own `on_click` → `open_provider_usage`. The disable and
priority pills keep `open_models_panel`.

This fixes §3.5 outright, lets the enormous merged tooltip split into two focused ones,
removes the `_append_usage_content` / `_usage_segment_budget` coupling, and is a
prerequisite for S7 (you cannot position the usage block independently while it is glued
to the routing pills).

### S7 — Move it to the first slot after `#tab-bar`

```python
with Horizontal(id="top-bar"):
    yield TabBar(id="tab-bar")
    yield UsageWindowsIndicator(id="usage-windows-indicator")   # <- volatile, leftmost
    yield ProviderDisablesIndicator(id="provider-disables-indicator")
    yield ProcIndicator(id="proc-indicator")
    ...                                                          # all now positionally fixed
```

Per §4.4 this makes the usage block the only widget in the bar whose position ever
changes, and pins its own right edge. It also resolves §3.6 for free: `+N` is no longer
adjacent to `+sase`.

*Optional hardening:* set `#tab-bar { width: auto; }` and insert a `width: 1fr` spacer
after it. The flex then sits between navigation and status, so the tab labels stop
reflowing across their truncation thresholds when the usage block breathes.

### S8 — Measure emoji in rendered cells

Introduce a display-width helper that treats a grapheme cluster ending in U+FE0F as 2
cells, and use it everywhere the block measures itself (`UsageProviderGroup.icon_width`,
`UsageWindowFragment.width`, `_prefix_cell_widths`, `_rendered_cell_width`). Without
this, every Grok or Muse chip is one cell short of its own text and the budget can
overflow. The icons themselves are untouched.

### If you only do three of these

1. **S7** (placement) — one line in `_app_layout.py`, and the bar stops twitching.
2. **S1 + S2** (no punctuation, one bold token) — the legibility payoff, at *negative*
   cell cost.
3. **S4** (spacing-tier ladder) — one more window visible across the whole practical
   width range.

### Blast radius

| Surface | Impact |
| --- | --- |
| `_provider_usage_indicator.py` | Rewrite `_render_visible_windows`, `_prefix_cell_widths`, `build_usage_indicator_segment`; split the widget |
| `_usage_indicator_palette.py` | Add a normal-weight sibling of `usage_value_style`; no new hues |
| `provider_disables_indicator.py` | Extract usage; restore the disable pill's own click action |
| `_app_layout.py`, `styles.tcss` | Child order; new `#usage-windows-indicator` rule |
| `tests/test_provider_usage_indicator_presentation.py` | ~31 tests; the `\|`/`( )` assertions all go away |
| `tests/ace/tui/visual/snapshots/png/top_bar_usage_*` | 12 PNG snapshots regenerate |
| `docs/ace.md:3398-3440` | The grammar paragraph and the tooltip notation legend shrink substantially |

The doc shrinkage is itself a signal. Today `docs/ace.md` needs a 90-word paragraph to
explain when parentheses appear and what the pipes mean, and the tooltip ships a
"Notation:" legend. A grammar that needs a legend in its own tooltip is a grammar that
is doing too much. After S1 the paragraph is: *one chip per provider; the chip holds
that provider's windows; the bold number is remaining capacity.*

---

## 7. What I deliberately did not change

- **Colors.** No hue is added, removed, or reassigned. S2 moves weight only; S3 pads
  with the field's existing style.
- **Icons.** Unchanged. S8 changes how they are *measured*, not what they are.
- **Content.** Same windows, same percentages, same countdown strings, same `!`, `↻`,
  `?`, `<1%`, and compact-name vocabulary. S3 pads existing strings; it does not
  reformat them.
- **Selection policy.** `llm_provider.usage_metrics.indicator` semantics are untouched.
  S5 changes render *order*, not which windows qualify.

---

## 8. Out-of-scope observations (not part of the recommendation)

Recording these because they are real, not because I am proposing them.

1. **The gap background is hard-coded and ignores the active theme.**
   `usage_gap_style` paints `#121212` (dark) / `#FAFAFA` (light) regardless of which
   Textual theme is active, and `_current_dark_theme()` only distinguishes dark from
   light. Under any theme whose background is not those exact values, the "gaps" render
   as visible mismatched rectangles rather than disappearing. Leaving the gaps unstyled
   so the parent shows through would be theme-correct — but that is a color change, so
   it is your call, not mine.

2. **`usage_rejected_style` omits the attribute guard its siblings carry.** Every other
   style in the palette begins `not bold not dim not reverse` specifically to avoid
   inheriting attributes from an unrelated ancestor; the rejected-marker style does not.

3. **The terminal fallback reports cardinality, not urgency.** `usage 4` → `4` → `…`.
   If you ever want the last surviving pixel to be useful, it should be the worst
   percentage (`🎭 0%`), not the count. That is a content decision.

4. **`0h9m` for "nine minutes".** The forced two-unit countdown spends two cells on a
   zero. `9m` would be narrower *and* clearer. Content decision.

5. **`weekly_all: always` plus `"weekly:claude-fable-5": always`** is what makes the
   default steady state four windows and ~62 cells. Any presentation work is fighting
   that number; a narrower default would change the problem more than any layout will.

---

## 9. Summary

The usage block is not ugly because of its colors or its data — both are good. It is
ugly because it uses a punctuation-based grammar that (a) marks the wrong boundary
loudest, (b) changes shape depending on how many windows happen to be visible, (c) gives
every field identical visual weight so nothing reads as the answer, (d) has no column
alignment so it jitters the entire right half of the top bar twice an hour, and (e)
falls off a cliff into a window count when space runs short.

The fix is to let the painted chip do the grouping it is already paying for, delete the
punctuation, make exactly one token per window bold, align the numbers into columns when
there is room, spend that alignment first when there is not, and move the whole thing to
the one position in the bar where its breathing cannot disturb anything else.

Net cost at the default four-window steady state: **−2 cells** in the relaxed tier,
**+7** in the aligned tier, **−11** in the tight tier — and one more window visible than
today across most of the practical width range.
