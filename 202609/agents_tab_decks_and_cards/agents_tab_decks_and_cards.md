# Agent Data Decks & Cards: Consolidated Research on Redesigning the Agents-Tab Detail Area

- **Role:** lead researcher; this report merges the three swarm reports with my own verification
- **Date:** 2026-09-23
- **Repo state:** `sase` master @ `28b3c1bab`. The cld report used `4b9da7a33`, 5 commits earlier, and none of those commits touch the Agents detail area.
- **Inputs:** [cld](agents_tab_decks_and_cards__cld.md), [mus](agents_tab_decks_and_cards__mus.md), [gem](agents_tab_decks_and_cards__gem.md)
- **Question:** Should the Agents tab's agent metadata panel and the Files / LLM Calls panels become one **deck panel** type that hosts **agent data cards**? If so, how should it be built, and what should change in the proposed requirements?

Paths are relative to `src/sase/ace/tui/` unless marked otherwise. Each finding marked **✔ verified** was re-checked against the code or the live environment for this report (see Appendix A).

---

## 0. Verdict and TL;DR

**Build it.** All three researchers agree, and so do I. This is a real simplification, not a rename:

- Three widgets become one panel type.
- Two layout enums (`DetailPanelMode`, `DetailLayoutMode`) disappear.
- Two modals disappear: the `p` view picker (813 LOC) and the `Z` zoom modal (1,627 LOC of production code, plus about 2,350 LOC of tests).
- File paging, the picker's layouts and the zoom modal all become special cases of one model: a deck of cards in a deck panel.
- It enables views the TUI cannot show today: **the reply next to the diff**, and **the prompt next to the reply**.

It is presentation-only Textual state, so under the Rust core boundary it stays in this repo: **no `sase-core` change is needed**.

The plan needs adjustments. These are the ones that matter most; the full list is in §4.

1. **Swap the card and deck keys.** Use **`Ctrl+N/P` to cycle cards** and **`]`/`[` to cycle decks**.
   - `Ctrl+Shift+N/P` does not reach the app on your terminal chain (✔ verified): kitty on the client, then SSH, then tmux 3.5a with `extended-keys off`.
   - kitty's defaults consume `Ctrl+Shift+N` (new OS window) and `Ctrl+Shift+P` (hints prefix). Even if they were passed through, tmux would collapse `Ctrl+Shift+N` into `Ctrl+N`, which your mapping assigns to *deck* cycling. The key would do the wrong thing, not nothing.
   - Cycling cards is also the frequent action. Files cards *are* files, so the swap keeps today's `Ctrl+N/P` file-cycling muscle memory.
2. **"Next card" means the same thing in both render modes.** Showing all cards on one page (**spread**) versus one per page (**paged**) is a rendering detail. `Ctrl+N` always brings the next card to the top, and a card tab strip always shows where you are.
3. **Measure the threshold in panel heights ("screens"), not lines.** Use hysteresis and a one-way rule while the same node stays selected.
   - Your median Main deck sits right at any sensible threshold (§2.6), so without these safeguards a streaming reply would flip the layout under the reader.
   - I recommend a default of **1.5 screens**.
4. **Collapse the node panel by hiding it (`display: none`), not by building a micro-rail.**
   - j/k keep working because they are app-level actions over the app's row model (✔ verified). gem's claim that hiding the list breaks j/k is wrong.
   - Show a `nodes 12/47 · ^S` chip in the info-row slot that the removed `view: … (p)` chip frees up.
   - A status rail can come later if it turns out to be needed.
5. **Rebind `Z` rather than just removing it.** `Z` becomes "maximize the focused deck": collapse the node panel and switch to a single layout. Press it again to restore. Retire `p` as proposed.
6. **The identity header and the numbered jump panel stay outside decks** as shared chrome. They describe the *selection*, not a deck.
7. **Land a real bug fix first, independently.** The LLM Calls panel can paint agent A's calls onto agent B (✔ verified, §2.4).

---

## 1. How the three reports compare

### 1.1 Where they agree

- The unification is right, and removing the `p` picker and the zoom modal is right in steady state.
- Cap the design at **two deck panels** and one orientation at a time. No arbitrary tiling in v1.
- The automatic spread/paged switch needs **hysteresis**, and switching must not jump the reader's position.
- `Ctrl+F` currently collides with `scroll_prompt_down`, and `Ctrl+Shift+N/P` is risky in terminals.
- Collapsing the node panel is load-bearing for left-right splits, not decoration.
- It is presentation-only, with no Rust core work.

### 1.2 Where they disagree, and my resolution

| Topic | cld | mus | gem | Resolution and evidence |
|---|---|---|---|---|
| Card and deck keys | `Ctrl+N/P` cards, `]`/`[` decks | Keep your mapping after a key audit | Keep your mapping, plus `]`/`[` as a card alias | **cld.** I verified your terminal chain: tmux `extended-keys off`, the client is `xterm-kitty` over `sshd-session`, and client features lack `extkeys`. gem's alias puts `Ctrl+N` (old file cycling) on decks, so muscle memory hits the wrong action. |
| `Ctrl+S` for collapse | Free at app level | Might misfire with gate `submit_branch`; XOFF risk | Fine | **Free.** `submit_branch: "ctrl+s"` sits in the `ace.keymaps.gate` modal scope. Every other `ctrl+s` is modal-local or `TextArea`-local. Textual clears `IXON`, so XOFF never fires. |
| Deck-focus key | `Ctrl+F`, with `Ctrl+B` as reverse | Keep scrolling on `Ctrl+F`; use another key | `Ctrl+F` plus `Tab` alias | **`Ctrl+F` as you asked.** On Agents, `Ctrl+F/B` only half-page scroll the *metadata* panel while another panel is visible. Once `Ctrl+D/U` scroll the focused deck, that pair is redundant. **`Tab` is not free:** it is the app-level `next_tab`. |
| Threshold unit and default | Panel heights, 1.0 | Rendered lines, 200–300 | Logical lines, 80 | **Panel heights, default 1.5** (§5.5). Your wording is panel-relative, and a line count behaves differently in a 60-row single panel and a 28-row top/bottom panel. |
| Collapsed node panel | `display: none` plus an info-row chip; rail later | 2–4 cell rail | 4-cell micro-rail, "because display:none breaks j/k" | **`display: none` plus chip.** gem's premise is false: `action_next_patch` → `_navigate_agents_panel` walks the app's stop model, not the widget. A rail is a second render path for the most performance-sensitive widget. |
| Textual name for `\|` | `vertical_line` | `vertical_bar` | `pipe` | **`vertical_line`** (Textual 8.0.1, `_character_to_key("\|")`). `backslash` for `\`. |
| Error traceback | Top of the Reply card | Context | Context | **Short ERROR summary in Context; traceback at the top of Reply.** This also fixes a rendering quirk (§2.3). |
| Identity header, family roster, neighbors | Shared chrome outside decks | Inside Context | Inside Context | **Shared chrome.** The header is already `AgentHeaderPanel`, and `FAMILY SHELLS`/`NEIGHBORS` moved to the jump panel in `78f1d71e7` (✔ verified). mus and gem inventoried stale structure. |
| Removing zoom and picker | Delete in the final phase of a beta-flagged epic; `Z` becomes maximize | Keep both until their replacements are proven | Delete | **The flag-gated epic satisfies mus's concern:** the old UI stays the default until cut-over. Then delete, with `Z` becoming maximize. |
| Manual spread/paged override | None | Per-deck override | `0` / `-1` sentinels | **Config `0` means always paged.** No per-deck override until someone asks for one (`corpus-before-mechanism`). |
| Glossary strands | deck, card, deck-panel, node-panel, plus 3 strand edits | deck, card, deck-panel, deck-layout | deck, card, deck-panel | **deck, card, deck-panel, node-panel, plus cld's edits.** Deck layout belongs inside the deck-panel strand (§6). |

---

## 2. What exists today (condensed, verified)

### 2.1 Layout

```
#agents-view
  #agent-info-row    AgentInfoPanel ("Agents: N agents [x running · y queued] … view: <mode> (p) … group: …")
  AgentsFilterBar
  #agents-content (Horizontal)
    #agent-list-container   one AgentList per tribe panel; width content-driven, clamped to 60..130 cells
    #agent-detail-container width 1fr
      AgentDetail (widgets/agent_detail.py:68-85; used only on the Agents tab)
        AgentHeaderPanel        sticky identity header (`d` expands)
        #agent-prompt-scroll    AgentPromptPanel   ← the "metadata panel"
        #agent-search-scroll    frozen metadata search overlay
        #agent-file-scroll      AgentFilePanel     (widgets/file_panel/)
        #agent-llm-calls-scroll AgentLLMCallsPanel (widgets/llm_calls_panel.py)
        AgentJumpPanel          numbered family/neighbor roster footer (`.` expands)
