# Agents-Tab Node Finder (`"`): Consolidated Research, Critique, and Recommendation

- **Lead researcher:** consolidated from four independent reports (`__cdx`, `__cld`,
  `__mus`, `__gem`, all in this directory) plus the lead's own code verification.
- **Date:** 2026-09-25
- **Repo state:** `sase` master @ `43f724619` (the researchers reviewed `27d03a7b7`; no
  relevant drift).
- **Request:** Add a `"` key to the Agents tab. It opens a large panel for jumping to any
  node, shown or hidden: hidden session shells and hidden clan members, but not agent-shell
  Bash/Python steps. Jump hints always appear next to nodes. A name-filter query bar at the
  top starts unfocused. `<tab>` toggles focus between the query bar and the hints, `<enter>`
  jumps to the highlighted node, and `<ctrl+n/p>` cycle through nodes. The panel includes a
  large, fast preview of the highlighted node.

---

## TL;DR

**Verdict: build it. It is a good idea, and the hardest part already exists.** Every jump
surface on the Agents tab today reaches only rendered rows, or only the relations of the
selected container. The codebase already has an identity-based reveal primitive,
`_reveal_agent_row()`. It expands the ancestor folds, grouping banners, and collapsed
tribe panels, selects the row, and saves a `ctrl+o` anchor. What's missing is a
well-designed modal on top of it.

All four researchers endorse the request's interaction model (hints first, `<tab>` to
search). They converge on these points:

- a dedicated Agents-only `ModalScreen` on `quotation_mark`, separate from the backtick
  `JumpAllModal`;
- the modal returns a stable `Agent.identity`, never a list index;
- landing goes through the existing `_agent_reveal` contract;
- a two-tier preview: a synchronous, I/O-free tier plus a debounced tier that loads off
  the message pump;
- reuse of house hint styling, the Rust fuzzy matcher, and the palette's `ctrl+n/p`
  forwarding.

They disagree on five material questions:

1. what "hidden" covers;
2. how to reach a node that the Agents query hides;
3. whether monitors, gates, and proc shells are included;
4. how broad the Bash/Python exclusion is;
5. what an unrecognized key does.

§3 resolves each one using the code.

**Recommendation in one line:** build a **Node Finder** modal ("✦ Jump to Node ✦",
action `jump_to_node`, key `"`). It shows a tree-shaped snapshot of every reachable sase
node, and every jumpable row always carries a prefix-free hint. The modal opens in hint
mode on "you are here". `<tab>` or `/` switches to fuzzy name search, and
`<enter>`/`ctrl+n/p` work in both modes. The preview is two-tier. Jumps go through
`_reveal_agent_row`; a jump only clears the Agents query, with history and a toast, when
the query is what hides the target. §10 has the full recommendation.

---

## 1. What exists today (verified in-tree)

### 1.1 Navigation surfaces and their shared blind spot

| Surface | Key | Reaches | Blind spot |
|---|---|---|---|
| Entry jump | `'` (`''` / `ctrl+o` back) | Rows currently rendered in the Agents list, collapsed banners, panel titles (`_jump_candidate_targets`, `actions/navigation/_entry_jump_mode.py`) | Folded children, rows in collapsed panels, anything filtered |
| Cross-tab jump | `` ` `` (`` `` `` back) | `app._agents`, the already folded and filtered list (`actions/navigation/_modals.py`, `modals/jump_all_modal.py`) | Same. It has no filter, no cursor, and no preview, and **any non-hint key dismisses it** (`jump_all_modal.py:349-353`) |
| Roster digits | `0-9`, `00-99` | Agent relation jump targets of the **selected** container only, revealed through folds (`_member_jump.py`) | Anything unrelated to the selection |
| Jump panel | `.` | Sticky footer listing those relation targets | Same as roster digits |
| Link follow | `$` | `agent:` links, resolved in `_agents_with_children` | Only linked nodes |

In cld's live capture on this host, the backtick modal listed 8 agents in total. None of
the six `research.8.*` clan members appeared, nor any `sase-169.*` session or its
`--plan`/`--mon-N` shells. Reaching `sase-169.3--mon-1` today means drilling through
clan, then session, then shell. That is exactly the gap this request describes.

### 1.2 The reveal primitive already does the hard part

`MemberJumpNavigationMixin._reveal_agent_row(identity, *, subject="Member")`
(`actions/navigation/_member_jump.py:370`) sits on `prepare_agent_navigation_target()` and
`reveal_agent_navigation_target()` (`actions/navigation/_agent_reveal.py`). It:

- validates the target's ancestor chain against `_agents_with_children`;
- expands exactly the needed folds (`FULLY_EXPANDED` for hidden steps), the enclosing
  grouping banners, and the tribe panel;
- saves the Agents jump anchor and rolls it back if the reveal fails;
- focuses the panel, selects the row, acknowledges unread state, and requests one
  structural refresh;
- reports typed failures (`TARGET_MISSING`, `TARGET_AMBIGUOUS`, `TARGET_NOT_CURRENT`,
  `ANCESTRY_INVALID`, `REFILTER_UNAVAILABLE`, `TARGET_FILTERED`, `PANEL_MISSING`,
  `TARGET_NOT_VISIBLE`) through `_notify_member_reveal_failure(..., subject=)`, which
  already accepts caller-specific wording.

`Agent.identity` is value-based (`(type, cl_name, raw_suffix)`, or the clan key plus its
generation) and survives reloads, so it is the correct key for a snapshot-then-jump modal.

### 1.3 "Hidden" has several meanings, and they need different machinery

This table merges cdx's and cld's tables. The lead verified rows 4 and 5.

| # | Hidden by | Row lives in | `_reveal_agent_row` handles it? |
|---|---|---|---|
| 1 | Clan, session, or workflow fold (monitor and gate shells gated by the session fold; `models/_fold_filter.py`) | `_agents_with_children`, not `_agents` | **Yes** |
| 2 | Collapsed grouping banner | `_agents` (hidden at render time) | **Yes** |
| 3 | Collapsed or `=`-isolated tribe panel | `_agents` | **Yes** |
| 4 | Agents query (`/`, `f`) | `_agents_with_children` **if loaded**. With a windowed, pushdown-safe query the loader applies a `candidate_filter` and may **never load** non-matching rows (`models/agent_loader.py:536-565`); `query_incomplete` marks this | **No**: fails with `TARGET_FILTERED` |
| 5 | `I` hide-non-run (**default on**, `app.py:205`). It hides rows with `agent.hidden` set (`%hide` or axe-spawned) that are still running or failed; successful ones are auto-dismissed (`_loading_compute.py:466-497`, `_loading_helpers.py:93`) | Only `_agents_capacity_with_children` (flat, not clan-projected) | **No**: `TARGET_MISSING`. Undoing it needs an async reload (`_filter_actions.py:27-35`) |
| 6 | Dismissed or explicitly removed | `_dismissed_agent_objects` | **No**, and correctly so: getting it back is a revive, which is a mutation |
| 7 | Structurally unreachable: `STARTING` provisional rows, historical workflows with only hidden steps (`hidden_only_parents`) | `_agents` / `_agents_with_children` | **No**, and correctly so |

### 1.4 Other load-bearing facts the lead verified

- **`quotation_mark` is unused everywhere.** Textual reports `"` as `quotation_mark`.
  The name appears nowhere in `src/`, and `keymaps/key_validation.py` `_KEY_DISPLAY` has
  `apostrophe` and `grave_accent` but no `quotation_mark`. Without a display entry, user
  overrides fail validation and the help screen renders the raw name.
