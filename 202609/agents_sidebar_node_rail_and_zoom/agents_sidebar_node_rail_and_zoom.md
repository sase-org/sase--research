# Agents Tab: a Node Rail for `Ctrl+S` and a Distinct Zoom Mode — Consolidated Research

- **Lead:** consolidated from five researcher reports (`cdx`, `cld`, `grk`, `mus`, `gem`,
  sitting next to this file as `agents_sidebar_node_rail_and_zoom__<suffix>.md`), plus the
  lead's own code, font, and state-machine checks.
- **Date:** 2026-09-27
- **Inspected sase revision:** `2d8f2f056` (master)
- **Question:** Today `Ctrl+S` collapses the Agents-tab node sidebar, and `Z` zooms one
  deck. Both leave the left edge looking the same. Should `Ctrl+S` instead keep every
  tribe, group, and node visible in a narrow, fixed-width icon form? How should zoom look
  unmistakably different? Is the plan sound, and what should be built?

---

## TL;DR

**Build it. It is the right idea, and the current collapse is the weakest part of the
decks design.** The recommended shape was the majority view (four of five reports), and
the lead's own checks confirmed it:

1. **Three sidebar presentations, not two.**
   - **Expanded** (today's list).
   - **Rail** (`Ctrl+S`, persisted).
   - **Hidden** (zoom only). Hidden is derived from zoom and never written into the
     `Ctrl+S` preference.
2. **The rail is a 9-cell, row-for-row "minimap" of the expanded list.**
   - It uses the same tribe panels and the same visible rows at the same heights.
   - Each row shrinks to one glyph plus an optional count and an unread pip.
   - Toggling `Ctrl+S` changes only the width. Your row never moves vertically.
3. **Build it as a render mode of the existing `AgentList` widgets, not as a new
   widget.** It paints a rail visual for each existing `Option`, so it cannot drift from
   the list it summarizes.
4. **Zoom becomes loud and structural.**
   - The left edge is flush: no rail and no spine.
   - The zoomed deck gets a *heavy* border in its own accent color.
   - A reverse-gold ` ZOOM ` chip leads the deck title.
   - A `Z restore` hint appears in the deck's bottom border, and the info-row chip and
     footer match.
5. **Fix a real state bug on the way.** Zoom currently writes `nodes_collapsed=True`,
   and that value leaks into the user's sidebar preference. The lead reproduced this.

**Changes to your requirements, called out:**

- "Every node" means **every visible row**, and folds are respected.
- Icons act as **redundant cues**. They are not identifiers; identity comes from
  position, the identity header, tooltips, and jump hints.
- **No per-group-type pictograms.** Non-status groups get a lead initial plus a rule
  instead.
- **`Ctrl+S` while zoomed restores the pre-zoom layout,** like `Z` does. Today it
  silently drops a split.
- **`NodeSpine` is deleted.**

---

## 1. What exists today (verified)

### 1.1 The collapsed sidebar is not literally invisible, but it is semantically empty

Commit `71fff39d1` (2026-09-24) added `NodeSpine` (`widgets/decks/node_spine.py`). It is a
2-cell strip: a gold `»`, a dim `│` track, and a proportional gold `┃` scroll thumb.
Clicking it expands the sidebar. Apart from the thumb it carries no structure, identity,
or status, so the user's "completely invisible" is effectively accurate (noted by `cdx`,
`cld`, `grk`).

| Piece | Where | Behavior |
|---|---|---|
| State | `widgets/decks/model.py` `DeckAreaState.nodes_collapsed`, `zoom_snapshot` | One bool for "sidebar collapsed"; zoom snapshots the whole deck-area state. |
| `Ctrl+S` | `widgets/decks/layout.py` `toggle_nodes_collapsed` | Drops any zoom snapshot (no restore), then flips the bool. |
| `Z` | `layout.py` `_enter_zoom` | Snapshots, forces `layout=SINGLE`, **forces `nodes_collapsed=True`**. |
| Chrome | `_agent_detail_deck_layout.py` `_sync_nodes_collapsed_chrome` | Toggles `-nodes-collapsed` on `#agents-content`, shows or hides the spine, and moves focus off the hidden list. |
| CSS | `styles.tcss` ~L3775 | `-nodes-collapsed` hides `#agent-list-container`; the spine is 2 cells wide. |
| Info row | `agent_info_panel.py` ~L453 | Collapsed shows `nodes i/N · Ctrl+S`; zoom only prefixes a bold gold `zoom · Z`. |
| Persistence | `models/agent_deck_persistence.py` (schema v1) | Persists `nodes_collapsed` from the pre-zoom snapshot; zoom itself is never persisted. |

The goldens `agents_decks_collapsed_single_120x40.png` and
`agents_decks_zoomed_120x40.png` are almost identical. Both show the same spine and a
full-width deck; only the small `zoom · Z` info-row word differs. The zoom golden still
shows the `»` spine, so **zoom currently looks like a collapse.**

### 1.2 Zoom leaks into the `Ctrl+S` preference (lead-reproduced; first reported by `cld`)

The lead ran the pure layout functions at `2d8f2f056`:

