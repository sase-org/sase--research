# Naming the "Prompt Input Widget" for the SASE Glossary

_Independent researcher report (`gem`) · 2026-11-21 · verified against `sase` `master` @ `811576c390`_

## Bottom Line

**#1 Recommendation: `Prompt Composer`**, with short alias **`composer`** (plus transition aliases `prompt bar` and `prompt input widget`, and optional `prompt input bar`).

Today the surface is fragmented across **six informal names** in docs and code (`prompt bar` 176, `prompt input` 175, `prompt input bar` 42, `prompt input widget` 30, `prompt widget` 20, `prompt editor` 9), while Bryan himself writes `prompt input widget` (23 hits in prompt history; `prompt bar`: 0) and calls its top panel the `property panel` (while code/docs call it `FrontmatterPanel` / `frontmatter panel`, 37 hits).

`Prompt Composer` wins because:

1. **It matches what the widget actually is today.** `PromptInputBar` outgrew a 3-row horizontal bar long ago. It is now a multi-region bottom-docked authoring container combining Vim-modal panes, a vertical multi-agent + auxiliary **stack** (`#prompt-stack`), and a structured YAML **property panel** (`#frontmatter-panel`), plus completions, search, leader hints, macro targeting, and `$EDITOR` handoff. A *composer* naturally holds a properties header, multiple stacked panes, and rich completions; a *bar* or *box* misrepresents that architecture.
2. **Zero collisions — verified against `sase-core`'s live Rust glossary matcher.** Across all 72 existing glossary strands, all `docs/**/*.md`, and recent prompt history, both `Prompt Composer` and bare `composer` produce **0** false-positive matches and **0** validation diagnostics. Unlike `Prompt Bar`, it also unlocks an unambiguous one-word shorthand (`composer`) and a unique CLI lookup prefix (`sase memory read glossary:composer` / `glossary:comp`).
3. **Clean composition with stacks and the property panel.** *"composer stack"*, *"composer property panel"*, *"composer pane"*, and *"open the composer"* read cleanly without noun-piling (compare *"prompt bar property panel"*).
4. **Zero-cost adoption.** Adding `sase/memory/glossary/prompt-composer.md` with aliases (`composer`, `prompt bar`, `prompt input widget`) immediately unifies existing docs, Bryan's habit, and future agent lookups without renaming `PromptInputBar` or churning code identifiers.

If you want **zero new vocabulary** and prefer to codify the codebase's existing majority prose label despite its "thin horizontal strip" connotation, **#2 `Prompt Bar`** is the clear conservative fallback. If you want a **punchy two-syllable metaphor**, **#3 `Prompt Pad`** (writing pad of stacked sheets + launch pad) is the strongest alternative.

---

## 1. Anatomy of What Is Being Named

Before picking a word, it helps to pin down the exact three-part surface verified in `src/sase/ace/tui/` at `811576c390`:

```text
╭─ Prompt · 2 agents · ✎ #review · ● [NORMAL]  TODO 1 ────────────────────────╮
│ [ #prompt-completion ]      dropdown menu / Jinja diagnostics / arg hints   │
│ ╭─ frontmatter (#mini)  ⟨✓⟩ ──────────────────────────────────────────────╮ │
│ │ ▸ input       ▾ 2 items    (FrontmatterPanel / "property panel", g=)    │ │
│ │ ▸ macros      ▾ 1 item                                                  │ │
│ ╰─────────────────────────────────────────────────────────────────────────╯ │
│ [ #prompt-dispatch-context ]  Target / Source / %auto validation line       │
│ [ #prompt-g-prefix-hints / #prompt-search-command ]                         │
│ ─────────────── ▍ agent 1 ────────────────────────────── Ln 2, Col 14 ───── │
│   Active PromptTextArea (expanded; Vim INSERT/NORMAL/VISUAL/V-LINE)         │
│ ──────────────── agent 2 ─────────────────────────────── Ln 1, Col 8  ───── │
│   Parked PromptTextArea (compact)                                           │
│ ─────────────── ⇥ fix · ~/.config/sase/sase.yml new ─────────────────────── │
│   Optional pinned auxiliary pane: snippet (gt) OR mini-macro (gx)           │
╰─ [g<enter>] launch  [gj/gk] pane  [gJ/gK] move  [^S/gs] stash   Ln 2, Col 14╯
```

### 1.1 The Widget (`PromptInputBar`)

