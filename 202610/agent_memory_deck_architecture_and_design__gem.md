# Agent Memory Deck Architecture & Design: Critique, Placement Analysis, and Implementation Blueprint

**Researcher**: `research.4x.gem`  
**Date**: October 19, 2026  
**Topic**: Decoupling Agent Instruction Bundles from the Files Deck and Establishing a Dedicated Memory Deck in SASE TUI  
**Target Artifact**: `research:202610/agent_memory_deck_architecture_and_design__gem.md`

---

## Executive Summary & Core Verdict

In the SASE ACE TUI, the Agents tab provides developers with a multi-deck interface (`MAIN`, `FILES`, `TOOLS`, `FINAL`, `RECORD`) to inspect the complete operational state of an agent. In recent release `v0.18.0` (commit `552b38f7ed`, bead `sase-1lj.4`), support was added to inspect an agent's compiled instruction bundle (`00-bundle.md`) directly within the TUI. As an expedient landing mechanism, this bundle was injected into the **Files deck** alongside git diffs and modified files.

This research report investigates and critiques the proposal to:
1. Extract the instruction bundle out of the Files deck.
2. Establish a new **Memory deck** (`DeckId.MEMORY`) that houses the instruction bundle, on-demand reference memory reads, and potentially prompt macros.
3. Evaluate whether these elements should instead live in an existing deck, particularly the **Record deck** (`DeckId.RECORD`).

### The Verdict

* **Proceed with a dedicated Memory deck (`DeckId.MEMORY`)**: Elevating agent memory to a top-level deck is structurally and philosophically aligned with SASE. SASE is founded on Structured Agentic Software Engineering, where durable memory (core notes, reference notes, memory webs) is a first-class citizen. Grouping the prompt compilation bundle and on-demand retrievals into a dedicated surface provides the missing "Cognitive Context" pane.
* **Firmly reject stuffing instruction bundles and memory reads into the Record deck**: The Record deck is a compact tabular metadata ledger (averaging 15–30 lines per card across Lifecycle, Provenance, Relations, and Links). Injecting a 1,500-line Markdown instruction bundle or multi-page memory read reports into Record creates a severe ergonomic and visual impedance mismatch, destroys Record's spread-mode heuristics, and pollutes its identity.
* **Completely purge instruction bundles from the Files deck**: Files deck semantics ("*Diffs and files the agent touched*") are violated by host-generated instruction bundles. Removing them restores pure workspace diff/edit visibility and eliminates false-positive availability signals for read-only agents.
* **Adjust Deck Placement & Cycle Order**: Rather than appending Memory as deck #6 at the far end of the cycle, place `MEMORY` immediately after `MAIN` (`MAIN` $\to$ `MEMORY` $\to$ `FILES` $\to$ `TOOLS` $\to$ `FINAL` $\to$ `RECORD`). When investigating an agent, navigating between the agent's generated reply (`MAIN`) and the instructions/memory that governed that reply (`MEMORY`) is the highest-frequency contextual leap.
* **Resolve the Picker Key Collision**: In the `p` (pick deck) modal, `m` is already bound to `MAIN`. We recommend binding `e` (m**E**mory) to the Memory deck, following the exact precedent established when `n` was chosen for fi**N**al because `f` was claimed by Files.

---

## 1. Critique of Current State & The Proposed Change

### 1.1 How Instruction Bundles Landed in Files (`sase-1lj.4`)

In `src/sase/ace/tui/widgets/file_panel/_file_list.py`:
```python
extra_files = list(agent.extra_files)
pages.extend(extra_files)
from ._instruction_bundles import instruction_bundle_pages

pages.extend(instruction_bundle_pages(agent))
```

During epic `sase-1lj.4`, the team needed a way to verify that rendered instruction bundles matched host manifests. Because `AgentFilePanel` already possessed syntax-highlighted Markdown viewing and file pagination, appending `run_bundle_paths(artifacts_dir)` to `desired_file_pages` was a rapid zero-infrastructure solution.