```text
expanded split → Z → '\'     ⇒ layout=top-bottom, nodes_collapsed=True   (user never pressed Ctrl+S; this is persisted)
expanded split → Z → Ctrl+S  ⇒ layout=SINGLE, nodes_collapsed=False      (the pre-zoom split is silently discarded)
collapsed split → Z → Ctrl+S ⇒ layout=SINGLE, nodes_collapsed=False      (split lost *and* preference flipped)
```

`test_layout_key_ends_zoom_without_restoring` never checks `nodes_collapsed`, so the leak
is not covered by any test. `test_collapse_key_ends_zoom_then_toggles` *pins* the
split-dropping behavior, and `docs/ace.md` ("Agents Zoom and Node-Panel Collapse")
documents it.

### 1.3 How the node panel is built (what a rail must preserve)

- `#agent-list-container` stacks one `AgentList` (a Textual `OptionList`) per tribe panel.
  Each panel has a `border: solid` box, a border title of the form `[hint] ❖/▸ {icon}
  @tribe · N …`, and `padding: 0 1`.
- The options are, in order: group banners, agent rows, and blank spacer rows between
  L0 groups. `AgentList` has `text-wrap: nowrap`, so **every row is exactly one line**.
  That is what makes a row-for-row rail with unchanged heights possible.
- Several maps are kept in parallel with the rows: `_row_entries`, `_row_render_ctx`,
  `_row_tier_styles`, and `_banner_at_row`.
  - `_row_render_ctx` already carries `is_unread`, `is_marked`, `hint_char`,
    `fold_annotation`, `is_expanded`, `is_selected`, and `tribe_colors`: everything a
    rail cell needs for agent rows.
  - `_banner_at_row` holds only *collapsed* (selectable) banners. Expanded banners are
    not recoverable at paint time, so a new `_group_at_row` map is needed (`cld`,
    confirmed).
- **Width.** Each panel publishes a requested width. The column is clamped to 60–130
  cells and written as an **inline** style (`_settle_agent_list_container_width`,
  `on_agent_list_width_changed`). Inline styles beat CSS, so rail mode must bypass these
  writers.
- **Highlight chrome.** The highlighted option uses `border-left: thick $accent` over a
  40% accent background, so a 1-cell selection bar already exists.
- **Double borders are reserved for modals.** `double` is used exclusively for dialogs
  in `styles.tcss`: HITL, plan approval, launch approval, gate input, provider routing,
  and others.
- **Gold means focus.** Gold is the tribe-panel focus color (`-focused-panel`, and the
  heavy `-whole-panel-focus` outline).
- **Deck borders.** They are `solid` in per-deck accents (Main `$secondary`, Files
  green, Tools `#87D7FF`, Final `#FF87D7`), dimmed to 35% when unfocused.

### 1.4 Icon inventory: does every group have an icon?

**No.** The inventory, merged from `cld` and `grk` and re-checked by the lead:

- **Tribes.** Config icons: `⌂` default, `▲` epic, `†` job, `◆` pinned, `◉` review.
  User-defined tribes may have **no icon**, and the merged panel reads `All agents`.
- **Status buckets.** The glyphs in `agent/status_buckets.py` are `▲` Stopped, `◐`
  Starting, `▶` Running, `…` Queued, `⏳` Waiting, `✗` Failed, `✓` Done. They appear only
  in by-status banners, by-machine L1 banners, and the detail roster. Agent rows show
  status as a colored word, e.g. `(RUNNING)`.
- **Node kinds.**
  - Monitor and named proc share `⚙`; gate is `⋔`; bash/python step is `❯`; workflow is
    `≡`; Patch is `❑`; user-stopped is `Ø` (`models/agent_status.py`).
  - Plain agents, clans, and sessions have **no glyph**, only name colors.
  - Provider emoji (`🎭 🤖 🚀 …`) are 2 cells wide.
- **Group banners.** Project uses `▌`; Patch and L1 use `▎`; name-root uses `▸`; by-status
  uses the bucket glyph. **By-date L0 and by-machine L0 have no glyph.**

Problems that matter for a 1-cell world:

- **`▲` means three things:** the `@epic` tribe, the pre-prompt marker, and the
  **"Stopped" bucket**. That bucket is really *needs you*: `QUESTION` plus pending
  plan/tale/epic review (`_STOPPED_STATUSES`). The user-killed `STOPPED` status buckets
  as *Done*.
- **`⏳` is 2 cells, but banner width math uses `len()`** (`_agent_list_render_banner.py`
  ~L175–187). The Waiting banner therefore overruns by one cell. This is an existing bug.
- **`…` is nearly invisible at 1 cell.**

### 1.5 Glyph width and font checks (lead)

The lead measured each proposed glyph with Rich `cell_len` and checked it against the
cmaps of the bundled screenshot fonts (Fira Code, DejaVu Sans, Noto Emoji):

