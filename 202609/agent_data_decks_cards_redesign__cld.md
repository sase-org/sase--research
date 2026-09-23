# Agent Data Decks & Cards: Redesigning the Agents-Tab Detail Panels

- **Researcher:** cld, one of three independent researchers in the swarm
- **Date:** 2026-09-23
- **Repo state:** `sase` master @ `4b9da7a33`
- **Question:** Should the Agents tab's metadata, Files and LLM Calls panels become one "deck panel" type that hosts "agent data cards"? If so, how should it be built?

---

## 0. TL;DR

**Verdict: yes, build it.** It removes more code than it adds and generalizes three existing mechanisms:

- File paging becomes cards.
- The `p` picker's layouts become deck layouts.
- The `Z` zoom modal becomes collapsing the node panel and showing a single deck.

It also unlocks the most useful view the TUI can't show today: **the reply next to the diff**, or **the prompt next to the reply**.

The plan needs a few adjustments. Section 4 lists each one; the most important are:

1. **Don't rely on `Ctrl+Shift+N/P` as a default.** On athena, tmux runs with `extended-keys off`, so tmux delivers Ctrl+Shift+N as plain Ctrl+N. Kitty's default `kitty_mod` also takes Ctrl+Shift+N (new window) and Ctrl+Shift+P (hints) before tmux sees them.
   - Recommended defaults: **`Ctrl+N/P` cycles cards**, **`]`/`[` cycles decks**.
   - This keeps file-cycling muscle memory, since Files-deck cards *are* files.
   - It matches the zoom modal's existing `]`/`[` panel cycling.
   - It makes the stale "press ] for the full LLM Calls timeline" hint true again.
2. **Card navigation should mean the same thing in both render modes.** "All cards on one page" and "one card per page" are rendering details. `Ctrl+N/P` always means "go to the next card", and a card tab strip always shows where you are.
3. **The automatic one-page-vs-paged choice needs hysteresis and must keep your reading position.** The median agent's Main deck is about 80–100 lines, which sits right at any sensible threshold. Without these safeguards a streaming reply would flip the layout under the reader.
4. **Use unambiguous names.** Your "vertical layout" is Textual's `layout: horizontal`, and vim calls a top/bottom split "horizontal" while tmux's `split-window -h` means side-by-side.
   - Deck layouts: `single`, `left-right`, `top-bottom`.
   - Render modes: **spread** (all cards on one page) and **paged**. Avoid "stacked": a stack of cards shows only the top card, which is the opposite meaning.
5. **Collapse the node panel by hiding it, not remounting it.** Hide it with `display: none` so it stays mounted and j/k keep working. Show a position chip (`nodes 12/47 · ctrl+s`) in the info-row slot the `p` hint frees up. A two-column status rail can come later.
6. **Keep what `p` and `Z` did that people use:**
   - Split ratios (70/30, 50/50, 30/70) move to `{`/`}`, the same keys Artifacts uses for its split ratio.
   - `Z` becomes "maximize the focused deck": collapse the node panel, switch to a single layout, press again to restore.
   - The zoom modal's any-panel search is reused for card search.

Section 9 gives the recommended solution. It is a Python-only presentation change; nothing crosses the Rust core boundary. The plan is a 6-phase epic behind a `beta` flag that the epic itself removes.

---

## 1. What exists today

Paths are relative to `src/sase/ace/tui/` unless marked otherwise.

### 1.1 Layout

The node list is on the left, the detail on the right (`_app_layout.py:101-121`):

```
#agents-view
  #agent-info-row   AgentInfoPanel | AgentLoadIndicator | LaunchContextBar   ← shows "view: <mode> (p)"
  AgentsFilterBar
  #agents-content (Horizontal)
    #agent-list-container    one AgentList per tribe panel      width 60..130 cells, content-driven
    #agent-detail-container  width 1fr
      AgentDetail (widgets/agent_detail.py:68-85)
        AgentHeaderPanel        sticky identity header (2-row compact, `d` expands, ≤50%)
        #agent-prompt-scroll    AgentPromptPanel  ← "metadata panel"
        #agent-search-scroll    frozen search overlay for metadata
        #agent-file-scroll      AgentFilePanel     (widgets/file_panel/, ~2.85k LOC)
        #agent-llm-calls-scroll AgentLLMCallsPanel (llm_calls_panel.py + 4 helpers)
        AgentJumpPanel          numbered roster footer (`.` expands, ≤40%)
```

- **List width.** `agent_list_column_width()` clamps the width to `MIN_AGENT_LIST_WIDTH=60` / `MAX_AGENT_LIST_WIDTH=130` (`_app_layout.py:47-60`). The user can't resize it. Unlike the AXE sidebar, it has no terminal-width cap, so on a 160-column terminal the detail pane can shrink to about 30 columns.
- **Hiding the list already works.** It is hidden with `display: none` in two places: onboarding (`styles.tcss:3725-3727`) and the tmux artifact-file viewer (`styles.tcss:3729-3731`). Collapsing the node panel with `Ctrl+S` therefore reuses a proven path.
- **Metadata is always the primary panel.** At most one secondary panel shows, File or LLM Calls, never both.
  - `DetailPanelMode` is `AUTO`(=file) / `LLM_CALLS` / `INFO`.
  - `DetailLayoutMode` is `METADATA_ONLY` / `METADATA_LARGER` (70/30) / `EQUAL` / `SECONDARY_LARGER` (30/70) / `SECONDARY_ONLY` (`widgets/_agent_detail_panels.py:24-65`).
  - Sizes are applied through CSS classes (`styles.tcss:3858-3991`).
- **The layout is session-local and is not persisted** (`docs/ace.md:5134`). A new session starts in `METADATA_ONLY`, so Files and LLM Calls stay hidden until the user opens `p`.

### 1.2 The `p` picker and the `Z` zoom modal

- **`p` → `choose_agent_view` → `AgentViewModal`.**
  - Code: `modals/agent_view_modal.py`, 305 LOC, and `actions/agents/_agent_view_picker.py`, 508 LOC.
  - It is a single-key chooser. `f` File or `t` LLM Calls picks the view; `[`, `1`, `=`, `2`, `]` pick the layout, and `p`/`P` cycle layouts.
  - Three retired actions (`toggle_layout`, `toggle_thinking`, `toggle_thinking_reverse`) now just open this picker (`actions/agents/_panel_detail.py:161-165,452-462`).
- **`Z` → `zoom_panel` → `ZoomPanelModal`.**
  - A 98%×96% `ModalScreen` with targets METADATA / FILE / LLM_CALLS (`modals/zoom_panel_types.py:14-19`).
  - Keys: `]`/`[` cycle the panel; `Ctrl+N/P` cycle files, with a file rail and a file list frozen for the modal's lifetime; `h/l/H/L` set LLM detail; `/ ? n N` search; `E`, `y`, `r`; `q`/`Esc`/`z` close.
  - Size: **1,627 LOC** across 8 `modals/zoom_panel_*.py` files, about 167 LOC of actions, about 127 LOC of TCSS and **about 2,350 LOC of tests**.
  - The zoom modal has to subclass the file and LLM panels only to override their hard-wired scroll-container IDs (`modals/zoom_panel_widgets.py:53-57,131-138`).

### 1.3 Metadata-panel inventory for the Main deck

The metadata panel is **one `Static` rendering one Rich `Group`** per update. Section headings are tagged with hidden `sase_prompt_panel_section=<id>` metadata (`widgets/prompt_panel/_helpers.py:111-132`). `SectionTrackingVisual` turns those tags into row anchors for `Ctrl+J/K` and folds (`widgets/prompt_panel/_section_navigation.py:115-387`). This matters: **the same anchor machinery can supply card boundaries and card heights for free** (§5.7).

For a normal agent shell or agent node, the body order is (`widgets/prompt_panel/_agent_display_header.py:85-520`, `_agent_display_render.py:256-609`):

