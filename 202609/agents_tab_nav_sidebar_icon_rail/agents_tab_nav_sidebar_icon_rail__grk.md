# Agents-tab nav collapse: icon rail, and zoom as a distinct mode

- **Researcher:** grk (`research.h.grk`)
- **Date:** 2026-09-27
- **Question:** When `Ctrl+S` collapses the Agents-tab node panel, how should tribes, grouping banners, and nodes stay represented in a fixed-width rail? How should `Z` zoom stay visually distinct from that rail? Is the proposed direction the right one?

## Recommended solution

Treat **collapse** and **zoom** as two different layouts that currently share one chrome path, and split them.

- **`Ctrl+S`** compresses the live agent tree into a **5-cell icon rail**: the same stacked tribe panels, the same grouping banners, the same visible nodes, each reduced to a one-cell glyph. `j`/`k`, click-to-select, `'` hints, `h`/`l` folds, and the identity header keep working. Overflow scrolls; the selected glyph stays in view.
- **`Z`** is tmux-style pane zoom: the left column is **gone**, the focused deck fills the Agents content, and a gold **ZOOM** frame plus reverse-video info-row chip make the mode unmissable. A second `Z` restores the snapshot exactly, as today.

Reuse the glyphs the tree already has (tribe `ace.tribes.icon`, status `▶✗✓…`, type `⚙⋔≡❯`, banner `▌▎▸`). Add only a small set of missing 1-cell glyphs for date buckets, machine buckets, and unconfigured tribes.

Do this as a compact **render mode of the existing `AgentList` widgets**, not a second tree. Retire `NodeSpine`. Decouple zoom hide from `nodes_collapsed`.

---

## 1. Critique of the request

The direction is right. The current `Ctrl+S` path solves the wrong problem, and `Z` accidentally inherited that solution.

### 1.1 What the request gets right

The Agents tab is a **control tower**. The left column is the fleet; the right column is the selected node's work. Collapsing the fleet to reclaim width is a real need: the expanded list is clamped around 60 cells (`#agent-list-container` in `styles.tcss`, with `_MIN_AGENT_LIST_WIDTH` / `_MAX_AGENT_LIST_WIDTH` negotiation). On a 120-column terminal that is half the screen.

Keeping **identity** while reclaiming width is the actual product requirement. A gold scrollbar does not identify a tribe, a Running bucket, or a failed node. An icon rail does.

Making **zoom look like zoom** is equally right. Visual goldens `agents_decks_collapsed_single_120x40` and `agents_decks_zoomed_120x40` are the same layout: 2-cell gold `»` spine, identity header, one deck. The only difference is a small `zoom · Z` chip in the info row. That chip is easy to miss once the row also carries counts, filter, grouping, load, and model.

The VS Code / JetBrains / Discord pattern the request is reaching for is well-established:

| Product | Compact nav | Focus / zen |
| --- | --- | --- |
| VS Code | Activity Bar (icons stay) + `Ctrl+B` hides the sidebar | Zen Mode (`Ctrl+K Z`) hides Activity Bar too |
| JetBrains | Tool-window icon strip | Distraction Free |
| Discord | Server icon rail | Fullscreen hides the rail |
| tmux | Tree stays in its pane | `Z` zooms the pane; status shows `Z` |

`Ctrl+S` should be the Activity Bar. `Z` should be Zen / tmux zoom. Those are different verbs.

### 1.2 Where the request overreaches

**"Every node should be represented"** cannot mean "every node is on screen at once." A typical Agents query already overflows a 40-row terminal once clans, sessions, monitors, gates, and steps are unfolded. The expanded list already scrolls. A rail that packs 80 nodes into 30 cells as a heatmap would recreate today's spine: a proportional thumb with no identity.

The justified reading: every **currently visible tree row** (respecting the same folds the expanded list uses) gets a glyph, in the same order, and the rail **scrolls** with selection. A folded Running banner is one `▶`. Unfold it and its member glyphs appear. Hidden steps stay hidden. That is representation. It is also the only version that stays truthful to `h`/`l`/`H`/`L`/`z` fold state.