| Proposed by | Glyph | Problem |
|---|---|---|
| `gem` | `🟣 🟢 🔵 📅 🗄` | 2 cells wide. `gem`'s 6-cell rows like `▌🟣▶#1│` actually measure 7+ cells. |
| `gem` | `⤢` (ZOOMED badge), `⑂` (Patch), `⧖` (gate) | **No glyph in any bundled font**, so they render as tofu in goldens. `⧖` is already a known tofu case (`cld`). |
| `gem` | `⏱` | Present only in Noto *Emoji*, so it risks emoji-width rendering. |
| `grk` | `☰` (merged panel) | 2 cells wide. |
| existing | `⏳`, `⚡` | 2 cells wide. Keep them out of the rail. |
| `cld` | `◷ ○ ◐ ✓ ● • ▪ ◧ ◨ ━ ┃` | 1 cell, and in Fira Code. |
| `cld`/`cdx` | `✗ ⋔ ❯ ❑ ▸ ▾ ▴ ⋈ ≣ ⬒ ⬓` | 1 cell, in DejaVu only. Acceptable: most are already used in the TUI. |

---

## 2. Is this a good idea?

**Yes.** All five reports agree, and so does the lead. The sidebar should have three
densities, each answering a different question:

| Density | Question it answers | Precedent |
|---|---|---|
| Expanded | "Which agent is which, and what exactly is it doing?" | — |
| **Rail** | "Where is everything, what needs me, where am I?" | VS Code Activity Bar, JetBrains tool-window stripes, Discord/Slack server rail |
| Hidden (zoom) | "Let me read this one thing." | tmux `Z` pane zoom, VS Code Zen Mode, JetBrains "Hide All Windows" |

**Why it pays off:**

- On a 120-column terminal the expanded list takes about half the screen. At 80 columns
  it leaves the decks about 20 cells; a 9-cell rail leaves about 70.
- Today, trading that space costs *all* orientation, and `j`/`k` in collapsed mode is
  effectively blind.
- Zoom and collapse are different verbs, but they currently share one chrome path.

**Where the request needs care** (the adjustments are in §3):

- **Icons alone cannot identify dynamic things.** Tribes, projects, Patches, machines,
  and agent names are user-defined. No icon vocabulary can name them, and NN/g's icon
  research shows unlabeled navigation icons are ambiguous (`cdx`).
- **Icons in the rail must therefore be *redundant semantic cues* (status, kind,
  urgency).** Identity comes from elsewhere (§4.4).
- **"Every node" taken literally breaks folding.** It would show descendants of folded
  groups, making the rail disagree with the expanded list.

### 2.1 Where the researchers disagreed, and the resolution

| Question | cdx | cld | grk | mus | gem | **Resolution** |
|---|---|---|---|---|---|---|
| Rail width | 14 | 9 | 5 | 6 | 6 | **9** (§4.2). 5 cannot hold glyph + count + pip, and it forces dropping the tribe box. 14 spends width on 2–3-character name tokens that are cryptic and churn when siblings appear. `gem`'s 6 does not fit its own emoji. |
| Row mapping | 1:1 visible | 1:1 visible | 1:1 visible | **aggregate per group** | 1:1 visible | **1:1 visible rows.** `mus`'s aggregation breaks the explicit "every node" ask and `j`/`k` continuity, and needs a second cursor model. Keep its idea of rolling urgency up into *folded* containers only. |
| Mechanism | compact formatter in build path | **paint-time projection** (`_get_visual`) | compact formatter in build path | separate `NodeRail` widget | compact formatter + cache key | **Paint-time projection**, with the build-path formatter as fallback (§5.2). A separate widget is rejected by 4 of 5. |
| Node glyph | kind glyph + name token + status | status glyph | status glyph | none (aggregated) | provider emoji + status + index | **Status glyph**, or a kind glyph for non-agent nodes. |
| `Ctrl+S` while zoomed | exit to Expanded, drop snapshot | **restore snapshot** | restore snapshot + force rail | keep today's behavior | keep today's behavior | **Restore the snapshot, exactly like `Z`** (§3, A4). |
| Spine/rail in zoom | none | none | none | **keep spine** | none | **None.** A spine in zoom is what makes zoom look like a collapse today. |
| Zoom frame | gold outer outline | **heavy border, own accent** | heavy gold outline | gold border | **double** gold border | **Heavy border in the deck's own accent** (§4.6). Gold already means tribe focus and `double` means modal. Also, a Textual outline paints over the border cells, so `cdx`'s "outer frame around the deck border" would need a wrapper. |
| Full-bleed split without zoom | — | — | reject 3-way cycle | — | add hidden mode / key | **Not in v1** (§6). |

---

## 3. Requirement adjustments (explicit)

- **A1. "Every tribe, group, and node" means every *visible* row, one to one.**
  - Folds stay authoritative.
  - A folded group is one collapsed-banner row with its hidden count.
  - A folded clan or session is its container row with a member count.
  - A collapsed tribe (`h`) is a title-only strip.
- **A2. Icons are redundant cues, not labels.**
  - Each row carries **one** semantic glyph: status, or kind for non-agent nodes.
  - Identity comes from position (same y as in the expanded list), the identity header,
    hover tooltips, jump hints (`'`), and the node finder (`"`).
- **A3. No new pictogram per group type.**
  - Status banners use their bucket glyph.
  - Every other banner (project, Patch, date, machine, name-root) renders as a **lead
    initial plus a rule** (`s━━━━━`); the hover tooltip gives the full label.
  - This answers the "does every group have an icon?" question. The gaps are dynamic
    labels, and initials beat invented symbols for those.
  - Where a 1-cell glyph is genuinely missing or broken, only four are added or
    swapped, all 1 cell and in the bundled fonts:
    - `?` chip for *needs you* (replacing the overloaded `▲`);
    - `◷` for Waiting (replacing the 2-cell `⏳`);
    - `○` for Queued (replacing the unreadable `…`);
    - a tribe's bold initial as the fallback when it has no configured icon.
