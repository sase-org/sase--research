# Agents-Tab Node Finder (`"`): Research, Critique, and Recommended Design

- **Researcher:** cld (4-researcher swarm; independent report)
- **Date:** 2026-09-25
- **Repo state:** `sase` master @ `27d03a7b7`
- **Request:** A new `"` keymap on the Agents tab. It opens a large panel with always-visible jump hints next to _every_ sase node, including hidden ones. The panel has a name-filter query bar that is unfocused by default, `<tab>` to toggle focus, `<enter>` to jump, `<ctrl+n/p>` to cycle, and a fast preview. Agent-shell Bash/Python steps are excluded.

---

## TL;DR

**Verdict: build it.** It is a good idea and fills a real gap. Every jump surface on the Agents tab today can reach only rows that are already rendered, or only the relations of the currently selected container. The risky part is already solved: `_reveal_agent_row()` reveals a node by stable identity through tree folds, grouping banners, and collapsed tribe panels, and saves a jump-back anchor. Most of the work is a well-designed modal on top of it.

I endorse the user's interaction model (hints first, `<tab>` to search) with these main adjustments, each detailed in §4:

1. **Name and vocabulary.** Call it the **Node Finder**, titled "Jump to Node". Do not call it a "jump panel": that name already belongs to the sticky roster footer below the deck panels.
2. **"Hidden" is tiered.** Hidden by structure (folds, banners, collapsed or isolated panels) is fully supported in v1. Hidden by the Agents query is listed with a badge; jumping clears the query, records it in query history, and shows a toast. Hidden by `I` (`%hide`/axe-spawned) is phase 3 unless Bryan says that is what "hidden" meant. Dismissed agents are never listed.
3. **Every hint must work.** List only nodes the jump can actually reach. The list is a snapshot taken on open, so hints never reshuffle under the user's fingers. The target is revalidated by identity at jump time.
4. **Tree-shaped list, not a flat list.** It mirrors the Agents tab (tribe → clan → member → session → shells). Hidden rows are ghosted and carry a one-glyph _why-hidden_ marker. While filtering, ancestors stay visible as dim context rows.
5. **Opens on "you are here".** The highlight starts on the currently selected node. `""` jumps back, following the SASE convention where `''` and `` `` `` do the same.
6. **Esc behaves like vim.** In search mode Esc returns to hint mode; in hint mode it closes. A key that is not a hint is swallowed with a footer flash; it does not dismiss the modal (JumpAllModal does dismiss).
7. **Two-tier preview.** Tier 0 is synchronous with zero I/O and built from existing pure renderers. Tier 1 is a debounced, off-pump prompt/reply load with a small modal-local LRU. The preview never reuses `AgentDetail`/deck rendering, which reads disk synchronously on the pump.

The full recommendation is in §10.

---

## 1. What exists today

### 1.1 Four jump surfaces, one shared blind spot

| Surface | Key | What it can reach | Blind spot |
|---|---|---|---|
| Entry jump | `'` (`ctrl+o` back) | Rows currently rendered in the Agents list, collapsed banners, and panel titles (`_jump_candidate_targets`, `src/sase/ace/tui/actions/navigation/_entry_jump_mode.py:180`) | Folded children, rows under collapsed panels, anything filtered |
| Cross-tab jump | `` ` `` | `app._agents`, i.e. the already folded and filtered visible rows (`actions/navigation/_modals.py:51-57`) | Same as above. It also shows raw names such as `sase/20260925094154` (`modals/jump_all_modal.py:176-186`) |
| Roster digits | `0-9`, `00-99` | Agent relation jump targets of the **selected** container only (session shells, neighbors, clan or tribe members), revealed through folds (`actions/navigation/_member_jump.py:249-275`) | Anything not related to the current selection |
| Link follow | `$` | `agent:` links, looked up in `_agents_with_children` (`actions/_link_follow_targets.py:228-300`) | Only nodes that are linked from somewhere |

**Live evidence** (captured with `sase screenshot` on this host): the Agents tab showed `@research` with a collapsed `research.8` clan of 6 members and `@epic` with a collapsed `sase-169` clan. Pressing `` ` `` listed **8 agents in total**. None of the 6 `research.8.*` members, the `sase-169.*` sessions, or their `--plan`/`--mon-N` shells appeared. The only way to reach `research.8.cdx` today is to select the clan and then press its roster digit. Reaching `sase-169.3--mon-1` means drilling through clan → session → shell.

### 1.2 The reveal primitive already does the hard part

`MemberJumpNavigationMixin._reveal_agent_row(identity, subject=...)` (`actions/navigation/_member_jump.py:370`) is built on `prepare_agent_navigation_target()` and `reveal_agent_navigation_target()` (`actions/navigation/_agent_reveal.py:129`, `:312`). Given a stable `Agent.identity`, it:

- walks and validates the whole ancestor chain against `_agents_with_children`, then expands exactly those folds (`FULLY_EXPANDED` for hidden steps, `EXPANDED` otherwise);
- expands only the grouping banners that enclose the target, and expands the target's tribe panel;
- saves an Agents jump anchor first, so `ctrl+o` / `''` return to where you were, and rolls the anchor back if the reveal fails;
- focuses the right panel, selects the row, acknowledges unread state, and triggers one structural refresh;
- reports typed failures (`TARGET_MISSING`, `TARGET_FILTERED`, `TARGET_NOT_VISIBLE`, …) through `_notify_member_reveal_failure(..., subject=)` (`:463`), which already accepts other callers' wording.