### 1.2 The Three Critical Flaws of the Current Files Deck Placement

While functional, this placement introduces three significant technical and usability flaws:

1. **Semantic Dissonance**:
   According to `src/sase/ace/tui/widgets/decks/spec.py`:
   ```python
   _DeckSpec(
       deck_id=DeckId.FILES,
       name="FILES",
       blurb="Diffs and files the agent touched",
       count_noun=("file", "files"),
   )
   ```
   An instruction bundle (`00-bundle.md`) is **not** a file the agent touched, edited, or produced. It is the static system prompt injected by the host runtime before the agent began execution. Mixing injected system rules into a list of repository code diffs creates cognitive confusion.
2. **Availability & Count Distortion**:
   In `src/sase/ace/tui/widgets/decks/availability.py`, `probe_files_deck()` checks whether `desired_file_pages(agent)` is non-empty. If an agent performs a read-only investigation (or fails immediately on startup) without modifying any workspace files, `probe_files_deck()` returns `has_content=True` with `count=1`. The Files deck lights up in the deck switcher, misleading the developer into thinking changes were staged when only a bundle file exists.
3. **Paging Friction**:
   When reviewing an agent's code modifications with `ctrl+n` / `ctrl+p` (next/prev file), the developer is forced to cycle past `00-bundle.md` and any helper bundles before reaching actual code diffs.

### 1.3 Fragmentation of Agent Memory Across the TUI Today

Currently, an agent's memory and prompt context is splintered across multiple disconnected locations in the TUI:

| Information Asset | Current Location in TUI | Visual Presentation | Limitation |
| :--- | :--- | :--- | :--- |
| **Instruction Bundle** | `FILES` deck | Static file page | Clutters code diffs; lacks manifest metadata (tokens, layers, SHA). |
| **Launched Instruction Status** | `MAIN` deck (Context card preamble) | Single row in `MEMORY` lane | Only shows launch channel, size, and hash match badge. |
| **Audited Memory Reads** | `MAIN` deck (Context card preamble) | Compact lane in `SASE CONTEXT` | Capped at 5 reads; truncated reasons; no body content. |
| **Memory Read Full Content** | Ephemeral Hint Modal | Triggered via `[1]` hint marker | Materializes a temporary report popup; detached from deck navigation. |
| **Glossary Lookups** | `MAIN` deck (Context card preamble) | Compact lane in `SASE CONTEXT` | Separate lane from Memory; capped; requires hint modal to read. |
| **Prompt Macros** | `MAIN` deck (Detail Header) | Chip row in compact header | Summary count and truncated argument chips only. |
| **Bundle Archive Path** | `RECORD` deck (`Provenance` card) | `Bundle: /path/to/archive.tgz` | Bare text string pointing to disk; non-renderable. |

This fragmentation confirms that the user's instinct is entirely correct: **Agent memory lacks a unified, cohesive home.**

---

## 2. Architectural Placement Analysis: Where Does Memory Belong?

The user requested:
> *"Think hard about what other cards/blocks should be included and whether or not these cards actually belong in a different existing deck (the record deck maybe?)."*

To answer this rigorously, we evaluate the three credible options:
* **Option A**: A New Dedicated `MEMORY` Deck.
* **Option B**: Integrating into the Existing `RECORD` Deck.
* **Option C**: Restructuring and Expanding the `MAIN` Deck.

### 2.1 Option B: Integrating into the `RECORD` Deck (Deep Rebuttal)

Could we simply add an "Instructions" card and a "Memory" card to the `RECORD` deck?

At first glance, this seems appealing because `RECORD` already houses `Provenance` and `Lifecycle`. However, a deep architectural and visual analysis demonstrates that **this is a severe anti-pattern**:

1. **Document Scale & Density Mismatch**:
   Let us inspect the existing cards in `src/sase/ace/tui/widgets/decks/record/`:
   * `Lifecycle`: Status, times, runtimes, outcome, revival, restartability (~15 lines).
   * `Provenance`: Project, workspace, model, provider, owner, artifacts dir (~20 lines).
   * `Relations`: Parent, retry, clan links (~15 lines).
   * `Links`: Outgoing and incoming artifact graph links (~20 lines).
   
   Every card in `RECORD` is a **compact key-value fact sheet** rendered using simple `rich.text.Text` strings. In contrast, an instruction bundle (`00-bundle.md`) is a **massive 1,000 to 2,500-line Markdown document** containing full policy notes, tool definitions, and system prompts.
   
   If `Instructions` were card #3 in `RECORD`:
   * Cycling cards with `ctrl+j` / `ctrl+k` would jump from a 15-line tabular overview to an overwhelming 1,500-line wall of Markdown, and then back to a 15-line Relations table.
2. **Spread-Mode Heuristic Destruction**:
   In `src/sase/ace/tui/widgets/decks/record/document.py`:
   ```python
   def decide_record_mode(card_count: int) -> RenderMode:
       if card_count <= 1:
           return RenderMode.SPREAD
       return RenderMode.PAGED
   ```
   When a deck renders in spread mode, all cards are stacked vertically on a single scrollable page. While `RECORD` currently pages multi-card documents, users can force spread mode via `P` (`cycle_deck_view`). Spreading a 1,500-line Markdown document across concise metadata cards renders the metadata virtually unfindable.
3. **Rendering Pipeline Divergence**:
   `RecordView` (`src/sase/ace/tui/widgets/decks/record/view.py`) is optimized for static metadata formatting. It lacks Markdown parser caching, header collapsible folding, and code-block syntax styling. Turning `RecordView` into a hybrid metadata-table plus full-text Markdown reader introduces unnecessary complexity into a clean, single-purpose widget.
4. **Conclusion on `RECORD`**:
   `RECORD` is an **audit ledger**, not a **document library**. `RECORD.Provenance` should retain a lightweight link/hash to the bundle (`Bundle: 00-bundle.md · bytes match`), but the actual content must live elsewhere.

### 2.2 Option C: Expanding the `MAIN` Deck

Could `MAIN` deck house the instruction bundle as a card alongside `Context` and `Reply`?

* `MAIN` currently consists of:
  * Card 1: `Context` (`CONTEXT_CARD_ID` = `"context"`)
  * Card 2: `Reply` (`REPLY_CARD_ID` = `"reply"`)
* If we added Card 3: `Instructions`:
  * **Pros**: Keeps the total deck count at 5; avoids adding a 6th deck to the deck cycle.
  * **Cons**: `MAIN` is the live operational cockpit of the agent. When an agent is running or streaming, the user constantly focuses on the `Reply` card (or toggles between Prompt and Reply). Adding a static 2,000-line instruction document between or after these cards dilutes the rapid feedback loop of the `MAIN` deck.
  * Furthermore, `MAIN` already struggles with vertical space in its `Context` card, where 7 different lanes (`BEAD`, `PLAN`, `ARTIFACTS`, `MEMORY`, `GLOSSARY`, `SKILLS`, `WORKSPACES`) compete for room.

### 2.3 Option A: Dedicated `MEMORY` Deck (The Superior Architecture)

Creating a dedicated `MEMORY` deck (`DeckId.MEMORY`) cleanly resolves the systemic issues:
* **Separation of Concerns**: Workspace code changes stay in `FILES`; operational streaming stays in `MAIN`; audit metadata stays in `RECORD`; agent knowledge and prompt architecture live in `MEMORY`.
* **Rich Document Model**: The deck can be built on `CardDocumentView`, supporting full Markdown rendering, block navigation, and spread/paged transitions.
* **First-Class SASE Alignment**: It reflects SASE's core architectural principle that agent memory is as vital as agent code.

---

## 3. Deck Taxonomy: What Cards and Blocks Belong in `MEMORY`?