- **A4. Zoom stops writing the `Ctrl+S` preference, and `Ctrl+S` while zoomed restores
  the snapshot exactly like `Z`.**
  - The rule becomes "in zoom, any sidebar key gives you your layout back." No split is
    ever silently lost.
  - This fixes §1.2, changes the pinned test `test_collapse_key_ends_zoom_then_toggles`,
    and needs a `docs/ace.md` update.
  - Layout keys (`\`, `|`) keep ending zoom without a restore, but the sidebar now
    returns at the user's preference.
- **A5. Zoom is always fully hidden** (the user's own premise, kept): no rail and no
  spine.
- **A6. Delete `NodeSpine`.** The rail supersedes it. Mouse expansion moves to a
  clickable info-row chip.
- **A7. Vocabulary.**
  - The compact state is the **node rail**. The binding label becomes "Toggle Node Rail"
    instead of "Collapse/Expand Node Panel".
  - "Hidden" is reserved for zoom, so future code cannot conflate the two again.
- **A8. Onboarding and the artifact-file viewer keep hiding the whole left column,** as
  they do today for both the list and the spine (`grk`).

---

## 4. Design

### 4.1 State model

```text
SidebarMode = HIDDEN    if is_zoomed(state)
            | RAIL      if state.nodes_collapsed      # persisted Ctrl+S preference
            | EXPANDED  otherwise
```

| From | `Ctrl+S` | `Z` | `\` / `\|` |
|---|---|---|---|
| EXPANDED | → RAIL (saved) | → HIDDEN (zoom) | split as usual |
| RAIL | → EXPANDED (saved) | → HIDDEN (zoom) | split as usual; rail stays |
| HIDDEN (zoomed from X) | **restore snapshot → X** *(changed)* | restore snapshot → X | end zoom without restore; sidebar = preference |

- `_enter_zoom` no longer sets `nodes_collapsed`.
- `toggle_nodes_collapsed` becomes: if zoomed, `_exit_zoom`; otherwise flip the bool.
- Persistence schema v1 is unchanged. `nodes_collapsed` simply *means* "rail" now, so no
  migration is needed.

### 4.2 Rail anatomy

**The width is 9 cells, as a single code constant** (not user config in v1; `cdx`, `cld`,
`mus` agree on fixed):

- 2 cells of tribe-panel border;
- 1 selection gutter, holding the existing thick highlight bar;
- 6 content cells.

In rail mode the list has no padding and no scrollbar (`scrollbar-size-vertical: 0`), and
option padding is `0 0 0 1`.

**Principles:**

- **Position = identity.** Rail row *k* is expanded row *k*, at the same y and scroll
  offset. Panel heights and the 1-row gaps between panels are unchanged.
- **Shape = kind or status.** Every row has exactly one 1-cell glyph.
- **Color = urgency.** Colors reuse each status's existing color.
  - Read/done rows are dim.
  - *Needs you* is the **only** reverse-video chip.
- **Right edge = unread.** Unread shows as an aligned column of `•` pips, and marked
  rows show `▪`, which wins over unread.
- **Calm by default.** No emoji, runtimes, provider badges, machine chips, or `⚡ ◌ ↻ ↺`.
  Runtime ticks stop repainting rail rows.

```text
content cell:     0       1       2       3       4       5
node, depth 0:    glyph   count   count                   pip
node, depth 1:    guide   glyph   count   count           pip
node, depth 2:    guide   guide   glyph   count   count   pip
banner (L0):      lead    ━ ━ ━ ━ ━                          (L1+: thin ─ rule)
folded banner:    ▸       lead    ━ ━     hidden-count (gold)
spacer:           (blank, preserved)
```

Depth is clamped at 2 (clan → member → step), using `│`/`└` guides in the existing tier
colors. Container counts cap at `99`.

### 4.3 Rail vocabulary (one new pure module, the single source of truth)

| Row | Glyph | Style |
|---|---|---|
| Needs you (bucket "Stopped": QUESTION, plan/tale/epic review) | `?` | bold dark-on-gold **reverse chip**, the loudest thing in the rail |
| Failed | `✗` | bold red |
| Running (incl. ANSWERED, active hand-offs) | `▶` | existing running color |
| Starting | `◐` | existing color |
| Queued | `○` | existing queued `#5F87FF` |
| Waiting | `◷` | existing waiting color |
| Done (unread / read) | `✓` | normal + `•` pip / dim |
| User-stopped (`STOPPED`) | `Ø` | existing stopped color |
| Clan / session container | aggregate status glyph + member count | count tinted clan `#D75FFF` / session `#00AFFF` |
| Monitor / named proc | `⚙` | existing lane colors; settled = grey |
| Gate turn | `⋔` | existing gate colors |
| Workflow / step / Patch | `≡` / `❯` / `❑` | existing type colors |
| Jump hint active | hint letter(s) | existing hint chip; they take the glyph cell and, for 2-character hints, the count cells |

**Glyph precedence:** jump hint > kind glyph (for non-agent nodes) > status glyph.

**Banner leads:**

| Grouping mode | L0 lead | L1 and below |
|---|---|---|
| Standard | project initial, bold sky, heavy `━` rule | Patch or name-root: thin `─` rule |
| By status | bucket glyph from the table (`?` chip for needs-you) | — |
| By date | `T` / `Y` / `W` / `E` | thin rule |
| By machine | alias initial | bucket glyph + thin rule |

Backing test: an **exhaustiveness test**. Every status and bucket override, every node
kind, and every `GroupingMode` must map to text whose `cell_len` equals the content width.

### 4.4 Tribe chrome and identity without labels

- **Tribe title** (centered in the top border, at most 5 cells):
  - `[hint]` while panel hints are up;
  - then `❖` (whole-panel focus) or `▸` (collapsed tribe);
  - then the configured icon, or the tribe's **bold initial in its identity color**.
    The initial beats `grk`'s `@` because it distinguishes multiple unconfigured tribes.
  - The merged panel shows `All`.
- **Collapsed tribes carry urgency.** The title gains the most urgent mark inside the
  tribe: the `?` chip, else a red `✗`, else a gold `•`. This keeps `mus`'s roll-up idea
  where rows are genuinely absent.
- **Borders** are unchanged: the gold focused-panel border and the heavy gold
  whole-panel outline both still work.
- **Overflow.** The bottom border shows `▴3 ▾2` (rows above and below the viewport) in
  place of the scrollbar.
- **Identity, in order of reach:**
  1. The existing identity header always names the selection. `j`/`k` in the rail is
     therefore never blind.
  2. Hovering a row shows *the expanded row itself* as a tooltip. It is formatted on
     demand from `_row_render_ctx` through the existing `format_agent_option` /
     `format_banner_option`.
  3. Jump hints and the node finder give by-name keyboard access without expanding.

### 4.5 Interaction

- **Keyboard.** Nothing changes: `j`/`k`, `h`/`l`/`H`/`L`/`z` folds, `'` hints, `"`
  finder, marks, and whole-panel focus all work, because the options and nav stops are
  unchanged.
  - Focus **stays** on the list in rail mode. Only HIDDEN calls
    `_move_focus_off_hidden_list`.
- **Mouse.**
  - Clicking a row selects it. Clicking a tribe title selects the panel. The wheel
    scrolls.
  - The info-row `nodes 12/47 · Ctrl+S` chip becomes clickable to expand; it replaces
    the spine's click target.
  - Rows never expand on click, and nothing expands on hover or focus. Auto-overlay
    expansion was rejected by `cdx` and `gem`: it causes jitter, covers the decks, and
    turns stray mouse moves into layout events.
- **No animation.** An animated width would re-flow the deck spreads every frame. That
  goes against the TUI performance rules, so `gem`'s `transition: width` is rejected.
  The switch is instant.
- **Footer.** In rail mode it offers `Ctrl+S expand nodes`.

### 4.6 Zoom chrome

Zoom needs redundant, *structural* cues where the eye already is:

1. **Flush left edge.** No rail and no spine. *A rail means compact; no left column means
   zoom.*
2. **The zoomed deck panel's border becomes `heavy`, in the deck's own accent.**
   - It is geometry-neutral: 1 cell either way, so there is no reflow.
   - It keeps deck identity: Main, Files, Tools, and Final colors survive.
   - It avoids gold, which already means tribe focus, and `double`, which means modal
     dialog in this TUI.
3. **A reverse-gold ` ZOOM ` chip leads the deck border title.** `deck_title()` gets a
   budget reduced by the chip's width, and the chip is never dropped from the width
   ladder.
   - A word is more reliable than a maximize glyph, and `⤢` is tofu in the bundled fonts.
4. **A restore hint leads the deck's bottom border.**
   - It reads `◧ 1 of 2 · Z restore` when zoomed from a split. The glyph shows which half
     is zoomed: `◧`/`◨` for left/right, `⬒`/`⬓` for top/bottom.
   - It reads `Z restore` when zoomed from a single deck.
   - The existing availability segment (`main 1 · files 0 · …`) shrinks first.
5. **Info row.** The bold word `zoom` becomes the same reverse ` ZOOM ` chip, followed by
   `Z restore`, and the chip is clickable.
   - Keep `node 12/22`, because `j`/`k` still moves the selection while zoomed.
   - Drop the `Ctrl+S` hint, since it now also restores.
6. **Footer.** `Z restore layout` moves to the first slot while zoomed.

`cld`'s prototype render shows exactly this treatment:
![zoom](agents_node_rail_and_zoom_chrome__cld_zoom.png)

### 4.7 What it looks like

A 9-cell rail next to the decks. This is a conceptual wireframe; the real borders are
Textual `solid` in tribe colors.

```text
┌── ⌂ ──┐   @default: configured icon, centered
│ s━━━━━│   project "sase": initial + heavy rule
│ ?     │   an agent waiting on you (reverse gold chip)
│▌▶3   •│   selected running clan of 3, unread (thick accent bar = selection)
│ │▶    │   clan member
│ └✓   •│   last member, done, unread
│ ✗    •│   failed, unread
│ ▸b━━━4│   folded project "beads", 4 hidden rows
└─ ▾2 ──┘   2 more rows below
             (existing 1-row panel gap)
┌─ ▸†? ─┐   collapsed @job tribe that contains a needs-you agent
└───────┘
```

`cld`'s prototype (a standalone Textual mock rendered through sase's own PNG renderer; the
colors approximate the real renderer):
![rail](agents_node_rail_and_zoom_chrome__cld_rail.png)
![hints](agents_node_rail_and_zoom_chrome__cld_hints.png)