| # | Heading as rendered | Conditional? | Typical size | Proposed card |
|---|---|---|---|---|
| – | Identity (name, model, xprompts, queue/wait, retries, timestamps, …) | detached into `AgentHeaderPanel` | 2 rows compact | **shared chrome, outside decks** |
| 1 | `❖ QUEUE · N waiting` | queued agents | ≤7 rows | Context |
| – | `FAMILY SHELLS`, `NEIGHBORS` | – | – | **jump panel**, since commit 78f1d71 |
| 2 | `MEMBERS · N` (legacy parallel families) | legacy | 1 row per member | Context |
| 3 | `OUTPUT VARIABLES` | if any | few to dozens of lines | Context |
| 4 | `WORKFLOW VARIABLES` | workflow children | few lines | Context |
| 5 | `SASE CONTEXT`: lanes PLAN, BEAD, ARTIFACTS (Beads/Reads/Commits/Deltas/Files), MEMORY, GLOSSARY, SKILLS, WORKSPACES | if non-empty | medium–large | Context |
| 6 | `SLOW TOOL CALLS · ≥Ns · N calls` | ≥1 slow call | ≤8 rows + tail | Context (per the request), linking to the Tools deck |
| 7 | `ERROR` + `Output:` | failed | 1–3 lines | Context (summary). See adjustment A7 for the traceback. |
| 8 | `AGENT XPROMPT` | raw xprompt exists | small | Context |
| 9 | `AGENT PROMPT` | always | **p50 14 / p90 289 lines** | Context |
| 10 | `AGENT REPLY`, or `AGENT CHAT` when DONE/FAILED; with follow-up phase dividers, `ATTEMPT k` dividers in merged view, and "Waiting for agent response…" | always | **p50 31 / p90 481 lines** | **Reply** |

**Sections the request doesn't name** that belong in Context: QUEUE, MEMBERS, OUTPUT VARIABLES, WORKFLOW VARIABLES and ERROR. The request's "SLOW TOOLS" is literally titled `SLOW TOOL CALLS`.

**Quirk found:** the error traceback `Syntax` block is appended after the carrier, and the carrier already ends with the `AGENT PROMPT` heading. As a result the traceback renders *under the AGENT PROMPT heading, above the prompt body*. See `_agent_display_render.py:441` then `:455/:519/:557`; the family path does the same at `_agent_display_family_render.py:102-152`. The card split is a natural moment to fix this (A7).

**Other node kinds** each need a mapping, because the Main deck must exist for every node:

| Node kind | Document today | Proposed Main-deck cards |
|---|---|---|
| Agent / agent shell / family container | above; family adds `AGENT REPLY · N` with per-shell phase dividers | `context`, `reply` |
| Pinned attempt | banner, `ATTEMPT ERROR`, `AGENT PROMPT`, `ATTEMPT N REPLY` | `context`, `reply` |
| Proc shell | `COMMAND`, `PROC DETAILS`, `LOG TAIL` | `context`, `reply` (titled **Output**) |
| Monitor | `MONITOR`, `OUTPUT` | `context`, `reply` (titled **Output**) |
| Gate | `GATE`, `OUTPUT` | `context`, `reply` (titled **Output**) |
| Bash/Python step | `BASH COMMAND`/`PYTHON CODE`, `STEP OUTPUT` | `context`, `reply` (titled **Output**) |
| Parallel step | `STEP OUTPUT` only | `reply` (titled **Output**) |
| Top-level workflow row | `WORKFLOW DETAILS` … `WORKFLOW STEPS`, `AGENT PROMPT` | `context` only |
| Clan | summary, `ERRORS`, `OUTPUT VARIABLES`, `WORKFLOW VARIABLES`, `REPLIES`, `SASE CONTEXT`, `SLOW TOOL CALLS`, `PROMPTS` (fold-driven triage document) | single `summary` card |
| Tribe summary | description, `NEEDS ATTENTION`, `CLAN SUMMARIES`, `PROMPTS`, `ERRORS`, …, `RUNTIME STATISTICS` | single `summary` card |

Clan and tribe documents are fold-driven triage digests. Splitting them into Context and Reply would scatter summaries that are designed to be read together, so each gets one card.

### 1.4 Files panel, which becomes the Files deck

**Pages** are strings in `self._file_list`, ordered by `_desired_file_list` (`widgets/file_panel/_file_list.py:188-221`):

1. commit diffs (`__commit_diff__:{i}`; primary repo, then linked repos, then external repos)
2. live diff (`__live_diff__`; omitted for done agents that have commit diffs)
3. linked-repo diffs (`__linked_diff__:{repo}`)
4. `agent.extra_files`: plan, PDFs rendered to markdown, images, videos

**Current behavior:**

- **One page at a time.** `Ctrl+N/P` wraps through pages (`_file_list.py:104-130`).
- **Titles.** The page's source label is the border title. The `[i/n]` counter appears on the *metadata* panel's subtitle (`widgets/_agent_detail_panels.py:439-497`).
- **Scroll anchoring.** An LRU of 64 `(agent, page)` scroll anchors restores your position when you revisit a page (`_scroll_anchor.py`).

**Size facts relevant to spread mode:**

- The live diff and linked diffs are already in memory, so they are cheap to count.
- Commit diffs and extra files are paths read on a worker only when you select that page, with no content cache (`_display.py:226-236`, `_static_read.py:30-81`).
- Render caps: highlighting up to 64 KB / 1,500 lines (24 KB / 600 lines for markdown); plain text beyond that, capped at 5,000 lines / 128 KB (`util/lazy_syntax.py:30-40`).

**Coupling to fix:**

- `_get_scroll_container()` looks up the scroll container with an app-wide query, `self.app.query_one("#agent-file-scroll")` (`_content.py:129-134`). A second file-card view on the same screen would bind to the first match.
- `AgentDetail` writes the panel's private fields (`_agent_detail_panels.py:318-320`) and calls `_reconcile_file_list` (`_agent_detail_state.py:152`).

### 1.5 LLM Calls panel, which becomes the Tools deck

- **Rendering.** A single `Text` timeline (`LLM CALLS`, a summary line, then one row per call) at three detail levels, COMPACT, EXPANDED and FULL (`widgets/_llm_calls_panel_types.py:12-24`). Rows are not virtualized.
- **Data.** Data is fetched on a throttled worker (0.5 s) through an mtime-keyed cache (`llm_calls/cache.py:130-200`). The **SLOW TOOL CALLS** section shares that same cache, so it and the Tools deck are two views of one dataset.
- **Confirmed bug found while reading.** In `_update_display_impl` (`widgets/llm_calls_panel.py:151-177`), if a fetch for agent A is still running when you select agent B, it returns early without starting B's fetch. `on_worker_state_changed` (`:343-357`) has no identity check, so **A's calls paint onto B's panel**. They stay there until the next update for B. The deck refactor fixes this naturally (§6 phase 1), but it is also a standalone bug.
- **Hidden panels still do work.** Both the File and LLM Calls panels are populated even when hidden (`widgets/_agent_detail_display.py:226-271`). Only visible decks need their data (§5.14).
- **`sase tool` runs are not shown anywhere in the TUI.**
  - The ledger is Rust-owned: `sase_home()/tools/runs.sqlite`, read through `sase.core.tool_run.tool_run_list(...)` with an `agent` filter (`src/sase/core/tool_run.py:134-230`).
  - Calls take a 250 ms busy timeout, so a future Tool Runs card must read from a worker.

### 1.6 Keymap facts

Every Agents-tab key is an **app-level** binding in `ace.keymaps.app`, scoped to a tab at runtime by `check_app_action` (`_app_action_availability.py:76-470`). Several actions can share a key: the first action available on the current tab wins. A user override that makes two actions share a key is reverted unless the pair is listed in `_CONTEXTUAL_APP_DUPLICATES` (`keymaps/registry.py:95-130`).