**"Maybe add a few more icons if every agent group lacks one"** is the right instinct, and the set of gaps is small. Status buckets, tribe identity, type, and project/name-root banners already have glyphs. Date L0 and machine L0 do not. Inventing a large new icon language would fight the visual grammar the list already teaches.

**A dedicated parallel rail widget** is the tempting implementation, and the worse one. The tree, selection, folds, hints, and incremental `patch_row` path already live on `AgentList`. Duplicating them onto a `NodeRail` will drift. Compact-mode rendering of the widgets that already own the rows is the reliable design.

### 1.3 Justified requirement adjustments

These change the request. Each is called out so a later plan can accept or reject it explicitly.

**A1. Visible-tree rail, not an all-nodes minimap.** Represent every currently visible row (tribe chrome, grouping banner, node). Folded subtrees stay one glyph. Off-screen rows exist; the rail scrolls. The info-row `nodes 12/47` chip stays as the overflow caption.

**A2. Zoom hide is independent of `nodes_collapsed`.** Today `_enter_zoom` sets `nodes_collapsed=True`, and `_sync_nodes_collapsed_chrome` drives one CSS class for both verbs. Zoom should hide the left column because `is_zoomed`, even if the snapshot's collapse flag is false. Restoring zoom then restores whatever collapse state the snapshot had.

**A3. `Ctrl+S` while zoomed restores the snapshot with the rail showing.** Today it *drops* the snapshot and then toggles collapse, so a zoomed split becomes a single expanded deck. That is a footgun. Intent of `Ctrl+S` is "give me the nav." Restore layout (same as `Z`) and land in rail mode (`nodes_collapsed=True`). A second `Ctrl+S` expands names.

**A4. Fixed width is 5 cells, not 2.** Two cells cannot hold a selection gutter, a nested-child tick, and a glyph. Five cells: 1-cell left tribe/selection accent + 1-cell optional nest tick + 1-cell glyph + 2 cells of breathing room / jump-hint. This is still an 55-cell gift versus the ~60-cell expanded list.

**A5. Clicking a rail glyph selects that row.** Clicking the current spine expands the panel. That made sense when the spine had no destinations. On a rail, click-to-select matches the expanded list. Expansion is `Ctrl+S`, or a gold `«` affordance on the first rail row.

**A6. Retire `NodeSpine`.** The 2-cell `»` + thumb widget is the thing users read as "the sidebar vanished." It has no job once the rail and the zoom-hide path exist.

**A7. Onboarding and the artifact-file viewer keep hiding the left column entirely.** Those modes already `display: none` both `#agent-list-container` and `#agent-node-spine`. The rail must honor the same exceptions.

---

## 2. What the code does today

### 2.1 Two verbs, one chrome

| Verb | Key | State | Left column |
| --- | --- | --- | --- |
| Collapse | `Ctrl+S` → `action_toggle_node_panel` | `DeckAreaState.nodes_collapsed` flips | `#agents-content.-nodes-collapsed` sets `#agent-list-container { display: none }` and unhides `#agent-node-spine` (2 cells) |
| Zoom | `Z` → `toggle_zoom` | Snapshot the deck area; layout becomes `SINGLE`; **also** `nodes_collapsed=True` | Same collapsed chrome as `Ctrl+S` |

Sources: `widgets/decks/layout.py` (`toggle_nodes_collapsed`, `_enter_zoom`), `widgets/_agent_detail_deck_layout.py` (`_sync_nodes_collapsed_chrome`), `styles.tcss` lines 3775–3792, `widgets/decks/node_spine.py`.

The list is **not unmounted**. `display: none` takes it out of layout; `j`/`k` (`action_agents_next`) still walk rows; the identity header follows. Docs in `docs/ace.md` §"Agents Zoom and Node-Panel Collapse" and glossary `node-panel` already describe this. The spine is a proportional thumb over "navigation stops," plus a gold `»`. It is a scrollbar, not a tree.

