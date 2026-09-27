# Agents-tab collapsed sidebar: icon rail + zoom indicator — research (`mus`)

## Summary

The request is sound: today `ctrl+s` (collapse) and `Z` (zoom) converge on the
same visual — the node panel vanishes and only a 2-cell scroll-thumb spine
remains — so the two states are indistinguishable and collapse destroys all
navigational context. Replacing collapse with a narrow icon rail that preserves
one row per tribe / group / node, and giving zoom a distinct, unmissable
treatment, is the right fix. The codebase already owns ~90% of the needed
vocabulary (status glyphs cover every group kind; tribe identity colors exist;
the info panel already distinguishes collapsed vs zoomed). Recommendation: build
a **~6-cell icon rail** reusing the existing status/type glyphs plus tribe
color chips, keep it read-only-navigable (cursor moves, `enter`/click expands
to the target), and mark zoom with a **gold border + "ZOOM" badge on the deck
panel chrome** rather than anything in the rail. Details below.

## Current behavior (verified in tree)

- `ctrl+s` → `toggle_node_panel` (`src/sase/ace/tui/bindings.py:276`); `Z` →
  `zoom_panel` (`bindings.py:44`). Gated to the Agents tab
  (`tests/.../test_deck_collapse_zoom.py`: `test_collapse_and_zoom_gating`).
- State is `DeckAreaState.nodes_collapsed: bool` + `zoom_snapshot`
  (`widgets/decks/model.py:140-148`). Zoom snapshots layout/panels/focus/ratio
  and forces `SINGLE` + collapsed (`widgets/decks/layout.py:139-159`); unzoom
  restores exactly. `ctrl+s` while zoomed ends the zoom then toggles
  (`layout.py:124-131`) — sensible, keep.
- Collapsed rendering today: `#agent-list-container { display: none }` and a
  2-cell `NodeSpine` (scrollbar-thumb minimap + `»`, click-to-expand, tooltip)
  (`styles.tcss` ~`#agents-content.-nodes-collapsed`, `widgets/decks/node_spine.py`).
  Zoomed rendering today is pixel-identical plus an info-panel chip
  (`agent_info_panel.py:453-469`: `zoom <key> · nodes pos/total <key>`).
- Node panel content: one `AgentList` widget per tribe/panel key, mounted in
  `#agent-list-container` (`_app_layout.py:137-138`,
  `actions/agents/_display_panel_widgets_mount.py`). Rows are banners
  (project / Patch / bucket / name-root tiers) + agent/attempt rows.
- **Icon coverage is already complete for groups**: every status bucket has a
  glyph — `Stopped ▲, Starting ◐, Running ▶, Queued …, Waiting ⏳, Failed ✗,
  Done ✓` (`src/sase/agent/status_buckets.py:18-26`), reused in `BY_STATUS`
  banners (`_agent_list_styling.py:97-99`). So the "not sure every group has an
  icon" worry is resolved for status; project/Patch/date/machine tiers use the
  `▌ ▎ ▸` bar/branch registers instead of semantic icons.
- Row-level glyphs exist too: `_TYPE_GLYPHS`, monitor/gate/named-proc glyphs,
  provider emoji badges (`_agent_list_render_agent_prefix.py`,
  `_agent_list_styling.py`). Tribes have per-tribe identity colors via
  `ace.tribes` config (`models/tribe_display.py`).
- Grouping modes that the rail must survive: `STANDARD / BY_DATE / BY_STATUS /
  BY_MACHINE` (`models/agent_groups/_buckets.py:39-51`).

## Critique of the plan

**Good idea, worth doing.** Collapse-that-erases is hostile to the
"glance, then dive back in" loop the Agents tab exists for; an icon rail keeps
orientation (which tribe is hot? did something just fail?) at ~6 cells cost.
And zoom-vs-collapse confusion is a real misread risk precisely because the two
states share all chrome today.

**Adjustments I would make (called out):**