| Key | Today on Agents | Free to repurpose? |
|---|---|---|
| `Ctrl+N` / `Ctrl+P` | `next_agent_file` / `prev_agent_file`: file paging. Ctrl+N/P means "next/previous" in about 15 other SASE surfaces, including zoom's file cycling. | Yes, and the meaning maps directly to cards |
| `Ctrl+Shift+N/P` | unbound | Unreliable (below) |
| `Ctrl+S` | unbound at app level; used only for prompt-local stash and in modals | Yes |
| `Ctrl+F` / `Ctrl+B` | `scroll_prompt_down/up`: half-page metadata scroll | Yes once scrolling follows focus; `Ctrl+B` is freed too |
| `\` → `backslash`, `\|` → `vertical_line` | unbound | Yes, but user overrides to these keys are rejected (below) |
| `[` / `]` | Artifacts-only subtab cycling | **Free on Agents**; zoom already uses them to cycle panels |
| `{` / `}` | Artifacts-only split ratio | **Free on Agents** |
| `p` | `choose_agent_view` | Freed when the picker is removed |
| `Z` | `zoom_panel` | Freed when zoom is removed |
| `-`, `=` | `collapse_panel_folds`, `isolate_panels` | Taken |

**Ctrl+Shift reality check (athena):**

- `tmux show -s extended-keys` → `off` on tmux 3.5a. `TERM=tmux-256color`.
- With extended keys off, tmux sends Ctrl+Shift+N as the same byte as Ctrl+N. **With the proposed defaults, Ctrl+Shift+N would trigger "next deck", not "next card".**
- Textual itself requests kitty "disambiguate" mode (`\x1b[>1u`) and parses CSI-u into `ctrl+shift+n` (`.venv/.../textual/drivers/linux_driver.py:276`, `_xterm_parser.py`), so the app side is ready. The terminal chain is the problem.
- The deployed `~/.config/kitty/kitty.conf` doesn't clear kitty's defaults. `kitty_mod` is Ctrl+Shift, so `kitty_mod+n` opens a new OS window and `kitty_mod+p` is the hints prefix. Both are consumed before tmux sees them.
- **Could not verify:** which terminal you actually attach from (athena runs no terminal-emulator process). This finding is for the tmux server on athena; check your client terminal separately.

**Validation gap:** `is_valid_key("backslash")`, `is_valid_key("vertical_line")`, `"\\"` and `"|"` all return **False**, which I confirmed in the project venv. Defaults aren't validated, so a default of `backslash` binds fine, but **any user override to `\` or `|` is silently reverted**. The fix is to add `backslash` and `vertical_line` to `_KEY_DISPLAY` (`keymaps/key_validation.py:7-40`).

### 1.7 How big is the content?

Measured over this month's 2,794 `ace-run` agents in `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/`. These are raw source lines; wrapped rendering only adds rows.

| Content | p10 | p50 | p75 | p90 | max |
|---|---|---|---|---|---|
| Prompt (`*_prompt.md`) | 3 | **14** | 55 | 289 | 21,407 |
| Reply (`live_reply.md`) | 9 | **31** | 125 | 481 | 52,124 |
| `tool_calls.jsonl` rows | 46 | 140 | 264 | 466 | 4,344 |
| Diff pages per agent | 1 | **3** | 5 | 7 | 27 |
| Total diff lines per agent | 82 | **693** | 1,517 | 2,310 | 135,737 |

What this means:

- **Main deck:** prompt + reply + roughly 20–40 lines of context comes to about 80–100 lines for the median agent. That is right at the height of a single full-height detail pane (about 40–60 rows) or a top/bottom split (about 20–28 rows). **The spread/paged decision will be close for a large share of agents, and running agents grow across the threshold while you watch.** Hysteresis and position preservation (§5.7) are required, not polish.
- **Files deck:** it will almost always be paged. Spread mode helps the bottom decile of agents (≤ about 80 diff lines), which is still useful for small fixes.
- **Tools deck:** it has one card, so spread vs paged doesn't apply yet.

---

## 2. Critique

### 2.1 What is right about the plan

1. **It removes an asymmetry, not just a widget.** Today metadata is always primary and exactly one secondary panel is allowed, so **you cannot read an agent's reply while looking at its diff** without scrolling a 100+ line document. With decks, "Reply | Files" and "Context | Reply" become ordinary layouts.
2. **It consolidates three bespoke mechanisms into one.** File paging (Files cards), the `p` picker (deck layouts) and the zoom modal (collapsed node panel with a single deck) all fold into the deck model. That is about 2,100 LOC of production UI and about 2,400 LOC of zoom/picker tests that stop being special cases.
3. **The two-level hierarchy is justified by the data.** A flat tab list ("Context, Reply, diff 1…27, LLM Calls") breaks down at the p90 of 7 pages and a max of 27. Deck → card keeps the top level short (3 decks) and lets one deck grow.
4. **The Tools deck is a well-placed extension point** for the future `sase tool` card.
5. **Collapsing the node panel is overdue.** The list takes 60–130 columns with no way to reclaim them outside the zoom modal.

### 2.2 Problems and risks, highest impact first

**R1. The Ctrl+Shift+N/P defaults won't work in the environment I could inspect (§1.6).** Worse, they fail as a *wrong action*, not as nothing: Ctrl+Shift+N arrives as Ctrl+N and cycles decks. Separately, on frequency grounds the ergonomic key belongs to the more common action. You set up a deck layout once, but you cycle files every time you review an agent. The plan gives the frequent action (card/file cycling) the harder chord and the rare action (deck cycling) the easy one.

**R2. "Automatically spread or paged" can feel random unless navigation is mode-independent.** If Ctrl+Shift+N sometimes scrolls and sometimes swaps pages, and the Reply is sometimes "below" and sometimes "on the next page", you can't predict what a key will do. The fix is a principle, not a feature:

- A deck is an ordered sequence of cards, and the card tab strip is always visible.
- "Next card" always brings the next card's header to the top of the viewport.
- Whether that happens by scrolling (spread) or by swapping the page (paged) is invisible.

**R3. Flapping.** Per §1.7, the median Main deck sits near the threshold. Several things change its height or the panel's height:

- a running agent streaming its reply
- SASE CONTEXT lanes resolving asynchronously ("resolving…" becoming rows)
- toggling the header (`d`) or the jump panel (`.`)
- terminal resize, or switching between layouts

Without hysteresis and "keep the card I'm reading", the layout will flip under the reader.

**R4. Measuring height has a cost.** Exact rendered height at a given width requires a Rich render, which for Rich renderables in Textual means a full render. Doing that for every card on every selection violates the TUI perf rules ("render paths never stat/glob", "debounce detail panels"). There is a cheap, sound shortcut:

- Only content under the threshold needs exact measurement.
- Content under the threshold is small, and small content is cheap to render.
- A cheap lower bound (logical line count, or bytes ÷ width for unread files) settles every large case with no rendering at all.

See §5.7.

**R5. Naming collisions:**

- **"Horizontal/vertical split"** means opposite things in vim (`:split` stacks top/bottom), tmux (`split-window -h` puts panes side by side) and Textual (`layout: horizontal` means side by side). The request itself labels `|` a "horizontal split" in one bullet while describing side-by-side.
- **"Stacked"** as the all-on-one-page mode is backwards for the card metaphor: a stack of cards shows only the top card.
- **"Tools" deck.** The glossary deliberately separates **LLM Calls** (a read model of provider tool calls) from **Tool Run** (`sase tool` executions). A deck titled "Tools" that holds both is fine as a *grouping*, but the card titles must keep the glossary's precise names: an "LLM Calls" card now, a "Tool Runs" card later.

**R6. Ctrl+F collides with `Ctrl+F`/`Ctrl+B` metadata scrolling.** This is mostly harmless: once scrolling follows focus (`Ctrl+D/U` scroll the focused deck), the separate "scroll metadata while a file is shown" pair has no reason to exist. But the plan should say what happens to `Ctrl+B`. Recommendation: `Ctrl+F`/`Ctrl+B` = focus next/previous deck panel. With two panels both toggle, and the f/b pair keeps its forward/back mnemonic.

**R7. Removing `p` and `Z` loses features the plan doesn't replace:**

- Split ratios (70/30 and 30/70). The proposed splits are 50/50 only.
- Zoom's search over *any* panel. Today only metadata has `,/` search.
- Zoom's file rail and frozen file list.
- Tribe zoom.

Each has a cheap home in the deck model (A9–A11).

**R8. Empty decks.** What happens when the Files deck is shown and you j/k onto an agent with no files, or the Tools deck onto a clan? Today the metadata panel expands to fill the space whenever the secondary panel is empty. That produces the layout jumping you see while navigating. The deck design should choose stable geometry deliberately (A12).

**R9. Many existing actions implicitly target "the metadata panel" or "the visible secondary panel":**

- `Ctrl+D/U`, `g`/`G` (and the bottom pin), `Ctrl+J/K`, `z` folds
- `,/` search, `E`, `y`, `V`, `v` hints
- `l`/`h`/`L`/`H` LLM detail

There are about 260 source references in 23 files to the hard-wired detail IDs, the `is_*_visible` predicates or the mode enums, and 49 test files reference them. Every one must be retargeted to "the focused deck panel's active card". This is the bulk of the work and needs its own phase.

**R10. Duplicate decks.** The request already says `\`/`|` fall back to "show the current deck" when no other deck exists, so duplicates are implied. Duplicates are *useful*, not just a fallback: Main in both panels with different active cards gives **Context | Reply side by side**. The design should say so explicitly (A5).

**R11. Scope creep.** Arbitrary N-way tiling, user-defined decks and per-deck plugins would be building mechanism ahead of need (compare decision `corpus-before-mechanism`). Cap the design at **≤2 deck panels and 3 built-in decks**. Keep the data model a list of panels plus an orientation, so a third panel remains possible later without a redesign.

---

## 3. Alternatives I considered

| Alternative | Why not |
|---|---|
| **Keep metadata-primary + one secondary; just add a left/right orientation and list collapse** | Cheapest option, but it still can't show Reply next to Files and still needs the `p` modal and the mode/layout enums. It fixes the symptom, not the model. |
| **Flat tabs per panel (Context, Reply, file 1…n, LLM Calls) with no decks** | One level is simpler to explain, but it breaks down at 7–27 file pages, and adding the Tool Runs card later would crowd it further. |
| **Full tmux-like tiling (arbitrary splits)** | Speculative (R11). Two panels cover every workflow in the request. |
| **A vim-style window prefix (`Ctrl+W s/v/w/o/h/j/k/l`)** | Familiar to vim users, but a prefix mode is slower than your single keys. Worth offering later as an *alias* layer; not the default. |
| **Split the metadata document into two independent widgets (one builder per card)** | Would duplicate the fold/hint/search/bottom-pin/section machinery per card. The card-partitioned document in §5.2 keeps one builder and one anchor system. |

---

## 4. Requirement adjustments

Each row states the original requirement, the change and the reason.

| # | Original | Adjusted | Why |
|---|---|---|---|
| **A1** | `Ctrl+Shift+N/P` cycles cards | **`Ctrl+N/P` cycles cards.** Optionally also bind `Ctrl+Shift+N/P` as alternates after enabling tmux extended keys. | R1: the chord doesn't reach the app on athena, and cards are the frequent action. Files cards = files, so the old file-cycling muscle memory still works. |
| **A2** | `Ctrl+N/P` cycles decks | **`]` / `[` cycle decks** | Free on the Agents tab; identical to the zoom modal's panel cycling; the existing SLOW TOOL CALLS hint "press ] for the full LLM Calls timeline" (`widgets/prompt_panel/_agent_slow_tools.py:246`) becomes accurate again (today `]` does nothing on Agents). |
| **A3** | "Stacked" when all cards fit, else one card per page | Name the modes **spread** / **paged**. Card navigation behaves the same in both, and the card tab strip is always shown. | R2, R5 |
| **A4** | Configurable size threshold | Threshold in **panel heights** (`ace.decks.spread_max_screens`, default `1.0`), with a ±15% hysteresis band. When the mode changes for the same selection, the active card is the one at the top of the viewport. | R3: absolute line counts behave differently across terminal sizes and split layouts. |
| **A5** | `\`/`|` open the "next not currently shown" deck, else the current one | Keep that, and **let `]`/`[` cycle through all decks, including one already shown in the other panel**. When both panels show the same deck, the new panel's active card defaults to the first card not active in the other panel. | R10: enables Context \| Reply. |
| **A6** | Context card contains `SASE CONTEXT`, `SLOW TOOLS`, `AGENT XPROMPT`, `AGENT PROMPT` "and anything I forgot" | The Context card also contains `QUEUE`, `MEMBERS`, `OUTPUT VARIABLES`, `WORKFLOW VARIABLES` and the `ERROR` summary. The identity header and the numbered rosters stay **outside decks** as shared chrome (header on top, jump panel at the bottom, both spanning every deck panel). | §1.3; the header and jump panel describe the *selection*, not a deck. |
| **A7** | Reply card = `AGENT REPLY` | Reply card = `AGENT REPLY`/`AGENT CHAT` **plus the error traceback at its top**. The short ERROR summary stays in Context. | A failure is the run's outcome. This also fixes the quirk of the traceback rendering under the AGENT PROMPT heading. |
| **A8** | Main deck = Context + Reply | Per node kind: agent-like nodes get `context` + `reply`. Proc, monitor, gate and step nodes get `context` + `reply` **titled "Output"**. Clans and tribes get one `summary` card. Card ids are stable (`context`/`reply`/`summary`), so "which card am I on" carries over as you j/k. | §1.3 table |
| **A9** | 50/50 splits | **`{` / `}` cycle the split ratio 30/50/70** | R7: keeps the `p` picker's ratios; mirrors Artifacts' `{`/`}` split. |
| **A10** | Remove the zoom panel | Remove the modal, but **rebind `Z` to "maximize the focused deck"**: collapse the node panel and switch to a single layout, and press again to restore. Reuse `zoom_panel_search.py` as generic card search for `,/`. | R7; tmux `prefix z` behaves the same way. |
| **A11** | Remove the `p` panel | Remove it. Put `nodes 12/47 · ctrl+s` in its freed `view: … (p)` slot in the info row when the node panel is collapsed. | §5.9 |
| **A12** | (unspecified) | **Stable geometry.** A deck panel whose deck has no content for the selected node shows a one-line empty-state card ("No files for this agent · `]` next deck") instead of collapsing the layout. | R8: no layout jumping during j/k. This deliberately changes today's "metadata expands when there are no files" behavior. |
| **A13** | `Ctrl+F` toggles focus | `Ctrl+F` / `Ctrl+B` = focus next/previous deck panel. Focus is **logical**: a highlighted border, not Textual widget focus, so j/k still drive the node list. | R6 |
| **A14** | (unspecified) | **Persist** the deck layout, decks per panel, ratio, node-panel collapse and each panel's stable active card across restarts in `~/.sase/ace_agents_deck_state.json`. | A layout you set up once shouldn't reset every session. This reverses the "session-local" note in `docs/ace.md:5134`. |
| **A15** | `\` "horizontal split", `\|` "horizontal split" (typo) | `\|` = **left-right** layout; `\` = **top-bottom** layout. Code and glossary use `LEFT_RIGHT` / `TOP_BOTTOM`, never horizontal/vertical. | R5 |
| **A16** | (unspecified) | Allow **`\` and `\|` as user overrides** by fixing `key_validation._KEY_DISPLAY`. | §1.6 gap |
| **A17** | (unspecified) | Images and videos in the Files deck are **solo cards**: when present the deck is always paged. | Their height is viewport-driven (`_display.py:363,396-403`), and graphics-protocol images inside a scrolling spread are fragile. |

---

## 5. Recommended design

### 5.1 Vocabulary

This is what the glossary strands in §5.17 will say:

- **Agent data deck ("deck"):** a named, ordered set of agent data cards about the selected sase node. Built-in decks: **Main**, **Files**, **Tools**.
- **Agent data card ("card"):** one titled unit of detail content in a deck. It has either a *stable id* (`context`, `reply`, `summary`, `llm-calls`) or a *dynamic id* (a file page).
- **Deck panel:** one detail region that shows one deck. There are 1–2 of them; one is **focused**.
- **Deck layout:** `single`, `left-right` or `top-bottom`.
- **Spread / paged:** how a deck panel renders a multi-card deck. Spread shows all cards on one scrollable page with card rules; paged shows one card at a time.
- **Node panel:** the Agents tab's left column of sase nodes. It can be expanded or collapsed.

### 5.2 Model: separate deck sources from deck views

Today each panel widget is both the data model and the view. That is why zoom had to subclass them, and why a second panel is impossible. Split the two:

```python
# decks/_model.py  (presentation layer; lives in sase, not sase-core; see §5.16)
@dataclass(frozen=True)
class CardDocument:
    card_id: str               # "context" | "reply" | "summary" | "llm-calls" | file page id
    title: str                 # "Context" | "Reply" | "Output" | "LLM Calls" | "src/foo.py" …
    renderables: tuple[Any, ...]
    digest: str                # blake2b of renderables (reuse util/renderable_digest.py)
    solo: bool = False         # images/videos
    lower_bound_rows: Callable[[int], int] | None = None  # cheap estimate at width