`Agent.identity` is value-based: `(type, cl_name, raw_suffix)`, or `clan:<name>` plus generation for clans. It survives reloads, so it is the right key for a snapshot-then-jump modal.

### 1.3 Every way a node can be hidden (and what the primitive can undo)

| # | Mechanism | Row lives in | Undone by `_reveal_agent_row`? |
|---|---|---|---|
| 1 | Tree folds: clan, session, workflow; monitor/gate shells gated by the session fold (`models/_fold_filter.py:8`, `models/_agent_tree.py:43-75`) | `_agents_with_children`, not `_agents` | **Yes** |
| 2 | Collapsed grouping banners (Running/Done/by machine) | `_agents`, hidden at render time | **Yes** |
| 3 | Collapsed or `=`-isolated tribe panels | `_agents` | **Yes** (reopening a non-isolated panel drops the `=` restore record) |
| 4 | Agents query (`/`, `f`), applied after folds (`filter_tree_rows`, `models/_agent_tree.py:607`) | `_agents_with_children`. Under query pushdown, rows outside the window may not be loaded at all | **No**: fails with `TARGET_FILTERED` |
| 5 | `I` hide-non-run, **default on** (`app.py:205`). Hides `agent.hidden` rows (`%hide`, axe-spawned), running or failed; hidden rows that finished successfully are auto-dismissed (`actions/agents/_loading_compute.py:466-495`, `_loading_helpers.py:93`) | Only `_agents_capacity_with_children` (flat, and stale after kill/dismiss) | **No**: fails with `TARGET_MISSING`, and undoing it needs an async reload |
| 6 | Dismissed or removed | `_dismissed_agent_objects` | **No**: the only way back is a *revive*, which is a mutation |
| 7 | Structurally unreachable: top-level workflows containing only hidden steps (`hidden_only_parents`, `_fold_filter.py:63`); `STARTING` rows (not rendered in panels) | `_agents_with_children` / `_agents` | **No** |

Nothing in the codebase today clears the Agents query or flips `I` in order to reach a target. The closest precedents are the Artifacts link-follow ladder (`actions/_link_follow_ladder.py`, toast wording in `_link_follow_toast.py`, e.g. "hidden by ‹terms›") and `prospective_clan_projection()` (`actions/agents/_prospective_clan.py`). The latter simulates relaxed folds on `_agents_with_children` with `_FoldStateProjection(levels)` and then applies the live query. That simulation is the template for this feature's classification step.

---

## 2. Critique: is this a good idea?

**Yes.** Reasons:

- **It closes a real gap.** The Agents tab has become a deep tree: tribes, clans, sessions, shells, monitors, gates, workflow steps. Folding is essential for keeping the overview readable, but today folding makes nodes unreachable without manual drilling. A global "go to anything" palette is the standard answer in tree UIs.
- **Strong precedents.** tmux `choose-tree` is the closest analog: a tree plus shortcut keys (`0-9a-z`) plus a filter plus a preview of the selection. Telescope has a normal/insert split where hints (normal) and typing (insert) coexist. VS Code quick-open, fzf, and flash.nvim labels fill the same role.
- **Low implementation risk.** The reveal, hint allocation (`jump_hints.py`), Rust fuzzy matcher (`sase.core.fuzzy_facade.fuzzy_match`), match highlighting, compact identity renderers, and debounce/pump-free machinery all exist. The new code is mostly a modal plus one pure projection function.

**Risks and critiques, each addressed in §4 and §5:**