- **Implementation:** `PromptInputBar` (`src/sase/ace/tui/widgets/prompt_input_bar.py`, `#prompt-input-bar`, CSS `dock: bottom` in `src/sase/ace/tui/styles.tcss:4531–4537`), composed in `_prompt_input_bar_lifecycle.py:56–81`.
- **Three modes (`_mode`):**
  - `prompt` — full agent drafting, stacks, property panel, stashing, macro targeting (double border + `✎ <ref>` chip + `✓`/`●`/`🔒 read-only`/`⚠ changed on disk` state + `gw` write-back), auxiliary panes, and pre-mounted `space-hot-spare` reveal (`_is_prompt_spare`).
  - `feedback` ("Plan Feedback") — single-pane, warning border, optional read-only `#prompt-feedback-carries` lines; no stacks, properties, or stashing.
  - `approve_prompt` ("Coder Prompt") — single-pane; no stacks, properties, or stashing.
- **Editor & assist stack:** Each pane is a `PromptTextArea` (`prompt_text_area.py`) with Vim INSERT/NORMAL/VISUAL/V-LINE modes, Markdown + SASE highlighting (`#macro`, `%directive`, `/skill`, `@ref`, `+project`, `%{alt}`, Jinja, `<placeholder>`, `TODO`, glossary/repo/bead underlines), `Ctrl+T` completion + Fish-style next-word ghosts/peeks, `Ctrl+R` fuzzy finder, `/` / `?` + operator search, and `Ctrl+G g` `$EDITOR` handoff (with ` @` review-return marker).

### 1.2 How Stacks Work (`#prompt-stack`, `PromptStackState`)

Verified in `_prompt_stack_state.py`, `_prompt_stack_targets.py`, `_prompt_input_bar_stack_rendering.py`, `_prompt_input_bar_stack_separator.py`, `_prompt_input_bar_stack_navigation.py`, and `_prompt_input_bar_submission_actions.py`:

- **Ordered agent panes:** `PromptStackState` holds 1..N `PromptStackItem`s in **top-to-bottom launch order** (`agent 1`, `agent 2`, …). Loading multi-agent Markdown (`from_text`, whole-bar `$EDITOR` return, or ` @`-marked editor return) lifts leading YAML frontmatter onto the stack and splits top-level `---` lines into panes. During live INSERT typing, `---` stays literal; `g-` / `Ctrl+G -` appends a new bottom agent pane seeded with the active pane's workspace tag.
- **Visual hierarchy:** In solo mode (1 pane), the text area fills the frame with no separator. In multi-pane mode, the active pane takes available height while parked panes stay compact beneath `PromptStackSeparator` hairline rules (`─── agent N ─── Ln L, Col C ─`) showing each parked pane's Vim-colored cursor readout.
- **Actions:** `gj`/`gk` (`Ctrl+G j/k`) cycle pane focus with wraparound; `gJ`/`gK` (`Ctrl+G J/K`) reorder agent panes; `g<enter>` (`Ctrl+G Enter`) submits only the active agent pane (re-attaching shared frontmatter and keeping the remaining stack open); `Enter` opens the submit chooser (`a`/all joins non-empty agent panes with `---` and re-attaches shared frontmatter; `c`/current; `w`/write bound macro; `X`/fork); `Ctrl+S` stashes one pane and `gs` bundles all non-empty agent panes into one `Prompt Stash` row.
- **Pinned auxiliary pane (at most one):** A stack may also hold one bottom-pinned non-agent pane — either a **snippet pane** (`gt`, `$primary` accent, `⇥ <trigger>`) or a **mini-macro pane** (`gx`, `$secondary` accent, `#<name>`). Auxiliary panes are excluded from launches, stashes, and save-as; `Enter` inside one saves its snippet/macro definition instead of launching; `Ctrl+C` discards it (with a dirty confirmation guard) and restores focus, cursor, and Vim mode to the originating pane.

### 1.3 How the Property Panel Works (`FrontmatterPanel`, `#frontmatter-panel`)

Verified in `frontmatter_panel.py`, `_frontmatter_panel_rendering.py`, `_prompt_input_bar_frontmatter.py`, and `modals/property_picker_modal.py`:

- **Placement & lifecycle:** Mounted directly above `#prompt-stack` in `prompt` mode only (absent in `feedback` and `approve_prompt`). Toggled/focused via `g=` / `Ctrl+G =` (in-panel `g=`, `Esc`, or `q` returns to the originating pane; `gj`/`gk` jump to top/bottom pane). Auto-shows whenever frontmatter or a macro target is loaded, and hides/drops empty frontmatter on close (no stray `---\n---`).
- **Editing model:** Renders one row per set YAML field (`name`, `description`, `input:`, `macros:`, etc.) under a border title `frontmatter [<scope>]  ⟨✓⟩` / `⟨! N⟩` / `⟨ ⟩` live-validated by `sase-core`. Supports `j`/`k` row navigation, `h`/`l` fold/unfold on `input:` / `macros:` subtrees, `a` add-property picker (`AddPropertyModal` / `PropertyPickerModal`), `e`/`Enter` inline or cell-strip editing (`name`, `type`, `choices`, `default`, `description`), `o`/`A` ghost sub-item creation, `d` delete, `u` undo, `J`/`K` reorder, and `R` raw-YAML escape hatch.
- **Dynamic scope switching (`_frontmatter_scope`):**
  - On ordinary agent panes, it edits the **stack's shared prompt-level frontmatter**, persisted byte-stably onto `PromptStackState.frontmatter` — feeding local `macros:` and `input:` into `Ctrl+T` completion, the `#@` picker, Jinja assist, inline-expansion undo/redo (`#@` + `Ctrl+I`), and single-pane or whole-stack launches.
  - When a **mini-macro auxiliary pane** is active, the panel automatically switches scope to that mini-macro's own isolated frontmatter (`frontmatter #<name>`) without touching the surrounding stack's frontmatter.
- **Noteworthy terminology split:** Code and docs mostly say **Frontmatter Panel** (37 hits), while Bryan ("property panel"), subtitles (`[^G =] properties`), empty-state copy (`No properties yet.`), docstrings (`"Toggle the macro properties panel"`), and modals (`AddPropertyModal`, `PropertyPickerModal`) use **property / properties**. The new glossary entry should bridge both spellings explicitly so future agents never miss `FrontmatterPanel` when Bryan writes "property panel".

### 1.4 Four Easy-to-Confuse Neighbors (Essential Disambiguations)

Future agents routinely confuse this widget with four adjacent SASE surfaces:

1. **`AgentPromptPanel`** (`src/sase/ace/tui/widgets/prompt_panel/`, 55 hits for `prompt panel`) — the **read-only** Agents-tab detail surface displaying an existing agent's context, prompt, and reply.
2. **Prompts overlay** (`docs/reference/tui/prompts-overlay.md`) — the full modal with Stash, Trash, and History tabs.
3. **Prompt Inputs modal** (`Fill in this prompt`, `src/sase/agent/prompt_inputs.py`) — the pre-launch form collecting raw `<placeholder>` tags and required `input:` values on submit.
4. **External `$EDITOR` / `sase-nvim`** — the full editor handed off to via `Ctrl+G g`.

---

## 2. Empirical Terminology & Glossary-Matcher Audit

### 2.1 Current Fragmentation Across Repo vs. Prompt History

Measured across `docs/` and `src/sase/` (tracked files at `811576c390`) and the 3 local `~/.sase/prompt_history/` shards:

| Existing phrase | `docs/` + `src/sase/` hits | Prompt history hits | Notes |
| --- | ---: | ---: | --- |
| `prompt bar` | 176 | 0 | Dominant in TUI docs & `_prompt_bar_*.py`, but never used by Bryan in prompts |
| `prompt input` | 175 | 23 | Overlaps with `Prompt Inputs` modal (mechanically broken in matcher — §2.2) |
| `prompt stack` | 78 | 0 | Specifically names `#prompt-stack` (the inner pane list) |
| `prompt panel` | 55 | 0 | Already belongs to read-only `widgets/prompt_panel/` |
| `prompt input bar` | 42 | 0 | Mirrors class name `PromptInputBar` |
| `frontmatter panel` | 37 | 0 | Class `FrontmatterPanel` (`frontmatter_panel.py`) |
| `prompt input widget` | 30 | 23 | Bryan's own habitual term; verbose (3 words, 5 syllables) |
| `prompt widget` | 20 | 0 | Shortened form in docs/blog |
| `prompt editor` | 9 | 0 | Collides with `$EDITOR` / Neovim |
| `properties panel` / `property panel` | 3 / 0 | 0 / 1 | Matches `AddPropertyModal`, `[^G =] properties`, Bryan's phrasing |

### 2.2 SASE Glossary Naming Patterns

Inspecting all 72 existing glossary strands (`sase memory web show glossary -f json`):

- **Every TUI surface term is a crisp 2-word `<qualifier> <surface>` noun phrase** (or a 3-word formal term with a 1-word alias):
  `Deck Panel`, `Node Panel`, `Nav Section`, `Nav Item`, `Agent Tab`, `Machine Tab`, `Prompt Stash (stash)`, `Stash Trash`, `Raw Prompt`, `Agent Data Deck (deck)`, `Agent Data Card (card)`, `Agent Data Card Block (card block)`.