---

## 5. Implementation

This is presentation-only: glyph choice, layout, and Textual chrome. It reads existing
status-bucket semantics and **does not cross the `sase-core` boundary** (all five reports
agree). `default_config.yml` needs **no** new keys, because the `ctrl+s` and `Z` bindings
are unchanged.

### 5.1 Phases

1. **State model** (`widgets/decks/layout.py`, `widgets/_agent_detail_deck_layout.py`)
   - Stop `_enter_zoom` from setting `nodes_collapsed`.
   - `Ctrl+S` while zoomed calls `_exit_zoom`.
   - Add `sidebar_mode(state)`.
   - Replace `_sync_nodes_collapsed_chrome` with `_sync_sidebar_chrome(mode)`, which
     toggles `-nodes-rail` / `-nodes-hidden` on `#agents-content` and a `-zoomed` class
     on the focused deck panel.
   - Update `test_deck_collapse_zoom.py`: the zoom tests asserting
     `nodes_collapsed is True`, and the pinned `Ctrl+S`-in-zoom test.
   - Add leak and persistence round-trip tests.
2. **Rail vocabulary** (a new module, e.g. `widgets/_agent_list_render_rail.py`, pure
   functions)
   - `rail_node_visual`, `rail_banner_visual`, and `rail_panel_title`.
   - Record a `_group_at_row` map (all banners, plus banner hint and mark state) in the
     same build and patch paths that fill `_banner_at_row`.
   - Exhaustiveness tests.