- **Hint allocator** (`actions/navigation/jump_hints.py`): base-62 alphabet.
  `prefix_free=True` gives single keys first and reserves the minimum number of trailing
  characters as untimed two-key prefixes. Both modes top out at 62² = **3,844** labels,
  and extra targets silently get no hint.
- **The app-level `on_key` has no modal guard** (`actions/_event_keyboard.py:94-98`,
  `_custom_mode_prefixes`). Any printable key the modal fails to stop can arm an app
  custom mode underneath it, so the modal must swallow every key it doesn't use.
- **`ctrl+n/p` forwarding precedent:** `CommandPaletteModal.on_key`
  (`modals/command_palette_modal.py:414-422`) moves the highlight on
  `ctrl+n/p`/`↑↓` while its `Input` has focus. Textual's `Input` binds neither key.
- **Hint-plus-search precedent:** `ModelPickerModal` and about 14 Admin Center panes use
  `KeyedPaneEntryJumpMixin` (`modals/pane_entry_jump.py`). It is a *transient* mode: `'`
  enters it, an invalid key exits, fixed-width allocation, and a hit selects rather than
  dismisses. The Node Finder needs always-on hints, prefix-free allocation, and
  dismiss-on-hit, so it should use `build_jump_hint_maps`/`match_jump_hint` directly, as
  `JumpAllModal` does. It can still reuse the mixin's renderer,
  `apply_jump_hint_prefix` (`[h]` in `bold #FFFF00`).
- **Preview building blocks exist and are pure:** `identity_kind_for_agent`,
  `build_agent_compact_lines`, `append_highlighted`, `Agent.proc_log_tail`, which holds
  a bounded monitor/proc output tail in memory, `DetailPanelDebouncer` (150 ms), and
  `spawn_pump_free_task`.
- **Query clearing has two code paths behind the `agents_unified_query` flag.**
  - The filter-bar path, `_commit_agents_filter_query`, records a history transition,
    but it assumes an open filter session.
  - The legacy path calls `_record_explicit_agents_query_commit`, then
    `_refilter_agents`, then `_schedule_agents_async_refresh`.

  Clearing the query from the finder needs a small helper that is correct on both paths.

---

## 2. Critique: is this a good idea?

**Yes.** The Agents tree has become deep (tribe → clan → session → shells, monitors,
gates, and workflow steps). Folding is what keeps it readable, but today folding also
makes nodes unreachable without manual drilling. A "go to anything" palette with direct
hints is the standard answer in tree UIs. Close analogs are tmux `choose-tree` (tree plus
shortcut keys plus filter plus preview), Telescope's normal/insert split, VS Code Quick
Open, and flash.nvim/Vimium labels. The `'`/`"` pairing is a real mnemonic: `'` jumps
within what you see, and `"` (Shift+`'`) jumps to everything on the tab.

**Risks, all addressed below:**