- **Single-word aliases work when unambiguous:** `deck`, `card`, `stash`, `gate`, `turn`, `hood`, `smack`, `ref`. Generic words like `bar`, `box`, `pad`, `dock`, or `panel` **cannot** safely be bare aliases because the Rust matcher highlights them on unrelated prose (`top bar`, `filter bar`, `foo/bar`, `padding`, `dock: bottom`).
- **Direction of SASE's terminology evolution:** Recent renames (`ACE → TUI`, `AXE → scheduler`, `chop → job`, `sase shell → sase turn`, `agent family → agent session`, `xprompt → macro`, `macro reference → macro invocation`) consistently favor **self-describing, industry-grounded names** over opaque or cute metaphors, keeping legacy spellings as lookup aliases rather than forcing immediate code sweeps.

### 2.3 Live Rust Glossary Matcher & Collision Verification

Probed directly through `sase.core.glossary_facade` (`validate_glossary_entries`, `build_glossary_catalog`, `compile_glossary_catalog`, `scan_glossary_spans`) against all 72 live glossary strands, `docs/reference/tui/*.md`, and all `docs/**/*.md`:

| Candidate | Validation | `tui_docs` hits (keyword) | `all_docs` hits (keyword) | Bare 1-word alias safe? | Key collisions / findings |
| --- | --- | ---: | ---: | --- | --- |
| **`Prompt Composer`** | OK | 0 | 0 | **Yes (`composer`: 0 doc/glossary/history hits)** | Only 6 internal Python docstring comments (`snippet_catalog_facade`, `pager/_body_lines`, `followup_prompt`); unique `glossary:comp` prefix |
| **`Prompt Bar`** | OK | 29 | 58 | **No** (`bar`: `TopBar`, `TabBar`, `FilterBar`, `foo/bar`) | All 58 doc hits are true positives for this widget; no 1-word shorthand |
| **`Prompt Pad`** | OK | 0 | 0 | **No** (`pad`: padding / layout alignment in code) | 0 doc/glossary/history hits for `Prompt Pad` |
| **`Prompt Dock`** | OK | 0 | 0 | **No** (`dock`: CSS `dock: bottom`, `services-tab.md:220` "detail dock") | 0 doc hits for `Prompt Dock`; mild TUI CSS / detail-dock overlap |
| **`Prompt Bay`** | OK | 0 | 0 | Borderline (`bay`: 0 repo hits, but sci-fi bare) | 0 repo hits; slightly sci-fi metaphor |
| **`Prompt Slate`** | OK | 0 | 0 | **No** (`slate`: MkDocs `slate` color scheme, diagram colors) | 0 doc hits for `Prompt Slate` |
| **`Prompt Box`** | OK | 0 | 0 | **No** (`box`: search box, dialog box, box drawing) | 0 doc hits; diminutive |
| **`Prompt Input`** | OK | 30 | 74 | N/A | **DISQUALIFIED:** auto-derives plural `Prompt Inputs`, false-matching *"Open the Prompt Inputs panel before launch"* and *"Collect raw prompt inputs on submit"*! |
| **`Prompt Panel`** | OK | — | — | No | **DISQUALIFIED:** collides with `widgets/prompt_panel/` (`AgentPromptPanel`, 55 hits) |
| **`Prompt Deck`** | OK | — | — | No | **DISQUALIFIED:** collides with `Agent Data Deck` (`deck`, `Deck Panel`) |
| **`Prompt Drawer`** | OK | 0 | 0 | No (`drawer`: 19 doc hits, 32 prompt-history hits) | **DISQUALIFIED:** Patch `.sase` `CHAT:`/`PLAN:`/`DIFF:` lines are already called **drawers** |
| **`Prompt Bench`** | OK | 0 | 0 | No (`bench`: 15 doc hits) | **DISQUALIFIED:** `bench` already means SASE's perf benchmark harness (`just bench-*`) |

---

## 3. Evaluation Rubric

Candidates are judged on six criteria derived from SASE's prior naming decisions and the specific requirements in this request:

1. **Three-part structural fit:** Does the name naturally encompass (a) the Vim-modal authoring widget across its three modes, (b) vertical multi-agent + auxiliary stacks, and (c) the structured YAML property panel above the stack?
2. **Compound ergonomics:** How naturally do *"`<X>` stack"*, *"`<X>` property panel"*, and *"`<X>` pane"* read in everyday prompts and specs?
3. **Conciseness & shorthand:** Is it short to write and speak, and does it admit an unambiguous one-word shorthand (like `deck`, `card`, `stash`) and clean `glossary:<prefix>` lookup?
4. **Cold-start clarity for future agents:** Can an LLM agent infer its role immediately from the `AGENTS.md` glossary roster without guessing or misinterpreting?
5. **Collision cleanliness:** Zero conflict with existing SASE glossary terms, TUI widgets, `$EDITOR`, Patch/bench/CSS vocabulary, or `sase-core`'s auto-pluralizing glossary matcher.
6. **Industry alignment & adoption cost:** Fits established AI/TUI conventions and bridges cleanly from existing prose via glossary aliases.