3. **Paint-time projection in `AgentList`** (§5.2).
   - CSS under `#agents-content.-nodes-rail`.
   - Width writers bypassed.
   - Rail titles, with the rail flag added to `panel_paint_key`, so that
     `_panel_content_is_unchanged` cannot skip the title repaint.
4. **Chrome polish.**
   - Collapsed-tribe urgency marks, the `▴N ▾N` overflow subtitle, hover tooltips, and
     the clickable info-row chip.
   - Delete `NodeSpine`, `on_node_spine_expand_requested`, the `#agent-node-spine` CSS
     and compose, and the spine tests. Then run `just symvision`.
5. **Zoom chrome.**
   - The heavy-border class on the deck panel, the `ZOOM` chip in `deck_title`, and the
     restore segment in `deck_subtitle` (`widgets/decks/titles.py`, `panel_chrome.py`).
   - The info-row chip and footer ordering.
6. **Goldens, docs, memory.** See §5.4.
7. **Optional, separable vocabulary alignment** (recommended in the same epic; a small
   phase):
   - Move the *expanded* by-status banners onto the rail's glyphs: `▲` → the `?` chip,
     `⏳` → `◷`, `…` → `○`.
   - This keeps one visual language across both densities, and it fixes the `⏳` 2-cell
     banner overrun.
   - The rail must not depend on it.

### 5.2 Mechanism: paint-time projection (with a build-time fallback)

The lead verified the load-bearing assumption against the installed **Textual 8.0.1**:
`OptionList` routes **both** height arrangement (`_update_lines`) **and** painting
(`_get_option_render`) through `_get_visual(option)`, and `_clear_caches()` clears both
the `_option_render_cache` and the `_line_cache`.

`AgentList` therefore overrides `_get_visual`:

- When the rail is off, it calls `super()`.
- When the rail is on, it maps `option` → `_option_to_index` → row. It reads
  `_row_entries`, `_agents`, `_row_render_ctx`, `_row_tier_styles`, and `_group_at_row`.
- It returns a rail visual from a per-widget cache keyed by the `Option`. Patches
  replace `Option`s, so invalidation is automatic.
- `AgentList.set_rail(enabled)` stores the flag and calls `_clear_caches()`.

Why this is the right choke point:

- The build, patch, and insert paths, `AgentRenderCache`, and incremental refresh are
  all **untouched**. The rail is correct by construction, including for future row
  states.
- A toggle is a cache clear plus a repaint. There is **no option rebuild**, and scroll
  and highlight are preserved.
- Coupling to `OptionList` internals is established precedent: `install_options` already
  writes `_options`, `_option_to_index`, `_id_to_option`, and `_mouse_hovering_over`, and
  calls `_clear_caches`/`_update_lines`.

Two constraints on the override:

- It **must not** write `option._visual`, which is the base class's per-option cache.
  The expanded visual must stay cached for the toggle back.
- It needs a **guard test** that fails loudly if a Textual upgrade stops routing through
  `_get_visual`.