A dedicated `MEMORY` deck must not be a one-trick pony that only shows the static `00-bundle.md` file. It should serve as the comprehensive **Cognitive Context** of the agent.

We recommend a four-card structure (plus one high-value optional fifth card):

```
┌────────────────────────────────────────────────────────────────────────┐
│  ◈ MEMORY DECK                                                         │
├──────────────┬──────────────┬──────────────┬─────────────┬─────────────┤
│ Instructions │ Memory Reads │   Strands    │   Macros    │ [Coverage]  │
│    (Card)    │    (Card)    │    (Card)    │   (Card)    │   (Card)    │
└──────────────┴──────────────┴──────────────┴─────────────┴─────────────┘
```

### Card 1: `Instructions` (card_id: `bundle`, Title: `Instructions`)

The foundation of the deck: what the agent was told before turn 1.

* **Preamble Header (Telemetry & Manifest)**:
  Extracted from `<artifacts_dir>/instructions/00-manifest.json` via `RunManifest`:
  * **Delivery Metadata**: Sequence (`00`), Provider (`claude` / `codex` / `grok`), Model name, Attempt number.
  * **Integrity Status**: `bytes match` (green) or `MISMATCH` (bold red) with SHA-256 digest preview.
  * **Channel & Timing**: Delivery channel (`explicit` / `stdin`), Render time (`render_ms`), Rendered timestamp.
  * **Sizing**: Estimated tokens (`tokens_est`), total bytes, total line count.
  * **Layer Breakdown**: Token/byte breakdown across base layers (System Directive, Core Memory, Reference Inventory, Memory Web Descriptors, Helper Instructions).
* **Card Blocks (`CardBlock`)**:
  * **Block 0 (`00-bundle`)**: The primary root bundle (`00-bundle.md`).
  * **Blocks 1..N (`01-helper`, etc.)**: If helper invocations occurred (e.g. `01-codex.helper.md`), each helper bundle renders as an additional block within the card, navigable with `[` and `]`.
* **Body Rendering**:
  Rendered Markdown with syntax-highlighted code blocks, formatted headers, and standard GitHub alert styling.

### Card 2: `Memory Reads` (card_id: `reads`, Title: `Memory Reads`)

What the agent dynamically retrieved during execution.

* **Data Source**:
  Audited `MemoryReadEvent` entries recorded in `memory_reads.jsonl` (loaded via `src/sase/ace/tui/memory_reads.py`).
* **Behavior & Content**:
  * If zero reads: Clean empty state ("*No on-demand memory reads recorded during this turn. Core memory was delivered via the Instruction Bundle.*").
  * If $\ge 1$ reads: Each read event forms a distinct `CardBlock` (or vertical spread section):
    * **Block Header**: `[#] <local-time> ◈ <canonical_path>` with version chip (`[v3:abc1234]`) and agent role label.
    * **Audit Reason**: The required reason passed to `sase memory read -r "<reason>"` rendered in distinct styling (`#FFAF5F`).
    * **Reproduced Output**: The actual Markdown content returned to the agent during that read (reconstructed via `MemoryReadReportSpec` without triggering a modal popup).
* **User Value**:
  Developers no longer need to click tiny `[1]` hint markers in the Main deck to spawn ephemeral modal pagers. The entire reading history is browsable and searchable in-place.

### Card 3: `Strands` (card_id: `strands`, Title: `Strands & Webs`)

Keyed memory collection lookups.

* **Data Source**:
  `MemoryReadEvent` where `kind in ("web", "strand")` (e.g., `glossary:stitch`, `decisions:gates-never-block`, `task_types:bug`).
* **Why Separate from General Reads?**
  In SASE, memory webs possess unique closure mechanics: reading a glossary term evaluates the transitive closure of all dependent terms and formats them together.
* **Content**:
  * Grouped by Web (`glossary`, `decisions`, `task_types`).
  * Displays the requested term, the reason for consulting it, and the expanded strand definition.
  * *Design Alternative*: If an agent only has 1 strand read and 1 note read, splitting them into separate cards can feel sparse. In the technical blueprint below, we discuss combining Cards 2 and 3 into a single **`Reads`** card with tag badges (`[note]` vs `[strand]`) if card minimalism is desired.