@dataclass(frozen=True)
class DeckDocument:
    deck_id: Literal["main", "files", "tools"]
    subject_identity: object   # node identity + attempt number
    cards: tuple[CardDocument, ...]
    default_card_id: str
```

- **Main source.** Refactor the prompt-panel builder (`widgets/prompt_panel/_agent_display_render.py` and friends) so it *returns* a card-partitioned document instead of calling `self.update(Group(...))`.
  - The boundary already exists in code: every branch builds `reply_header` and then appends the reply (`:441-603`).
  - Tag each card's first line with a hidden `sase_deck_card=<id>` style, the same trick as `sase_prompt_panel_section`. The existing `SectionTrackingVisual` then publishes **card anchors** alongside section anchors.
  - One document feeds every panel showing Main, so a duplicate Main (A5) costs nothing to build.
- **Files source.** Lift `_file_list` / `_desired_file_list` / page contents out of `AgentFilePanel` into a per-selection `FilesDeckSource`. It holds the ordered page ids, labels and cached contents. Keep the `AnchorStore` keyed by `(agent, page id)`.
- **Tools source.** Lift the worker and cache out of `AgentLLMCallsPanel`, and **add a subject-identity check on worker completion** (fixes the §1.5 bug).
- **Lazy loading.** A source loads content only while a deck panel shows its deck. Availability for tab-strip badges ("files ● 5", "llm calls ●") comes from cheap probes:
  - `agent_commit_diffs` does no I/O.
  - The linked-delta cache read does no I/O.
  - The llm-calls cache comes from `build_cached_slow_tool_sources`.

  This removes today's "hidden panels are still populated" cost.

### 5.3 The Main deck

- **Card assignment.** Per §1.3 and adjustments A6–A8.
- **Default card.** `context`.
- **Active-card memory.** A *stable* card id sticks across selection changes in paged mode: if you were reading Reply, j/k keep you on Reply, which suits comparing replies across agents. It falls back to the default when the new node has no such card.
- **Duplicate Main.** A second panel showing Main defaults to `reply` if the first panel is on `context`, and the reverse.
- **Folds, hints and search** operate on the whole Main document, so hint numbers stay stable in both spread and paged modes.
- **Section stops.** `Ctrl+J/K` walk the section anchors of the *visible* cards: all of them in spread mode, the active card in paged mode.

### 5.4 The Files deck

- **Cards.** One card per current page, in the existing `_desired_file_list` order. The title is the existing `source_label_for_slot` label (`diff`, `repo shortsha`, `▣ repo`, basename).
- **Spread mode.** Only for decks under the threshold, so the content is small by definition. Render all file cards into **one** `Static` `Group` separated by titled card rules. The same anchor mechanism gives scroll-spy, and no N-widget mount churn happens.
- **Paged mode.** Renders one page, exactly like today's panel.
- **Solo cards (A17).** When an image or video is present, the Files deck is always paged.
- **Reconciling cards.** Reconciliation keeps the current card by id (as `_reconcile_file_list` does today) and never jumps the viewport. The zoom modal froze its file list because refresh jumping was a real complaint, so the deck panel must reconcile without moving: new pages appear in the tab strip and the active card stays put.

### 5.5 The Tools deck

- **Now:** one card, **LLM Calls**, carrying today's timeline and detail levels unchanged. `l`/`h`/`L`/`H` change the detail level when the focused panel shows the Tools deck.
- **Later:** a **Tool Runs** card that calls `tool_run_list({"agent": …})` from a worker, plus `reconcile_unsettled_tool_runs()` without reaping, the same way `src/sase/tool/query.py:67-105` does. It must keep the glossary distinction: an LLM Calls row is not a ToolRun.

### 5.6 Deck panels, layouts, focus, ratio

- **Composition.** `AgentDetail` becomes: `AgentHeaderPanel`, then `DeckArea`, then `AgentJumpPanel`.
- **DeckArea.**
  - It **pre-composes both `DeckPanel`s** and keeps the second hidden, so switching layouts never mounts or unmounts widgets.
  - The layout is a CSS class on `DeckArea`: `-single`, `-left-right` (Textual `layout: horizontal`) or `-top-bottom` (`layout: vertical`).
  - The ratio uses classes as well: `-ratio-30|50|70` sets `fr` widths or heights.
- **DeckPanel.**
  - A bordered frame. Its `border_title` is the **deck-and-card tab strip**: `MAIN ▸ Context · Reply`. It is built with `PanelTabStrip`'s tier logic (full → compact → micro, `widgets/panel_tab_strip.py`), which already handles narrow widths and click ranges.
  - With many cards the title shows `FILES ‹ 3/27 › src/foo.py`.
  - The `border_subtitle` shows mode and position (`spread` or `2/3`) and the file line count (today's `N lines` / `1-V of T lines (E: editor)`).
  - Inside is one `VerticalScroll`. Card views look up their scroll container **through their ancestor**, never an app-wide ID.
- **Focus.**
  - It is logical: `DeckArea.focused_index`.
  - The focused panel gets an accent border; the unfocused one gets a dim border. In the `single` layout there is no focus styling.
  - Clicking a panel focuses it, and clicking a card tab activates that card (`PanelTabStrip.TabClicked`).
- **Layout transitions (your rules, made precise):**
  - From single, `\` → top-bottom and `|` → left-right. The new second panel (placed after the current one) gets the next deck in `main → files → tools` order that isn't shown and has content, falling back to the current deck (A5). Focus stays on the original panel.
  - Pressing the same layout key again returns to single, **keeping the focused panel's deck**.
  - Pressing the opposite key switches orientation and keeps both decks and focus.

### 5.7 Spread vs paged: the algorithm

The decision is made per deck panel from three inputs: the deck, the panel's content-region height `H` and width `W`, and the previous mode.

```python
def decide_mode(doc: DeckDocument, H: int, W: int, prev: Mode | None) -> Mode:
    if len(doc.cards) <= 1:
        return SPREAD                    # trivial; no strip navigation needed
    if any(c.solo for c in doc.cards):
        return PAGED
    budget = cfg.spread_max_screens * H  # 0 ⇒ always paged
    limit = budget * (1.15 if prev is SPREAD else 0.85 if prev is PAGED else 1.0)
    # 1) cheap lower bounds settle the big cases with zero rendering
    total = 0
    for c in doc.cards:
        total += c.lower_bound_rows(W)   # logical lines, or ceil(bytes / W) for unread files
        if total > limit:
            return PAGED
    # 2) everything is small ⇒ exact measurement is cheap; cache by (digest, W)
    exact = sum(measure_rows(c, W) for c in doc.cards)
    return SPREAD if exact <= limit else PAGED