1. **Too many jump surfaces.** `'`, `` ` ``, digits, `$`, `,j`/`,J`, and now `"`. Mitigation: position `"` as the Agents-only superset ("anything on this tab"). Reuse the house conventions: hint style, `[h]` gutter, double-press means back, `ctrl+o` history. Put it right next to the existing jump rows in `?` help.
2. **Name collision.** "Jump panel" is a glossary term (the sticky footer that lists agent relation jump targets, toggled with `.`), and plain "jump target" is flagged as ambiguous. Calling the new thing the "jump panel" would confuse users and agents. → **Node Finder**.
3. **"Hidden" is ambiguous in SASE.** It means both *not currently rendered* and the literal `agent.hidden` (`%hide`/axe-spawned, toggled by `I`). The two need very different machinery (see rows 1-3 versus row 5 in §1.3). The request's examples ("hidden agent session shells and hidden agent clan members") read as folded-away nodes. That is my working assumption, flagged as open question Q1.
4. **Mode confusion.** Hint mode and search mode make the same letter key mean different things. That is fine if the mode is unmistakable: hints dim while typing, the input border lights up, a mode pill shows, and the footer changes.
5. **Hints must never lie.** A hint on a node that cannot be reached, or that changes during a background refresh, is the fastest way to make this feel unreliable. The list is snapshotted on open, only reachable nodes are listed, and identity is revalidated at jump time.
6. **Preview cost.** The obvious shortcut is to embed the real detail/deck renderer. It would violate the TUI perf rules: `AgentDetail`'s debounced paint reads prompt and reply files synchronously on the pump, keeps single-slot caches, and publishes jump maps as a side effect. The preview must be purpose-built from pure pieces plus one off-pump loader.

---

## 3. Alternatives considered

| Alternative | Verdict | Why |
|---|---|---|
| **A. The user's design:** modal, hints by default, `<tab>` for search | **Adopt (with refinements)** | The fast path (see it, press a key) is 2 keystrokes: `"` plus a hint. Search is one `<tab>` away. Maps onto Telescope normal/insert and tmux choose-tree. |
| B. Search-first modal with a transient hint leader (the ModelPicker pattern: `'` enters jump mode) | Reject | Makes the common "I can see it" case slower. Hints are not visible by default, which contradicts the request. |
| C. flash.nvim-style labels drawn from characters that cannot extend the query (type and jump with no mode) | Reject for v1 | Clever, but labels change with every keystroke. Under fuzzy/subsequence matching almost every character extends *some* match, so the label alphabet collapses. Unpredictable for muscle memory. |
| D. Split the alphabet: lowercase always types, uppercase is always a hint | Reject | Every hint needs Shift. Breaks the house `0-9a-zA-Z` hint convention. Digits appear in names (`research.8`, `sase-169`), so they cannot be reserved either way. |
| E. "Show all" mode for `'` that temporarily expands the real Agents tab with hints | Reject | Mutates or simulates fold state in the live list. Full agent-list rebuilds are the most expensive UI operation (perf rule 6). Restoring folds on cancel is fragile. |
| F. Live-preview-in-place: moving in the modal selects and reveals the node behind it (like VS Code) | Reject | Churns fold state and triggers structural refreshes on every `ctrl+n`, and cancel has to undo it. The in-modal preview gives the same information safely. |
| G. `:jump <name>` in the command line with completion | Complement, not a substitute | Good for scripting and muscle memory, but it has no browsing or preview. Could reuse the same projection later. |

---

## 4. Requirement adjustments (explicitly called out)

Each adjustment is tagged **[ADJ-n]** so the lead can accept or reject them individually.

- **[ADJ-1] Name and vocabulary.** The feature is the **Node Finder**, the modal title is "✦ Jump to Node ✦" (matching "✦ Jump to Entry ✦"), and the action id is `open_node_finder`. Never "jump panel" or bare "jump target". Add a glossary strand after it lands (memory write via `/sase_memory_write`).
- **[ADJ-2] Scope of "any node", tiered.**
  - **v1:** nodes hidden by structure (§1.3 rows 1-3) and visible nodes.
  - **v1.1:** nodes hidden by the Agents query (row 4). Listed with a `⊘` badge; jumping clears the committed query through the normal commit path (so `/` then `^` restores it) and shows a toast.
  - **Phase 3:** `I`-hidden rows (row 5), with an async flip-and-reveal.
  - **Never:** dismissed rows (row 6), because that is a revive, not a jump; and unreachable rows (row 7).
  - If Bryan's "hidden" meant `%hide`/`I`, pull phase 3 into v1.1 (Q1).
- **[ADJ-3] Exclusion rule for steps, made precise.** Exclude `bash`/`python` workflow-step rows whose tree parent is an agent entry (`tree_parent_lookup(...)` then `parent.is_agent_entry`, with `row.parent_appears_as_agent` as a fallback). Also exclude embedded pre-prompt steps (`is_pre_prompt_step`, the `▲` rows). Keep steps of genuine workflows, since they are sase nodes per the glossary, including their hidden steps, which get a "hidden step" badge. (Q2)
- **[ADJ-4] Tree-shaped list with context.** Rows are grouped by tribe panel (in the panel order the tab uses), with indentation guides in the tab's depth colors. Hidden rows are ghosted and carry a why-hidden glyph. While filtering, ancestors of matches stay as dim, unhinted, unselectable context rows. This mirrors `filter_tree_rows`' "keep ancestors of matches" semantics, so a match never floats without its clan or session.
- **[ADJ-5] Filter on name *and* displayed title.** The primary haystack is the node's canonical name (`1o`, `research.8.cdx`, `sase-169.3--mon-1`, the clan name, the step name, the proc label). The secondary haystack is the visible title (e.g. the project `bob-cli`); name matches rank above title matches. Rationale: users often remember an agent by the big label shown on its row. Pure "name only" is the stricter reading of the request.
- **[ADJ-6] Open on "you are here".** The initial highlight is the Agents tab's current node, marked `◆` and scrolled into view. The preview therefore starts with context, and `ctrl+n/p` walks outward from where you are, including through hidden nodes. That makes browsing with preview useful on its own.
- **[ADJ-7] `""` means jump back.** Pressing `"` inside the modal dismisses it and runs the same back-jump as `''` / `ctrl+o` (`action_jump_to_entry_fast`). This matches `` `` `` in JumpAllModal and `''` in entry jump. (Q5)
- **[ADJ-8] Esc behaves like vim.** In search mode Esc returns to hint mode and keeps the query; in hint mode Esc closes. This matches the user's vim-first UI and the repo precedent `DurationChoiceModal` (Esc first backs out of a focused input). `/` also focuses the query in hint mode (`/` is not a hint character and is the tab's query key). (Q3)
- **[ADJ-9] Forgiving keys.** An invalid key in hint mode is swallowed and flashes "no hint ‹x›" in the footer; it does not dismiss (unlike JumpAllModal). Backspace cancels a pending two-character prefix. Every printable key the modal does not use must be stopped. This matters because the app-level `_custom_mode_prefixes` branch (`actions/_event_keyboard.py:94-99`) has no modal guard.
- **[ADJ-10] Prefix-free hints.** Allocate with `build_jump_hint_maps(targets, prefix_free=True)`: single keys for most rows, reserved trailing characters as two-key prefixes, never timed. Hints are re-allocated over the *filtered* list on each query change, so filtering always shortens them.
- **[ADJ-11] Explicit preview contract.** Tier 0 is synchronous with no I/O; Tier 1 is debounced and off the pump (§5.7). "Good" means: identity, location, what Enter will do, and the prompt head plus reply tail. It does not mean the full deck.
- **[ADJ-12] Honest scope strip.** The header shows `142 nodes · 97 hidden · 3 filtered`, and adds `· history partial` when the loader is marked `query_incomplete`. Under query pushdown some nodes are not even loaded, and the finder must not imply they don't exist.