### Card 4: `Macros` (card_id: `macros`, Title: `Prompt Macros`)

The prompt expansion layer.

* **Critique: Do Macros Belong in a Memory Deck?**
  The user explicitly asked:
  > *"This deck would also include cards for other types of memory (and maybe macros?) that the agent used."*
  
  We must be intellectually honest about the SASE taxonomy:
  * **SASE Memory** (`sase/memory/`) is durable project knowledge written in Markdown.
  * **Macros** (`src/sase/macros/`) are prompt templates (`#workflow`, `#part`, `#swarm`) that expand user prompts.
  
  Strictly speaking, macros are **prompt authoring mechanisms**, not memory notes.
  
  **However**, from the developer's debugging mental model:
  > *"What was this agent told, and what context was it given?"*
  
  Context is composed of two streams:
  1. The systemic instructions & memory (Bundle + Reads).
  2. The prompt expansion template & evaluated parameters (Macros).
  
  Therefore, including a `Macros` card in this deck is **justified and highly practical**, provided it is clearly titled `Macros` or `Prompt Macros`.
* **Content**:
  * Loaded from `macros.json` / `macros_{step_name}.json` via `load_macros_used(agent)`.
  * Renders each macro with its signature glyph: `⌘` (workflow), `▣` (part), `❋` (swarm).
  * Displays evaluated positional arguments, named flags, and the template preview.

### Card 5 (Recommended Addition): `Coverage` (card_id: `coverage`, Title: `Memory Coverage`)

A novel, high-impact card uniquely suited for SASE:

* **What it does**:
  Compares the project's total memory catalog (`sase memory list`) against what this specific agent actually received.
* **Matrix Display**:
  1. **Core Notes (Inlined)**: Marked with `✔ inlined` (e.g., `sase.md`, `gotchas.md`).
  2. **Reference Notes (Read On-Demand)**: Marked with `◈ read` and timestamp (e.g., `tui.md`).
  3. **Reference Notes (Untouched)**: Marked with `dim · unread` (e.g., `cli_rules.md`, `demos.md`).
  4. **Web Strands Consulted**: List of glossary terms / decision records resolved.
* **Why this is killer**:
  When an agent makes a mistake (e.g., violates a CLI guideline), the developer opens `Coverage` and immediately sees:
  * *`cli_rules.md` was available as reference memory, but the agent never called `sase memory read cli_rules.md`.*
  This transforms agent debugging from guesswork into instant root-cause analysis.

---

## 4. Technical TUI Architecture & Ergonomics

Integrating a 6th deck into the Textual ACE TUI requires addressing navigation ergonomics, picker key mappings, and layout lifecycle.

### 4.1 The Picker Key Conflict

In `src/sase/ace/tui/widgets/decks/spec.py`:
```python
DECK_SPECS: tuple[_DeckSpec, ...] = (
    _DeckSpec(DeckId.MAIN,   name="MAIN",   picker_key="m", ...),
    _DeckSpec(DeckId.FILES,  name="FILES",  picker_key="f", ...),
    _DeckSpec(DeckId.TOOLS,  name="TOOLS",  picker_key="t", ...),
    _DeckSpec(DeckId.FINAL,  name="FINAL",  picker_key="n", ...),
    _DeckSpec(DeckId.RECORD, name="RECORD", picker_key="r", ...),
)
```

The picker keys are single characters used in the `p` (pick deck) modal. Capital letters (`M`, `F`, `T`, `N`, `R`) target the "other split panel". Furthermore, `j`, `k`, `q`, `enter`, `escape` are reserved for modal navigation.

`m` is already claimed by `MAIN`. What key should `MEMORY` use?