### 2.2 Why it feels invisible

From `agents_decks_collapsed_single_120x40.png`: a 2-cell gold bar, then the identity header and the deck edge-to-edge. Tribe titles (`⌂ @default`), project banners (`▌ sase`), and the agent row are gone. The info row says `nodes 1/1 · Ctrl+S`. That is the entire remaining nav identity.

From `agents_decks_zoomed_120x40.png`: the same picture, plus `zoom · Z` in gold before `nodes 1/1`. A user who arrived via `Z` from a split can believe they only collapsed the sidebar.

### 2.3 A collapse that already keeps identity

Lowercase `h` collapsing a **tribe panel** is the in-product proof that compact-but-present works. Golden `agents_collapsed_panel_120x40.png` shows `@job` reduced to one title row `▸ † @job · 2 [R1 W1]` with the panel still in the stack, still selectable, still gold-outlined when focused. `Ctrl+S` should be that idea applied to the whole column: keep the objects, drop the words.

The Artifacts relation rail (`.` in `docs/artifacts_pane_visual_grammar.md`) is the other analog: collapsed is a one-line chip rail with counts and keys still live, not `display: none`.

### 2.4 Glyphs that already exist

The list is already an icon language. Compact mode should *reuse* it.

**Tribes** (`docs/configuration.md` `ace.tribes`, `agent_panel_border_title`):

| Tribe | Bundled icon | Color |
| --- | --- | --- |
| `default` | `⌂` | sky `#87D7FF` |
| `epic` | `▲` | lavender |
| `job` | `†` | amber |
| `pinned` | `◆` | gold fallback |
| `review` | `◉` | gold fallback |
| unconfigured | *(none)* | gold fallback |

Identity color already applies only to the icon and `@tribe` name. A rail that shows `⌂` in sky blue is the same surface.

**Status buckets** (`AGENT_STATUS_BUCKET_GLYPHS` and BY_STATUS banners):

| Bucket | Glyph |
| --- | --- |
| Stopped | `▲` |
| Starting | `◐` |
| Running | `▶` |
| Queued | `…` |
| Waiting | `⏳` |
| Failed | `✗` |
| Done | `✓` |

**Types / lanes** (`_TYPE_GLYPHS`, `_STEP_TYPE_GLYPHS`, monitor/gate/proc):

| Kind | Glyph |
| --- | --- |
| workflow | `≡` |
| agent / patch ("cl") | `❑` |
| named proc | `⚙` |
| monitor | `⚙` |
| gate | `⋔` |
| python / bash step | `❯` |
| hidden | `◌` |
| auto-approve | `⚡` |
| whole-panel selected | `❖` |
| collapsed tribe title | `▸` |
| fold restore | `▿` |

**Grouping banners** (`_agent_list_render_banner.py`):

| Mode / level | Glyph |
| --- | --- |
| STANDARD L0 project | `▌` sky |
| STANDARD L1 Patch / BY_DATE L1 / BY_MACHINE L1 | `▎` |
| name-root | `▸` teal |
| BY_STATUS L0 | the status glyph above |
| BY_DATE L0 | **label only — no glyph** |
| BY_MACHINE L0 | **alias label only — no glyph** |