---

## 4. Ranked List of Candidate Names

### 1. `Prompt Composer` (short alias: `composer`) — **Recommended #1**

- **Shape:** 2 words (15 chars) · 1-word alias `composer` (8 chars) · CLI: `glossary:composer` / `glossary:comp`.
- **Compounds:** *"composer stack"*, *"composer property panel"*, *"composer pane"*, *"open the prompt composer"*, *"hand off from the composer to `$EDITOR`"*.
- **Why it is #1:**
  - **Exact architectural fit for all three surfaces.** In modern AI coding tools, chat apps, and UI component systems (shadcn, Assistant UI, Slack, Linear, Gmail), a *composer* is specifically a rich multi-part authoring container — not a plain text box. Having a structured properties header (`FrontmatterPanel`) above a stack of editable panes (`#prompt-stack`) plus auxiliary macro/snippet panes, completions, and submit actions is *textbook* composer anatomy.
  - **Best shorthand & compound ergonomics.** It is the **only** strong candidate that safely unlocks a crisp, collision-free 1-word alias (`composer`) — matching `Agent Data Deck (deck)`, `Agent Data Card (card)`, and `Prompt Stash (stash)`. Saying *"composer property panel"* and *"composer stack"* avoids the 4-noun pileup of *"prompt bar property panel"*.
  - **Zero matcher collisions.** 0 hits in `docs/`, 0 in existing glossary strands, 0 in prompt history for both `Prompt Composer` and `composer`.
  - **Clean separation from `$EDITOR`.** *"Move from the composer to `$EDITOR` with `Ctrl+G g`"* is crystal clear.
- **Trade-offs to weigh:**
  - Longer in full form than `Prompt Bar` (4 syllables vs. 2), though shorter whenever you use `composer`.
  - Mild external echo of Cursor's former "Composer" agent mode (since merged into Cursor Agent) and 6 internal Python docstring uses of "composer" in unrelated SASE modules (`snippet_catalog_facade.py`, `pager/_body_lines.py`, `monitor/followup_prompt.py`). Neither causes real ambiguity in TUI/prompt contexts.
  - Introduces a new canonical label rather than codifying existing `prompt bar` doc prose (mitigated cleanly by keeping `prompt bar` and `prompt input widget` as glossary aliases).

### 2. `Prompt Bar` — **Best Zero-Friction Conservative Option**

- **Shape:** 2 words (10 chars, 2 syllables) · no safe 1-word alias · CLI: `glossary:prompt-b`.
- **Compounds:** *"prompt bar stack"* / *"the prompt bar's stack"*, *"prompt bar property panel"*, *"prompt-bar pane"*.
- **Why it is #2:**
  - **Already the codebase's de facto name:** 176 hits across `docs/` and `src/sase/`, class `PromptInputBar`, modules `_prompt_bar_*.py`, state `_active_prompt_bar`. Every one of its 58 matches in `docs/` is a true positive.
  - **Ultra-concise and zero metaphor budget.** Two short monosyllables; immediately recognizable to any developer.
  - **Fits SASE's `<qualifier> <surface>` TUI pattern** (`Node Panel`, `Deck Panel`, `Top Bar`, `Tab Bar`, `Prompt Stash`).
- **Why it loses to #1:**
  - **Mental-model understatement:** In SASE itself, `TopBar`, `TabBar`, `AgentsFilterBar`, and `BeadFilterBar` are all 1-row horizontal strips. Calling a tall multi-pane Vim stack + structured YAML property inspector a "bar" actively fights intuition (*why does a bar contain a vertical stack and a property panel?*).
  - **No 1-word shorthand:** Bare `bar` collides with `TopBar`, `TabBar`, `FilterBar`, and `foo/bar`.
  - **Awkward compounds:** *"prompt bar property panel"* stacks four nouns; *"bar property panel"* is unusable.
  - **Not even Bryan's own habit:** 0 hits in Bryan's prompt history (vs. 23 for `prompt input widget`), suggesting "bar" never felt quite right once stacks and the property panel landed.

### 3. `Prompt Pad` — **Best Punchy Two-Syllable Metaphor**