1. **Too many jump surfaces** (`'`, `` ` ``, digits, `.`, `$`, `,j`, and now `"`). Each
   surface needs a crisp one-line job in `?` help:
   - `'`: jump within this layout.
   - `` ` ``: switch across tabs.
   - digits and `.`: jump within the selected container's relations.
   - `"`: find any node on the Agents tab and reveal it.
2. **Name collision.** "Jump panel" is already a glossary term (the `.` footer). "Agent
   node" is also a glossary term, and it covers *only* session and standalone agent rows,
   not shells or clans. So `jump_to_agent_node` (proposed by cdx and gem) would be wrong
   vocabulary.
3. **"Hidden" is ambiguous** (§1.3). One design cannot treat fold-hiding, query-hiding,
   and `I`-hiding alike.
4. **Mode confusion.** In hint mode and search mode, the same letter key means different
   things. The active mode has to be unmistakable.
5. **Hints must never lie.** A hint on a node that can't be reached, or one that changes
   under a background refresh, kills trust immediately.
6. **Preview cost.** Embedding `AgentDetail` or the deck renderer would violate TUI perf
   rules 1, 7, and 8: it reads prompt and reply files synchronously on the pump and
   publishes jump maps as a side effect.

**Alternatives considered and rejected:**

| Alternative | Verdict | Why |
|---|---|---|
| Extend `JumpAllModal` (`` ` ``) with filter, preview, and hidden rows | Reject (all four) | It is a lightweight cross-tab switcher over `_agents`. Adding Agents-specific depth bloats it and mixes Patch and Service hits into searches |
| In-place "show all" for `'`: expand every fold with hints | Reject | It mutates fold state, full list rebuilds are the costliest UI operation (perf rule 6), and restoring folds on cancel is fragile |
| Search-first modal where `'` enters jump mode (the ModelPicker pattern) | Reject | It makes the common "I can see it" case slower, and it contradicts the request's hints-by-default |
| flash.nvim-style labels from characters that can't extend the query | Reject for v1 | Labels change every keystroke. With subsequence matching almost every character extends some match, so the label alphabet collapses |
| Live preview in place (moving selects the real row behind the modal) | Reject | It churns folds and structural refreshes on every `ctrl+n`, and cancel must undo all of it |
| `:jump <name>` command-line completion | Complement later | Useful for scripting, but it offers no browsing or preview. It can reuse the same projection |

---

## 3. Where the researchers disagreed, and how it's resolved

| Question | Positions | Resolution | Why |
|---|---|---|---|
| **Reaching a query-hidden node** | cdx: a transient "reveal lease" that unions the target into the filtered view. cld: clear the query through the commit path with history plus a toast (v1.1). gem: set the query string to `""` directly. mus: not addressed | **Clear the query through a history-recording helper, with a toast. Ship it in v1, as the last step of the ladder.** Reject the lease | A lease adds a new cross-cutting concept to the filter pipeline. It needs lifetime hooks on every selection change, and while it is active the list disagrees with the committed query the filter bar shows. Clearing is honest, uses existing paths, and can be undone from query history. gem's raw assignment bypasses history. The request says "regardless of whether or not it is shown", so deferring this would leave the headline promise false for filtered rows |
| **`I`-hidden rows** | cdx: in scope via a pre-hide roster the loader publishes. cld: phase 3. gem and mus: silent | **Phase 2**, using cdx's roster design and cld's async flip-and-reveal. v1 discloses the count honestly | These rows are not in `_agents_with_children` (verified), and undoing `I` needs an async reload. It is solvable, but it is a separate loader-boundary change. The request's own examples (hidden shells and clan members) are fold-hidden |
| **Monitors, gates, proc shells** | cdx and cld: include. gem and mus: exclude | **Include** | The glossary defines an agent session's shells as "monitor and gate shells included", and the request asks for *hidden session shells*. Stand-alone proc shell nodes are sase nodes too |
| **Bash/Python exclusion breadth** | cld: only agent-shell steps plus pre-prompt steps; keep genuine workflow steps. cdx and mus: every non-`agent` workflow step. gem: `step_type in {"bash","python"}` | **Every non-`agent` workflow step (bash, python, parallel, pre-prompt) is not a jump target.** A step with jumpable descendants renders as a dim context row. Flagged as adjustment A2 | The predicate is future-proof: a new step kind won't leak in. Steps are reachable through their workflow row plus fold keys, and flipping to cld's narrower rule is a one-predicate change if Bryan wants it (Q2) |
| **Unrecognized key in hint mode** | mus: auto-focus the query and seed the character. cld: swallow and flash. cdx: clear the pending prefix and stay open | **Swallow and flash "no hint ‹x›"; never dismiss; never leak** | mus's auto-seed is a trap. At ≥62 jumpable rows every alphanumeric is a hint (prefix-free allocation uses the whole alphabet), so the same keystroke would jump on a big list and type on a small one. Keys must not change meaning with list size |
| **Esc in search mode** | cld: back to hints, query kept. gem: clear the query, then unfocus, then close. cdx: close | **Back to hints, query kept. Esc in hint mode closes** | This matches vim insert→normal and the `DurationChoiceModal` precedent, and pairs with `<tab>`. gem's three-stage Esc adds a state nobody needs (`ctrl+u` clears the query) |
| **`"` inside the modal** | cld: `""` = jump back. cdx: `"` closes | **`""` = jump back** | House convention, verified: `` ` `` inside `JumpAllModal` jumps back (`jump_all_modal.py:318-322`), and `'` inside entry-jump does the same (`_entry_jump_dispatch.py:107`) |
| **List shape** | cld: tree plus ghosted hidden rows plus dim ancestor context while filtering. cdx: breadcrumbs, fuzzy-rank order. mus: sections per panel, flat. gem: tree | **cld's tree**, grouped by tribe panel in tab order, with tree order preserved while filtering. The *highlight* moves to the best match | Tree order keeps positions and hints predictable and shows each match's context (clan/session), and `<enter>` right after typing still picks the best match |
| **Filter execution** | cdx: thread worker plus generation guard, hints disabled until published. cld: synchronous within budget | **Synchronous, gated by a bench.** Fall back to latest-wins coalescing only if the bench fails | Rows are in memory and matching runs in Rust. A synchronous filter removes a whole class of stale-hint races: an async filter would require disabling hints between keystroke and result |
| **Rendered-row cap** | mus: render about 200, "keep typing". Others: list all | **List all jumpable rows** (bounded by 3,844 labels). If exceeded, show unhinted overflow rows plus a "type to narrow" note. Switch `OptionList` to a line-API virtual list only if the bench fails | A cap breaks "every node has a hint". Real rosters are hundreds of rows |
| **Panel titles and banners as targets** | mus: include | **Exclude** | The glossary says banners and tribe-panel titles are not nodes, and `'` already covers them |
| **Widget focus in hint mode** | cld: nothing focused (`AUTO_FOCUS = ""`). cdx: the `OptionList` | **Focus the `OptionList`** (hint keys are handled in the screen's `on_key`) | It gives a native focused highlight style and scrolling, and `<tab>` explicitly toggles between two known focus targets |
| **Size** | 84–96% wide × 80–92% tall | **~94% × 90%**, `border: double $primary` | The preview is a headline requirement. The border keeps the modal a visual sibling of `JumpAllModal` |

---

## 4. Requirement adjustments (explicitly called out)

Each can be accepted or rejected independently.

- **A1. It's a modal, not a docked "panel".** The request says "panel". A large
  transient `ModalScreen` fits the requested behavior (keyboard-modal, two columns,
  large) and puts no permanent pressure on the Agents layout. It must also not be named
  a "jump panel" (§2, risk 2).
- **A2. Scope of "any node".** In scope: every loaded, non-dismissed sase node (clans,
  agent nodes, session shells including monitors and gates, workflow roots, workflow
  `agent` steps, stand-alone proc shells). Out of scope as jump targets:
  - every non-`agent` workflow step, which is broader than "agent shell Bash/Python
    steps" (Q2);
  - `STARTING` rows;
  - structurally unreachable rows;
  - dismissed rows, which the revive modal handles.
- **A3. Hidden-ness is tiered.**
  - v1: fold, banner, and panel hiding (full reveal), plus query-hidden rows that are
    loaded (the jump clears the query).
  - Phase 2: `I`-hidden rows.
  - Rows a windowed query never loaded cannot be listed. The finder says so instead of
    implying they don't exist.
- **A4. The finder may clear the Agents query.** This is its only persistent view-state
  mutation. It happens only when the query hides the chosen target, the change is
  recorded in query history, and a toast announces it.
- **A5. Keys beyond the request.**
  - `/` also focuses the query.
  - `↑`/`↓` also cycle.
  - `""` jumps back.
  - Esc in search mode returns to hints.
  - Backspace cancels a pending hint prefix.
  - Invalid keys flash; they never dismiss.
- **A6. It opens on "you are here".** The highlight starts on the Agents tab's current
  node (marked `◆`), so the preview starts with context.
- **A7. "Fast preview" means two tiers**, not the full deck:
  - an instant, I/O-free identity/context card;
  - a debounced prompt head and reply tail loaded off the pump.
- **A8. Filtering is by name first.** The haystacks are the canonical node name
  (primary) plus the displayed title (secondary; name hits rank higher). It is *not* the
  structured Agents query language. Pure name-only is the stricter reading (Q4).

---

## 5. Recommended design

### 5.1 Name, key, action

- Feature: **Node Finder**. Modal title: `✦ Jump to Node ✦`, a sibling of "✦ Jump to
  Entry ✦".
- Action: `jump_to_node`, in the `jump_to_entry` / `jump_to_all_entries` family.
- Default key: `quotation_mark`. Agents tab only. Also runnable from the command palette,
  for layouts where `"` is awkward.

### 5.2 Layout (≥140 columns, hint mode)

```
╔═════════════════════════════════════ ✦ Jump to Node ✦ ══════════════════════════════════════╗
║ ❯ Tab or / to filter…                                     HINTS   142 nodes · 97 hidden · 3 ⊘ ║
╟─────────────────────────────────────────────┬────────────────────────────────────────────────╢
║ @default ───────────────────── 9 · 4 hidden │ AGENT SHELL  research.8.cdx                    ║
║ [0] ◆ 1o  sase                  RUNNING 12s │ codex · gpt-6 @ high · RUNNING · 16m42s        ║
║ [1]   1n  sase                  RUNNING  8m │ @research ▸ research.8 ▸ research.8.cdx        ║
║ [2]   1m  bob-cli                  DONE 18m │ ▸ hidden in collapsed clan research.8          ║
║ [3] ▸   └ 1m--plan                 DONE 19m │ ⏎ expands 1 fold, then selects it              ║
║ @research ───────────────────── 7 · 6 hidden│                                                ║
║ [4] ▸ research.8       clan · 6 RUNNING 16m │ PROMPT ──────────────────────────────────────  ║
║ [5] ▸   ├ research.8.cdx        RUNNING 16m │ You are researcher cdx in a 4-researcher       ║
║ [6] ▸   ├ research.8.cld        RUNNING 16m │ swarm. The other researchers …                 ║
║ [7] ▸   ├ research.8.gem        RUNNING 16m │                                                ║
║ [8] ▸   └ research.8.mus        RUNNING 16m │ REPLY · tail ────────────────────────────────  ║
║ @epic ──────────────────────── 14 · 13 hidden│ ⋯ loading                                      ║
║ [9] ≡ sase-169         clan · 5        DONE │                                                ║
║ [a] ▸   ├ sase-169.3                   DONE │                                                ║
║ [b] ▸   │ ├ sase-169.3--plan           DONE │                                                ║
║ [c] ▸   │ └ sase-169.3--mon-1     COMPLETED │                                                ║
╟─────────────────────────────────────────────┴────────────────────────────────────────────────╢
║ 0-Z jump · tab or / search · ^n ^p move · ⏎ jump · "" back · esc close                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

Search mode (after `<tab>`, typing `cdx`). Survivors keep tree order, ancestors stay as dim
unhinted context, and hints are re-allocated over the survivors, so they get shorter:

```
║ ❯ cdx▏                                                   SEARCH   1 of 142              ║
╟─────────────────────────────────────────────┬──────────────────────────────────────────╢
║ @research                                   │ AGENT SHELL  research.8.cdx              ║
║       research.8     clan · 6               │ …                                        ║
║ [0] ▸   ├ research.8.cdx        RUNNING 16m │                                          ║
║ ⏎ jump · tab hints · ^n ^p move · esc hints · ^u clear                                ║
```

**Visual language: reuse the house style, don't invent one.** The finder should read as a
*map of the Agents tab*, not a foreign widget.

- **Hint gutter.** Fixed width. `[h]` in `bold #FFFF00` inside dim brackets, via
  `apply_jump_hint_prefix`. Hints render *dim* while the query has focus: still readable,
  but visibly inactive until `<tab>`.
- **Pending prefix.** The footer shows `a…`. Rows whose hint doesn't start with the
  prefix dim out. There is no timeout.
- **Why-hidden column (1 cell).**

  | Glyph | Meaning |
  |---|---|
  | blank | visible |
  | `◆` | you are here |
  | `▸` | inside a collapsed fold |
  | `≡` | inside a collapsed banner |
  | `▭` | inside a collapsed or isolated-away panel |
  | `⊘` | hidden by the query |
  | `◌` | hidden by `I` (phase 2) |

  Hidden rows use a lower-intensity palette rather than dim-on-dim, so they stay
  readable.
- **Tree guides, glyphs, and colors.**
  - Tree guides use `_TREE_DEPTH_COLORS`.
  - Type glyphs, step glyphs, and status colors come from
    `widgets/_agent_list_styling.py`.
  - Tribe headers use `models/tribe_display.py` colors.
  - Kind chips (AGENT SHELL / SESSION / CLAN / MONITOR / GATE / WORKFLOW) come from
    `identity_kind_for_agent`.
- **Match highlighting.** `append_highlighted` with `bold underline` in the row's own
  color, not the default `bold #FFD700`: a second yellow would compete with the hints.
- **Mode pill.** `HINTS` in yellow or `SEARCH` in cyan. The input border is muted when
  unfocused and `$accent` when focused. The footer legend changes with the mode.
- **Scope strip.** `N nodes · H hidden · F ⊘`. It adds `· history partial` when
  `query_incomplete` is set, and in v1 `· I hides K` from `_hidden_count`, so the finder
  never implies completeness it doesn't have.
- **Responsive layout.**
  - ≥140 columns: list 44%, preview 56%.
  - 100–139 columns: 50/50, and the list drops its status column.
  - Under 100 columns: the preview stacks below the list at 40% height.

### 5.3 Interaction model

| Key | Hint mode (default; `OptionList` focused) | Search mode (query `Input` focused) |
|---|---|---|
| `0-9a-zA-Z` | Complete a hint and jump, or set a pending prefix | Edit the query; live refilter; hints re-allocated |
| `<tab>` | Focus the query | Back to hint mode, query kept |
| `/` | Focus the query | Types `/` |
| `<enter>` | Jump to the highlighted node | Jump to the highlighted node |
| `ctrl+n` / `ctrl+p`, `↓` / `↑` | Next/previous jumpable row, **wrapping**, skipping context rows | Same (forwarded as in `CommandPaletteModal`) |
| `"` | Jump back (`''` / `` `` `` semantics) | Types `"` |
| `backspace` | Cancel a pending prefix | Delete a character |
| `esc` | Cancel a pending prefix, otherwise close | Back to hint mode |
| `ctrl+u` | — | Clear the query (native `Input`) |
| any other key | Swallow; footer flashes "no hint ‹x›" | Types |

Implementation notes:

- **Tab.** `Screen` binds `tab`/`shift+tab` to focus traversal, so bind `tab` as a
  screen-level `Binding(..., priority=True)` (precedent: `revive_agent_modal.py:109`).
  Ctrl+I arrives as Tab.
- **App bindings while the modal is open.** The app's `next_tab`/`prev_tab` priority
  bindings are disabled while a modal is active. Plain app bindings, including `"`
  itself, don't fire inside a `ModalScreen`.
- **Stop every key.** `Input` stops printable keys itself. In hint mode the screen's
  `on_key` must `stop()` every key it sees, because the app's `_custom_mode_prefixes`
  branch has no modal guard.
- **Hint characters.** None of the modal's command keys (`/`, `"`, tab, esc, enter,
  ctrl+*) are in `JUMP_HINT_CHARS`, so nothing needs to be excluded from the hint
  alphabet. Don't bind `j`/`k`/`q`: they must stay hint characters.

### 5.4 Node set and classification (pure; computed once on open)

`build_node_finder_snapshot(owner) -> NodeFinderSnapshot` lives in a pure module with no
Textual imports. It is O(n), in memory, and never stats or globs. It stays in Python: it
depends on TUI fold, panel, and query state, which is on the presentation side of the
Rust-core boundary. The only shared primitive it uses, fuzzy matching, is already in
`sase_core`.

1. `complete = owner._agents_with_children`: loaded, non-dismissed, clan-projected, taken
   before folds and before the query.
2. **Rendered set:** the identities of the `("agent", idx)` entries from
   `_jump_candidate_targets()`. That call walks each panel's grouping tree exactly as
   rendered.
3. **Reachable with the query:** `filter_agents_by_fold_state(complete,
   _FoldStateProjection({all fold keys: FULLY_EXPANDED}))` followed by the active query.
   This is the same technique `prospective_clan_projection` uses
   (`actions/agents/_prospective_clan.py`).
4. **Reachable without the query:** step 3 without the query.
5. Classify each row that passes the A2 exclusions:
   - in (2) → `visible`;
   - in (3) and in `_agents` → `banner` or `panel`;
   - in (3) and not in `_agents` → `folded`, recording the nearest collapsed ancestor for
     the preview line;
   - in (4) but not (3) → `query`;
   - otherwise → not listed.
6. Emit frozen `NodeFinderRow`s in tribe-panel order, then tree order. Each row carries:
   - identity, name, title, kind, status, and depth;
   - panel key, hidden reason, and nearest collapsed ancestor;
   - search haystacks;
   - `jumpable` (false for context-only step and scaffolding rows);
   - a read-only `Agent` reference for the Tier 0 preview.

Deduplicate by identity. **The snapshot is fixed for the modal's lifetime.** Background
refreshes never reshuffle rows or hints. An optional subtle `list changed` chip can
appear instead.

### 5.5 Filtering

- Split the query on whitespace; every token must match (AND). Use the Rust
  `fuzzy_match(token, haystack)` tiers (0 prefix, 1 basename-prefix, 2 substring,
  3 subsequence) with the help modal's two-pass policy (`modals/help_modal/filter_model.py`).
  Pass 1 accepts contiguous matches only (tier ≤ 2). If nothing survives, pass 2 relaxes
  to subsequence matching and the strip shows `relaxed`. This avoids the "everything
  subsequence-matches" noise on names like `sase-169.3--mon-1`.
- Smart case: an all-lowercase query is case-insensitive.
- Survivors keep **tree order**, and their ancestors appear as dim, unhinted, unselectable
  context rows, mirroring `filter_tree_rows`. The **highlight** moves to the best match
  (lowest tier, then highest score, then name haystack before title haystack), so
  `<enter>` right after typing does the right thing.
- If the previously highlighted identity still survives a filter change, keep it
  highlighted only when it is also the best match. Otherwise go to the best match.
  Preserve the highlight across `<tab>` round trips that don't change the query.

### 5.6 Hints

- Allocate over **jumpable rows only**, in display order:
  `build_jump_hint_maps(identities, prefix_free=True)`. Normalize keys with
  `normalize_jump_key` so uppercase hints work, and match with `match_jump_hint`.
- Re-allocate **only when the query changes**. Filtering therefore always shortens hints:
  typing three letters and pressing `<tab>` usually leaves single-key hints.
- Past 3,844 jumpable rows (not realistic, but it must be handled), the overflow rows show
  no hint, and the strip says "type to narrow". Don't silently truncate.
- The hint map maps hint → identity, never hint → index.

### 5.7 Preview

**Tier 0: synchronous on every highlight change, zero I/O.** The highlight and Tier 0
paint together in under 16 ms.

| Node kind | Content (all from memory) |
|---|---|
| Every kind | Kind chip and accent; two-line compact identity (`build_agent_compact_lines` and its clan, workflow, and proc variants); breadcrumb `@tribe ▸ clan ▸ session ▸ node`; why-hidden line; **"⏎ will …"** line, e.g. "expands 2 folds, then selects it" or "clears query ‹status:done›" |
| Agent / agent shell | Provider/model/effort, status, runtime, tribe/clan/session role, wait and queue chips |
| Session container | Shell lane: one line per shell (name · kind · status glyph · duration), using the member-roster field helpers without publishing a jump map |
| Clan | Member counts and status roster from `aggregate_clan_in_memory` |
| Monitor / proc shell | Command, state, exit code, and `proc_log_tail` (already in memory) |
| Workflow root / agent step | Workflow name, step index, status |

**Tier 1: debounced and off the pump.** Applies to agents, shells, and agent steps.

- **Pipeline:** `DetailPanelDebouncer` (150 ms) → `spawn_pump_free_task` →
  `asyncio.to_thread`.
- **Content:** a bounded **prompt head** (~2 KB / 8 lines) and **reply tail**
  (~8 KB / 20 lines), read through the mtime-keyed artifact file cache. Check
  `projected_agent_waiting_for_hydration` first for projected rows.
- **Caching:** a modal-local LRU of about 128 entries, keyed by identity plus an mtime
  token.
- **Staleness guard:** paint a result only if the same identity is still highlighted
  (generation counter). Cancel outstanding tasks on unmount.
- **No layout shift:** section headers and fixed-height `⋯ loading` skeleton lines are
  painted by Tier 0, so the preview never jumps around.
- **What not to do:** don't copy `revive_agent_modal`'s synchronous on-highlight read,
  and don't embed `AgentDetail`.
- **v1 rendering:** plain wrapped text. Markdown via `LazySyntaxRenderCache` off the pump
  can come later.

### 5.8 Jump execution: a small ladder, modeled on link-follow

The modal dismisses with `NodeFinderResult(identity=…)` or `NodeFinderResult(back=True)`.
The app callback then runs:

1. **Back:** `action_jump_to_entry_fast()`.
2. **Default:** `_reveal_agent_row(identity, subject="Node")`. This covers `visible`,
   `folded`, `banner`, and `panel` rows, including monitor and gate shells (the ancestor
   walk expands the gating session fold) and hidden steps (`FULLY_EXPANDED`). It saves
   the `ctrl+o` anchor first and performs one structural refresh.
3. **`TARGET_FILTERED` with an active query**, whether or not the row was pre-classified
   `query`:
   - Call a new `_clear_agents_query_for_navigation()` helper that is correct on both
     `agents_unified_query` branches. It records the `agents-live` history transition
     where that exists, calls `_record_explicit_agents_query_commit("")` and
     `_refilter_agents()`, then schedules the async refresh.
   - Retry step 2 synchronously against the refiltered in-memory rows.
   - Toast: *"Cleared Agents query ‹status:done› to reach research.8.cdx (restore it from
     query history)"*.
4. **Phase 2, `◌` rows:**
   - Set `hide_non_run_agents = False` and call
     `_schedule_agents_async_refresh(on_complete=…)`.
   - In `on_complete`, re-capture the tab and selection (perf rule 4), then retry
     step 2.
   - Toast: *"Showing hidden agents (I) to reach ‹name›"*.
5. **Anything else:** `_notify_member_reveal_failure(failure, subject="Node")`. A
   vanished or ambiguous identity produces "Node changed; jump cancelled" and leaves
   navigation state untouched.

The classification is only a display hint; the ladder is authoritative. This covers edge
cases such as a node that survives the query only as the ancestor of a match inside its
own collapsed fold.

**Phase 2 roster (cdx's design).** The worker-side prepare/apply pipeline publishes
`_agents_navigation_roster`: the clan-projected `capacity_agents`, taken after dismissal
filtering and before `hide_non_run_agents`. It is published alongside the other prepared
rosters. The finder never rebuilds "all nodes" by concatenating rosters: that would
duplicate the projection rules and drift from the loader.

### 5.9 Reliability rules

1. **Snapshot on open. Every listed hint works.** Only reachable rows get hints, and
   identity is revalidated at jump time (`prepare_agent_navigation_target(...,
   require_current=False)`).
2. **Identity crosses the modal boundary, never an index.**
3. **One structural refresh per jump.** Expanded folds stay expanded, consistent with
   roster jumps, and `ctrl+o` returns to the saved anchor.
4. **Availability guard.** The action is available only on the Agents tab, when the
   prompt bar doesn't own keys, when no modal is active, when the first load is done, and
   when `_guard_agent_navigation_for_artifact_file_viewer` doesn't block it.
5. **Programmatic highlight guard.** Guard `OptionList` programmatic highlight echoes
   with a flag that is cleared synchronously in `finally:` (perf rule 12).
6. **The finder mutates committed view state only through the ladder** (query clear, and
   `I` in phase 2), and always announces it.

### 5.10 Performance budgets (enforced by a bench)

| Path | Budget (2,000 synthetic nodes) | How |
|---|---|---|
| `"` to first paint | < 50 ms p95 | O(n) pure snapshot, list, and Tier 0; no I/O |
| Keystroke to refiltered paint | < 16 ms p95 | tokens × n Rust `fuzzy_match` calls plus one list update. If over budget: latest-wins coalescing |
| `ctrl+n/p` to highlight plus Tier 0 | < 16 ms p95 | Pure renderers; Tier 1 debounced |
| Tier 1 | Off the pump | Thread plus LRU; stale results dropped |

Start with `OptionList`: it provides highlighting, scroll-into-view, and disabled
options, so header and context rows are skipped for free. Switch to a line-API
`ScrollView` only if the bench misses budget. Emit `SASE_TUI_TRACE` spans
(`node_finder.open`, `node_finder.filter`, `node_finder.preview`) and check with
`SASE_TUI_PERF`.

---

## 6. Implementation map

New files:

- `src/sase/ace/tui/modals/node_finder_rows.py`: snapshot and classification (§5.4),
  filtering (§5.5), and hint allocation (§5.6). Pure and unit-testable.
- `src/sase/ace/tui/modals/node_finder_preview.py`: Tier 0 builders, and the Tier 1
  loader plus LRU.
- `src/sase/ace/tui/modals/node_finder_modal.py`:
  `NodeFinderModal(ModalScreen[NodeFinderResult | None])`.
- `src/sase/ace/tui/actions/navigation/_node_finder.py`: `action_jump_to_node()` plus the
  dismiss ladder (§5.8), mixed in next to `NavigationModalMixin`.

Wiring checklist:

1. `keymaps/key_validation.py`: add `"quotation_mark": '"'` to `_KEY_DISPLAY`, plus a
   `'"' → quotation_mark` alias.
2. `keymaps/app_keymaps.py`: a `jump_to_node: str` field next to `jump_to_all_entries`.
3. `src/sase/default_config.yml` under `ace.keymaps.app`: `jump_to_node: "quotation_mark"`,
   with an "Agents only" comment. The registry raises at startup if this entry is
   missing, and project gotchas require default-config updates for keymap changes.
4. Binding metadata: `keymaps/metadata.py`, plus a fallback in `tui/bindings.py` if tests
   rely on it.
5. `commands/_app_metadata_nav.py` with `AGENTS_ONLY`. The metadata coverage check fails
   at import if this is missing.
6. `_app_action_availability.py`: the guard from §5.9, rule 4.
7. `modals/help_modal/agents_bindings.py` Navigation section:
   `Jump to any node ("" back)`.
8. Modal exports: `modals/_export_table.py`, `modals/__init__.py`, `modals/__init__.pyi`.
9. A `styles.tcss` block next to `JumpAllModal` (about line 5949).
10. Docs: Agents navigation docs. After it lands, add a glossary strand for "Node Finder"
    via `/sase_memory_write`.

No feature flag is expected: the change is additive and has no old branch that must
stay reachable. Confirm against the `sase_flags.md` memory when writing the plan.

---

## 7. Test plan

**Snapshot and classification tests** (one per class): visible; collapsed-clan member;
collapsed-session shell; monitor and gate gated by the session fold; collapsed banner;
collapsed and isolated panel; query-filtered; remote fleet row (listed).

**Exclusion tests:** bash, python, parallel, and pre-prompt steps are not jumpable, and
they appear as context rows only when they have jumpable descendants; a synthetic future
step kind is excluded. `STARTING`, `hidden_only_parents`, and dismissed rows are not
listed. Identities are unique, and with an empty query the order matches the tab's tree
order.

**Filtering and hint tests:**

- Tokens use AND; the contiguous pass runs before the relaxed pass; smart case works.
- Ranking is deterministic, and the highlight lands on the best match.
- Prefix-free allocation holds at 61, 62, 63, 3,844, and more than 3,844 rows, with the
  overflow note shown.

**Modal key tests** (the `_ModalHost(App)` pattern):

- The `OptionList` has focus on open, and the current node is highlighted.
- A single-key hint dismisses with the identity. A two-key hint goes pending, then
  completes, and backspace cancels a pending prefix.
- An invalid key neither dismisses nor reaches the app: assert that
  `_custom_mode_prefixes` never sees it.
- `<tab>` round-trips focus; `/` focuses the query; Esc in search mode returns to hints;
  Esc in hint mode closes.
- `<enter>` works in both modes. `ctrl+n/p` and the arrow keys wrap in both modes and
  skip context rows.
- `""` returns the back result.
- A background roster change while the modal is open doesn't change hints.

**Jump tests** through a real `AcePage`:

- A visible row lands with no structural rebuild.
- Collapsed clan + banner + panel layers all expand in one rebuild.
- A query-hidden target clears the query, records the history transition on both flag
  branches, and shows the toast.
- A vanished identity rolls back the anchor, and the failure toast says "Node".
- `ctrl+o` after a finder jump returns to the saved anchor.

**Preview tests:**

- Tier 0 is pure: monkeypatch `open`, `os.stat`, and `os.scandir` to raise during
  highlight moves.
- Tier 1 drops stale results, hits the LRU on revisit, and is cancelled on unmount.
- An echoed `OptionHighlighted` never paints a stale preview.

**Keymap tests:** `quotation_mark` validates, displays as `"`, and has the alias. Default
config, registry, metadata, command catalog, and help all agree. The action is unavailable
off the Agents tab and while an editor owns keys.

**Visual PNG goldens** (template: the command-palette snapshot test):

- `node_finder_hints_160x48`
- `node_finder_search_160x48`
- `node_finder_pending_prefix`
- `node_finder_narrow_100x40`
- `node_finder_no_results`

Inspect every golden change.

**Perf bench:** `pytest -m slow` on a synthetic 2,000-node clan/session tree, checked
against the §5.10 budgets.

---

## 8. Phasing

| Phase | Contents | Exit criteria |
|---|---|---|
| **P1: MVP** | Keymap wiring; snapshot and classification; tree list with hidden-reason glyphs; prefix-free hints; full key model; `_reveal_agent_row` landing; the TARGET_FILTERED query-clear rung; Tier 0 **and** Tier 1 preview (a headline requirement); scope strip with `history partial` and `I hides K`; tests, goldens, bench | Every fold-, banner-, or panel-hidden node (e.g. `research.8.cdx`, `sase-169.3--mon-1`) is reachable in 2–4 keystrokes; a query-hidden node is reachable, and the query is restorable; budgets are met |
| **P2** | `_agents_navigation_roster` published at the loader boundary; `◌` rows; async `I` flip-and-reveal rung; glossary strand | An `I`-hidden running `%hide` agent is reachable and the toast explains why |
| **P3 (feedback-gated)** | Viewport-relative hints (label only on-screen rows, so every visible row is one key); recall of the last query on reopen; Markdown reply rendering; optional `:jump <name>` using the same snapshot | Driven by usage |

---

## 9. Open questions for Bryan

1. **Q1: Is `I` in scope?** Did "regardless of whether it is shown" include `%hide` and
   axe-spawned rows that `I` hides? If yes, P2 should follow P1 immediately.
2. **Q2: How broad is the step exclusion?** The default is every non-`agent` workflow step
   (A2). The alternative is cld's narrower rule: exclude only agent-shell bash/python and
   pre-prompt steps, and keep standalone workflows' steps.
3. **Q3: Is query clearing acceptable?** The default clears the query with history and a
   toast. The alternative lists query-hidden rows but won't jump to them.
4. **Q4: Filter haystack.** The default is the name plus the displayed title, with name
   hits ranked higher. The stricter alternative is the name only.
5. **Q5: Keep `""` for back?** It mirrors `''` and `` `` ``.

---

## 10. Recommended solution

Build the **Node Finder**: an Agents-only `ModalScreen` bound to `"` (`quotation_mark`,
action `jump_to_node`), about 94% × 90%, in the `JumpAllModal` visual family.

- **List.** It shows a snapshot, taken on open, of every reachable, non-dismissed sase
  node in `_agents_with_children`.
  - It is grouped by tribe panel in tab order and drawn as a tree with the tab's own
    guides, glyphs, and colors.
  - It includes clans, agent nodes, session shells (monitors and gates too), workflow
    roots, agent steps, and stand-alone proc shells.
  - Non-`agent` workflow steps are never jump targets; they appear only as dim context
    rows.
  - Hidden rows are ghosted and carry a one-glyph reason. The current node is marked `◆`
    and highlighted on open.
- **Hints.** Every jumpable row always carries a house-style `[h]` hint, allocated
  prefix-free (mostly single keys). Hints change only when the query changes, and they
  dim while the query bar has focus.
- **Keys.**
  - Hint mode is the default: a hint jumps, `<tab>` or `/` searches, `ctrl+n/p` and the
    arrow keys cycle with wrap-around, `<enter>` jumps, `""` jumps back, and Esc closes.
    Invalid keys flash instead of closing, and nothing leaks to the app.
  - Search mode: tokenized, contiguous-first Rust fuzzy filtering on name, then title.
    Matches keep tree order with their ancestors as context, and the highlight lands on
    the best match. `<enter>` jumps; `<tab>` or Esc returns to hints with the query kept.
- **Preview.** Tier 0 is instant and I/O-free: kind chip, compact identity, breadcrumb,
  why-hidden, and a "⏎ will …" line, plus kind-specific in-memory content. Tier 1 is
  debounced, runs off the pump, is LRU-cached and generation-checked, and shows the
  prompt head and reply tail behind fixed skeletons.
- **Jumping.** The modal dismisses with the node's identity. `_reveal_agent_row(identity,
  subject="Node")` then expands exactly the needed folds, banner, and panel, selects the
  node, and saves a `ctrl+o` anchor. If the Agents query is what hides the node, the
  query is cleared through a history-recording helper, the reveal is retried, and a toast
  says so. `I`-hidden nodes follow in phase 2 through the same ladder, once the loader
  publishes a pre-hide navigation roster.
- **Guardrails.** Budgets are enforced by a bench (open < 50 ms, keystroke and highlight
  < 16 ms p95 at 2,000 nodes), backed by the §7 tests and PNG goldens.

This design delivers everything requested. It is **intuitive**: two explicit modes, a
visible mode pill, the `'`/`"` mnemonic, and one-line jobs for each jump surface. It is
**reliable**: a snapshot where every hint works, identities instead of indices, the
proven reveal primitive, and announced view changes. It is **fast**: every keystroke
path stays in memory and disk reads are debounced off the pump. And it is **beautiful**:
it reads as a map of the Agents tab in the house hint and tree style, not a bolted-on
picker.
