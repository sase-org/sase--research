# Agents-tab `"` node-jump panel: research & recommended design

Researcher: mus. Independent report; no peer reports consulted.
Scope: a new `"` keymap on the Agents tab opening a large panel that jumps to
*any* node — including hidden agent-session shells and hidden clan members —
with always-visible jump hints, a filter query bar, `<tab>` focus toggle,
`<enter>` selection, a fast preview of the selected node, and
`<ctrl+n/p>` cycling. Bash/Python workflow steps are explicitly out of scope
(they must never be jump targets).

## 1. What exists today (verified in-tree)

### 1.1 The backtick panel: `JumpAllModal` (cross-tab)

- `src/sase/ace/tui/modals/jump_all_modal.py` — `JumpAllModal`, opened by the
  `grave_accent` (`` ` ``) app binding `jump_to_all_entries`
  (`src/sase/ace/tui/bindings.py:24`, `src/sase/default_config.yml:747`).
- Lists entries from all tabs (Artifacts/Patches, Agents, Services/AXE) with
  **adaptive one- or two-character hints** from
  `src/sase/ace/tui/actions/navigation/jump_hints.py`
  (`build_jump_hint_maps`, `match_jump_hint`, `normalize_jump_key`;
  `JUMP_HINT_CHARS` is base-62, capacity 62 / 3844). Hint keypresses jump
  immediately; two-char hints use a pending-prefix state. `esc` cancels,
  `` ` `` jumps back to the last position, `ctrl+d/u` scrolls.
- Important limitation for this feature: it is a **static snapshot** —
  entries are built once in `__init__` (`_build_entries`), there is **no
  filter input, no selection cursor, no preview**. Any key that is not a hint
  (or the few scroll keys) dismisses the modal. That "type-to-jump-or-leave"
  contract is exactly what the new panel must *not* copy for its filter bar.

### 1.2 The apostrophe mode: in-place entry-jump (`'`)

- `action_jump_to_entry` (`'`, `src/sase/ace/tui/actions/navigation/
  _entry_jump_mode.py:18`) enters jump mode **in the current tab's own list**
  rather than opening a modal. On the Agents tab it allocates hints over
  `_jump_candidate_targets()` (same file, ~line 180): panel titles
  `("panel", key)`, collapsed in-panel banners `("banner", ...)`, and visible
  **agent rows** — walking each tribe panel's grouping tree in render order
  (`build_agent_tree`, `rendered_panel_slice`).
- Critically, jump candidates are **visible rows only**: collapsed panels
  contribute only their title target; hidden members/shells under a collapsed
  fold never get hints. The requested `"` panel is therefore *not* a
  duplicate of `'`: `'` jumps within what you can already see, `"` must
  reach what you cannot see. Keep both; they compose (`"` reveals, `'`
  fine-navigates).
- Related machinery worth reusing: `prepare_agent_navigation_target` /
  `reveal_agent_navigation_target` in `_agent_reveal.py` — the validated
  reveal contract (unfold ancestors to `FULLY_EXPANDED`, re-snap focus,
  `AgentRevealFailure` taxonomy including `TARGET_FILTERED`). A jump to a
  hidden node from the new panel should go through this reveal path, not
  hand-rolled fold mutation.

### 1.3 The closest interaction precedent: `CommandPaletteModal`

- `src/sase/ace/tui/modals/command_palette_modal.py` already implements the
  **filter-input + list + footer** shape the request describes: a `FilterInput`
  (`modals/base.py`), an `OptionList`, live ranked filtering (`_score_match`:
  exact > prefix > substring, stable for ties), empty-state handling, and —
  directly on point — **`ctrl+n`/`ctrl+p` and `up`/`down` work even while the
  Input has focus** via `on_key` forwarding (`action_next_option` /
  `action_prev_option`). This is the template for the "query bar focused but
  ctrl+n/p still cycles" requirement. `OptionListNavigationMixin`
  (`modals/base.py`) also standardizes `escape/q` cancel, `j/k` + arrows +
  `ctrl+n/p` navigation bindings.
- So the requested `<ctrl+n/p>` cycling is a solved problem in-tree; the new
  panel should copy the palette's `on_key` forwarding pattern verbatim.

### 1.4 The node universe the panel must enumerate

- `is_agents_tab_agent_node` (`models/agent_nodes.py`): agent nodes are
  standalone root rows and sequential-session containers — **not** clan
  containers, session-member shells, workflow/step children, proc shells,
  monitors, or gates. The request's "hidden agent session shells" are
  `concrete_agent_session_shell_rows(agent)` and "hidden clan members" are
  `clan_members(agent)` (`models/_agent_clan.py:230`) —
  both pure in-memory projections, cheap to enumerate.
- Explicitly excluded per the request: Bash/Python steps. The codebase
  already draws this line: `_concrete_agent_rows`
  (`models/agent_session_members.py`) returns `()` for non-agent workflow
  steps, and `is_hidden_step` rows (`models/_agent_state.py:143`) are
  scaffolding, not destinations. The panel's enumerator must apply the same
  predicate: agent-type steps and session shells yes; `step_type != "agent"`,
  `agent_session_parallel` scaffolding, proc shells, monitors, gates no.
- Names: `agent_tree_title(ag) or presented_agent_name or agent_name or
  display_name or humanize_cl_name(cl_name)` (+ `raw_suffix`) is the exact
  expression `JumpAllModal._build_entries` uses — reuse it so names in the
  new panel match names elsewhere.

### 1.5 Filtering and preview precedents

- The Agents tab already has a query language (`_agent_search_query`,
  `actions/agents/_core.py`) and a live-query engine
  (`models/agent_live_query*.py`). The new panel should **not** reuse the
  tab's query syntax (too powerful/confusing for a jump box); it needs the
  palette's simple rank-by-name substring match. "Filtering by node name" is
  the right scope — status/type facets would bloat v1.
- Preview cost is the main perf risk. The Agents detail panel is updated
  through a `DetailPanelDebouncer` (`actions/agents/_display.py:554`) precisely
  because prompt-panel enrichment is disk-backed (see the clan-sections note:
  "Disk-backed enrichment lives in the prompt-panel worker layer"). A "good
  but fast" preview therefore means: render **in-memory row facts only**
  (name, status bucket, model, workspace, timing, member/shell counts —
  the `ClanMemberDigest`-style fields), never trigger the disk worker or a
  refilter. Debounce preview updates (~100ms) while ctrl+n/p is held.

### 1.6 Keymap facts

- `"` is Textual key name **`quotation_mark`** (verified against the
  vendored Textual 8.0.1: `key_to_character('quotation_mark') == '"'`). The
  repo's `key_validation.py` has no `quotation_mark` entry yet and **nothing
  in-tree binds it** (no grep hits), so it is free in every scope. It needs:
  a `_KEY_DISPLAY` entry (`'"'`), likely no new alias, a keymap default
  (`app_keymaps.py` + `default_config.yml`), metadata row, and help-modal
  text.
- `"` is `Shift+'` on US layouts — adjacent to the existing `'` jump key,
  which is a genuine mnemonic win ("`'` jumps to what you see, `"` jumps to
  everything"). Note the failure mode: some layouts/terminals deliver `"`
  unreliably over SSH/tmux; keep the action also runnable from the command
  palette so it is never unreachable.
- `<tab>` focus toggle: `tab`/`shift+tab` currently switch tabs at app level
  (`default_config.yml`: `next_tab: "tab"`). Inside a modal, `Input` focus
  handling takes precedence, but the panel must explicitly bind `tab` to
  cycle input-focus while open, and document that tab-switching is suspended
  until the panel closes (same as every other modal).
- `<enter>`: `Input.Submitted` already submits the highlighted row in the
  palette pattern — reuse directly.
- `ctrl+n`/`ctrl+p` on the Agents tab are already movement-adjacent
  (`next_chop_run`/`prev_chop_run`, `next_deck`/`prev_deck` in app scope),
  but modal bindings shadow app bindings while the modal is open, and the
  palette precedent proves this composition works. No conflict.

## 2. Critique of the plan

**Is it a good idea? Yes — with the scope as stated it fills a real gap.**
`'` covers visible rows, `` ` `` covers cross-tab top-level entries, but
nothing reaches a shell buried three folds deep in a collapsed clan without
manual unfolding. A fuzzy "go to node" box is the standard solution
(vscode `ctrl+p`, IntelliJ double-shift, emacs `consult-buffer`) and the
request maps onto it cleanly. The "hidden members/shells, no Bash/Python
steps" scoping is correct and matches predicates the codebase already has.

**Adjustments I would make (called out explicitly):**

1. **Default focus: keep the request's choice (hints active, input
   unfocused) but add first-keystroke auto-focus.** The request says the
   query bar starts unfocused with `<tab>` to focus. That is right for
   hint-speed, but users will type a letter expecting to filter and instead
   jump somewhere. Mitigation: when unfocused and the pressed key matches no
   hint prefix, **move focus into the query bar and feed it that character**
   instead of dismissing (the backtick modal's "unknown key dismisses" is
   the behavior not to copy). This keeps hint-first speed with zero
   lost-keystroke rage. Still bind `<tab>` as the explicit toggle.
2. **Hints must be reallocated on every filter change — and that is fine.**
   The request says hints "always render next to nodes". With filtering, hint
   labels cannot be stable across keystrokes; re-run `build_jump_hint_maps`
   over the *filtered* list on each change (fixed-width mode is O(n)). Do not
   try to preserve labels — flicker is worse than reassignment, and the
   palette's stable-sort keeps row order predictable so re-hinting feels
   stable in practice. Consider `prefix_free=True` (exists in
   `jump_hints.py`) once target counts routinely exceed 62; default
   fixed-width is fine for v1.
3. **Make it Agents-tab-scoped, not cross-tab.** The request says "navigate
   to any node" — read "node" as "Agents-tab node" (agents, clan members,
   session shells, panels/banners), not "any entry in any tab". Cross-tab is
   `` ` ``'s job; duplicating it splits muscle memory. The panel lists one
   section per tribe panel plus Members/Shells groupings.
4. **Preview: in-memory facts only, debounced (see 1.5).** "Large panel with
   preview" is right, but the preview must never do disk I/O or trigger the
   prompt-panel worker. Show: full name + suffix, status bucket, model,
   workspace, start/stop timing, session-shell roster position (e.g. shell
   3 of 7), clan membership, and the unfold path that Enter will reveal.
   That last line ("will expand Clan X › Session Y") is what makes hidden
   jumps *reliable-feeling*.
5. **Cap and virtualize.** A huge fleet can mean thousands of shells;
   `JumpAllModal` truncates at `ZZ` (3844) and renders one `Static`. The new
   panel should cap the *rendered* list (e.g. show first ~200 ranked matches
   + "N more — keep typing") while keeping hints allocatable over at most
   the rendered set. Filtering keeps this fast; rendering must not be O(all
   shells) per keystroke.
6. **Jump must reveal, then focus, and offer back-jump.** Route Enter/hint
   through `prepare_agent_navigation_target` /
   `reveal_agent_navigation_target`, set `current_idx`, and push the
   pre-jump anchor so `'`-back (existing `_entry_jump_agents_anchor_stack`
   machinery) returns. A jump that lands you somewhere with no way back will
   train users not to use the panel.
7. **Beauty specifics (since the request asks):** reuse `JumpAllModal`'s
   visual language (section rules `── Label (count) ──`, `[hint]` in bold
   yellow, status right-column with `_AGENT_STATUS_STYLES` colors) so the two
   jump surfaces look like siblings; three-column layout
   list | preview with the query bar on top, footer with live
   `shown/total` count + position gauge copied from the palette
   (`_build_count_text`, `_build_position_text`); size like the palette
   (85% × 80%, `border: double`) rather than inventing new chrome. The
   single most beautiful thing this panel can do is update all three regions
   (list, hints, preview) synchronously per keystroke with no flicker —
   prefer one `Static`-per-region update over an `OptionList` rebuild if
   profiling shows rebuild flicker at 200 rows.

## 3. Recommended solution

Build **`NodeJumpModal`** (`src/sase/ace/tui/modals/node_jump_modal.py`),
a large `ModalScreen` opened by a new Agents-tab action
`action_jump_to_node` bound to **`quotation_mark`** (`"`), following the
`CommandPaletteModal` architecture with `JumpAllModal`'s hint system:

- **Layout:** title (`✦ Jump to Node` + shown/total count) → `FilterInput`
  (starts **unfocused**) → horizontal split: filtered node list with always-
  rendered `[hint]` labels (left, ~60%) + in-memory preview of the
  highlighted node (right, ~40%) → footer (key hints + position gauge).
- **Data:** enumerate all Agents-tab nodes in render order — agent nodes,
  panel titles, collapsed banners (as in `_jump_candidate_targets`), **plus**
  hidden session shells (`concrete_agent_session_shell_rows`) and hidden
  clan members (`clan_members`), excluding Bash/Python steps, parallel
  scaffolding, proc shells, monitors, gates (reuse `_concrete_agent_rows`
  predicates). Allocate hints over the filtered list with
  `build_jump_hint_maps` per keystroke.
- **Interaction:** hint keys jump immediately (pending-prefix for two-char
  hints); `<tab>` toggles query-bar focus; first non-hint keystroke
  auto-focuses the bar and seeds it (adjustment 1); `<enter>` reveals +
  focuses the highlighted node via the `_agent_reveal` contract and pushes a
  back-jump anchor; `<ctrl+n/p>`, arrows, `j/k` cycle with debounced preview
  refresh; `esc` cancels; list capped at ~200 rendered rows.
- **Wiring:** new `jump_to_node: "quotation_mark"` keymap entry
  (`app_keymaps.py`, `key_validation.py` display entry, `metadata.py`,
  `default_config.yml`, `bindings.py`, help-modal Agents text, command
  catalog entry so it is palette-runnable as a fallback for awkward
  layouts). Reuse `agent_tree_title` naming, `_AGENT_STATUS_STYLES` colors,
  palette footer/count/gauge helpers, and palette `on_key` ctrl+n/p
  forwarding. Styles in `styles.tcss` next to `JumpAllModal` (same border,
  same dimensions family).
- **Tests:** hint reallocation over filtered lists (incl. >62 targets),
  Bash/Python-step exclusion, auto-focus-seed behavior, reveal-through-
  `_agent_reveal` for a collapsed-clan member, rendered-row cap, and
  `enter`-on-empty-filter no-op. Screenshot-verify the three-region layout
  per the repo's TUI snapshot tooling.

This delivers every requested behavior, stays inside proven in-tree patterns
(palette for filter+cycle, backtick modal for hints, reveal contract for
landing), and the seven adjustments above are the difference between a demo
and a daily driver.