**Fallback.** `cdx`, `grk`, and `gem` favor B1: a compact formatter in the build path,
with density in the render/paint cache keys. It works, but it must be honored at every
build/patch/insert call site (five or more), and a future site that forgets would paint
an expanded row into the rail. The pure vocabulary module from phase 2 serves both
approaches, so switching costs little.

**Width gotcha.** `_settle_agent_list_container_width` and `on_agent_list_width_changed`
write the column width as an inline style, which beats CSS.

- In rail mode both must set the rail constant (or no-op), and `WidthChanged` requests
  must be ignored.
- On expand, re-settle the negotiated width.

### 5.3 Performance (per the TUI performance rules)

- **Toggle.** A flag, `_clear_caches()` per tribe list, a CSS class, and title repaints.
  No disk I/O, remount, or rebuild. Target: one frame at 200 rows, with a trace span on
  the toggle.
- **`j`/`k` in rail mode** stays under the 16 ms p95 target (`SASE_TUI_PERF=1`). The
  highlight paints immediately and deck detail stays on its debouncer.
- **No periodic "minimap" work.** The rail *is* the list. Runtime-only patches should
  hit the rail cache or re-render a 6-cell strip.

### 5.4 Tests, goldens, docs

- **Pure tests:**
  - every visible expanded row produces exactly one rail row, in the same order and with
    the same selection identity;
  - folded descendants stay absent;
  - `cell_len` is exact for long Unicode names, emoji tribe icons, deep nesting, and
    2-character hints;
  - state transitions, including the leak and the `Ctrl+S`-restores-split behavior;
  - `Expanded ⇄ Rail` round trips preserve selection, folds, deck layout, card, and
    scroll;
  - restart persists Rail/Expanded but never Zoom.
- **Widget tests:**
  - focus stays on the list in rail mode and moves off in zoom;
  - a click selects a row, and the chip click expands;
  - onboarding and the artifact-file viewer still hide the column;
  - the Textual `_get_visual` guard.