```

- **When the decision runs:**
  - on the **debounced** full detail update (`DetailPanelDebouncer`, 150 ms), never on the immediate header paint during j/k
  - on a layout, ratio, header or jump-panel toggle
  - on a debounced resize
  - when a same-selection content update crosses the hysteresis band
- **Keep the reading position on a same-selection flip.** Spread → paged makes the card at the viewport top active, at the same offset. Paged → spread scrolls to the active card's anchor. Changing the selection uses the deck's default card or the sticky card (§5.3).
- **Measurement.** Measure a card by rendering its `Group` at width `W` with the app console. Only cards already known to be small reach step 2. For the spread Main deck this render is the same pass `SectionTrackingVisual` already does and caches (LRU 8 keyed by `(digest, width)`, `widgets/prompt_panel/_section_navigation.py:76-112`), so the card heights come from the card anchors at no extra cost.
- **Files lower bound:** `ceil(stat.st_size / W)` for unread pages, computed off-thread with the file list and cached by `(path, mtime, size)`. It is conservative for ASCII diffs, which is the case that matters.

### 5.8 Visuals

**Single layout, Main deck, spread.** Card rules are one row each, with no nested boxes:

```
╭─ MAIN ▸ Context · Reply ─────────────────────────────────────── spread ─╮
│ ❖ SASE CONTEXT · 4 lanes                                                │
│   ▸ PLAN · epic sase-172 · phase 2/6                                    │
│ SLOW TOOL CALLS · ≥20s · 2 calls                                        │
│ AGENT PROMPT                                                            │
│   Fix the flaky test in …                                               │
│━━ Reply ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│ AGENT CHAT                                                              │
│   Done. The flake came from …                                           │
╰────────────────────────────────────────────────── ^N/^P card · ] deck ──╯
```

**Left-right layout, node panel collapsed, Main | Files, left panel focused (gold border):**

```
 nodes 12/47 · ctrl+s   filter: …   group: by project