Gaps worth filling (A4's "few more icons"): date L0, machine L0, unconfigured tribe, merged `All agents`.

**Collision to live with:** epic tribe `▲` and Stopped `▲` are the same character. They are already disambiguated by color and position (title vs banner vs node). The rail keeps that: tribe `▲` sits on a title row in epic lavender; Stopped `▲` sits on a banner or node in the Stopped grey `#8787AF`. Do not invent a second Stopped glyph.

### 2.5 Persistence and keymap

`nodes_collapsed` is already in `~/.sase/ace_agents_deck_state.json` (schema v1). The rail can keep that flag. Zoom remains a session snapshot (`zoom_snapshot`), unrestored across restart, which is correct.

`Ctrl+S` is Agents-only (`check_app_action` returns false on Artifacts/Services). Prompt stash uses the same chord in the prompt, which is a different widget. No keymap change is required.

---

## 3. Design: the icon rail (`Ctrl+S`)

### 3.1 What you see

A 5-cell column on the left of `#agents-content`. Stacked tribe `AgentList` widgets stay mounted. Each visible row of the expanded tree becomes one rail row.

```
 «          gold expand affordance (click / Ctrl+S)
 ┃⌂         @default, sky, selected whole-panel would be gold ❖
 ┃▌         project "sase"
 ┃▸         name-root "visual-decks"
 ┃✓         done agent          ← row highlight (gold reverse)
    ← 1-cell gap (existing .agent-panel-separated)
 ┃†         @job, amber
 ┃▶         running agent
```

`┃` is a 1-cell left accent in the tribe identity color (or gold under whole-panel / row focus). It replaces the current full box border, which at 5 cells would consume two columns of inner space and leave nothing for the glyph.

**Row grammar (inner 4 cells after the accent):**

| Row kind | Cells | Notes |
| --- | --- | --- |
| Expand affordance | `«` | Gold, tooltip `Expand node panel (Ctrl+S)` |
| Tribe title | tribe icon, or `@` if unconfigured, or `☰` for merged `All agents` | Same `compose_tribe_identity_style` as today's title |
| Collapsed tribe (`h`) | `▸` + icon compressed to the icon, dim | One row, children omitted — same as today |
| L0 project banner | `▌` | Sky; collapsed banner selectable |
| L0 status banner | status glyph | Color from wait/status presentation |
| L0 date banner | new 1-cell glyph (below) | |
| L0 machine banner | new 1-cell glyph (below) | |
| L1 / name-root | `▎` or `▸` | Keep the existing tier register |
| Agent / clan / session node | **status glyph** | Status is the pulse; type is secondary |
| Monitor / gate / proc | `⚙` / `⋔` / `⚙` | Lane color already in `_agent_list_styling` |
| Workflow container | `≡` | |
| python / bash child | `❯` | Amber / green from `_STEP_TYPE_COLORS` |
| Nested child | `│` in the nest cell, then glyph | Depth color from `TREE_DEPTH_COLORS` |

**Why status, not type, for ordinary agent nodes.** The expanded row already leads with a type badge (`[agent]`) and puts status in a parenthetical. In 1 cell, status is the higher-bandwidth signal: a column of `▶▶✗✓` is a fleet heartbeat. Type is recoverable from the identity header the moment the row is selected. Clan/session containers can keep a structural glyph (`◆` / fold `▸`) because they are not themselves a status bucket.

**Unread / asking.** Bold the glyph (unread) and use the Stopped/asking color when the node is waiting on a human. Do not add a second overlay character; 1 cell cannot carry it.

### 3.2 New glyphs only

Keep the set tiny and geometric (1 cell in Fira Code / the bundled TUI fonts; no emoji).

| Missing surface | Glyph | Rationale |
| --- | --- | --- |
| Date: Today | `●` | Filled = now |
| Date: Yesterday | `○` | Hollow neighbor |
| Date: This Week | `◌` | Dotted, still in the week |
| Date: Earlier | `·` | Minimal, sorts last visually |
| Date: (no time) | `?` | Already a last-sort bucket |
| Machine: here | `▣` | Local box; avoids `⌂` (default tribe) |
| Machine: remote alias | `▢` | Empty box; tooltip / header still names the alias |
| Unconfigured tribe | `@` | The panel label already is `@name` |
| Merged `All agents` | `☰` | One panel, many tribes |

Date glyphs are the only grouping family with no leading mark today (`format_banner_option` documents "no project bar — the bucket name is the visual anchor"). Machine L0 is the other. Both become necessary the moment labels disappear.

### 3.3 Interaction

- **`j` / `k`:** same `action_agents_next` path. Scroll the owning `AgentList` so the highlighted rail row stays in view. Whole-panel `j`/`k` still cycles tribes when a `❖` title is selected.
- **Click glyph:** select that row (post the same highlight the expanded list uses). Click tribe icon: whole-panel select if the panel is expanded enough to allow it; on a collapsed-`h` tribe, the first click keeps whole-panel focus (today's first `l` expands).
- **`Ctrl+S` / click `«`:** expand to the named list.
- **`'` hints:** the hint letter *replaces* the glyph for the armed frame, as it already replaces a prefix on expanded rows. Five cells is enough for `[7]`.
- **`h` / `l` / `H` / `L` / `z`:** unchanged semantics, compact rendering. A collapsed grouping banner remains a selectable rail row.
- **Focus:** stop calling `_move_focus_off_hidden_list` in rail mode. The list is visible; leaving Textual focus on it is fine. App-level `j`/`k` already work either way.
- **Tooltip on hover:** `{tribe} / {banner or node name} · {status}` so a new user can learn the glyphs. Native Textual tooltips already exist on `NodeSpine`.

### 3.4 What the rail deliberately does not do

- It does not show names, runtimes, provider emojis, or metric chips. The identity header and Main deck already carry those for the selection.
- It does not pack multiple nodes per cell.
- It does not sticky-pin running/failed glyphs out of scroll order. v1 follows tree order. A later pass can add a "attention" pin if the heartbeat is still hard to scan.
- It does not grow past 5 cells when jump hints arm; hints overlay.

---

## 4. Design: zoom chrome (`Z`)

### 4.1 Layout

When `is_zoomed`:

1. `#agent-list-container` `display: none` (same as today).
2. The rail / spine is also `display: none`. **No 2-cell remnant.**
3. The focused deck panel fills `#agents-content`.
4. Identity header, filter bar, info row, footer stay. Zoom is "maximize this node's work," not "hide who this node is." `j`/`k` still change the selected node (already documented: "Z plus j/k steps whole tribe summaries"); the header is how you see that.

### 4.2 How the user knows they are zoomed

Layer three cues so any one of them can fail and the mode still reads:

1. **Deck frame.** The zoomed `DeckPanel` takes a heavy gold outline (`outline: heavy #FFD700`, the same accent as `-whole-panel-focus` and `-focused-panel`). Expanded/rail modes keep the current per-deck accent border (`#B48EAD` Main, green Files, cyan Tools). Gold-around-the-work is reserved for zoom.
2. **Info-row chip.** Replace the current `zoom · Z · nodes 1/1 · Ctrl+S` with a reverse-video gold ` ZOOM ` chip, then dim `Z restore`. Drop the `nodes N/M · Ctrl+S` pair while zoomed; those describe a sidebar that is not there. Keep `group:` and counts.
3. **Footer.** Promote `Z restore layout` to the first Agents footer slot while zoomed (conditional footer, already the pattern for `Ctrl+J/K` cards).

Optional fourth, only if the title strip has room: a tiny `ZOOM` prefix on `deck_title`. `deck_title` already has a width ladder that drops badges; this prefix must be the last thing added and the first thing dropped, so it must not steal the card tabs. Prefer cues 1–3.

### 4.3 Key behavior while zoomed

| Key | Behavior |
| --- | --- |
| `Z` | Restore snapshot exactly (today) |
| `Ctrl+S` | Restore snapshot **and** set `nodes_collapsed=True` (rail showing) — **A3** |
| `\` / `\|` | End zoom, apply split to current state (today) |
| `p` / `Ctrl+N` | Stay in zoom, change the zoomed panel's deck (today) |
| `j` / `k` | Move selection; header follows; rail remains hidden |

The gold frame plus the missing left column is the anti-confusion device. A user who wanted the rail hits `Ctrl+S` and gets the rail *and* their split back.

---

## 5. Implementation approach

### 5.1 State

Keep `DeckAreaState.nodes_collapsed` as "rail vs named list."

Change `_enter_zoom` so it **does not** force `nodes_collapsed=True`. The snapshot already records the pre-zoom flag. Chrome sync keys off `is_zoomed` first:

```
if is_zoomed(state):
    hide list, hide rail, add -nodes-zoomed
elif state.nodes_collapsed:
    show list in rail mode (width 5), add -nodes-rail, hide spine
else:
    show named list, hide rail chrome
```

`toggle_nodes_collapsed` while zoomed becomes: `_exit_zoom` then `nodes_collapsed=True` (A3). Tests in `test_deck_collapse_zoom.py` (`test_collapse_key_ends_zoom_then_toggles`, `test_collapse_key_ends_zoom`) need to be rewritten around restore-snapshot-plus-rail rather than drop-snapshot-plus-toggle.

### 5.2 Render path

Add a `rail: bool` (or `compact=`) argument to `format_agent_option` / `format_banner_option` and to `AgentRenderCache` keys. `patch_row` / incremental display (`tui_perf.md` rule 6) must emit the compact form when the app is in rail mode, and must **not** full-rebuild the list on `Ctrl+S`. Toggle is: set CSS + restyle existing options in place (or rebuild option prompts from cache). Target: collapse/expand in well under the 16 ms p95 `j`/`k` budget, since it is a keystroke path.

Force `#agent-list-container` width to 5 in rail mode inside `_settle_agent_list_container_width`; ignore `AgentList.WidthChanged` content requests while `-nodes-rail` is on.

Tribe `border_title`: in rail mode, either empty the title and paint the icon as row 0, or set `border_title` to the single icon. Empty + row-0 is more reliable at 5 cells (Textual border titles reserve corners). Use **left outline** rather than a four-sided `border: solid` so the inner width stays usable. Existing `-whole-panel-focus` already prefers outline for this reason (`styles.tcss`: "Outlines are paint-only").

**Fallback if OptionList is unusable at 5 cells** (highlight bar, scrollbar, minimum inner width): keep `AgentList` mounted at width 5 with `overflow: hidden` and paint a sibling `Static` rail from the same `_row_entries`. That is a last resort. Try OptionList first; the rows are already `Option`s.

### 5.3 Retire `NodeSpine`

Once the rail and `-nodes-zoomed` land, delete `widgets/decks/node_spine.py`, its compose in `_app_layout.py`, the expand-requested handler, and the spine tests. The gold `«` affordance on the rail replaces `»`.

### 5.4 Tests and goldens

Must-have:

- Pure layout: zoom no longer implies `nodes_collapsed`; `Ctrl+S` while zoomed restores snapshot with rail.
- Compact render unit tests for tribe / banner / node / nested child / collapsed-`h` tribe, one per grouping mode.
- Info-row: rail shows `nodes N/M · Ctrl+S`; zoom shows reverse `ZOOM` and hides the nodes chip.
- Visual goldens: replace `agents_decks_collapsed_single_120x40`, `agents_decks_collapsed_split_120x40`, `agents_decks_zoomed_120x40`. Add a multi-tribe BY_STATUS rail golden and a zoomed-from-split golden so the gold frame is regression-locked.
- `just fix-tui-screenshots` for those selectors; inspect the report (`tui_screenshot.md`).

### 5.5 Perf constraints

From `tui_perf.md`:

- No disk I/O, no list remount, no full rebuild on toggle.
- Highlight still paints immediately; detail panel stays on the 150 ms debouncer.
- Rail restyle is prompt-width work only; it can reuse `AgentRenderCache` with the extra key bit.
- Do not add a periodic "minimap recompute." The rail *is* the list.

### 5.6 Docs

Update `docs/ace.md` §Agents Zoom and Node-Panel Collapse, the Navigation table row for `Ctrl+S`, and glossary `node-panel`. Describe three layouts: named list, icon rail, zoomed. Mention that `Z` hides the rail on purpose.

---

## 6. Alternatives considered

### 6.1 Activity-bar of tribes only

A 3-cell strip of tribe icons, groups and nodes omitted. Cheap, pretty, and closer to VS Code. It throws away the fleet heartbeat, which is the reason to show nodes at all. A user collapsed the sidebar to watch a deck *and* still glance at Running vs Failed. Tribe icons cannot do that.

### 6.2 Keep `NodeSpine`, add tick marks per tribe

Section the current thumb. Still no identity, still identical to zoom. This is a polish pass on the thing the request is trying to leave behind.

### 6.3 All-nodes heatmap (many glyphs per cell, scaled to viewport)

Shows the whole fleet at once. Selection mapping becomes proportional and error-prone (the spine already has this geometry in `_spine_geometry`). Beautiful in screenshots, unreliable under the cursor.

### 6.4 Three-way cycle: named → rail → hidden

A hidden-but-not-zoomed mode duplicates `Z` without the snapshot. Users would lose the tree with no zoom frame to explain why. Two layouts for the sidebar (named, rail) plus zoom as a separate verb is the smaller language.

### 6.5 New `NodeRail` widget fed from `_row_entries`

Clean isolation, and a way out if OptionList cannot render at 5 cells. Cost: a second consumer of selection, hints, folds, clicks, and `patch_row`. That duplication is how this tab has frozen in the past. Compact-mode `AgentList` is the default; `NodeRail` is the escape hatch in §5.2.

### 6.6 Width 8–12 with truncated names

`▶ visua…` is friendlier on day one and spends the width the feature is trying to give back. Five cells is the point: reclaim ~55 columns. Tooltips and the identity header teach names.

---

## 7. Risks

- **Textual OptionList at 5 cells.** Highlight, scrollbar, and border may eat the glyph. Mitigation: outline-not-border, hide the list scrollbar, fallback widget.
- **Glyph collisions.** `▲` epic vs Stopped, `⚙` monitor vs proc, `⌂` default tribe vs any future "home" mark. Mitigation: color + row kind (title vs banner vs node); machine-here uses `▣` specifically to spare `⌂`.
- **Wide Unicode.** `⏳` and any accidental emoji can be 2 cells. Stick to the existing 1-cell set; verify date/machine glyphs in the bundled Fira Code snapshot renderer before locking them.
- **Hint overlay.** `[12]` is 4 cells. Two-digit overflow already has a golden (`agents_jump_panel_collapsed_two_digit_overflow_120x40`). Accept truncation to `[x]` as the expanded titles already do.
- **Snapshot tests.** Collapse/zoom goldens will all move. That is expected; inspect them, do not rubber-stamp.
- **`Ctrl+S` while zoomed (A3)** changes a documented behavior (`docs/ace.md`: "Using a layout key or Ctrl+S while zoomed drops the snapshot"). Document the new restore-plus-rail rule in the same paragraph.

---

## 8. Recommended solution

Ship **two layouts for the left column**, and make zoom a third, visually louder state.

1. **Named list** (today's default). ~60 cells, full titles, banners, rows.
2. **Icon rail** (`Ctrl+S`). 5 cells. The same `AgentList` widgets, compact prompts, left identity accent, gold `«` to expand. Visible-tree 1:1 glyphs, status-as-heartbeat for nodes, existing tribe/type/banner glyphs, four new date marks and two machine marks, `@` for unconfigured tribes. Scroll with selection. Persist as `nodes_collapsed`.
3. **Zoom** (`Z`). Left column gone. Heavy gold outline on the focused deck, reverse-video ` ZOOM ` chip, footer `Z restore layout`. Snapshot restore on `Z`. `Ctrl+S` restores the snapshot *and* lands on the rail.

Implementation: compact render mode + CSS classes `-nodes-rail` / `-nodes-zoomed`; stop forcing `nodes_collapsed` on zoom; retire `NodeSpine`. No keymap change. No sase-core change. Visual goldens and the three `test_deck_collapse_zoom` behaviors are the acceptance tests.

This is the VS Code Activity Bar for a live agent tree, and tmux zoom for a deck, using the icon language the Agents tab already taught.