- **Shape:** 2 words (10 chars, 2 syllables) · no safe bare `pad` alias · CLI: `glossary:prompt-p`.
- **Compounds:** *"prompt pad stack"*, *"prompt pad property panel"*, *"pad pane"*.
- **Why it is #3:**
  - **Uncanny double meaning:** A *writing pad* is literally a stack of tear-off sheets (panes you navigate, reorder, tear off via `g<enter>` or `Ctrl+S` stash) bound under a top header (the property panel); a *launch pad* is where agents launch from.
  - **Zero collisions** in `docs/`, glossary, or prompt history (`Prompt Pad`: 0). Same compact 2-syllable weight as `Prompt Bar`.
- **Why it loses to #1 and #2:**
  - **Cold-start ambiguity with `Prompt Stash`:** An agent seeing `Prompt Pad` in the roster before reading the strand could easily mistake it for a persistent scratchpad (which is `Prompt Stash`), not the live submission widget.
  - **No safe bare alias:** `pad` collides with padding/alignment (`pad_left`, `<pad>`, `padding`).
  - The "launch pad" resonance drops away in `Plan Feedback`, `Coder Prompt`, and macro-editing modes.

### 4. `Prompt Dock` — **Best TUI-Layout / Spatial Option**

- **Shape:** 2 words (11 chars, 2 syllables) · no safe bare `dock` alias · CLI: `glossary:prompt-d`.
- **Compounds:** *"prompt dock stack"*, *"prompt dock property panel"*, *"dock pane"*.
- **Why it is #4:**
  - **Literally matches TUI geometry:** `PromptInputBar { dock: bottom; }` — a bottom-anchored expandable dock that hosts multiple stacked sub-regions (completion, property panel, stack) and dismisses cleanly.
  - Recognized TUI/IDE layout vocabulary (Ratatui/VS Code docked bottom regions), crisp 2 syllables, 0 occurrences of `Prompt Dock`.
- **Why it loses to #1–#3:**
  - **Container-first, not authoring-first:** "Dock" describes *where it sits*, not *what you do in it* (*"edit a macro in the prompt dock"* feels slightly mechanical).
  - **Minor internal collisions:** `docs/reference/tui/services-tab.md:220` already uses *"detail dock"* for the Services-tab schema help area, and `styles.tcss` uses `dock: bottom`/`dock: left` extensively, ruling out bare `dock` as an alias.

### 5. `Prompt Bay` — **Cleanest Multi-Slot Staging Metaphor**

- **Shape:** 2 words (10 chars, 2 syllables) · CLI: `glossary:prompt-ba` (shares `prompt-b` with nothing unless `Prompt Bar` existed).
- **Compounds:** *"prompt bay stack"*, *"prompt bay property panel"*.
- **Strengths:** Literally **0** occurrences anywhere in the repo (`bay: 0`). Evokes a multi-slot staging bay where agent prompts are stacked, configured with properties, and launched.
- **Weaknesses:** Noticeably sci-fi/industrial ("launch bay", "cargo bay"), less natural for writing prose or `Plan Feedback`, and slightly out of tune with SASE's grounded TUI terms (`Deck Panel`, `Node Panel`, `Nav Section`, `Prompt Stash`).

### 6. `Prompt Slate` — **Best Poetic / Writing-Surface Option**