1. **Do not try to represent literally every node as its own rail row.**
   The prompt asks for "every tribe, agent group, and node ... still
   represented". A 1:1 row mapping reproduces the full tree height in 6 cells
   and reintroduces scrolling inside the collapsed thing — at which point it is
   just a small sidebar, not a collapsed one. Instead: one rail section per
   tribe panel, inside it one glyph per *group banner* (status glyph for status
   buckets, `▌/▎/▸` tier marks otherwise), and per-node presence *aggregated*
   into its group's glyph (count badge + worst-status color). Nodes remain
   "represented" (their status visibly rolls up) without a 1:1 row tax.
   If the user wants node-level targeting, selecting a rail entry expands the
   panel with the cursor pre-moved there — cheaper and more reliable than
   aiming at a 1-cell node row.
2. **Scope the rail to collapse only; zoom keeps the current spine.**
   Zoom means "this deck is my whole world for a while" — adding a live rail
   beside it invites focus/keybinding ambiguity for no benefit, and keeping the
   spine-only treatment makes zoom *visually distinct* from collapse, which is
   half the request. The zoom indicator work (below) carries the
   disambiguation instead.
3. **Do not add new group icons.** Status glyphs + existing tier marks + tribe
   colors cover everything. New glyphs would fragment a coherent visual
   language for marginal gain. The one gap worth filling is *tribe identity in
   1 cell*: use the tribe's identity color as the section marker background
   (or first-letter-on-color when a letter is unambiguous), not a new icon.
4. **Make the rail an indicator first, a navigator second.** Passive value
   (failure `✗` turning red somewhere in peripheral vision) is the 80% win.
   Navigation (j/k over rail entries, `enter`/click to expand-and-jump) is the
   20% — include a minimal version, but do not replicate the tree's full
   keyboard model inside the rail.

## Recommended design

### Collapsed rail (ctrl+s)

- **Geometry**: replace `NodeSpine` (2 cells) with a `NodeRail` widget,
  fixed **6 cells** wide (`min=max=6`), full height, `background: $surface`.
  6 cells fits `▌▶` + 2-digit count + padding, and stays affordable on
  80-column terminals next to `MIN_AGENT_LIST_WIDTH = 60`. Keep the container
  swap CSS-driven (`-nodes-collapsed` class, same pattern as today) so no
  unmount/remount of `AgentList` widgets is needed — state and scroll survive.
- **Content model** (top to bottom): for each mounted tribe panel in order, a
  1-row tribe header (color chip in the tribe identity color + abbreviated
  name, truncated to width), then one row per top-level group banner of that
  panel: `<tier-mark><status-glyph> <count>`, colored by worst status in the
  group (failed-red wins over running-green wins over idle-dim). Attempt-level
  detail is never shown; selected/failed nodes surface only through the
  aggregate color + count. Cap total rows to rail height with overflow
  collapsed into a final `⋯N` row (same aggregation rule) rather than
  scrolling — scrolling a 6-cell rail is fiddly; the expand path covers
 precision.
- **Reuse, concretely**: status glyphs from `AGENT_STATUS_BUCKET_GLYPHS`;
  tier marks `▌ ▎ ▸` from `_agent_list_styling.py`; tribe colors from
  `tribe_display_for(panel_key)`; count/badge styling from the info panel's
  `_COUNT_STYLES`. No new glyph inventory, no new palette.
- **Interaction**: rail is focusable as a single unit. `j/k` (or arrows) move a
  highlight across rail entries; `enter` or click expands the panel
  (`toggle_nodes_collapsed`) and moves the tree cursor to that tribe/group;
  `ctrl+s` / `Escape` expands without moving the cursor. Tooltip per entry
  (`group label · N nodes · worst status · click to expand`) mirrors the
  existing spine tooltip pattern. Respect the existing focus-safety helper
  (`_move_focus_off_hidden_list` inverse: focus has somewhere legal to go in
  both directions).
- **Persistence**: keep persisting the `nodes_collapsed` bool as today
  (`agent_deck_persistence.py` schema v1); rail *selection* is ephemeral and
  not persisted. No schema change needed.

### Zoom indicator (Z)

The requirement is "can't mistakenly think the sidebar is just collapsed", so
the signal must live where the user is looking — the deck — not in the rail:

- **Gold focus border on the zoomed deck panel** + a right-aligned `ZOOM`
  badge in the panel title/chrome (reuse the `#FFD700` gold already used for
  focused-panel borders and the info-panel `zoom` chip). Border color is
  visible in peripheral vision; a text badge is unambiguous up close.
- **Keep the info-panel chip** (`zoom <key> · nodes pos/total`), since it also
  teaches the exit key — but it is not sufficient alone (one-line text is easy
  to miss), hence the border+badge as primary.
- **Exit paths unchanged**: `Z` restores the snapshot; `ctrl+s` ends zoom then
  toggles (current, tested behavior); layout keys end zoom without restore
  (`test_layout_key_ends_zoom_without_restoring`). The badge should show the
  exit key (`Z`) in dim text to close the loop.
- Explicitly **do not** show the new icon rail while zoomed — spine-only +
  gold deck chrome is then the unique zoom signature, and collapse (rail, no
  gold) can never be confused with it.

### Reliability notes

- **Focus legality** is the sharpest edge: collapsing today already needs
  `_move_focus_off_hidden_list`; the rail adds the reverse path. Both
  directions must be covered by widget tests (extend
  `test_deck_collapse_zoom.py` — pure-state tests plus an `AgentDetail` chrome
  test asserting rail/spine visibility classes and focus container).
- **Grouping-mode independence**: the rail reads the same `GroupRow` banner
  list the tree renders, so all four `GroupingMode`s work by construction;
  add one test per mode asserting rail rows ≤ height cap and counts sum to
  panel totals.
- **Narrow terminals**: at <~70 cells the rail + deck minimum may squeeze;
  rule: rail keeps its 6 cells (it is the orientation device) and the deck
  scrolls horizontally — never auto-expand the panel as a "responsive" move,
  which would yank state the user explicitly set.
- **Performance**: rail content derives from already-computed banner summaries
  (`compute_banner_summary`); update it on the same refresh tick as the tree,
  not on its own timer. No new data pipeline.
- **Accessibility/mouse-optional**: every rail action has a key equivalent
  (`ctrl+s` expand, `enter` expand-and-jump); click is a shortcut, never the
  only path. Keep the `»`-style affordance glyph on the rail's top row as a
  discovered affordance for mouse users (continuity with today's spine).

### What I would explicitly not do

- No per-node 1:1 rail rows (argued above).
- No new icon set, no emoji in the rail (emoji width is unreliable in
  terminal cells; the existing glyphs are all single-cell).
- No rail-while-zoomed, no auto-expand heuristics, no persisted rail cursor.
- No change to the zoom snapshot semantics — they are well-tested and the
  `exit_zoom_keeping_panels` path (deck changed while zoomed) already handles
  the tricky case.

## Implementation sketch

1. New `widgets/decks/node_rail.py` (`NodeRail` Static): `update_from_panels(
   list[(panel_key, tribe_display, list[GroupRow + summary])])`, fixed-width
   render, highlight index, `ExpandRequested(tribe, group)` message.
2. Compose `NodeRail` next to `NodeSpine` in `_app_layout.py` (`agents-content`
   block); `_sync_nodes_collapsed_chrome` shows rail when collapsed-and-not-
   zoomed, spine when zoomed, neither when expanded.
3. `panel.py` chrome: add gold border class + `ZOOM` title badge when
   `is_zoomed(state)` and panel is focused one (`area.py:80-94` already
   isolates the zoomed panel — hook the badge there).
4. Key/action wiring: reuse `toggle_node_panel` / `zoom_panel` actions; add
   rail-local `j/k/enter` handling + click → existing expand + cursor-move
   helpers. No keymap defaults change.
5. Tests: extend `test_deck_collapse_zoom.py` (rail row model incl. overflow
   cap × 4 grouping modes; chrome visibility matrix expanded/collapsed/zoomed;
   focus legality both directions; snapshot semantics untouched).

## Open questions for the lead

- Is 6 cells the right rail width, or should it be a user setting (like deck
  ratios)? I lean fixed — one less preference, and dynamic widths fight the
  "collapsed means predictable" contract.
- Should the rail's worst-status rollup include `Stopped ▲` (needs-you) at the
  same urgency as `Failed ✗`? I say yes — both are "user action required" —
  but that is a product call.