- **PNG goldens** (judge structure, don't rubber-stamp):
  - rail grouped by project, by status, and by machine;
  - a clan expanded to depth 2;
  - rail with jump hints;
  - collapsed tribes with urgency;
  - whole-panel focus;
  - a narrow 80×24 terminal;
  - zoom from single and zoom from split;
  - dark and light themes.
- **Goldens to regenerate:** `agents_decks_collapsed_single/split` and
  `agents_decks_zoomed`.
- **Docs and keymap text:**
  - `docs/ace.md` §"Agents Zoom and Node-Panel Collapse" (three presentations and the
    new `Ctrl+S`-in-zoom rule);
  - the help modal (`modals/help_modal/agents_bindings.py`);
  - the binding label in `bindings.py` (`"Collapse/Expand Node Panel"` →
    `"Toggle Node Rail"`);
  - the command palette text.
- **Memory.** The glossary strand **Node Panel** still describes the slim spine. It must
  be rewritten through the `/sase_memory_write` flow, not by editing the file.

---

## 6. Alternatives considered and rejected

| Alternative | Why not |
|---|---|
| Keep the spine and add per-tribe ticks | Still no identity or structure, and still identical to zoom. |
| Tribe-icons-only activity bar (`grk` §6.1, `cld` D) | Calm and pretty, but it drops the per-node heartbeat that is the reason to keep the rail. Possibly a *later* ultra-compact density. |
| Group-aggregate rail with its own cursor (`mus`) | It violates "every node", breaks `j`/`k` continuity, and requires a parallel widget and selection model. |
| Separate `NodeRail` widget | It must mirror panels, heights, scroll, folds, hints, marks, clicks, and `patch_row`. That is two sources of truth, and duplication like that is how this tab has frozen before. |
| 14-cell rail with name tokens (`cdx`) | Shortest-unique-prefix tokens are cryptic, churn as siblings appear, and give back less width. The tooltip plus header give real names. |
| Provider emoji in the rail (`gem`) | 2 cells each; noise; provider is not what a glance needs. |
| Hover or focus auto-expanding overlay | Jitter, covered content, accidental activation. |
| Just narrowing the column and letting rows clip | The leftmost cells are gutters, `[agent]` badges, and emoji. It looks broken, not designed. |
| Third "hidden without zoom" mode or key (`gem`) | Split decks lose only about 7 cells compared with today's spine (≈55 vs ≈59 per side at 120 columns). A third state duplicates `Z` without its chrome and reintroduces the "why is my sidebar gone?" confusion. Revisit only if users ask. |
| Double-border or gold-outline zoom frame (`gem`, `grk`, `cdx`) | `double` reads as a modal here, and gold reads as tribe focus. |

---

## 7. Risks and open decisions

- **Decision for you: `Ctrl+S` while zoomed.**
  - The recommendation is to restore the pre-zoom snapshot, exactly like `Z`.
  - The alternative keeps today's "end zoom, stay single, flip the sidebar," which
    silently drops a split.
  - Only one pinned test and one docs paragraph hinge on the choice.
- **Decision for you: the phase-7 vocabulary alignment** in the expanded by-status
  banners (`▲` → `?`, `⏳` → `◷`, `…` → `○`). It is recommended but separable.
  - The label "Stopped" for the *needs you* bucket is itself misleading. Renaming it
    touches shared bucket semantics, so it is out of scope here.
- **Private Textual hook.** Mitigated by the guard test, the `install_options` precedent,
  and the B1 fallback.
- **Glyph rendering on exotic terminal fonts.** Everything chosen is 1 cell in Rich and
  present in the bundled fonts, and most glyphs already ship in the TUI. `⋔`, `✗`, `◷`
  and friends may still draw poorly in unusual fonts.
- **By-status grouping is redundant in the rail:** every row under `▶` is `▶`. That is
  acceptable, because the rail still carries position, counts, and unread. It shines in
  by-project mode, where statuses mix.
- **Follow-up, not in scope:** an automatic *effective* rail on terminals narrower than
  about 100 columns, where the 60-cell expanded minimum starves the decks. It would have
  to be non-persisted so it never overrides an explicit user choice.

---

## 8. Recommended solution

1. **Model.**
   - `nodes_collapsed` becomes purely the persisted `Ctrl+S` rail preference.
   - Derive `SidebarMode = HIDDEN (zoomed) | RAIL | EXPANDED`, and stop zoom from
     writing the preference. This fixes the reproduced leak.
   - `Ctrl+S` while zoomed restores the snapshot like `Z`.
2. **Rail.**
   - Replace the 2-cell `NodeSpine` with a **9-cell node rail**: the same tribe panels,
     the same visible rows, and the same heights, so a toggle moves nothing vertically.
   - Each row gets **one** 1-cell glyph from a single vocabulary module:
     - status glyphs, with a reverse-gold `?` chip for *needs you*, `◷` for waiting, and
       `○` for queued;
     - kind glyphs for monitors, gates, procs, steps, and workflows;
     - member counts on containers, and a right-edge `•` unread pip;
     - banners as lead initial + rule (bucket glyph for status groups);
     - tribe titles as icon or bold initial, with urgency marks on collapsed tribes;
     - `▴N ▾N` overflow in the border.
   - No emoji, no runtimes, no animation.
   - Identity comes from the identity header, a hover tooltip showing the full expanded
     row, jump hints, and the node finder.
3. **Mechanism.**
   - A **paint-time projection inside `AgentList`** (a `_get_visual` override behind
     `set_rail()`), with a `_group_at_row` map, inline-width writers that defer to the
     rail, and rail-aware panel titles.
   - A guard test on the Textual hook. The build-path formatter is the fallback.
4. **Zoom.**
   - Fully hidden left column.
   - The zoomed deck gets a **heavy border in its own accent**, a **reverse-gold `ZOOM`
     chip** in its title, and a **`◧ 1 of 2 · Z restore`** hint in its bottom border.
   - A matching clickable info-row chip, and `Z restore layout` first in the footer.
5. **Ship it with:**
   - vocabulary exhaustiveness tests;
   - state-transition and persistence tests, including the leak;
   - the Textual hook guard;
   - the rail and zoom PNG goldens listed in §5.4;
   - the help, palette, binding-label, and `docs/ace.md` updates;
   - a Node Panel glossary rewrite through `/sase_memory_write`;
   - optionally, the phase-7 alignment of the expanded by-status glyphs.

---

## Sources

- sase at `2d8f2f056`:
  - `widgets/decks/{layout,model,node_spine,titles,panel_chrome,picker}.py`
  - `widgets/_agent_detail_deck_layout.py`
  - `widgets/_agent_list_{widget,base,build_rows,build_rebuild,render_banner,render_layout}.py`
  - `actions/agents/{_display_panel_layout,_deck_layout_actions,_panel_detail}.py`
  - `actions/_event_widgets.py`
  - `agent_info_panel.py`
  - `models/{agent_deck_persistence,agent_status}.py`
  - `agent/status_buckets.py`
  - `styles.tcss`
  - `bindings.py`, `default_config.yml`
  - `docs/ace.md`
  - `tests/ace/tui/widgets/decks/test_deck_collapse_zoom.py`
  - PNG goldens `agents_decks_{collapsed_single,collapsed_split,zoomed}_120x40.png`
- Lead checks:
  - the pure-function state reproduction (§1.2);
  - Textual 8.0.1 `OptionList` internals (§5.2);
  - Rich `cell_len` plus fontTools cmap coverage of the bundled `src/sase/ace/tui/fonts`
    (§1.5).
- Researcher reports (this directory):
  - `__cdx` (compact 14-cell mini-tree; UX literature on icons, color, rails);
  - `__cld` (9-cell paint-time rail, the leak, font checks, prototype PNGs and
    `agents_node_rail_and_zoom_chrome__cld_proto.py`);
  - `__grk` (5-cell icon rail; tmux/VS Code framing; onboarding exceptions);
  - `__mus` (aggregate rail; focus-legality and passive-awareness arguments);
  - `__gem` (6-cell emoji rail; double-border zoom; split full-bleed concern).
- External UX references (via `cdx`):
  - [VS Code user interface](https://code.visualstudio.com/docs/editing/getting-started/userinterface)
  - [IntelliJ IDEA tool windows](https://www.jetbrains.com/help/idea/tool-windows.html)
  - [Apple HIG: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars)
  - [NN/g: Icon Usability](https://www.nngroup.com/articles/icon-usability/)
  - [WCAG 1.4.1 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
  - [WCAG 1.4.11 Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