---

## 5. Design

### 5.1 Layout (hint mode, ≥140 columns)

```
╔══════════════════════════════════════ ✦ Jump to Node ✦ ═══════════════════════════════════════╗
║ ❯ filter nodes by name…                                   HINTS   142 nodes · 97 hidden · 3 ⊘ ║
╟─────────────────────────────────────────────┬─────────────────────────────────────────────────╢
║ @default ─────────────────── 9 · 4 hidden   │ AGENT SHELL  research.8.cdx                     ║
║ [0] ◆ sase  1o                  RUNNING 12s │ CODEX(gpt-6) @ high · RUNNING · 16m42s          ║
║ [1]   sase  1n                  RUNNING  8m │ @research ▸ research.8 ▸ research.8.cdx         ║
║ [2]   bob-cli  1m             TALE DONE 18m │ ▸ hidden in collapsed clan research.8           ║
║ [3] ▸   └ 1m--plan                DONE  19m │   ⏎ expands 1 fold, then selects it             ║
║ @research ───────────────── 7 · 6 hidden    │                                                 ║
║ [4] ▸ research.8     clan · 6   RUNNING 16m │ AGENT PROMPT ───────────────────────────────    ║
║ [5] ▸   ├ research.8.cdx        RUNNING 16m │ You are researcher cdx in a 4-researcher        ║
║ [6] ▸   ├ research.8.cld        RUNNING 16m │ swarm. The other researchers …                  ║
║ [7] ▸   ├ research.8.gem        RUNNING 16m │                                                 ║
║ [8] ▸   └ research.8.image      WAITING     │ REPLY · tail ───────────────────────────────    ║
║ @epic ────────────────────── 14 · 13 hidden │ ⋯ loading                                       ║
║ [9] ≡ sase-169       clan · 5      DONE     │                                                 ║
║ [a] ▸   ├ sase-169.3            DONE        │                                                 ║
║ [b] ▸   │ ├ sase-169.3--plan    DONE        │                                                 ║
║ [c] ▸   │ └ sase-169.3--mon-1   COMPLETED   │                                                 ║
╟─────────────────────────────────────────────┴─────────────────────────────────────────────────╢
║ 0-Z jump · tab or / search · ^n ^p move · ⏎ jump · "" back · esc close                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

Search mode (after `<tab>`, typing `cdx`):

```
║ ❯ cdx▏                                                    SEARCH   1 of 142 · contiguous      ║
╟─────────────────────────────────────────────┬─────────────────────────────────────────────────╢
║ @research                                   │ AGENT SHELL  research.8.cdx                     ║
║       research.8     clan · 6               │ …                                               ║
║ [0] ▸   ├ research.8.cdx        RUNNING 16m │   (match run "cdx" rendered bold+underline)     ║
║ ⏎ jump · tab hints · ^n ^p move · esc hints · ^u clear                                        ║
```

**Visual language (reuse, don't invent):**

- **Hint gutter:** the house `[h]` marker in `bold #FFFF00` inside dim brackets (`apply_jump_hint_prefix` / `apply_jump_gutter`, `modals/models_panel_rendering_layout.py:73`), in a fixed-width gutter so rows align. In search mode hints render `dim`, which signals "press `<tab>` to use these".
- **Why-hidden column (1 cell):** blank = visible, `◆` = you are here, `▸` = inside a collapsed fold, `≡` = inside a collapsed grouping banner, `▭` = collapsed or isolated-away tribe panel, `⊘` = hidden by the query. Hidden rows' names render at reduced intensity. Keep them readable: use a lower-intensity palette, not `dim` on dim.
- **Tree guides** use `_TREE_DEPTH_COLORS`. Type and step glyphs and status colors come from `widgets/_agent_list_styling.py`. Tribe headers use `models/tribe_display.py` colors. Kind chips and accents (AGENT SHELL / SESSION / CLAN / MONITOR / GATE / WORKFLOW) come from `identity_kind_for_agent` (`widgets/prompt_panel/_identity_header.py:90`). The finder should read as a *map of the Agents tab*, not a foreign widget.
- **Match highlighting:** `append_highlighted` (`widgets/_completion_match_highlight.py:17`) with `bold underline` in the row's own color, **not** its default `bold #FFD700`. A second yellow would compete with the yellow hints.
- **Selected row:** the same reverse band as the Agents list selection. **Input:** muted border when unfocused, `$accent` border when focused. **Mode pill:** `HINTS` in yellow or `SEARCH` in cyan.
- **Container:** `ModalScreen`, about 96% × 92% (in line with `PromptHistoryModal` at 98% × 96%), list 44% and preview 56% with a vertical rule between them. Between 100 and 140 columns: 50/50, with the list's status column dropped. Below 100 columns: the preview stacks below the list at 40% height.