| Key Candidate | Mnemonic | Conflict / Usability Evaluation | Verdict |
| :---: | :---: | :--- | :---: |
| `m` | **M**emory | Directly conflicts with `MAIN` (`m`). Changing `MAIN` breaks muscle memory. | **Rejected** |
| `e` | m**E**mory | Available. Follows the exact precedent of `FINAL` using `n` (fi**N**al) because `f` was taken by Files. | **Recommended (#1)** |
| `i` | **I**nstructions | Available. Highly mnemonic if the deck is conceptualized as Instructions & Memory. | **Recommended (#2)** |
| `y` | memor**Y** | Available, but visually awkward on a QWERTY layout. | Feasible |
| `b` | **B**undle | Available, but overly specific to the first card. | Mediocre |

**Recommendation**: Set `picker_key="e"` (or `"i"`). In the picker UI, display:
`[e] MEMORY  ◈  Instructions, memory reads, and prompt macros`

### 4.2 Deck Cycle Order

Currently, `active_deck_cycle()` in `spec.py` returns:
`MAIN` $\to$ `FILES` $\to$ `TOOLS` $\to$ `FINAL` $\to$ `RECORD`

If we simply append `MEMORY` at the end:
`MAIN` $\to$ `FILES` $\to$ `TOOLS` $\to$ `FINAL` $\to$ `RECORD` $\to$ `MEMORY`
...a user on `MAIN` pressing `ctrl+n` must hop through 5 decks to reach `MEMORY`.

**Recommended Cycle Order**:
Place `MEMORY` in position 2, immediately following `MAIN`:
$$\text{MAIN} \longleftrightarrow \text{MEMORY} \longleftrightarrow \text{FILES} \longleftrightarrow \text{TOOLS} \longleftrightarrow \text{FINAL} \longleftrightarrow \text{RECORD}$$

* **Rationale**:
  * `MAIN` is what the agent **said/did**.
  * `MEMORY` is what the agent **knew/read**.
  * `FILES` is what the agent **wrote to disk**.
  * `TOOLS` is how the agent **executed commands**.
  * `FINAL` is how the node **landed & verified**.
  * `RECORD` is the agent's **audit provenance**.
  
  Toggling between `MAIN` and `MEMORY` with a single keystroke (`ctrl+n` / `ctrl+p`) creates an exceptionally fluid inspection workflow.

### 4.3 Visual Styling & Specifications

To ensure seamless integration with the existing Textual theme palette:
* **`DeckId`**: `DeckId.MEMORY = "memory"`
* **Name**: `"MEMORY"`
* **Glyph**: `◈` (Matches `COLOR_MEMORY_GLYPH` already used across SASE headers)
* **Fallback Accent**: `"#87D7FF"` (Soft cyan/sky blue) or `"#A3BE8C"` (Muted sage green)
* **Accent Class**: `"-deck-memory"`
* **Picker Class**: `"-deck-memory"`
* **Count Noun**: `("source", "sources")` or `("card", "cards")`
* **Blurb**: `"Instructions, memory reads, and prompt macros"`

### 4.4 Availability Probing Contract

In `src/sase/ace/tui/widgets/decks/availability.py`:
```python
def probe_memory_deck(agent: Agent, *, attempt_number: int | None) -> DeckAvailability:
    """Probe Memory deck availability without I/O."""
    if attempt_number is not None:
        return DeckAvailability(False, 0)
    if agent.is_clan_container or agent.is_named_proc:
        return DeckAvailability(False, 0)
        
    # Check for bundle or cached memory reads
    has_bundle = bool(getattr(agent, "instruction_bundle_files", None))
    # Memory deck is available for any agent that has an instruction bundle
    if has_bundle:
        return DeckAvailability(True, count=None)
    return DeckAvailability(False, 0)
```
Because every real SASE agent run compiles an instruction bundle, the Memory deck is reliably available across all standard agent runs, avoiding flickers or unexpected disabling.

---

## 5. Step-by-Step Implementation Blueprint

This section provides the concrete engineering blueprint for implementing the feature across the SASE codebase.

### Phase 1: Core Deck Infrastructure
1. **`src/sase/ace/tui/widgets/decks/model.py`**:
   * Add `MEMORY = "memory"` to `DeckId(StrEnum)`.
   * Update `DECK_CYCLE` to include `DeckId.MEMORY` in position 2.
2. **`src/sase/ace/tui/widgets/decks/spec.py`**:
   * Register `_DeckSpec` for `DeckId.MEMORY`:
     * `picker_key="e"`
     * `glyph="◈"`
     * `blurb="Instructions, memory reads, and prompt macros"`
3. **`src/sase/ace/tui/widgets/decks/card_documents.py`**:
   * Add `DeckId.MEMORY` to `CARD_DOCUMENT_DECKS`.
   * In `resolve_document_deck()`, map `case DeckId.MEMORY: return DeckId.MEMORY`.
   * In `document_view()`, map `case DeckId.MEMORY: return self.memory_view`.
   * In `document_for()`, map `case DeckId.MEMORY: return self._memory_document`.
4. **`src/sase/ace/tui/widgets/decks/availability.py`**:
   * Add `probe_memory_deck()`.
   * Update `probe_files_deck()` to remove instruction bundles from its file count.

### Phase 2: Decouple Instruction Bundles from Files Deck
1. **`src/sase/ace/tui/widgets/file_panel/_file_list.py`**:
   * Remove lines 66–68:
     ```python
     # DELETE:
     # from ._instruction_bundles import instruction_bundle_pages
     # pages.extend(instruction_bundle_pages(agent))
     ```
   * In `source_label_for_slot()`, remove the special `tag="bundle"` branch for `/instructions/`.
2. **`src/sase/ace/tui/widgets/_agent_detail_files.py`**:
   * Remove `instruction_bundle_files` checks from `_dispatch_file_view()` so read-only runs without file edits do not open the Files deck.

### Phase 3: Create the `decks/memory/` Subsystem
Create directory `src/sase/ace/tui/widgets/decks/memory/`:
* **`model.py`**:
  * Define `MemorySubject`: pump-captured identity, artifacts dir, bundle path, agent name, project.
  * Define `MemoryExtras`: worker-loaded bundle text, `RunManifest`, `MemoryReadEvent` list, `macros_used` list.
* **`cards/bundle_card.py`**:
  * Implements `build_bundle_card(extras: MemoryExtras) -> CardPart`.
  * Formats manifest telemetry header + Markdown text of `00-bundle.md` (and helper bundles as `CardBlock`s).
* **`cards/reads_card.py`**:
  * Implements `build_reads_card(extras: MemoryExtras) -> CardPart`.
  * Transforms `MemoryReadEvent` tuples into titled `CardBlock` items with reasons and reproduced Markdown bodies.
* **`cards/macros_card.py`**:
  * Implements `build_macros_card(extras: MemoryExtras) -> CardPart`.
  * Formats parsed macro invocations from `macros.json`.
* **`document.py`**:
  * Implements `build_memory_document(subject: MemorySubject, extras: MemoryExtras) -> MainDeckDocument`.
  * Assembles cards in order: `bundle`, `reads`, `strands`, `macros`.
* **`view.py`**:
  * Implements `MemoryDeckView(CardDocumentView)` specialized for `DeckId.MEMORY`.
* **`loader.py`**:
  * Implements off-thread `load_memory_extras(subject: MemorySubject) -> MemoryExtras`.
  * Performs disk I/O off the Textual UI event loop.

### Phase 4: DeckPanel Mixin & Navigation
1. **`src/sase/ace/tui/widgets/decks/panel_memory.py`**:
   * Create `DeckPanelMemoryMixin` modeled after `DeckPanelRecordMixin` and `DeckPanelFilesMixin`.
   * Manages `_memory_document`, `show_memory_document()`, and `_cycle_memory_card()`.
2. **`src/sase/ace/tui/widgets/decks/panel.py`**:
   * Inherit from `DeckPanelMemoryMixin`.
   * Mount `MemoryDeckView` in `compose()`.
3. **`src/sase/ace/tui/widgets/decks/panel_navigation.py`**:
   * Add `DeckId.MEMORY` card cycling handlers (`ctrl+j` / `ctrl+k`).

### Phase 5: Streamline `MAIN` Deck's Context Header
With full memory content living in the Memory deck:
1. In `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_reads.py`:
   * Retain the compact `MEMORY` lane in `SASE CONTEXT`, but replace the awkward modal hint markers `[1]` with a clean pointer hint:
     `→ [e] Memory deck for full content and audit`
2. This eliminates redundant popups and trains users to use the deck system naturally.

---

## 6. Testing & Verification Strategy

To satisfy SASE quality gates and prevent regressions:

1. **Unit Testing**:
   * `tests/ace/tui/widgets/decks/test_deck_memory.py`:
     * Test `build_memory_document()` with empty reads, single reads, multi-reads, and helper bundles.
     * Verify card order, block partitioning, and default card selection.
   * `tests/ace/tui/widgets/file_panel/test_file_list_no_bundles.py`:
     * Verify that `desired_file_pages()` strictly returns git diffs and workspace files, never bundle markdown files.
   * `tests/ace/tui/widgets/decks/test_deck_specs.py`:
     * Verify `spec.py` integrity, picker key uniqueness (no collision between `m` and `e`), and active cycle length (6 decks).
2. **Deterministic Visual Snapshot Testing**:
   * SASE maintains strict visual snapshot coverage via `tests/ace/tui/snapshots/test_ace_png_snapshots_agents_deck_views.py`.
   * Update visual baselines:
     * Add `test_agents_deck_view_memory_bundle_160x40.png`
     * Add `test_agents_deck_view_memory_reads_160x40.png`
     * Re-record `test_agents_deck_view_files_160x40.png` confirming the removal of `00-bundle.md` from the Files deck.

---

## 7. Summary of Justified Requirements Adjustments

To ensure the ultimate implementation is resilient and intuitive, we recommend the following adjustments to the user's initial proposal:

| Proposed Requirement | Recommended Adjustment | Rationale |
| :--- | :--- | :--- |
| *Show bundle in a new memory deck* | **Approved** | Cleanly separates system prompts from workspace code diffs. |
| *Include cards for other types of memory* | **Approved (with grouping)** | Include `Memory Reads` (on-demand) and `Strands` (webs), with block navigation per read event. |
| *Include macros in Memory deck* | **Approved with clear labelling** | Title the card `Prompt Macros` to distinguish template expansions from Markdown memory notes (`sase/memory/`). |
| *Consider moving these cards to Record deck* | **Rejected** | Record is a compact tabular metadata sheet. Long-form Markdown documents destroy Record's density and spread heuristics. |
| *Deck placement in cycle* | **Adjusted (Move to #2)** | Place `MEMORY` immediately after `MAIN` rather than at the end, minimizing cycle distance between prompt reply and prompt instructions. |
| *Picker key assignment* | **Assigned to `e` (or `i`)** | Resolves the direct collision with `MAIN` (`m`) while preserving mnemonic clarity. |
| *Add Memory Coverage Matrix* | **Added as High-Value Feature** | Add a `Coverage` card displaying what project memory was inlined vs read vs unread. |

---

## Conclusion & Next Steps

The proposal to transition agent instruction bundles and memory reads into a dedicated **Memory deck** is an outstanding architectural improvement. It rights a temporary wrong introduced in `sase-1lj.4`, cleanses the Files deck, unifies fragmented memory viewers, and elevates SASE's memory subsystem to its rightful place as a first-class citizen in the TUI.

By positioning the deck immediately after `MAIN`, utilizing `e` as the picker key, and pairing the bundle with on-demand reads and coverage telemetry, SASE will gain one of the most powerful agent inspection interfaces available in modern AI tooling.