```

- **Metadata is always primary.** At most one secondary panel (File *or* LLM Calls) is shown. `DetailPanelMode` is `AUTO`/`LLM_CALLS`/`INFO`. `DetailLayoutMode` is `METADATA_ONLY`/`METADATA_LARGER` (70/30)/`EQUAL`/`SECONDARY_LARGER` (30/70)/`SECONDARY_ONLY` (`widgets/_agent_detail_panels.py`).
- **The layout is session-local and not persisted** (`docs/ace.md`, "The layout choice is session-local").
- **Hiding the list is a proven path.** `#agent-list-container { display: none }` is already used for onboarding and the artifact-file viewer (`styles.tcss:3725-3731`). The viewer adds an explicit j/k guard (`_guard_agent_navigation_for_artifact_file_viewer`); a plain collapse would not need one.
- **Your live client is 261×79.** A single detail panel is therefore about 55–60 content rows, and a top/bottom panel about 25–28. With the list at 60–130 columns, a left-right split gives about 65–100 columns per deck; with the list collapsed, about 128 each. Collapsing matters most on smaller clients.

### 2.2 The `p` picker and the `Z` zoom modal

- **`p` → `AgentViewModal`** (`modals/agent_view_modal.py` + `actions/agents/_agent_view_picker.py`, 813 LOC).
  - A one-key chooser: `f` shows the File view and `t` shows LLM Calls; `[ 1 = 2 ]` pick the ratio. `toggle_layout` and the other retired actions route into it.
  - It shares `p` with Artifacts' `pick_artifacts_project` through `_CONTEXTUAL_APP_DUPLICATES`.
- **`Z` → `ZoomPanelModal`** (8 `modals/zoom_panel_*.py` files, 1,627 LOC).
  - A near-fullscreen modal. `]`/`[` cycle panels; `Ctrl+N/P` cycle files over a *frozen* file list with a file rail; it has its own search.
  - It has to subclass the File and LLM panels just to override their hard-wired scroll-container IDs.

### 2.3 Metadata panel inventory

The metadata panel is **one `Static` that renders one Rich `Group`**. Section headings carry hidden `sase_prompt_panel_section=<id>` tags. `SectionTrackingVisual` turns those tags into row anchors that drive `Ctrl+J/K` and folds, and it caches its layout by `(digest, width)`. That same anchor machinery can supply card boundaries and card heights almost for free.

Body order for an agent node or agent shell:

| # | Heading as rendered | When shown | Proposed card |
|---|---|---|---|
| – | Identity: name, model, status, timing | detached `AgentHeaderPanel` | **shared chrome** |
| – | `FAMILY SHELLS`, `NEIGHBORS` | jump panel since `78f1d71e7` | **shared chrome** |
| 1 | `❖ QUEUE · N waiting` | queued agents | Context |
| 2 | `MEMBERS · N` | legacy parallel families | Context |
| 3 | `OUTPUT VARIABLES` / `WORKFLOW VARIABLES` | when present | Context |
| 4 | `SASE CONTEXT` lanes: plan, bead, artifacts, memory, glossary, skills, workspaces | when non-empty | Context |
| 5 | `SLOW TOOL CALLS · ≥Ns · N calls` (you called it "SLOW TOOLS") | ≥1 slow call | Context |
| 6 | `ERROR` summary and output path | failed | Context |
| 7 | `AGENT XPROMPT` | raw xprompt exists | Context |
| 8 | `AGENT PROMPT` | always | Context |
| 9 | `AGENT REPLY` / `AGENT CHAT`: phase dividers, follow-up phases, `ATTEMPT k` dividers, "Waiting for agent response…" | always | **Reply** |
| 10 | Error traceback (`Syntax`) | failed | **Reply (moved, see quirk)** |

**Sections you didn't name** that belong in Context: QUEUE, MEMBERS, OUTPUT VARIABLES, WORKFLOW VARIABLES and the ERROR summary.

**Quirk (✔ verified):** the builder produces `renderables = [header_text, error_tb_syntax, prompt_syntax, …]`, and `header_text` already ends with the `AGENT PROMPT` heading (`widgets/prompt_panel/_agent_display_render.py`). So a failed agent's traceback renders *under the AGENT PROMPT heading, above the prompt body*. Splitting into cards is the natural moment to fix this.

**Other node kinds** each branch before this path. Proc shells, monitors, gates, bash/python steps, parallel steps, workflow rows, clans and tribe summaries each need a mapping (§5.3).

### 2.4 The Files and LLM Calls panels

**Files pages** come from `_desired_file_list` (`widgets/file_panel/_file_list.py`), in this order:

1. commit diffs
2. the live diff
3. linked-repo diffs
4. `extra_files`: plans, PDFs converted to markdown, images, videos

`Ctrl+N/P` wraps through the pages and keeps the current page when the list changes. A 64-entry LRU of `(agent, page)` scroll anchors restores your position on a revisited page.

Two couplings have to be fixed before a second view can exist:

- `_get_scroll_container()` does an **app-wide** `query_one("#agent-file-scroll")`, so a second view would bind to the first match.
- `AgentDetail` writes the panel's private fields directly.

**The LLM Calls panel** renders one `Text` timeline at the COMPACT / EXPANDED / FULL detail levels, fetched on a throttled worker through an mtime-keyed cache. `SLOW TOOL CALLS` reads the same cache, so the two are views of one dataset.

**Bug (✔ verified).** `_update_display_impl` returns early when a worker is still running, and `on_worker_state_changed` only checks `event.worker == self._current_worker`, never the agent.

- **Trigger:** select agent A, then agent B while A's fetch is in flight.
- **Result:** B shows its cache, or "loading", and then **A's calls are painted onto B's panel**. They stay there until B's next update.
- **Fix:** the fetch result should carry the subject identity, and completion should drop results that don't match `_current_agent`. The deck refactor (§5.2) fixes this naturally, but it is a standalone bug worth landing first.

**Hidden panels still do work.** The File and LLM Calls panels are populated even when hidden. Decks should load content only for the decks that are actually shown.

### 2.5 Keymap facts (✔ verified in `default_config.yml` and `_app_action_availability.py`)

| Key | Today on Agents | Status for this plan |
|---|---|---|
| `Ctrl+N/P` | `next_agent_file`/`prev_agent_file`. On **Services** the same action steps through chop runs. | Repurpose. Keep the Services branch. |
| `Ctrl+Shift+N/P` | unbound | **Unreliable** (§3, R1) |
| `Ctrl+F`/`Ctrl+B` | Half-page scroll of the *metadata* panel. Full-page scroll on Services. | Repurpose on Agents only |
| `Ctrl+S` | Not an app binding. Used only by modal save/submit, gate modal `submit_branch` and `TextArea` stash. | Free |
| `\` (`backslash`), `\|` (`vertical_line`) | unbound | Free as defaults, but **`is_valid_key` rejects both** (✔). User overrides to them are reverted, and they have no display glyph in `_KEY_DISPLAY`. |
| `]`/`[`, `}`/`{` | Artifacts-only (subtab and split cycling) | Free on Agents; needs a `_CONTEXTUAL_APP_DUPLICATES` pair |
| `Tab` | App-level `next_tab` | **Not available** (gem's alias would break tab switching) |
| `p`, `Z` | `choose_agent_view`, `zoom_panel` | Freed by this plan |
| tmux prefix | `C-a` (prefix2 `M-a`) | `Ctrl+B` does reach the app |

Every new app action needs:

- an `AppKeymaps` field
- a default in `src/sase/default_config.yml` (the core gotcha)
- a `_BINDING_META` entry
- a `check_app_action` gate
- a command-palette spec (enforced by `tests/test_command_catalog.py`)
- a help-modal row (`modals/help_modal/agents_bindings.py`)
- a footer entry

Retired action ids must go on the retired list; never reuse one.

### 2.6 How big is the content? (sizes the threshold)

| Content (Sept 2026 `ace-run` agents) | p10 | p25 | p50 | p75 | p90 | Source |
|---|---|---|---|---|---|---|
| Prompt, source lines | 3 | 5 | **14** | 57 | 323 | mine, n=2,340 (cld: 3/14/55/289) |
| Reply, source lines | 7 | 13 | **27** | 91 | 299 | mine (cld: 9/31/125/481) |
| Prompt + reply, rows wrapped at 120 cols | 27 | 44 | **114** | 340 | 690 | mine |
| Diff pages per agent | 1 | – | **3** | 5 | 7 (max 27) | cld |
| Total diff lines per agent | 82 | – | **693** | 1,517 | 2,310 | cld |

Share of Main decks that fit, estimated as prompt + reply rows plus about 30 rows of context, on a 60-row single panel:

| Threshold | Share of Main decks that spread |
|---|---|
| ≤1 screen (60 rows) | **13%** |
| ≤2 screens | **43%** |
| ≤3 screens | **56%** |

Implications:

- **Main deck.** The median is close to 2 screens. A 1.0-screen threshold would page about 87% of agents; that is a big change from today's single scroll. The decision is close for a large share of agents, and running agents cross it while you watch. Hysteresis is required, not polish.
- **Files deck.** Almost always paged. Spread mode only helps the bottom decile (small fixes).
- **Tools deck.** It has one card, so spread vs paged doesn't apply yet.

---

## 3. Critique

### 3.1 What the plan gets right

1. **It removes an asymmetry, not just a widget.** Today "metadata + one secondary panel" means you cannot read the reply beside the diff. Decks make "Reply | Files" and "Context | Reply" ordinary layouts.
2. **One model replaces four mechanisms:** file paging, the picker, zoom, and the two enums.
3. **The two-level hierarchy is justified by the data.** A flat tab list (Context, Reply, diffs 1…27, LLM Calls) breaks down at 7–27 file pages. Three decks keep the top level short and let one deck grow.
4. **The Tools deck is the right home** for the future `sase tool` card.
5. **Collapsing the node panel is overdue.** The list takes 60–130 columns, and today the only escape is the zoom modal.

### 3.2 Risks, highest impact first

- **R1. `Ctrl+Shift+N/P` fails as a wrong action** on your setup (§0 item 1). It is also a frequency inversion: you set up a deck layout once, but you cycle files on every review.
- **R2. Unpredictable navigation.** If "next" sometimes scrolls and sometimes swaps pages, and Reply is sometimes "below" and sometimes "the next page", keys stop being predictable. **Fix it with a principle:** a deck is an ordered card sequence with an always-visible tab strip, and "next card" always brings the next card's header to the top.
- **R3. Flapping.** Several things change content height or panel height:
  - a streaming reply
  - SASE CONTEXT lanes resolving asynchronously
  - toggling the header (`d`) or the jump panel (`.`)
  - resizing, or switching layouts

  §2.6 puts the median deck on the boundary.
- **R4. Measurement cost.** An exact rendered height requires a Rich render. Doing that for every card on every selection violates the TUI performance rules. There is a sound shortcut: only content *under* the threshold needs exact measurement, and small content is cheap to render. Cheap lower bounds settle every large case (§5.5).
- **R5. Naming collisions.**
  - vim's `:split` stacks top/bottom, tmux `split-window -h` goes side by side, and Textual's `layout: horizontal` is side by side. Your own bullet calls `|` a "horizontal split" while describing side-by-side.
  - "Stacked" would be the wrong word for the all-on-one-page mode, because a stack of cards shows only the top card.
- **R6. Everything that implicitly targets "the metadata panel" or "the visible secondary panel" must be retargeted** to "the focused deck panel's active card":
  - `Ctrl+D/U`, `g`/`G` and the bottom pin
  - `Ctrl+J/K`, `z` folds
  - `,/` search, `E`, `y`, `V`, `v` hints
  - `h/l/H/L` LLM detail

  That is about 216 source references to the hard-wired IDs and enums across 17 source files, plus about 37 test files (✔ counted). **This is the bulk of the work** and deserves its own phase.
- **R7. Removing `p` and `Z` loses things the plan doesn't replace:**
  - the 70/30 and 30/70 ratios
  - zoom's search over any panel
  - zoom's "frozen file list, so nothing jumps" behavior

  Each has a cheap home in the new model (A9, A10, §5.4).
- **R8. Empty decks.** Today the metadata panel expands whenever the secondary panel is empty, which makes the layout jump during j/k. Decks should keep geometry stable instead (A12).
- **R9. Scope creep.** N-way tiling, user-defined decks and per-deck plugins would be mechanism ahead of need. Cap v1 at two panels and three built-in decks. Keep the model a list of panels plus an orientation, so a third panel remains possible later without a redesign.

### 3.3 Alternatives considered

| Alternative | Why not |
|---|---|
| Keep metadata-primary + one secondary; add left-right orientation and list collapse | Cheapest, but still can't show Reply next to Files, and it keeps the picker and both enums. It fixes the symptom, not the model. |
| Flat tabs per panel (no decks) | Breaks down at 7–27 file pages, and the future Tool Runs card crowds it further. |
| Full tmux-style tiling | Speculative; two panels cover every workflow in the request. |
| A vim-style `Ctrl+W s/v/w/o` prefix | Slower than single keys. Possible later as an alias layer. |
| One widget per card for Main (separate builders) | Duplicates the fold, hint, search, bottom-pin and section machinery per card. A card-partitioned single document keeps one builder and one anchor system. |

---

## 4. Requirement adjustments (called out explicitly)

Strength: **S** = strongly recommended, based on verified evidence. **R** = recommended. **O** = optional.

| # | Your requirement | Adjusted to | Why | Strength |
|---|---|---|---|---|
| **A1** | `Ctrl+Shift+N/P` cycles cards | **`Ctrl+N/P` cycles cards.** Add `Ctrl+Shift+N/P` aliases only after the terminal chain is fixed (§5.7). | R1: verified not to reach the app. Cards are the frequent action. File cycling stays on the same key. | S |
| **A2** | `Ctrl+N/P` cycles decks | **`]` / `[` cycle decks** (wrapping main → files → tools). | Free on Agents; it is zoom's existing panel-cycling key. From Main, `[` reaches Tools directly. | S |
| **A3** | All cards on one page if under the threshold, otherwise one per page | Name the modes **spread** and **paged**. `Ctrl+N/P` means "next/previous card" in both. The tab strip is always shown. | R2, R5 | S |
| **A4** | A configurable threshold | **`ace.agent_decks.spread_max_screens`, default `1.5`**, measured in panel heights, with a ±15% hysteresis band. While the same node stays selected, the mode may only go spread → paged, and the card at the viewport top stays active. `0` means always paged. | R3; §2.6 data; split layouts change the panel height | S |
| **A5** | `\`/`\|` open the next deck not currently shown, else the current deck | Keep it, but skip decks with **no content for the selected node** before falling back to the current deck. `]`/`[` may pick a deck already shown in the other panel. A duplicate Main opens on the card the other panel isn't showing, so **Context \| Reply** is one keystroke. | With 3 decks and 1 shown, your fallback would otherwise never trigger. Duplicates are useful. | R |
| **A6** | Context = SASE CONTEXT, SLOW TOOLS, AGENT XPROMPT, AGENT PROMPT, plus anything forgotten | Also QUEUE, MEMBERS, OUTPUT/WORKFLOW VARIABLES and the ERROR summary. **The identity header and jump panel stay outside decks** and span all deck panels. | §2.3 | S |
| **A7** | Reply = AGENT REPLY | Reply = AGENT REPLY/AGENT CHAT **with the error traceback at the top**. | A failure is the run's outcome; this also fixes the traceback quirk. | R |
| **A8** | Main = Context + Reply | Cards depend on node kind (§5.3). Proc, monitor, gate and step nodes title the second card **Output**. Clans and tribes get one **Summary** card. Card ids are stable across j/k. | Every node kind must produce a Main deck | S |
| **A9** | 50/50 splits only | **`{` / `}` cycle the split ratio 30/50/70.** | Keeps the picker's ratios; mirrors Artifacts' `{`/`}` | O |
| **A10** | Remove the zoom panel | Remove the modal, but **rebind `Z` to "maximize the focused deck"**: collapse the node panel and switch to a single layout; press again to restore. Salvage zoom's search as card search. | R7; works like tmux `prefix z` | R |
| **A11** | Remove the `p` panel | Remove it. Add `choose_agent_view` to the retired ids and drop its contextual-duplicate pair. The freed info-row slot hosts the collapsed-node chip. | – | S |
| **A12** | (unspecified) | **Stable geometry.** A panel whose deck is empty for the current node shows a one-line empty-state card ("No files for this agent · `]` next deck") instead of reflowing. | R8: no layout jumping during j/k | R |
| **A13** | `Ctrl+F` toggles focus | Keep it. **Focus is logical**, shown by the border accent rather than Textual widget focus, so j/k still drive the node list. `Ctrl+B` becomes the reverse alias; with two panels it does the same thing. Retire the Agents branch of `scroll_prompt_*`; Services keeps its full-page scrolling. | Avoids a dead key and a silent scroll of a panel you're not looking at | S |
| **A14** | `\` horizontal split, `\|` "horizontal split" (a typo) | `\` = **top-bottom**, `\|` = **left-right**. Code and glossary use `TOP_BOTTOM`/`LEFT_RIGHT`, never horizontal/vertical. | R5 | S |
| **A15** | (unspecified) | Add `backslash` and `vertical_line` to `_KEY_DISPLAY`, so user overrides validate and help and footer show `\` and `\|`. | §2.5 gap | S |
| **A16** | (unspecified) | Images and videos in Files are **solo** cards: when one is present, the deck is always paged. | Their height depends on the viewport, and graphics-protocol images are fragile inside a scrolling spread | R |
| **A17** | (unspecified) | New split panels **take focus** (vim and tmux convention). Pressing the same split key again returns to single, **keeping the focused panel's deck**. | After `\|` opens Files, the next action is usually `Ctrl+N` or `Ctrl+D` on Files | R |
| **A18** | (unspecified) | **Persist** the layout, ratio, each panel's deck and stable card, focus and collapse state in `~/.sase/ace_agents_deck_state.json`, next to `ace_agents_fold_state.json`. | A layout you set up shouldn't reset every session. This reverses the documented "session-local" rule. | O |

---

## 5. Recommended design

### 5.1 Vocabulary

| Term | Meaning |
|---|---|
| **Agent data deck** ("deck") | A named, ordered set of cards about the selected sase node. Built-ins: **Main**, **Files**, **Tools**. |
| **Agent data card** ("card") | One titled unit of detail in a deck, with a stable id (`context`, `reply`, `summary`, `llm-calls`) or a dynamic id (a file page). |
| **Deck panel** | One detail region showing one deck. There are one or two; one is focused. |
| **Deck layout** | `single`, `left-right` or `top-bottom`. |
| **Spread / paged** | How a panel renders a multi-card deck: all cards on one scrollable page with card rules, or one card at a time. |
| **Node panel** | The Agents tab's left column of sase nodes; it can be expanded or collapsed. |

### 5.2 Architecture: separate deck *sources* from deck *views*

Today each panel widget is both data model and view. That is why zoom had to subclass them, and why a second panel is impossible.

```python
# widgets/decks/_model.py: presentation layer, lives in sase (not sase-core)
@dataclass(frozen=True)
class CardDocument:
    card_id: str                  # "context" | "reply" | "summary" | "llm-calls" | file page id
    title: str                    # "Context" | "Reply" | "Output" | "LLM Calls" | "src/foo.py" …
    renderables: tuple[Any, ...]
    digest: str                   # reuse util/renderable_digest.py
    solo: bool = False            # images/videos
    lower_bound_rows: Callable[[int], int] | None = None   # cheap estimate at a width

@dataclass(frozen=True)
class DeckDocument:
    deck_id: Literal["main", "files", "tools"]
    subject_identity: object      # node identity + attempt number
    cards: tuple[CardDocument, ...]
    default_card_id: str
```

- **Main source.** Refactor the prompt-panel builders (`widgets/prompt_panel/_agent_display_*.py`) to *return* a card-partitioned document instead of calling `self.update(Group(...))`.
  - The seam already exists: every branch builds a `reply_header` and then appends the reply.
  - Tag each card's first row with a hidden `sase_deck_card=<id>` style, the same trick as `sase_prompt_panel_section`, so `SectionTrackingVisual` also publishes **card anchors**.
  - One document feeds every panel that shows Main.
  - Don't split this into one widget per card (§3.3).
- **Files source.** Lift `_file_list`/`_desired_file_list` and the page contents out of `AgentFilePanel` into a per-selection `FilesDeckSource`. Keep the `(agent, page)` anchor store.
- **Tools source.** Lift the worker and cache out of `AgentLLMCallsPanel`, and **check the subject identity when a worker completes** (the §2.4 fix).
- **Scroll containers are resolved through the ancestor**, never by an app-wide ID.
- **Load lazily.** Only decks that are shown load content. Tab-strip availability badges come from no-I/O probes: commit diffs, the linked-delta cache, `build_cached_slow_tool_sources`. This removes today's "hidden panels are still populated" cost.
- gem's `AgentCard` Protocol with a `line_count()` method is too naive for measurement (it ignores wrapping). Use the document plus anchors instead.

### 5.3 Card mapping by node kind

| Node kind | Main-deck cards |
|---|---|
| Agent, agent shell, family container | `context` + `reply` (family: `AGENT REPLY · N` with per-shell phase dividers) |
| Pinned attempt | `context` (banner, `ATTEMPT ERROR`, prompt) + `reply` (`ATTEMPT N REPLY`) |
| Proc shell, monitor, gate, bash/python step | `context` (`COMMAND`/`MONITOR`/`GATE`/code) + `reply` titled **Output** (log tail / `OUTPUT` / `STEP OUTPUT`) |
| Parallel step | `reply` titled **Output** only |
| Top-level workflow row | `context` only |
| Clan, tribe summary | a single `summary` card. These fold-driven triage digests are meant to be read as a whole. |

- **Default card:** `context`.
- **Sticky card (recommended; see Q3).** In paged mode a stable card id sticks across j/k: if you were on Reply, you stay on Reply, which suits comparing replies. It falls back to the default when the new node has no such card.
- **Folds and hints** operate on the whole Main document, so hint numbering is stable in both modes. `Ctrl+J/K` walk the section anchors of the *visible* cards. **Search covers all cards of the focused deck** (mus); a match in a hidden paged card activates that card.
- **SLOW TOOL CALLS** stays in Context as a triage digest; the Tools deck has the full timeline. Make that duplication an explicit decision, as mus says.
  - Its overflow hint says "press ] for the full LLM Calls timeline". Today `]` does nothing on Agents, and under A2 `]` from Main goes to *Files*.
  - Generate the hint from the real keymap and deck order (`[` from Main), or make it a clickable jump that opens Tools in the other panel.

### 5.4 Deck panels, layouts and focus

- **Composition.** `AgentDetail` becomes `AgentHeaderPanel`, then `DeckArea`, then `AgentJumpPanel`.
- **`DeckArea` pre-composes both `DeckPanel`s** and hides the second, so switching layouts never mounts or unmounts widgets.
  - The layout is a CSS class: `-single`, `-left-right` (`layout: horizontal`) or `-top-bottom` (`layout: vertical`).
  - The ratio is also a class: `-ratio-30|50|70`.
- **`DeckPanel`** is a bordered frame with one `VerticalScroll` inside.
  - The `border_title` is the **deck and card tab strip**: `MAIN ▸ Context · Reply`, or `FILES ‹ 3/27 › src/foo.py` when there are many cards. Build it with `PanelTabStrip`'s full → compact → micro tiers, which already handle narrow widths and click ranges.
  - The `border_subtitle` shows the mode or position (`spread`, `2/3`) and file line counts.
- **Focus.** The focused panel gets an accent border and the other a dim border; the single layout has no focus styling. Clicking a panel focuses it, and clicking a tab activates that card.
- **Transitions:**

```
single ──\──▶ top-bottom      (new panel below; gets the next non-shown deck with content, else the current deck; new panel takes focus)
single ──|──▶ left-right      (same, to the right)
top-bottom ──\──▶ single      (keep the focused panel's deck)
left-right ──|──▶ single      (keep the focused panel's deck)
top-bottom ◀──|/\──▶ left-right  (opposite key: keep both decks and focus, rotate)
```

- **Reconciling.** When the file list changes, keep the current card by id, never move the viewport, and let new pages appear in the tab strip. This carries forward zoom's "frozen list, so nothing jumps" lesson without freezing anything.

### 5.5 Spread vs paged: the algorithm

```python
def decide_mode(doc: DeckDocument, H: int, W: int, prev: Mode | None, same_subject: bool) -> Mode:
    if len(doc.cards) <= 1:
        return SPREAD
    if any(c.solo for c in doc.cards):
        return PAGED
    budget = cfg.spread_max_screens * H            # 0 ⇒ always paged
    if same_subject and prev is PAGED:
        return PAGED                               # one-way while the same node is selected
    limit = budget * (1.15 if prev is SPREAD else 1.0)
    total = 0
    for c in doc.cards:                            # 1) cheap lower bounds settle big decks, no rendering
        total += c.lower_bound_rows(W)             #    logical lines, or ceil(bytes / W) for unread files
        if total > limit:
            return PAGED
    exact = sum(measure_rows(c, W) for c in doc.cards)   # 2) only small decks get here; cached by (digest, W)
    return SPREAD if exact <= limit else PAGED
```

- **When it runs:**
  - on the **debounced** detail update, never on the immediate header paint during j/k
  - on a layout, ratio, header or jump-panel toggle
  - on a debounced resize
  - when a same-subject update crosses the upper band
- **Keeping the reading position.** Going spread → paged activates the card at the top of the viewport and keeps its offset. On a new selection, show the sticky card or the default card.
- **Measuring Main is nearly free.** It is the render `SectionTrackingVisual` already does and caches, and the card heights fall out of the card anchors.
- **Files lower bound.** `ceil(st_size / W)` for unread pages, computed off-thread and cached by `(path, mtime, size)`. It is conservative for ASCII diffs.
- **Why 1.5 screens.**
  - `1.0` would page about 87% of Main decks.
  - `2.0`+ puts two screens of scrolling between Context and Reply.
  - Because `Ctrl+N` works identically in both modes, the exact value only affects feel, not reachability. Treat it as a tuning constant.

### 5.6 Collapsing the node panel (`Ctrl+S`)

What the user needs while the list is collapsed, and what already supplies it:

| Need | Supplied by |
|---|---|
| Know it's collapsed, and how to restore it | **New:** info-row chip `▸ nodes 12/47 · ^S`, in the slot freed by `view: … (p)`; clicking it expands |
| Know which node is selected | Existing `AgentHeaderPanel`, which updates on the immediate j/k paint |
| Local position (siblings, family) | Existing jump panel (numbered family and neighbor targets still work), plus the chip's `12/47`. Optionally show the previous and next node names in the chip when there is room. |
| Fleet-level changes | Existing info-row counts (`[x running · y queued]`) and top-bar notification indicators |

**Mechanism.** Add a `-nodes-collapsed` class on `#agents-content` with `#agent-list-container { display: none; }`.

- The list stays mounted, so selection, folds and incremental row patches keep running.
- j/k keep working because they go through `_navigate_agents_panel` over the app's stop model (✔ verified).
- This is the same mechanism onboarding and the artifact viewer already use.

**Interactions:**

- Collapsing **clears whole-panel focus**. Otherwise j/k would move an invisible tribe-panel focus via `_change_whole_panel_focus`.
- Actions whose only visible effect is on list structure **auto-expand first**: `J`/`K` tribe focus, list folds, `=` isolate, `-`/`_` collapse folds, filter edits.
- `Z` (A10) saves and restores both the collapse and the layout.

**Rejected for v1:**

- **gem's 4-cell micro-rail.**
  - It is a second row renderer for the most performance-sensitive widget.
  - It must stay in scroll sync across several tribe panels.
  - It can't map 1:1 once there are more rows than the rail is tall.
  - Its premise (that hiding the list breaks j/k) is false.
- **Auto-peeking the list on j/k**, which causes flicker.

**Follow-up if missed.** A 1–2 column status minimap (one cell per list row, compressed; colored by status; the selected row marked) that reads the in-memory row model and rebuilds only when rows change.

### 5.7 Keymap (recommended defaults)

| Key (Textual name) | Action id | Notes |
|---|---|---|
| `ctrl+n` / `ctrl+p` | `next_deck_card` / `prev_deck_card` | Replaces `next_agent_file`/`prev_agent_file`. Add those ids to `LEGACY_APP_KEY_ALIASES` so user overrides migrate. Keep the Services chop-run branch, either inside the action or split out with a contextual-duplicate pair. |
| `right_square_bracket` / `left_square_bracket` | `next_deck` / `prev_deck` | Contextual duplicate with Artifacts' subtab cycling |
| `backslash` | `toggle_deck_layout_top_bottom` | Needs A15 for user overrides |
| `vertical_line` | `toggle_deck_layout_left_right` | Needs A15 |
| `ctrl+f` / `ctrl+b` | `focus_next_deck_panel` / `focus_prev_deck_panel` | Agents only. Services keeps `scroll_prompt_*` through contextual duplicates. |
| `ctrl+s` | `toggle_node_panel` | |
| `Z` | `maximize_deck` | Replaces `zoom_panel` |
| `right_curly_bracket` / `left_curly_bracket` | `cycle_deck_split_ratio` / `…_reverse` | Optional (A9); contextual duplicate with Artifacts |
| `p` | – | `choose_agent_view` retired |
| `ctrl+shift+n` / `ctrl+shift+p` | *(not bound by default)* | See below |

**If you want your original mapping anyway** (cards on `Ctrl+Shift+N/P`, decks on `Ctrl+N/P`), it is a defaults change. But first, on every client:

1. In tmux: `set -s extended-keys always`, `set -s extended-keys-format csi-u`, `set -as terminal-features 'xterm-kitty:extkeys'`.
2. In kitty: unmap `kitty_mod+n` and `kitty_mod+p`.
3. Confirm with `textual keys` inside tmux.

Textual already requests the kitty disambiguate mode and parses CSI-u, so the app side is ready. I recommend against it regardless, on frequency and muscle-memory grounds.

### 5.8 Retargeting existing actions

| Action | New target |
|---|---|
| `Ctrl+D/U` (`scroll_detail_*`) | the focused deck panel's scroll |
| `g`/`G`, bottom pin | the focused panel. The pin follows Reply (spread) or the active card (paged). |
| `Ctrl+J/K` section stops | visible cards of the focused panel (Main) |
| `z…` folds, `v` hints | the Main document when the focused panel shows Main; otherwise nothing |
| `,/` search, `n`/`N` | all cards of the focused deck. Salvage `modals/zoom_panel_search.py` for non-Main text. |
| `E` editor, `y` copy, `V` pager | the focused panel's active card (Files: the real path; LLM Calls: markdown; Main: card text) |
| `l/h/L/H` | LLM detail level when the focused panel shows Tools; otherwise folds, as today |
| `D` attempt view, `d` header, `.` jump panel | unchanged (shared chrome) |
| clipboard `#agent-file-panel` queries | the focused panel's Files card view |

### 5.9 Config

In `src/sase/default_config.yml` under `ace:`, next to `tool_calls:` and `artifact_file_viewer:`, and in `src/sase/config/sase.schema.json`:

```yaml
  agent_decks:
    # Show every card of a multi-card deck on one scrollable page ("spread")
    # when their combined rendered height fits within this many deck-panel
    # heights; otherwise show one card per page ("paged"). 0 always pages.
    spread_max_screens: 1.5
```

- One field on purpose.
- Hysteresis is an internal constant.
- No `default_layout` field: persistence covers it.
- No per-deck override until a real complaint shows up.

### 5.10 Performance rules applied

- **j/k paint only the header immediately.** Deck content and mode decisions ride the debounced update.
- **Only visible decks load.** Availability badges come from no-I/O probes.
- **No remounts.** Layout and ratio are CSS classes on pre-composed panels.
- **Only small content is measured**, with results cached by `(digest, width)`.
- **Every source's worker checks subject identity.** `_agent_detail_generation` keeps gating Main.
- **Persistence writes happen off the event loop.**
- **Gates:**
  - `SASE_TUI_PERF=1` j/k p95 < 16 ms in the single and left-right layouts
  - `tests/ace/tui/bench_tui_jk.py` before and after

### 5.11 Removals and salvage

- **Delete:**
  - `modals/agent_view_modal.py`, `actions/agents/_agent_view_picker.py`
  - `DetailPanelMode`, `DetailLayoutMode`, `DETAIL_LAYOUT_CYCLE`
  - the `view:` chip and its (already stale) `_VIEW_MODE_STYLES`
  - `modals/zoom_panel_*.py`, the zoom seed code in `actions/agents/_panel_detail.py`, and the zoom TCSS
  - their tests
- **Salvage:**
  - zoom's search, as card search
  - the file rail, as the tab strip
  - "frozen list", as the reconcile rule
- **Fix stale text:**
  - `default_config.yml`'s "Z zooms agent detail…" comment
  - `AgentDetail.compose`'s "two-panel layout" docstring
  - the `docs/ace.md` zoom, view-picker and "session-local" sections

### 5.12 Rust core boundary

Deck and card composition, modes, focus, layout, keys and persistence are presentation-only, and the card *content* builders already live in `widgets/prompt_panel/`.

Litmus test: a web frontend would not need to match how the TUI paginates. It might someday want the card catalog (`deck_id`, `card_id`, `title`, `order`); only then should that move into a sase-core wire. **No sase-core change is needed now.**

---

## 6. Glossary strands (draft text)

Add these with `/sase_memory_write` in the phase that turns the feature on for users (§7 phase 6), so the glossary never describes unshipped behavior.

- **`glossary:agent-data-deck`** (aka deck, agent data decks)
  > An agent data deck is a named, ordered set of agent data cards about the selected sase node, shown in an Agents-tab deck panel. Built-in decks are **Main** (Context and Reply cards, with Output instead of Reply for proc, monitor, gate and step nodes, and one Summary card for clans and tribes), **Files** (one card per file page: commit diffs, the live diff, linked-repo diffs, attached files) and **Tools** (the [[glossary:llm-calls]] card). A deck is presentation only; it owns no agent data.
- **`glossary:agent-data-card`** (aka card, agent data cards)
  > An agent data card is one titled unit of detail in an agent data deck. Cards with stable ids (`context`, `reply`, `summary`, `llm-calls`) keep their place across selections; file-page cards are per node. A deck panel shows a multi-card deck **spread** (every card on one scrollable page) when the cards fit within `ace.agent_decks.spread_max_screens` panel heights and **paged** (one card at a time) otherwise; `Ctrl+N`/`Ctrl+P` move between cards in both modes.
- **`glossary:deck-panel`**
  > A deck panel is one Agents-tab detail region showing one agent data deck. The Agents tab shows one or two, in a `single`, `left-right` (`|`) or `top-bottom` (`\`) deck layout; `]`/`[` change the focused panel's deck and `Ctrl+F` moves the logical focus that detail actions target. The identity header and jump panel span every deck panel and belong to none.
- **`glossary:node-panel`**
  > The node panel is the Agents tab's left column of [[glossary:sase-node]] rows. `Ctrl+S` collapses it without unmounting it, so j/k still move the selection; while collapsed, an info-row chip shows the position and restores it.

**Edits to existing strands:**

- `glossary:llm-calls`: "the Agents detail and zoom view" → "the LLM Calls card of the Tools deck"
- `glossary:tool-run`: "not the Agents-tab LLM Calls view" → "not the LLM Calls card"
- `glossary:agent-relation-jump-target`: "below the Agents detail panels" → "below the deck panels"

The future `sase tool` card should be titled **Tool Runs**, not "Named Tools" as gem suggests. That keeps the glossary's LLM Calls ≠ Tool Run distinction.

---

## 7. Implementation plan (6-phase epic)

A **`beta` flag** (`sase flag new agent_decks`) scaffolds the epic. Phases 2–5 land behind it, so the old UI stays the default. Phase 6 deletes the Off branch and the flag, as the `sase_flags` epic-scaffolding rule prescribes.

The flag window also answers mus's "don't delete zoom and the picker before the replacements are proven". No `sunset` flag is needed for `p` and `Z`: you asked for their removal, and a one-time notice (precedent: `_keymap_unification_notice.py`) covers muscle memory.

| Phase | Scope |
|---|---|
| **0. Independent fixes (no flag)** | The LLM Calls subject-identity check (§2.4). `_KEY_DISPLAY` gains `backslash`/`vertical_line` (A15). |
| **1. Decouple (no UX change)** | Builders return a card-partitioned `DeckDocument`; the panel still renders all cards. File and LLM sources are lifted out of their widgets. Scroll containers are resolved through the ancestor. The traceback moves into the reply part (A7). |
| **2. Deck panel, single layout (flagged)** | The `widgets/decks/` package; `DeckPanel` with the tab strip; paged mode only; `Ctrl+N/P` cards; `]`/`[` decks; empty-state cards; lazy loading; keymaps, config, help, footer and palette. |
| **3. Splits and focus** | `\`, `\|`, `Ctrl+F/B`, optional `{`/`}`. `DeckArea` layout classes. Duplicate-deck rules. **Retarget every action in §5.8**, the largest phase. |
| **4. Node panel** | `Ctrl+S` collapse, the info-row chip, auto-expand rules, clearing whole-panel focus, `Z` = maximize. |
| **5. Spread mode** | Card anchors, lower bounds, the measurement cache, hysteresis and the one-way rule, keeping the reading position, `ace.agent_decks.spread_max_screens`, solo cards. **This is the natural cut point:** paged-only decks are already a complete, coherent design. |
| **6. Cut-over** | Remove `p`, zoom, the enums and old IDs; persistence (A18); `docs/ace.md`; glossary strands (§6); the one-time key notice; visual goldens; delete the flag. |

---

## 8. Testing

- **Pure model tests:**
  - `decide_mode`: boundaries, both sides of the band, the one-way same-subject rule, solo cards, `0`
  - the layout state machine: every transition, deck retention, focus, the duplicate-Main default card, skipping empty decks
- **Builder tests.** Every node kind yields the §5.3 partition. The traceback lands in `reply`. Card ids are stable.
- **Pilot tests:**
  - j/k across agents with and without files keeps geometry stable
  - `Ctrl+N` scrolls in spread mode and swaps the page in paged mode
  - a streaming reply that crosses the threshold keeps the reading position
  - `Ctrl+S` hides the list while j/k still update the header
  - `Z` round-trips
  - a stale LLM Calls worker for agent A never paints on agent B
- **Keymap tests:**
  - contextual duplicates resolve per tab (`]`, `{`, `Ctrl+F`)
  - the legacy alias migrates `next_agent_file` overrides
  - a `backslash` user override is accepted
  - the Services chop-run stepping is unchanged
- **Flag:** test both states while the flag exists.
- **Visual goldens:**
  - single/spread and single/paged
  - left-right, top-bottom
  - collapsed node panel
  - empty-state card
  - the narrow tab-strip tiers
- **Performance:** the j/k p95 bench before and after.

---

## 9. Open questions for you

1. **Q1. Do you accept the key swap** (A1/A2: `Ctrl+N/P` cards, `]`/`[` decks)? Keeping your mapping requires the tmux and kitty changes in §5.7 on every client, and it still puts the rare action on the easy key.
2. **Q2. Threshold default.** 1.5 screens (my recommendation), 1.0 (cld: spread only when nothing scrolls), or about 2.0?
3. **Q3. Sticky Reply across j/k in paged mode**, or always reset to Context?
4. **Q4. Empty decks:** stable geometry with an empty-state card (A12), or today's reflow-to-fill?
5. **Q5. Persist the layout across restarts (A18)**, or keep it session-local as documented today?

---

## 10. Recommended solution

Build **agent data decks and cards** as a presentation-layer redesign of the Agents detail area. It is a 6-phase epic behind a `beta` flag that the epic removes, with no sase-core changes, preceded by one independent bug fix.

1. **Model.** Three built-in decks:
   - **Main.** `context` + `reply` for agent-like nodes. Proc, monitor, gate and step nodes get `context` + **Output**. Clans and tribes get one `summary` card.
   - **Files.** One card per existing file page.
   - **Tools.** The **LLM Calls** card now; a **Tool Runs** card later.

   The identity header and the jump panel stay outside decks as shared chrome. Context absorbs QUEUE, MEMBERS, the variables sections and the ERROR summary. The traceback moves to the top of Reply.
2. **Architecture.**
   - Split sources from views, with one card-partitioned Main document using hidden card anchors.
   - File and LLM data move into per-selection sources with identity-checked workers.
   - Scroll containers are resolved through the ancestor.
   - Only visible decks load.
3. **Layout.**
   - At most **two** pre-composed deck panels, in `single`, `left-right` (`|`) or `top-bottom` (`\`), following your toggle and rotate rules.
   - New panels take focus and skip empty decks.
   - Duplicate decks are allowed, so Context | Reply is one keystroke.
   - Geometry stays stable when a deck is empty. Optional 30/50/70 ratio on `{`/`}`.
4. **Rendering.**
   - Show a deck **spread** when it fits within `ace.agent_decks.spread_max_screens` (default 1.5) panel heights, otherwise **paged**.
   - Decide with cheap lower bounds first and exact measurement only for small decks, plus ±15% hysteresis. While the same node stays selected, only spread → paged is allowed, and it keeps the card you were reading.
   - The tab strip is always visible, and `Ctrl+N/P` means "next/previous card" in both modes.
5. **Keys.**
   - `Ctrl+N/P` cards; `]`/`[` decks; `\`/`|` layouts
   - `Ctrl+F` (and `Ctrl+B`) focus
   - `Ctrl+S` collapse the node panel; `Z` maximize the focused deck
   - `p` retired
   - fix `\`/`|` override validation and display
   - `Ctrl+Shift+N/P` only as opt-in aliases after the terminal chain is fixed
6. **Node panel.** Collapse with `display: none` (the list stays mounted, so j/k keep working) plus a `nodes i/n · ^S` chip in the freed `view: (p)` slot. Rely on the existing header, jump panel and info-row counts for orientation. A status minimap is a follow-up only if it turns out to be needed.
7. **Removals.** Delete the `p` picker, the zoom modal, both mode enums and their tests, salvaging zoom's search, file rail idea and no-jump reconcile rule.
8. **Vocabulary.** Add glossary strands for agent data deck, agent data card, deck panel and node panel at cut-over, and update the LLM Calls, Tool Run and Agent Relation Jump Target strands.
9. **Land first, independently:** the LLM Calls stale-worker fix (§2.4) and the `_KEY_DISPLAY` fix (A15).

---

## Appendix A: Verification log (this report)

| Claim | How it was checked | Result |
|---|---|---|
| tmux delivers Ctrl+Shift+N as Ctrl+N | `tmux show -s extended-keys` / `extended-keys-format`; `tmux -V` | `off` / `xterm`; 3.5a |
| The live client is kitty over SSH | `tmux list-clients -F '#{client_termname} #{client_width}x#{client_height} #{client_termfeatures}'`; parent process of the client | `xterm-kitty 261x79`, no `extkeys`; parent is `sshd-session` |
| tmux prefix | `tmux show -g prefix` | `C-a` (prefix2 `M-a`), so Ctrl+B reaches the app |
| Textual names for `\|`, `\` | `textual.keys._character_to_key` (Textual 8.0.1) | `vertical_line`, `backslash` |
| `\`/`\|` fail override validation | `key_validation.is_valid_key` in the project venv; `registry.py` revert path | `False` for `backslash`, `vertical_line`, `pipe`, `vertical_bar`, `\`, `\|` |
| XOFF can't eat Ctrl+S | `textual/drivers/linux_driver.py` `_patch_iflag` clears `IXON` | confirmed |
| `Ctrl+S` is free at app level | `default_config.yml` (`submit_branch` sits under `keymaps.gate`); `grep ctrl+s` over the TUI | modal- and TextArea-local only |
| `Ctrl+F` on Agents | `actions/navigation/_basic.py` `action_scroll_prompt_down` | half-page scroll of `#agent-prompt-scroll`; full page on Services |
| `Tab` is taken | `default_config.yml` `next_tab: "tab"` | confirmed |
| j/k work with the list hidden | `action_next_patch` → `_navigate_agents_panel` (stop model, whole-panel focus hook) | confirmed; collapse must clear whole-panel focus |
| `]`/`[`/`{`/`}` are Artifacts-only | `_app_action_availability.py` | confirmed |
| Ctrl+N/P is shared with Services | `actions/agents/_panel_detail.py` `action_next_agent_file` | Services steps through chop runs |
| LLM Calls stale-worker bug | `widgets/llm_calls_panel.py` `_update_display_impl` / `on_worker_state_changed` / `_display_llm_calls_result` | no subject identity anywhere on the path |
| Traceback renders under the AGENT PROMPT heading | `widgets/prompt_panel/_agent_display_render.py` renderables order | confirmed |
| Rosters live in the jump panel | `git show --stat 78f1d71e7` | "move numbered roster sections into Agents jump panel" |
| `AgentDetail` is used only on the Agents tab | grep for constructors | `_app_layout.py` only |
| Size of the retarget | grep for hard-wired IDs and enums | 216 references across 17 source files; 37 test files |
| Zoom and picker LOC | `wc -l` | 1,627 and 813 |
| Content sizes | a script over `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/*/*/` (n=2,340) | §2.6 table |
| Config placement | `default_config.yml` `ace:` children | sits alongside `tool_calls:` and `artifact_file_viewer:` |

**Not verified:** the Mac-side kitty config. The chezmoi-deployed `kitty.conf` on athena doesn't unmap `kitty_mod`, and the tmux finding is decisive on its own either way.