┃ ● sase-172.2 · opus · ✓ done 4m                                      (header, spans both)
╭─ MAIN ▸ Context · [Reply] ─── 2/2 ─╮╭─ FILES ‹ 2/5 › src/foo.py ───── 212 lines ─╮
│ AGENT CHAT                         ││ @@ -10,7 +10,9 @@                          │
│   Done. The flake came from …      ││ -    await asyncio.sleep(0)                │
│                                    ││ +    await pilot.pause()                   │
╰────────────────────────────────────╯╰────────────────────────────────────────────╯
 0 family · 1 neighbor · …                                          (jump panel, spans both)
```

- **Card rules:** give each card view a top-only border (`border-top: heavy <card accent>`) carrying `border_title`. Textual supports per-edge borders, so the separation costs one row and no columns. Accents: Context gold, Reply green (the current reply accent), Output teal, LLM Calls `#87D7FF` (the current indicator color).

### 5.9 Collapsing the node panel (`Ctrl+S`)

**Goals when collapsed.** The user should still:

- know the panel is collapsed and how to restore it
- stay oriented while j/k keep moving through the hidden list
- notice fleet-status changes

**Recommended, in two layers:**

1. **MVP.** Toggle a `-nodes-collapsed` class on `#agents-content`. The rule `#agent-list-container { display: none }` hides the list; the widget stays mounted, so selection, folds and incremental row patching keep running. This is the same mechanism onboarding and the artifact viewer already use. Selection and orientation come from three places:
   - **The identity header**, which already updates on the immediate j/k paint.
   - **An info-row chip `nodes 12/47 · ctrl+s`** in the slot freed by the `view: … (p)` hint (`widgets/agent_info_panel.py:471-479`). Its hover or expanded form can show the previous/next node names.
   - **The jump panel.** Its numbered relation targets keep working as a navigation surface while the list is hidden.
2. **Follow-up: a 2-column node rail**, a minimap. Each cell is one visible list row, compressed when the list has more rows than the rail has height. Cells are colored by status: running, done, failed, unread dot. The selected row is marked `▶`, and clicking a cell selects that row. It reads the AgentList's in-memory row model, so it needs no I/O, and it should be rebuilt only when rows change (perf rule 6). It gives spatial position and fleet awareness for 2 columns.

**Rejected:**

- A narrow "compact list" (16–20 columns of glyph and truncated name): a second render path for the most performance-sensitive widget, still costing 20 columns.
- Auto-peeking the list on j/k: flicker, and it defeats the purpose.

**Interactions:**

- Actions whose only visible effect is on the list's structure auto-expand the node panel before they run:
  - `J`/`K` tribe-panel focus
  - list folds
  - `=` isolate
  - `-` collapse folds
  - filter edits
- `Z` (A10) = collapse the node panel + `single` layout. It saves the previous state and restores it on the next `Z`.
- Optional: if a left-right layout leaves either deck under about 60 columns, show a one-time toast suggesting `Ctrl+S`. Don't auto-collapse, because that is surprising.

### 5.10 Keymap (recommended defaults)

| Key (Textual name) | Action id (new) | Scope | Notes |
|---|---|---|---|
| `ctrl+n` / `ctrl+p` | `next_deck_card` / `prev_deck_card` | Agents | Replaces `next_agent_file`/`prev_agent_file`. Add `next_agent_file`/`prev_agent_file` → new ids to `LEGACY_APP_KEY_ALIASES` (`keymaps/registry.py:62`) so existing user overrides migrate. Services currently reuses this same action to step through chop runs. Either keep that Services branch inside the renamed action, or split out a Services action and register the pair in `_CONTEXTUAL_APP_DUPLICATES`. |
| `right_square_bracket` / `left_square_bracket` | `next_deck` / `prev_deck` | Agents | Shares the key with Artifacts subtab cycling; add the pair to `_CONTEXTUAL_APP_DUPLICATES`. |
| `backslash` | `toggle_deck_layout_top_bottom` | Agents | Needs the `_KEY_DISPLAY` fix for user overrides. |
| `vertical_line` | `toggle_deck_layout_left_right` | Agents | Same. |
| `right_curly_bracket` / `left_curly_bracket` | `cycle_deck_split_ratio` / `…_reverse` | Agents | Contextual duplicate with Artifacts' split. |
| `ctrl+f` / `ctrl+b` | `focus_next_deck_panel` / `focus_prev_deck_panel` | Agents | Replaces `scroll_prompt_down/up` on Agents. Services and Artifacts keep scrolling through contextual duplicates. |
| `ctrl+s` | `toggle_node_panel` | Agents | |
| `Z` | `maximize_deck` | Agents | Replaces `zoom_panel`. |
| `ctrl+shift+n` / `ctrl+shift+p` | *(optional)* aliases for the card actions | Agents | Ship them as comma-alternates only after verifying delivery (§8, Q1). |
| `p` | *(unbound)* | – | `choose_agent_view` retired → add it to the retired ids in `keymaps/registry.py:33-59`. |

**Every new action needs** (per `keymaps/` conventions):