### 5.2 Interaction model

| Key | Hint mode (default, nothing focused: `AUTO_FOCUS = ""`) | Search mode (query `Input` focused) |
|---|---|---|
| `0-9a-zA-Z` | Complete a hint (or set a pending prefix) and jump | Edit the query; the list refilters live and hints are re-allocated |
| `<tab>` | Focus the query | Back to hint mode, query kept |
| `/` | Focus the query | Types `/` |
| `<enter>` | Jump to the highlighted node | Jump to the highlighted node |
| `ctrl+n` / `ctrl+p` (also `↓`/`↑`) | Next / previous jumpable row, **wrapping** | Same |
| `ctrl+d` / `ctrl+u` | Half-page scroll | (Input's own: `ctrl+u` clears to start) |
| `"` | Jump back (`''` semantics) [ADJ-7] | Types `"` |
| `backspace` | Cancel a pending prefix | Delete a character |
| `esc` | Cancel a pending prefix, otherwise close | Back to hint mode [ADJ-8] |
| other printable | Swallow and flash "no hint ‹x›" [ADJ-9] | Types |

Implementation notes:

- Textual's `Screen` binds `tab`/`shift+tab` to focus traversal. Override with a priority screen `Binding("tab", …, priority=True)` (precedents: `revive_agent_modal.py:108`, `config_center_modal.py:107`) or intercept in `on_key`, as `xprompt_select_modal.py:343-357` does. Remember that Ctrl+I arrives as Tab.
- Textual 8.0.1 `Input` binds `enter`, `ctrl+a/e/d/u/w/f/k/x/c/v` and does **not** bind `ctrl+n`/`ctrl+p`, so both bubble to the screen in either mode. `Input._on_key` stops printable keys, so hint characters cannot leak while typing.
- The app's non-priority `"` binding does not fire inside a `ModalScreen`. The only app priority bindings (`next_tab`/`prev_tab`) are disabled while a modal is active (`_app_action_availability.py:218-226`).

### 5.3 Node set and classification (pure, computed once on open)

`build_node_finder_rows(owner) -> NodeFinderSnapshot` lives in a pure module with no Textual imports:

1. `complete = owner._agents_with_children`: every loaded, non-dismissed node, clan-projected, taken before folds and before the query.
2. **Rendered set:** the identities of `("agent", idx)` entries from `_jump_candidate_targets()`. That call already walks each panel's grouping tree exactly as rendered, so the set is exact.
3. **Reachable-with-query set:** `filter_agents_by_fold_state(complete, _FoldStateProjection({every fold key: FULLY_EXPANDED}))`, then `_apply_active_agent_query`. This is the same technique as `prospective_clan_projection`.
4. **Reachable-without-query set:** step 3 without the query.
5. Classify each row of `complete` that passes the exclusions [ADJ-3] and is not `STARTING`:
   - in (2) → `visible`;
   - in (3) and in `_agents` → `banner` or `panel`, depending on whether its panel is collapsed;
   - in (3) and not in `_agents` → `folded` (recording the nearest collapsed ancestor for the preview's "hidden in collapsed clan research.8" line);
   - in (4) but not in (3) → `query`;
   - otherwise → `unreachable`, which is not listed.
6. Emit frozen `NodeFinderRow`s carrying identity, name, title, kind, status, depth, tribe/panel key, reason, nearest collapsed ancestor, and search haystacks, in tribe-panel order then tree order. The snapshot also keeps a read-only reference to each `Agent` for the Tier 0 preview.

The work is O(n) in memory and never stats or globs. It stays in Python: it depends on TUI fold, panel, and query presentation state, which is on the TUI side of the Rust-core boundary. The only shared primitive, fuzzy matching, is already in `sase_core`.

### 5.4 Filtering

- Split the query on whitespace; every token must match (AND). Use the Rust `fuzzy_match(token, haystack)` tiers (0 prefix, 1 basename-prefix, 2 substring, 3 subsequence) with the help modal's policy (`modals/help_modal/filter_model.py:54`). Pass 1 accepts contiguous matches (tier ≤ 2); if nothing survives, pass 2 relaxes to subsequence and the strip shows `relaxed`. This avoids the noisy "everything subsequence-matches" failure mode on names like `sase-169.3--mon-1`.
- Survivors keep **tree order**. The highlight moves to the best match (lowest tier, then highest score, then name-haystack before title-haystack), so `<enter>` right after typing does the right thing.
- Smart case: an all-lowercase query is case-insensitive.

### 5.5 Hints

- Allocate over jumpable rows only (not context rows or headers) in display order, with `build_jump_hint_maps(rows, prefix_free=True)`. No characters are excluded, because the modal's hint-mode command keys (`/`, `"`, `tab`, `esc`, `enter`, `ctrl+*`) are not in `JUMP_HINT_CHARS`.
- Normalize with `normalize_jump_key(event.key, event.character)` so uppercase hints work. Match with `match_jump_hint`.
- Show a pending prefix in the footer (`a…`), as `_update_member_jump_footer` does for roster digits.
- **Stability:** hints change only when the query changes, never because of a background refresh (the snapshot rule, §5.8).

### 5.6 Jump execution (a small ladder, like link-follow)

The modal dismisses with `NodeFinderResult(identity, reason)` or `NodeFinderResult(back=True)`. The app callback then does one of the following:

1. **Back:** run `action_jump_to_entry_fast()`.
2. **Default:** `_reveal_agent_row(identity, subject="Node")`. This covers `visible`, `folded`, `banner`, and `panel`, including monitor and gate shells (the ancestor walk expands the gating session fold) and hidden steps (`FULLY_EXPANDED`).
3. **If step 2 fails with `TARGET_FILTERED` and a query is active** (whether or not the row was pre-classified `query`): commit an empty query through the same commit path the filter bar uses. That path records the history transition that `/` then `^` can restore (`actions/agents/_filter_bar_session.py:173`); factor out a non-session variant. Then refilter and retry the reveal. Toast: *"Cleared Agents query ‹status:done› to reach research.8.cdx · `/` `^` restores"*.
4. **Phase 3, for `I`-hidden rows:** set `hide_non_run_agents = False`, call `_schedule_agents_async_refresh(on_complete=…)`, and in `on_complete` re-capture the tab and selection (perf rule 4), then retry step 2. Toast: *"Showing hidden agents (I) to reach ‹name›"*.
5. Any other failure → the existing `_notify_member_reveal_failure(failure, subject="Node")`.

Classification is only a display hint; the ladder is authoritative. This handles the edge case where a node survives the query only as the ancestor of a match inside its own collapsed fold.

### 5.7 Preview

**Tier 0: synchronous on every highlight change, zero I/O.**

| Node kind | Content (all pure) |
|---|---|
| Every kind | Kind chip and accent (`identity_kind_for_agent`), 2-row identity (`build_agent_compact_lines`, `widgets/prompt_panel/_identity_header_compact.py:262`, plus its clan/workflow/proc variants), location breadcrumb `@tribe ▸ clan ▸ session ▸ node`, why-hidden line, and a **"⏎ will …"** line (e.g. "expands 2 folds, then selects it" or "clears query ‹…›") |
| Agent / agent shell | Model, status, runtime, tribe/clan/session role, wait and queue chips |
| Session container | Shell lane list: one line per shell (name · kind · status glyph · duration), via the member roster field helpers (`_member_roster.py:481-536`), with no jump-map publisher |
| Clan | Member counts and a status roster from `aggregate_clan_in_memory` |
| Monitor / proc shell | Command, state, exit code, and **`proc_log_tail`**, which is already in memory from the proc observer |
| Workflow root / step | Workflow name, step type and index, status |

Optional instant enrichment: if the Agents prompt panel's in-memory caches already hold this node (header summary, xprompt memo, clan/tribe snapshots), read them through their memory-only getters.

**Tier 1: debounced and off the pump** (agents, shells, session members, workflow steps).

- `DetailPanelDebouncer` (150 ms, `util/debounce.py:24`) → `spawn_pump_free_task` (`util/pump_tasks.py:64`) → `asyncio.to_thread`.
- In the thread: `get_artifacts_dir`, then reads through the process-wide mtime-keyed artifact file cache, keeping a bounded **prompt head** (about 2 KB, 8 lines) and **reply tail** (about 8 KB, 20 lines).
- Store results in a modal-local LRU (≈128 entries) keyed by identity plus an mtime token. When results land, paint only if the same identity is still highlighted (generation counter).
- The closest precedent for this shape is the notification modal's gate summary (`modals/notification_modal_gate.py:92-121`). Do **not** copy `revive_agent_modal`'s synchronous on-highlight preview read.
- While Tier 1 loads, section headers and fixed-height skeleton lines (`⋯ loading`) are already painted, so the preview never jumps around.
- v1 renders plain wrapped text. v2 can move to Markdown via `LazySyntaxRenderCache` off the pump, as `PreviewPanelModal` does.
- For projected list-shape records, check `projected_agent_waiting_for_hydration` first.

### 5.8 Reliability rules

1. **Snapshot on open.** Rows and hints are fixed for the modal's lifetime. Background refreshes don't reshuffle them. If the underlying list changes, a subtle `list changed` chip may appear, but nothing moves.
2. **Every hint works.** Unreachable, dismissed, and `STARTING` rows are not listed. Revalidation at jump time uses `prepare_agent_navigation_target(require_current=False)`.
3. **One structural refresh per jump.** This is `_reveal_agent_row`'s existing contract. Folds that were expanded stay expanded, consistent with roster jumps. `ctrl+o` returns to the saved anchor.
4. **Respect existing guards.** Action availability: Agents tab only, prompt bar not owning keys, no modal active, and not blocked by `_guard_agent_navigation_for_artifact_file_viewer`.
5. **Guard programmatic highlight echoes** if an `OptionList` is used (perf rule 12).

### 5.9 Performance budget (to enforce with a bench)

| Path | Budget (1,000 synthetic nodes) | How |
|---|---|---|
| `"` to first paint | < 50 ms p95 | O(n) pure projection; list and Tier 0 only; no I/O |
| Keystroke to refiltered paint | < 16 ms p95 | Up to tokens × n Rust `fuzzy_match` calls plus one list rebuild. If over budget, coalesce latest-wins in a thin synchronous callback |
| `ctrl+n/p` to highlight and Tier 0 | < 16 ms p95 | Pure renderers; Tier 1 debounced |
| Tier 1 | Off the pump | Thread plus LRU; stale results dropped |

Widget choice: start with `OptionList`. It handles highlighting, scroll-into-view, and disabled options (headers and context rows are skipped by `ctrl+n/p` for free), and rows are Rich `Text`. If the bench misses budget at 1,000 rows, switch to a line-API `ScrollView` (virtualized `render_line`). Measure with `SASE_TUI_TRACE=1` spans (`node_finder.open`, `node_finder.filter`).

---

## 6. Implementation map

New files (suggested):

- `src/sase/ace/tui/modals/node_finder_rows.py`: pure snapshot and classification (§5.3), filtering (§5.4), and hint allocation (§5.5).
- `src/sase/ace/tui/modals/node_finder_preview.py`: Tier 0 builders and the Tier 1 loader and LRU.
- `src/sase/ace/tui/modals/node_finder_modal.py`: `NodeFinderModal(ModalScreen[NodeFinderResult | None])`.
- `src/sase/ace/tui/actions/navigation/_node_finder.py`: `NodeFinderNavigationMixin.action_open_node_finder()` plus the dismiss ladder (§5.6). Mix it in next to `NavigationModalMixin`.

Wiring checklist (from the codebase survey):

1. `keymaps/app_keymaps.py`: add the `open_node_finder: str` field (next to `jump_to_all_entries`, `:121`).
2. `src/sase/default_config.yml` under `ace.keymaps.app`: `open_node_finder: "quotation_mark"`, with a comment that it is Agents-only (per the "Default Keymap Config" gotcha). `registry.py` raises at startup if this entry is missing.
3. `keymaps/metadata.py` `_BINDING_META`, plus the optional fallback in `tui/bindings.py`.
4. `keymaps/key_validation.py`: **add `"quotation_mark": '"'` to `_KEY_DISPLAY`** and a `'"': "quotation_mark"` alias. `quotation_mark` appears nowhere in `src/` or `tests/` today. Without the display entry, user overrides fail validation and help/footer render the raw name.
5. `commands/_app_metadata_nav.py` with `AGENTS_ONLY` (`ensure_metadata_covers_app_keymaps` fails at import if it's missing).
6. `_app_action_availability.py`: gate like `choose_agent_grouping` (Agents tab, prompt bar not active, no modal).
7. `modals/help_modal/agents_bindings.py` Navigation section, next to `:80`: `(d(a.open_node_finder), 'Jump to any node ("" back)')`. That fits the 32-character cap.
8. Exports in `modals/_export_table.py`, `modals/__init__.py`, and `modals/__init__.pyi`.
9. CSS block in `tui/styles.tcss`, near `JumpAllModal` (`:5949`).
10. Docs: the Agents navigation docs, plus a glossary strand "Node Finder" (a follow-up via `/sase_memory_write`).

No feature flag should be needed: the change is additive and there is no old branch to keep reachable. Confirm against `sase_flags.md` when writing the plan.

---

## 7. Test plan

- **Projection unit tests** (`tests/ace/tui/modals/test_node_finder_rows.py`), one per class:
  - visible;
  - member of a collapsed clan;
  - shell of a collapsed session;
  - monitor/gate gated by the session fold;
  - under a collapsed banner;
  - in a collapsed or isolated panel;
  - query-filtered;
  - excluded agent-shell `bash`/`python` steps and pre-prompt steps;
  - `hidden_only_parents` roots and `STARTING` rows (not listed);
  - remote fleet rows (listed).
- **Modal key tests** (the `_ModalHost(App)` pattern from `tests/ace/tui/modals/test_revive_agent_modal.py`):
  - nothing is focused on open;
  - a hint completes and dismisses with the identity; a two-character prefix is pending, then completes; Backspace cancels a prefix;
  - an invalid key neither dismisses nor leaks to the app (assert the app's `on_key` / `_custom_mode_prefixes` never sees it);
  - `<tab>` round-trips; `/` focuses; Esc in search mode returns to hints; Esc in hint mode closes;
  - `<enter>` works in both modes; `ctrl+n/p` wrap in both modes and skip context rows;
  - `""` returns the back result.
- **Jump tests:** a reveal per class through a real `AcePage`; the query-clear fallback records a history transition; the failure toast uses "Node" wording; the anchor is restored when a reveal fails.
- **Preview tests:**
  - Tier 0 is pure: monkeypatch `open`/`os.stat`/`os.scandir` to raise during highlight moves.
  - Tier 1 drops stale results and hits the LRU on revisit.
- **Keymap tests:** `tests/test_keymaps_app_bindings.py` (binding count), `test_keymaps_validation.py` (`quotation_mark` valid, `"` alias), `test_keymaps_display_help_key_display.py` (renders `"`), and the command catalog coverage tests.
- **Visual PNG goldens** (template: `tests/ace/tui/visual/test_ace_png_snapshots_command_palette.py`): `node_finder_hints_160x48`, `node_finder_search_160x48`, `node_finder_narrow_100x40`. Run `just fix-tui-screenshots` and inspect every golden change.
- **Perf bench:** `pytest -m slow`, measuring open and per-keystroke p95 over a synthetic 1,000-node roster, against the §5.9 budgets.

---

## 8. Phasing

| Phase | Contents | Exit criteria |
|---|---|---|
| **P1: MVP** | Keymap wiring; modal; projection for visible, folded, banner, and panel rows plus exclusions; prefix-free hints; tab, `/`, Esc, Enter, `ctrl+n/p`, and `""`; reveal via `_reveal_agent_row`; Tier 0 **and** Tier 1 preview (the preview is a headline requirement); tests; goldens | Every structurally hidden node in the live TUI (e.g. `research.8.cdx`, `sase-169.3--mon-1`) is reachable in 2-4 keystrokes; budgets met |
| **P1.1** | Query-filtered rows with the clear-query fallback and toast; scope strip with `history partial`; docs and glossary | A filtered node is reachable; `/` then `^` restores the query |
| **P3 (optional, feedback-gated)** | `I`-hidden rows with async flip-and-reveal; viewport-relative hints (label only on-screen rows, so every visible row is always one key); recall of the last query on reopen; Markdown reply rendering | Driven by usage |

---

## 9. Open questions for Bryan

1. **Q1: What does "hidden" mean?** Folded or otherwise not rendered (my assumption), or the literal `agent.hidden` / `%hide` / axe-spawned rows that `I` hides? If the latter matters, `I` support moves from P3 to P1.1.
2. **Q2: Which step exclusion?** Only *agent-shell* bash/python steps and pre-prompt steps (my default), or every bash/python workflow step?
3. **Q3: Esc in search mode.** Return to hints (vim; my default) or close immediately?
4. **Q4: Query-filtered targets.** Is "clear the query and show a toast with the restore path" acceptable, or should the finder never touch the query (query-filtered rows shown but not jumpable)?
5. **Q5: `""` as back.** Mirrors `''` and `` `` ``; OK?

---

## 10. Recommended solution

Build the **Node Finder**: an Agents-only `ModalScreen` bound to `"` (`quotation_mark`, with display and alias support added in `key_validation.py`).

- **Layout.** About 96% × 92%. A query bar on top, an unmistakable `HINTS`/`SEARCH` mode pill, and a scope strip (`N nodes · H hidden · F filtered`). Below that, a 44/56 split: a **tree-shaped node list** on the left and a **two-tier preview** on the right. A context-sensitive key legend sits at the bottom.
- **List.** A snapshot, taken on open, of every reachable node in `_agents_with_children`, grouped by tribe panel in tab order and indented with the tab's own glyphs and colors.
  - Includes clans, agents, sessions, session shells (monitors and gates too), and genuine workflow steps.
  - Excludes agent-shell bash/python steps, pre-prompt steps, `STARTING` rows, structurally unreachable rows, and dismissed rows.
  - Each hidden row is ghosted and carries a one-glyph reason (`▸` fold, `≡` banner, `▭` panel, `⊘` query). The current node is marked `◆` and highlighted on open.
- **Hints.** Always rendered in the house `[h]` style, prefix-free (mostly single keys), and re-allocated only when the query changes. They dim while the query bar has focus.
- **Keys.** Hint mode is the default, with nothing focused: a hint jumps, `<tab>` or `/` searches, `ctrl+n/p` (and arrows) cycle with wrap-around, `<enter>` jumps, `""` jumps back, and Esc closes. Invalid keys flash instead of closing. In search mode: live, tokenized, contiguous-first fuzzy filtering on name (then title) via the Rust matcher; survivors stay in tree order and the highlight lands on the best match; `<enter>` jumps; `<tab>` or Esc returns to hints with the query kept.
- **Jumping.** Dismiss with the node's identity, then call `_reveal_agent_row(identity, subject="Node")`. It expands exactly the ancestor folds, banner, and panel needed, selects the node, and saves a `ctrl+o` anchor. If the Agents query is what hides the node, clear it through the normal commit path (history recorded), retry, and toast the restore path. `I`-hidden rows come later behind the same ladder.
- **Preview.** Tier 0 on every move, pure and I/O-free: kind chip, compact identity, breadcrumb, why-hidden, and what Enter will do, plus kind-specific in-memory content (shell lanes, clan roster, monitor log tail). Tier 1 is debounced, off the pump, and LRU-cached: prompt head and reply tail, with skeleton placeholders so nothing shifts.
- **Guardrails.** Keep perf under the §5.9 budgets. Cover the change with the tests and visual goldens in §7. Ship in the §8 phases.

This delivers what was asked (hints next to every node, a filter bar that is unfocused by default, tab to toggle, enter to jump, ctrl+n/p to cycle, and a large fast preview). It leans on primitives the codebase has already hardened, keeps every hint honest, and looks like a native part of the Agents tab rather than a bolted-on picker.