- **Shape:** 2 words (12 chars, 2 syllables) · no safe bare `slate` alias (`data-md-color-scheme="slate"`).
- **Compounds:** *"prompt slate stack"*, *"prompt slate property panel"*.
- **Strengths:** 0 occurrences of `Prompt Slate`; dual sense of a clean writing surface *and* an ordered "slate" of agents to run.
- **Weaknesses:** Opaque on cold read from the glossary roster (agents won't immediately map "slate" to the bottom TUI input widget), and bare `slate` collides with MkDocs Material's dark theme name.

### 7. `Prompt Box` — **Ultra-Plain Minimalist Fallback**

- **Shape:** 2 words (10 chars, 2 syllables) · no safe bare `box` alias.
- **Compounds:** *"prompt box stack"*, *"prompt box property panel"*.
- **Strengths:** Plainest possible English, 0 existing hits in SASE, zero learning curve.
- **Weaknesses:** Even more diminutive than `Prompt Bar` — evokes a plain single `<textarea>` rather than a multi-pane stacked Vim editor with a structured YAML property panel and auxiliary snippet/mini-macro authoring.

---

## 5. Disqualified Candidates (and Why)

These plausible-sounding names were explicitly eliminated by codebase or matcher evidence:

| Disqualified name | Fatal flaw |
| --- | --- |
| **`Prompt Input`** | **Mechanically broken in `sase-core`:** auto-derives plural `Prompt Inputs`, false-highlighting the **Prompt Inputs** (`Fill in this prompt`) placeholder modal and `input:` prose. |
| **`Prompt Panel`** | **Direct widget collision:** `src/sase/ace/tui/widgets/prompt_panel/` (`AgentPromptPanel`, 55 hits) is the *read-only* Agents-tab detail view. |
| **`Prompt Editor`** | **Direct workflow collision:** in SASE, "the editor" means external `$EDITOR` (Neovim / `sase-nvim`, handed off via `Ctrl+G g`). |
| **`Prompt Deck`** | **Direct glossary collision:** `Agent Data Deck` (`deck`, `Deck Panel`) already owns `deck`. |
| **`Prompt Stack`** | **Part-for-whole error:** already names `#prompt-stack` (the pane list *inside* the widget); false in solo, `Plan Feedback`, and `Coder Prompt` modes, and makes *"how stacks work"* tautological. |
| **`Prompt Drawer`** | **Domain collision:** Patch `.sase` `CHAT:`/`PLAN:`/`DIFF:` lines are already called **drawers** (19 doc hits, 32 prompt-history hits). |
| **`Prompt Bench`** | **Domain collision:** `bench` already names SASE's perf benchmark harness (`just bench-*`, 15 doc hits). |
| **`Launch Pad` / `Launchpad`** | Collides semantically with **Launch Control** and is inaccurate for `Plan Feedback`, `Coder Prompt`, and macro/snippet authoring (none of which launch agents). |
| **`Prompt Tray` / `Shelf` / `Sheet` / `Strip` / `Rail`** | Each collides with an existing TUI surface (`#command-line-completion-tray`, `AgentArchiveShelf`, AXE `Property Sheet`, `AgentTabStrip`, node/note/link/block rails). |
| **`Prompt Stage` / `Console` / `Shell`** | Collide with tool/finalizer/seal stages (45 hits), Rich Console (167 hits), and retired `shell` terminology (`sase shell → sase turn`). |

---

## 6. Recommended Glossary Term Entry (#1 Pick: `Prompt Composer`)

Target file: **`sase/memory/glossary/prompt-composer.md`**

Verified against `sase.memory.web.frontmatter.parse_memory_strand` (0 parse errors) and `sase.core.glossary_facade.validate_glossary_entries` + `compile_glossary_catalog` over all 72 existing glossary strands (0 diagnostics; clean implicit links to `Macro`, `Prompt Stash`, and `Sase Agent`; 0 false positives on `Prompt Inputs`, `TopBar`, or `FilterBar`):

```markdown
---
keyword: Prompt Composer
aliases:
  - composer
  - prompt bar
  - prompt input widget
summary: Bottom-docked TUI authoring widget with multi-pane stacks and a structured YAML property panel.
---

The **Prompt Composer** (`composer`) is the bottom-docked TUI authoring widget
(`PromptInputBar`) for drafting agent prompts, editing targeted macro definitions, and
entering plan feedback or coder prompts. It hosts Vim-modal `PromptTextArea` panes,
Markdown and SASE syntax highlighting, token and next-word completion, incremental
search, `%dispatch` status, `g`/`Ctrl+G` leader hints, `$EDITOR` handoff (`Ctrl+G g`,
with ` @` review return), and bound macro editing (double border, `✎ <ref>` chip, `gw`
save). Full features run in `prompt` mode; `feedback` ("Plan Feedback") and
`approve_prompt` ("Coder Prompt") are single-pane modes without stacks, properties, or
stashing.

In `prompt` mode, the composer owns a **stack** (`#prompt-stack`, `PromptStackState`) of
one or more agent panes (`agent 1`, `agent 2`, …) in top-to-bottom launch order. Loaded
multi-agent Markdown splits top-level `---` lines into panes; typed `---` in INSERT
stays literal, and `g-` / `Ctrl+G -` appends a pane. The active pane expands while
parked panes stay compact beneath `PromptStackSeparator` rules carrying live cursor
readouts. Navigate with `gj`/`gk`, reorder with `gJ`/`gK`, submit one pane (`g<enter>`)
or the whole stack (`Enter` chooser, joining non-empty agent panes with `---` and
re-attaching shared frontmatter), and stash one pane (`Ctrl+S`) or all panes (`gs`) to
the [[glossary:prompt-stash]]. At most one pinned bottom **auxiliary pane** may join the
stack — a snippet pane (`gt`, `⇥ <trigger>`) or mini-macro pane (`gx`, `#<name>`) —
excluded from launches, stashes, and save-as, where `Enter` saves the definition.

Its **property panel** (`FrontmatterPanel`, `#frontmatter-panel`) sits directly above
`#prompt-stack` in `prompt` mode, toggled with `g=` / `Ctrl+G =` and auto-shown when
frontmatter or a macro target is present. It edits structured YAML fields (`name`,
`description`, `input:`, `macros:`, …) with foldable subtrees (`h`/`l`), an `a` property
picker, inline/cell editing (`e`/`Enter`, `o`/`A`, `d`, `u`), an `R` raw-YAML escape
hatch, and live `sase-core` validation (`⟨✓⟩` / `⟨! N⟩`), dropping empty frontmatter on
close. Its scope follows the stack's shared frontmatter on agent panes — feeding local
`macros:` and `input:` into completion, Jinja, and launches — and switches automatically
to the mini-macro's isolated frontmatter (`frontmatter #<name>`) while a mini-macro
auxiliary pane is active.

Distinct from `AgentPromptPanel` (`prompt_panel/`, the read-only Agents-tab detail
view), the Prompts overlay (`History`/`Stash`/`Trash` modal), the Prompt Inputs modal
(`<placeholder>` and `input:` collection on submit), and external `$EDITOR` / `sase-nvim`
sessions.
```

### Rollout Notes (If Accepted)

1. **Keep it glossary-only at first.** Do not rename `PromptInputBar`, `#prompt-input-bar`, `FrontmatterPanel`, or `prompt_stack.py` — the strand body names those exact symbols so future agents map cleanly from `Prompt Composer` / `composer` / `property panel` straight to the code.
2. **Optional 4th alias:** Add `prompt input bar` to `aliases:` if you also want prose mentions of "prompt input bar" underlined in the TUI (kept out above to keep the always-loaded `AGENTS.md` roster entry compact: `Prompt Composer (composer, prompt bar, prompt input widget)`).
3. **Roster wrap check:** Alphabetically, `Prompt Composer` sorts after `Macro (xprompt)`, so running `sase memory init` does **not** disturb the allowlisted `Macro (xprompt)` roster line pinned in `tests/_macro_terminology_docs.py`.
4. **Quick verification after landing:**
   - `sase memory init`
   - `sase memory read glossary:composer -r "Verify Prompt Composer strand"`
   - Confirm in the TUI that *"prompt composer"*, *"composer"*, *"prompt bar"*, and *"prompt input widget"* underline in muted blue while *"Prompt Inputs"* and *"top bar"* stay plain.

---

## Sources

- **Codebase (verified at `811576c390`):**
  - `src/sase/ace/tui/widgets/prompt_input_bar.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_lifecycle.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_title.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_subtitles.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_frontmatter.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_stack_rendering.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_stack_separator.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_stack_navigation.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_submission_actions.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_mini_macro_pane.py`
  - `src/sase/ace/tui/widgets/_prompt_input_bar_snippet_pane.py`
  - `src/sase/ace/tui/widgets/_prompt_stack_state.py`, `_prompt_stack_targets.py`
  - `src/sase/ace/tui/widgets/frontmatter_panel.py`, `_frontmatter_panel_rendering.py`
  - `src/sase/ace/tui/widgets/prompt_text_area.py`, `prompt_panel/__init__.py`
  - `src/sase/ace/tui/modals/property_picker_modal.py`
  - `src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount_home.py`
  - `src/sase/ace/tui/styles.tcss`
  - `src/sase/core/glossary_facade.py`, `src/sase/memory/web/frontmatter.py`
  - `tests/_macro_terminology_docs.py`
- **Docs & audited memory/artifact reads:**
  - `docs/reference/tui/{prompt-input,prompt-stacks,prompt-modes,prompt-completion,prompt-completion-panels,prompts-overlay,snippets,services-tab,tabs-and-panes,index}.md`
  - `docs/reference/memory/memory.md`, `docs/blog/posts/prompt-widget-and-nvim.md`
  - Audited memory read: full `glossary` web (72 strands), `sase_artifacts.md`, `tui.md`
  - Audited prior naming research: `research:202609/sase_terminology_renames/sase_terminology_renames.md`, `research:202610/macro_invocation_glossary_term_smack/macro_invocation_glossary_term_smack__final.md`, `research:202608/naming_the_change_unit/naming_the_change_unit.md`
- **Live verification:**
  - `sase.core.glossary_facade` validation, effective-alias derivation, and corpus span scan over `docs/reference/tui/*.md`, `docs/**/*.md`, and all 72 glossary strands.
  - `sase.memory.web.frontmatter.parse_memory_strand` parse check on the proposed strand file.
  - Aggregate frequency scan over local `~/.sase/prompt_history/` shards.