- an `AppKeymaps` field and a `_BINDING_META` entry
- a default in `default_config.yml` (and don't forget the default keymap config, per the core gotcha)
- a `check_app_action` gate
- a command-palette spec in `commands/_app_metadata_*.py` (`tests/test_command_catalog.py:45` enforces this)
- a help-modal row (`modals/help_modal/agents_bindings.py`)
- a footer entry (`widgets/_keybinding_bindings_agents.py`)

**Don't reuse retired ids** such as `toggle_layout` and `cycle_files_subtab`: their user overrides are silently dropped.

**If you keep your original mapping** (`Ctrl+N/P` = decks, `Ctrl+Shift+N/P` = cards), it is a 4-line defaults change. But first:

- In tmux: `set -s extended-keys always`, `set -s extended-keys-format csi-u`, `set -as terminal-features 'xterm-kitty:extkeys'`.
- In kitty: `map kitty_mod+n no_op` and `map kitty_mod+p no_op` (`no_op` should pass the key through; unverified, see Q1).
- Then confirm with `textual keys` inside tmux, from every terminal you attach from, including the Mac.

### 5.11 Existing actions to retarget

| Action | Today's target | New target |
|---|---|---|
| `Ctrl+D/U` `scroll_detail_*` | `effective_detail_scroll_id()` (LLM → File → search → metadata) | focused deck panel's scroll |
| `g` / `G`, bottom pin | metadata | focused panel; the pin follows the Reply card (spread) or the active card (paged) |
| `Ctrl+J/K` section stops | metadata | visible cards of the focused panel (Main only) |
| `z…` folds (`za`/`zA` = section at viewport top) | metadata | focused panel when it shows Main; no-op otherwise |
| `,/` search, `n`/`N` | metadata, frozen overlay | active card, or all cards in spread mode, of the focused panel. Reuse `modals/zoom_panel_search.py` over the card's text. |
| `E` editor, `y` copy, `V` pager | visible secondary, else metadata | active card of the focused panel (Files: real path; LLM Calls: markdown; Main card: card text) |
| `v` hints | metadata document | Main document; hint numbering spans cards |
| `l`/`h`/`L`/`H` | LLM detail when LLM Calls is visible | LLM detail when the focused panel shows Tools; otherwise folds, as today |
| `D` attempt view, `d` header, `.` jump panel | unchanged | unchanged (the header and jump panel are shared chrome) |
| clipboard `#agent-file-panel` queries (`actions/clipboard/_agents.py:141`) | fixed ID | focused panel's Files card view |

### 5.12 Config

Add to `src/sase/default_config.yml` under `ace:` and to `src/sase/config/sase.schema.json`:

```yaml
  decks:
    # Show every card of a multi-card deck on one scrollable page ("spread")
    # when their combined rendered height fits within this many deck-panel
    # heights; otherwise show one card per page ("paged"). 0 always pages.
    spread_max_screens: 1.0
```

- **One field on purpose.** Hysteresis (±15%) is an internal constant, not a knob.
- **No `default_layout` field.** Persistence (A14) covers it.
- **Don't add a per-deck override.** Add one only if a real complaint shows up, per `corpus-before-mechanism`.

### 5.13 Persistence

`~/.sase/ace_agents_deck_state.json` sits next to `ace_agents_fold_state.json` and holds:

- `{layout, ratio, panels: [{deck_id, stable_card_id}], focused, nodes_collapsed}`

Rules:

- Write it off-thread on change, debounced.
- Read it once at startup, before first paint. It is tiny.
- Unknown deck ids fall back to `main`.

### 5.14 Performance rules applied (from `tui_perf.md`)

- **Debounce detail, never highlight.** Deck content and mode decisions run on the debounced update; j/k paint only the header immediately (rules 7 and 13).
- **Load only visible decks.** Availability badges come from no-I/O probes, which removes the hidden-panel population cost (§1.5).
- **No remounts.** Both deck panels are pre-composed; layout and ratio are CSS classes.
- **Measure only small content,** cached by `(digest, width)`; lower bounds settle the rest (rules 6 and 8).
- **Keep the stale-result guards.** Each source's worker checks subject identity on completion, and `_agent_detail_generation` keeps gating Main.
- **Keep persistence writes off the pump.**
- **Verify perf:** `SASE_TUI_PERF=1` j/k p95 < 16 ms on the Agents tab in single and split layouts; `pytest -s -m slow tests/ace/tui/bench_tui_jk.py` before and after.

### 5.15 Removals and what survives

- **Delete:**
  - `modals/agent_view_modal.py`, `actions/agents/_agent_view_picker.py`, `DetailPanelMode`, `DetailLayoutMode`, `DETAIL_LAYOUT_CYCLE`, and the `view:` chip plus its `_VIEW_MODE_STYLES` (already stale: its keys are `tools`/`summary`).
  - The `modals/zoom_panel_*.py` modal, widgets, content, navigation, rendering and events, the zoom seed code in `actions/agents/_panel_detail.py:167-333`, and the zoom TCSS.
  - Their tests: about 2,350 LOC zoom and about 5 picker files. They are replaced by deck tests (§7).
- **Salvage:**
  - `zoom_panel_search.py`, as card search.
  - The file rail idea, now the card tab strip.
  - "Frozen list ⇒ no jumping", now a reconcile rule (§5.4).
- **Fix stale text:**
  - `default_config.yml:710-711` ("Z zooms … or isolates/restores").
  - The `agent_detail.py` docstrings ("two-panel layout").
  - `docs/ace.md` zoom and view-picker sections.

### 5.16 Rust core boundary check

Deck and card composition, spread/paged mode, focus, layout, keymaps and persistence are **presentation-only Textual state**. The card *content* comes from Python builders that already live in this repo (the metadata document is built in `widgets/prompt_panel/`, not in `sase_core`). Applying the litmus test in `rust_core_backend_boundary`:

- A web or mobile frontend would not need to match *how the TUI paginates*.
- It *might* someday want the same card catalog (which cards a node has, and their order).

Only if that frontend materializes should `(deck_id, card_id, title, order)` move into a small sase-core wire. **No sase-core change is needed now.**

### 5.17 Glossary strands (draft text)

Per `/sase_memory_write`, your prompt authorizes adding these strands when an approved plan implements them. Keep each short, since they're read on demand.

- **`glossary:agent-data-deck`** (aka deck, agent data decks)
  > An agent data deck is a named, ordered set of agent data cards about the selected sase node, shown in an Agents-tab deck panel. Built-in decks are **Main** (Context and Reply cards; a clan or tribe has one Summary card), **Files** (one card per file page: commit diffs, the live diff, linked-repo diffs, attached files) and **Tools** (the [[glossary:llm-calls]] card). A deck is presentation only; it owns no agent data.
- **`glossary:agent-data-card`** (aka card, agent data cards)
  > An agent data card is one titled unit of detail in an agent data deck. Cards with stable ids (`context`, `reply`, `summary`, `llm-calls`) keep their place across selections; file-page cards are per node. A deck panel shows a multi-card deck **spread** (every card on one scrollable page, separated by card rules) when the cards fit within `ace.decks.spread_max_screens` panel heights, and **paged** (one card at a time) otherwise; `Ctrl+N`/`Ctrl+P` move between cards in either mode.
- **`glossary:deck-panel`**
  > A deck panel is one Agents-tab detail region showing one agent data deck. The Agents tab shows one or two, in a `single`, `left-right` (`|`) or `top-bottom` (`\`) deck layout; `Ctrl+F`/`Ctrl+B` move the logical focus that actions target, and `]`/`[` change the focused panel's deck. The identity header and jump panel span every deck panel and belong to none.
- **`glossary:node-panel`**
  > The node panel is the Agents tab's left column of [[glossary:sase-node]] rows. `Ctrl+S` collapses it without unmounting it, so j/k still move the selection; a collapsed node panel is represented by the info-row position chip.

**Edits to existing strands:**

- `glossary:llm-calls`: "the Agents detail and zoom view" → "the LLM Calls card of the Tools deck".
- `glossary:tool-run`: "not the Agents-tab LLM Calls view" → "not the LLM Calls card".
- `glossary:agent-relation-jump-target`: "the sticky footer below the Agents detail panels" → "…below the deck panels".

---

## 6. Implementation plan (6-phase epic)

A **`beta` feature flag** (`sase flag new agents_decks`) scaffolds the epic. Phases 2–5 land behind it, so the old UI stays the default until phase 6, and the epic deletes the flag in phase 6, per `sase_flags.md` epic-scaffolding rules. No `sunset` flag is proposed for `p` and `Z`: you asked for their removal, and a one-time notice (precedent: `_keymap_unification_notice.py`) covers muscle memory.

| Phase | Scope | Main files |
|---|---|---|
| **1. Decouple (no UX change)** | Card-partitioned Main document (builder returns `DeckDocument`; the panel still renders all cards). File/LLM sources lifted out of widgets. `_get_scroll_container` via ancestor. LLM Calls identity fix. Traceback moved to the reply part (A7). `_KEY_DISPLAY` gains `backslash`/`vertical_line`. | `widgets/prompt_panel/_agent_display_render.py`, `_agent_display_family_render.py`, `_agent_display_step_render.py`, `widgets/file_panel/*`, `widgets/llm_calls_panel.py`, `keymaps/key_validation.py` |
| **2. Deck panel, single layout (flagged)** | `decks/` package (model, registry, sources). `DeckPanel` with a tab-strip border title; paged mode only. `Ctrl+N/P` cards, `]`/`[` decks. Empty-state cards (A12). Lazy loading. | new `widgets/decks/`, `widgets/agent_detail.py`, `styles.tcss`, `keymaps/*`, `default_config.yml`, commands metadata, help, footer |
| **3. Splits and focus** | `\` / `\|` / `{` / `}` / `Ctrl+F` / `Ctrl+B`; `DeckArea` layout classes; duplicate-deck rules (A5); retarget every action in §5.11. | `actions/navigation/_basic.py`, `actions/navigation/_fold.py`, `actions/agents/_metadata_search.py`, `actions/agents/_panel_detail.py`, `actions/clipboard/_agents.py`, `_app_action_availability.py` |
| **4. Node panel** | `Ctrl+S` collapse, info-row chip, auto-expand for list-structure actions, `Z` = maximize deck. | `_app_layout.py`, `styles.tcss`, `widgets/agent_info_panel.py`, `actions/agents/*` |
| **5. Spread mode** | Card anchors, lower bounds, exact measurement cache, hysteresis, reading-position preservation, scroll-spy tab strip. `ace.decks.spread_max_screens` in config and schema. Solo cards. | `widgets/decks/_mode.py`, `widgets/prompt_panel/_section_navigation.py`, `default_config.yml`, `src/sase/config/sase.schema.json` |
| **6. Cut-over and cleanup** | Remove `p` picker, zoom modal and old enums/IDs. Persistence (A14). Docs (`docs/ace.md`). Glossary strands (§5.17). One-time keymap notice. Visual goldens (`just fix-tui-screenshots`). Delete the flag. | as §5.15 |

Phase 5 can be dropped or deferred without hurting the rest: paged-only decks are already a complete, coherent design. That makes it a natural cut point if the epic runs long.

---

## 7. Testing strategy

- **Pure model tests:**
  - `decide_mode`: boundaries, hysteresis on both sides, solo cards, `spread_max_screens: 0`.
  - Deck availability.
  - Layout state-machine transitions (single ↔ left-right ↔ top-bottom with focus and deck retention; the duplicate-deck default card).
- **Builder tests.** Every node kind yields the §1.3 card partition. The traceback lands in `reply`. Card ids are stable.
- **Pilot tests (Textual `run_test`):**
  - j/k across agents with and without files keeps geometry stable (A12).
  - `Ctrl+N` in spread mode scrolls the next card's rule to the top; in paged mode it swaps the page.
  - A streaming reply that crosses the threshold keeps the reading position.
  - `Ctrl+S` hides the list and j/k still change the selection and header.
  - `Z` round-trips.
  - An LLM Calls stale worker for agent A never paints on agent B.
- **Keymap tests:**
  - Contextual duplicates resolve per tab (Agents `]` vs Artifacts `]`; Agents `Ctrl+F` vs Services `Ctrl+F`).
  - The legacy alias `next_agent_file` → `next_deck_card` migrates user overrides.
  - A `backslash` user override is accepted.
- **Visual goldens:** single/spread, single/paged, left-right, top-bottom, collapsed node panel, empty-state card, narrow-width tab-strip tiers.
- **Perf:** j/k p95 bench in single and left-right layouts, before and after.
- **Flag:** both states tested while the flag exists, per `sase_flags.md`.

---

## 8. Open questions for you

1. **Q1: Which terminal(s) do you attach from, and do you want extended keys?** If Ctrl+Shift chords work end to end (tmux `extended-keys always`, kitty `no_op` unmaps, and a check with `textual keys`), you could keep your original mapping. I still recommend `Ctrl+N/P` for cards on frequency grounds.
2. **Q2: Sticky Reply across j/k?** In paged mode, should moving to another agent keep you on Reply (my recommendation), or always reset to Context?
3. **Q3: Should the threshold be `1.0` screens?** At `1.0`, spread means nothing to scroll. Choose `1.5`–`2.0` if you'd rather see small multi-card decks spread even when they scroll a little.
4. **Q4: Empty decks (A12).** Stable geometry with an empty-state card, or today's collapse-to-fill behavior?
5. **Q5: Does SLOW TOOL CALLS stay in Context?** I kept it there as a triage digest, per your request. Its natural long-form home is the Tools deck, and `]` now reaches it.

---

## 9. Recommended solution

Build **agent data decks and cards** as a presentation-layer redesign of the Agents detail area. It is a 6-phase epic behind a `beta` flag that the epic removes, with no sase-core changes.

1. **Model.** Use three built-in decks:
   - **Main:** `context` + `reply` for agent-like nodes. Proc, monitor, gate and step nodes get `context` + `reply` titled "Output". Clans and tribes get one `summary` card.
   - **Files:** one card per existing file page.
   - **Tools:** the **LLM Calls** card now; a **Tool Runs** card later.

   Card ids are stable where possible. The identity header and the jump panel stay outside decks as shared chrome.
2. **Architecture.** Separate deck *sources* from deck *views*:
   - The prompt-panel builder returns a card-partitioned document, and one document feeds any panel that shows Main.
   - File and LLM data move out of their widgets into per-selection sources.
   - Scroll containers are resolved through the ancestor, never a global ID.
   - Only visible decks load content.
3. **Layout.**
   - Up to **two** pre-composed deck panels in a `single`, `left-right` (`|`) or `top-bottom` (`\`) layout, following your toggle and switch rules.
   - Split ratio 30/50/70 on `{`/`}`.
   - Logical focus on `Ctrl+F`/`Ctrl+B`.
   - Duplicate decks are allowed (Context | Reply).
   - Geometry stays stable when a deck is empty.
   - Everything is persisted across restarts.
4. **Rendering.**
   - Each deck panel shows its deck **spread** when all cards fit within `ace.decks.spread_max_screens` (default `1.0`) panel heights, else **paged**.
   - The decision uses cheap lower bounds first and exact measurement only for small content, with ±15% hysteresis. A same-selection flip keeps the card you were reading.
   - A tab strip in the border title always shows the deck, its cards and your position.
   - `Ctrl+N/P` means "next/previous card" in both modes.
5. **Keys:**
   - `Ctrl+N/P` cards; `]`/`[` decks; `\` and `|` layouts; `{`/`}` ratio
   - `Ctrl+F`/`Ctrl+B` focus
   - `Ctrl+S` collapse the node panel; `Z` maximize the focused deck
   - `p` retired
   - Fix `\`/`|` user-override validation.
   - `Ctrl+Shift+N/P` only as optional aliases once terminal delivery is verified.
6. **Node panel.** Collapse by hiding it (it stays mounted, so j/k keep working). Show a `nodes i/n · ctrl+s` chip in the info-row slot freed by the `p` hint. A 2-column status rail is a follow-up.
7. **Removals.** Delete the `p` picker and the zoom modal, together with their mode enums and tests. Salvage zoom's search as generic card search.
8. **Vocabulary.** Add glossary strands for agent data deck, agent data card, deck panel and node panel. Update the LLM Calls, Tool Run and Agent Relation Jump Target strands.
9. **Independent fix to land first:** the LLM Calls panel paints a previous agent's calls onto a newly selected agent when a fetch is still in flight (§1.5).
