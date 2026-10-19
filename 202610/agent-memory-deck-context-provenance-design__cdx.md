# An agent Memory deck: captured knowledge, separate from run provenance

Independent research by **cdx**, 2026-10-19.

**Recommendation:** Add a **Memory** deck, beginning with **Instructions** and **Recalled Memory** cards. Make it a historical view of recorded knowledge inputs, with explicit evidence and version labels. Keep macro invocation mechanics in **Record → Provenance**, and retain the authored/materialized prompt in **Main**. Add **Skills** and **References** cards when their existing evidence can be projected accurately; do not require a new universal context ledger before shipping the useful core.

The idea is good because an instruction bundle is an input to the agent, while the Files deck primarily explains its work products. Its value goes beyond moving a file: it should answer “Which guidance was supplied, which additional knowledge was retrieved, and can I inspect the historical content?” It cannot answer “What did the model believe, attend to, obey, or still remember?”

## Scope and method

I inspected the current SASE implementation, its relevant tests, the linked Rust core, audited SASE memory, and a small number of official product documents. This was an independent investigation: I did not read any other swarm researcher's report, transcript, or findings. No application code was changed and no application test suite was run. Findings below are based on source inspection, not a live usability study or measured performance experiment.

Code baselines:

- `sase`: `4b7b98153227a355e7d183ea25df4d56694e2998`.
- `sase-core`: `753fa21aa5b1d042d23112c04d30b0acd4159970`.

Pinned source links below identify what was inspected. Proposed behavior is explicitly described as a recommendation rather than an existing capability.

## 1. What the code already provides

### The change is more than a new deck registry entry

The current registry has **Main, Files, Tools, FINAL, and Record**. Record's four cards are **Lifecycle, Provenance, Relations, and Links**. Its description is already “Lifecycle, provenance, relations, links,” making it the appropriate place for run construction and relationship facts. The cards are presentation over existing records, not a separate data store. [Deck registry](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/spec.py), [Record document](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/record/document.py).

Files appends instruction bundle paths after commit/live/linked diffs and extra files. Completed agents retain bundle paths on `Agent.instruction_bundle_files`; running agents populate a cache in a worker. The archive dispatch has a separate branch that also appends instruction bundles. A correct move therefore changes page selection, availability/counts, live enrichment, completed loading, and archive handling—not merely the title of a file card. [File page selection](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/file_panel/_file_list.py#L40), [bundle cache](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/file_panel/_instruction_bundles.py), [archive and Files dispatch](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/_agent_detail_files.py).

### Instructions have unusually strong provenance already

The recorded bundle has a sibling manifest with invocation identity, provider, attempt, actor, delivery mode/channel, bundle digest, byte count, estimated tokens, source identities, and included/excluded sections. Included sections have **UTF-8 byte offsets and lengths**, so a section view can slice the frozen bundle rather than re-render current memory or parse Markdown headings. The loader tolerates missing/corrupt records and distinguishes root/helper entries. Integrity checking compares recorded bytes with the digest and can fall back to the bundle store. [Manifest reader and integrity checks](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/manifests.py), [section construction](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/sections_base.py), [Rust manifest wire contract](https://github.com/sase-org/sase-core/blob/753fa21aa5b1d042d23112c04d30b0acd4159970/crates/sase_core/src/instruction_manifest/wire.rs).

Two subtle distinctions matter:

- A reference note's bundle section contains its **catalog entry**, not its whole body. A web section contains its descriptor, while its source list can also identify strand files. A source appearing in the manifest is therefore **not evidence that its full body was supplied**. Use rendered section content and source role, not a flat list of `sources`, to make inclusion claims. [Memory section builders](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/sections_units.py#L92).
- A matching digest proves the stored bytes match the manifest. It does not prove the provider loaded them. The manifest starts with observation status `unobserved`; provider verification is a separate facility. [Manifest assembly](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/manifest.py), [observation models](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/models.py).

The existing Main/Context memory lane already offers “Instructions as launched,” including native/legacy `AGENTS.md` snapshot fallbacks and historical version chips. Preserve these capabilities when moving the main reading surface. Do not turn a shadow bundle into the claimed instructions of a native-delivery run. [Launch-row and version logic](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/prompt_panel/_agent_memory_versions.py).

### Recalled memory is already audited, but historical content is uneven

`MemoryReadEvent` v3 records identity, reason, timestamp, selectors, requested targets, transitively included targets, depth, scope information, and blob hashes. One command can produce a batch containing multiple notes and strands. The CLI appends the audit event **before emitting output**. Thus the event proves an audited read was prepared/recorded, not that every output byte reached the model through its tool transport. [Read model](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/memory/_read_log_models.py), [read pipeline](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/memory/cli_read.py).

There is an important historical-fidelity gap: the generated memory-read report re-resolves the selectors against the current filesystem. Its metadata includes version evidence, but its reconstructed output is not necessarily the output of the original read. Existing version pins can recover committed historical source content; hashes alone do not retain uncommitted content or the original rendering of a linked batch. [Report reconstruction](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/memory/memory_read_report.py#L51), [Rust history blob resolution](https://github.com/sase-org/sase-core/blob/753fa21aa5b1d042d23112c04d30b0acd4159970/crates/sase_core/src/memory_history/query.rs#L536).

The current Context lane shows at most **five** memory events. Its loader keeps at most **50**, even if a caller asks for a larger limit. It reads a project log snapshot and filters by artifacts directory, falling back to agent name for legacy events lacking that directory. Session aggregation deduplicates event IDs and labels the producing member. These are good starting points, but a full deck must not silently turn “last 50” into “all memory used.” [Memory loader](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/memory_reads.py), [Context lane](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/prompt_panel/_agent_memory_reads.py).

### Skills, artifacts, macros, and continuation inputs have different evidence

| Existing evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Skill-use events | Recorded skill name, actor/runtime, reason, time | Exact historical `SKILL.md` bytes; complete coverage of all provider-native skill loading |
| Artifact-read events | Ref, actor, time, reason, resolved path, link-recording result | Historical content of every mutable referenced artifact |
| `macros.json` / per-step metadata | Known top-level macro references, kind, arguments, tags, launch swarm provenance | Every recursive expansion or execution; repeated identical references are deduplicated |
| Expansion traces converted to continuation segments | Captured expansion-stage text, source reference/label | That each intermediate segment was separately sent to the provider unchanged |
| Prepared-prompt capture | Content-addressed materialized prompt and provenance-tagged segments, when capture succeeds | Complete provider-native context or attention; universal capture on every historical launch path |

Sources: [skill audit schema](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/skills/use_log.py), [artifact read schema](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/artifact_read_log.py), [macro usage collection](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/macro/used_macros.py#L159), [trace-to-segment conversion](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/continuation_capture/segments.py#L47), [prepared-prompt persistence](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/continuation_capture/prompt.py#L36).

One particularly relevant exception is `#memory/<name>`: it injects memory through macro expansion **without a memory-read audit event**. A deck based only on `memory_reads.jsonl` will miss it. Route captured `memory/` expansion segments into the recalled-memory view, labeled “Expanded into prompt,” without fabricating a CLI read. [Macro-memory tests](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/tests/test_macro_memory_loader.py#L193).

## 2. Is a new deck justified?

**Yes, if the deck unifies the inspection task rather than merely relocating one file.** The existing split requires the user to find the bundle in Files, recent reads in Main, version evidence in pager hints, and relationships in Record. A Memory deck gives this material a coherent place and allows side-by-side inspection with a reply or diff.

The costs are real:

- It adds a sixth stop to a deck cycle that intentionally visits empty decks. Frequent keyboard users pay that cost even when they rarely inspect memory.
- “Memory” can suggest the model's current mental state or a writable knowledge catalog. Both would be misleading here.
- Duplicating the existing Context lanes creates multiple seemingly authoritative views that can disagree on counts, attribution, or versions.
- The historical-data problem is more consequential than the visual move. A polished card showing today's note as yesterday's input would reduce trust.

The adjustment is to define Memory narrowly as **“Recorded instructions and recalled knowledge for this run.”** Keep the existing global memory browser/editor as the place to manage memory. Keep Main's context overview short and link into the deck. Avoid renaming the entire Main/Context system as part of this feature.

Official products provide useful precedent, but not proof of the proposed layout. Claude Code distinguishes its `/memory` file-management surface from `/context` inspection of launch-loaded instructions. VS Code distinguishes instructions, conversation history, explicit references, and tool outputs, and explains that compaction can summarize or omit earlier details. My inference is that SASE should likewise separate the memory catalog from run evidence, and avoid claiming a cumulative history is the model's current context. [Claude Code memory documentation](https://code.claude.com/docs/en/memory#view-and-edit-with-memory), [VS Code context concepts](https://code.visualstudio.com/docs/agents/concepts/context#context-window-and-compaction).

## 3. Placement rules: what belongs where?

Use the user's question to choose the primary home:

| User question | Primary deck |
| --- | --- |
| What was requested and what did it answer? | Main |
| What did it change or produce? | Files |
| Which recorded guidance and knowledge inputs can I inspect? | Memory |
| Which calls/commands did it run, and what happened? | Tools |
| How did the host finish this work? | FINAL |
| Where did this run come from, how was it configured, and what is it related to? | Record |

A relationship link and a content view may reference the same underlying record. That is useful navigation, provided there is one source of truth and one primary full-content view.

| Candidate | Recommended home | Treatment |
| --- | --- | --- |
| Frozen instruction bundle | Memory → Instructions | Full content, manifest summary, source/section navigation |
| Core memory bodies actually in the bundle | Inside Instructions | No separate duplicate card per note |
| Reference-note descriptions and web catalogs | Inside Instructions | Label as catalog/descriptor content; never count unread bodies as retrieved |
| Reference notes, decision strands, glossary strands, inline dependencies | Memory → Recalled Memory | Audited batches with requested/included distinctions |
| Legacy `sase glossary read` events | Recalled Memory | Normalize for display while preserving legacy evidence; no permanent separate Glossary card |
| `#memory/foo` text captured during prompt preparation | Recalled Memory | Label the macro-expansion channel and link to its prompt origin |
| Recorded skill invocations/use | Memory → Skills | Procedural guidance; metadata-only state when historical body is missing |
| Available-but-unused skills/macros | Existing catalog/browser | Do not populate a run's Memory deck merely from availability |
| Macro name, arguments, source, workflow kind | Record → Provenance | “Prompt construction” rows; source/expansion inspection on demand |
| General macro-expanded task text | Main's materialized-prompt inspection | Link from Record; do not add a universal Macros memory card |
| Workflow execution and tool-producing macro steps | Tools / relevant workflow node | Execution is distinct from prompt expansion |
| Research reports, plans, past-agent summaries, or other artifacts actually read/injected | Memory → References, later | Input evidence and historical content when available |
| Artifact `cites`, `read`, `related`, `produced` relationships | Record → Links | Graph and direction; a link alone is not proof of body delivery |
| Assigned goal/bead/plan identity | Main overview and Record relations/links | It becomes a Memory input only with read/injection evidence |
| Inherited continuation summary/checkpoint text | References, later | Explicitly identify the inherited material; parent relation stays in Record |
| Provider-managed memory or compaction summaries | References or Instructions only with provider-specific evidence | No guessed inventory or content; label capture coverage |
| Memory files authored/edited by this agent | Files | Output role; can also have a distinct read event if subsequently reread |
| Arbitrary source-file reads, web searches, terminal output | Tools / existing output viewers | Avoid turning Memory into another full transcript |
| Model, provider, machine, workspace, timestamps, retries | Record | Retain only small invocation labels beside Memory content |
| Bundle validation status and capture gaps | Inline beside the affected content | No standalone “Warnings,” “Manifest,” or “Budget” card in the first release |

**Why not put everything in Record?** Record is good at explaining provenance and relations; long instruction bodies and recalled notes are reading tasks. Adding all of them to Record would mix a run's biography with its knowledge inputs and make its four-card structure harder to scan.

**Why not put all macros in Memory?** A macro can set launch directives, orchestrate a workflow, inject a task prompt, or supply memory. Classifying by the `#` syntax hides those differences. Classify the resulting material and retain the invocation's provenance. `#memory/foo` is the useful special case, not a reason to treat every macro as a memory.

## 4. Proposed cards and blocks

Target four cards in a fixed order; ship the first two before expanding scope.

### Instructions

One card, with **one block per recorded instruction invocation/actor**. A concrete turn defaults to its applicable root invocation; a session container defaults to the newest concrete agent turn. Keep helper records separately labeled. A helper bundle/template does not establish that every helper received it.

Each block contains:

1. Compact identity: turn, attempt, invocation, root/helper role, provider.
2. Separate delivery/observation and content-integrity labels.
3. A section/source index with inclusion and catalog/body distinction; optional excluded-source rows explain shadowing or mode decisions.
4. The frozen bundle content, with an exact-text opening action and section jumps.
5. Optional comparison with another recorded invocation or with current source, clearly labeled as a comparison.

The initial viewport should show useful content and a short index, not a large manifest dump. Manifest JSON is an inspection action. Token estimates can appear in the header, marked approximate; they do not deserve a card.

### Recalled Memory

Use **one block per read batch**, not one block per target. A batch carries a single reason, timestamp, depth, and output context; splitting it into many cards would duplicate that information and obscure its dependency expansion.

Within a block, a compact target table distinguishes:

- Requested notes/strands.
- Additional material included by links.
- Scope and version evidence where available.
- Captured output or explicitly labeled reconstructed/current content.

The default reading order is chronological, landing on the latest block. This fits the existing block model's “last block is newest” convention. A source-focused index can deduplicate targets for discovery, but the underlying events remain available; rereading a changed note is not redundant history.

A prompt-expanded `#memory/foo` gets an expansion-origin block, not a fake read event. Legacy glossary reads are adapted into this card. Dependencies are rows within the block; **blocks must not nest**.

### Skills

Use one block per recorded skill-use event, retaining actor, reason, time, and runtime. Provide a compact unique-skill index when many uses repeat. “Use recorded; historical body unavailable” is an acceptable initial state. Opening today's installed skill must say “Current definition.”

Do not infer use from the available-skills list or promise comprehensive provider coverage. If better capture is later added, capture the actual rendered/deployed instruction bytes, not merely a source template or a source filename.

### References

This is a justified extension to the user's “other types of memory” requirement: a previous research report or continuation summary often functions as recalled knowledge even though it is not stored under `sase/memory/`.

Use one block per recorded input episode: an artifact read, prompt-reference expansion, or inherited summary/checkpoint. Show channel, actor, reason when recorded, canonical identity, and content fidelity. Keep a linked artifact's output/relationship roles in Files/Record. Do not populate this card from every graph neighbor or copy a whole parent's knowledge history into a child.

Defer this card until the evidence joins and historical-content behavior are sound. Existing artifact read logs and continuation captures are inputs to reuse, not a reason to claim all references have immutable content today.

### Keep the hierarchy shallow and navigation familiar

The existing `CardPart` / `CardBlock` model supports titled, stable, non-nesting blocks; blocks must be trailing and contiguous after the card preamble. Reuse it instead of adding a custom tree inside Memory. [Block contract](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/card_block.py), [card semantics](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/card_part.py).

Retain deck cycling, `Ctrl+J/K` card movement, and `(`/`)` block movement. Use the existing spread/paged sizing policy where practical; large bundles should page naturally. Do not assume all new decks automatically support Main's persisted view options: the current policy explicitly supports only Main/Files, and block dispatch contains deck-specific branches. Either add Memory deliberately to that contract or initially keep it automatic. [Deck model and view policy](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/model.py), [block dispatch](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/panel_blocks.py).

Suggested placement is **Main → Memory → Files → Tools → FINAL → Record**. Keep `m` for Main; use a free picker key such as `y` for Memory, subject to the existing binding map. The primary discovery mechanism should be a Main context summary such as “Instructions · 7 recorded reads · 2 skills → Memory,” not memorizing another key. Counts must state whether they cover all records or only a loaded subset.

Illustrative shape, not a measured screenshot:

```text
MEMORY   Instructions | Recalled Memory | Skills | References

Recalled Memory                       newest block selected
turn 3 · read 7 · 14:32 · CLI read recorded
Reason: Check the UI navigation and performance contract

Requested   tui.md                  project   recorded version available
Included    glossary:deck           project   recorded version available
Included    glossary:card           project   content unavailable

[Recorded content] [Current source] [Related tool call]
```

The controls represent actions, not a proposal to invent new keybindings for each one.

## 5. Evidence and version contracts

Use two independent dimensions rather than one ambiguous “loaded” badge:

| Dimension | Examples |
| --- | --- |
| **Exposure evidence** | Catalog entry included; bundle prepared; host delivery declared; provider observation available; CLI read recorded; prompt expansion captured; skill use recorded |
| **Content fidelity** | Captured bytes match digest; versioned source recovered; reconstructed rendering; current definition only; missing; corrupt/mismatched |

These dimensions answer different questions. A captured file can be exact without proof it was delivered. An audit event can prove retrieval was recorded while the historical bytes are unavailable. A source recovered from Git can be historically correct while its reconstructed batch formatting differs from the original output.

Specific implementation rules:

- **Never silently substitute current content for historical content.** Offer a separate current-source action. Preserve missing/corrupt cards and their evidence rather than dropping them.
- **Do not count catalog entries as body reads.** Core bodies, reference descriptions, web descriptors, and expanded strands have different roles.
- **Do not equate an event count with source count.** Show requested and included target counts separately. The existing `memory_read_event_targets` deliberately excludes link-expanded material; it is insufficient for an “all supplied knowledge” count. [Target-count semantics](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/memory/_read_log_events.py#L235).
- **Preserve original provenance on deduplication.** Deduplicate stored content by digest, event rows by event ID, and source-index entries by scope/identity/version. These are different operations. Identically named project and home notes are not automatically the same source.
- **Estimates are not usage accounting.** Bundle `tokens_est` uses a character-based heuristic. Do not present a sum of bundle/read/source estimates as live context occupancy, billed tokens, or model attention. Source layers, macro intermediate segments, repeated reads, and compaction would make such a total misleading. [Estimator](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/instructions/sections_base.py#L51).
- **Inspection is read-only.** Opening the deck must not invoke audited agent read commands or append new skill/read events. It must not expand macros, run substitutions, clone repositories, or perform network verification on navigation. Display existing records through side-effect-free readers.
- **Coverage is explicit.** Use “No recorded reads,” “Evidence unavailable on this machine,” or “Showing latest 50; more history not loaded” according to what is known. A missing local log is not proof of no reads.

A small future capture improvement has high value: store a versioned, content-addressed snapshot of the resolved memory read output and link it from the event. Serialize from the already-resolved view before emission, without resolving the sources a second time. Record the output format/renderer version; if storing canonical Markdown instead of exact transport bytes, say so. Keep the existing audit-before-output contract, and record a typed capture failure if optional content retention fails. Provider/tool truncation remains a separate observation, not something the snapshot proves away.

Historical events should continue to work through honest fallback states. Do not backfill them by replaying selectors and presenting the result as original output. Do not build an entirely new event system merely to add the two initial cards.

## 6. Agent, session, retry, and archive behavior

The scope should follow the selected node:

- **Concrete agent turn:** its records only. Prefer durable invocation/run identity and artifact location; name-only matching is a visibly weaker legacy fallback.
- **Session container:** aggregate its concrete member turns with actor labels and stable ordering. A monitor/gate turn without model context contributes no invented instruction bundle.
- **Pinned retry/attempt:** use that attempt's evidence paths and identity. Do not show the current attempt's reads next to the historical attempt's response.
- **Helper:** display its own record or recorded inheritance relationship. Do not merge helper reads into the root as though the root consumed them. A parent may receive only a helper summary.
- **Clan/tribe container:** initially show a concise member summary and links into member Memory decks. A union can be offered later as an explicitly aggregated view; it is never “the clan's shared model context.”
- **Archived/remote run:** serve captured evidence that is actually available. Current project-log loaders do not by themselves establish portable historical availability. Audit retention/export coverage before promising parity; missing data gets an explanatory state.

Persist card preference across agents, but scope block selection to the subject/run. Appended events should not steal a user's position while reading an older block. Restoring a session must not accidentally choose a helper template merely because it happens to be the last block. These are extensions of the existing card/block behavior, not reasons for another navigation model.

## 7. Implementation approach

### First delivery: useful and bounded

1. Add `DeckId.MEMORY`, registry metadata, picker/cycle integration, panel routing, title/count behavior, empty states, and search support. Keep its initial view policy automatic unless explicit block paging is implemented completely.
2. Build Instructions over the existing manifest/bundle readers, including native/legacy snapshot fallback. Preserve integrity and delivery distinctions. Present full bundle content and source-section jumps.
3. Build Recalled Memory over audited read events, with a legacy glossary adapter. Show event metadata immediately and load content lazily. Import captured `memory/` expansion evidence when it can be attributed; otherwise disclose the gap.
4. Remove automatic instruction-bundle pages from every Files path, including archive handling and availability counts. Keep the bundle locators/storage; they are not Files-owned data.
5. Replace the detailed Main memory lane with a concise summary and deep links to Memory. Reuse one projection so counts and labels agree. Keep important capture failures visible at their affected row.

This release is valuable even when some older reads have metadata only. It should not wait for perfect skill/reference capture or a comprehensive provider-context recorder.

### Second delivery: improve historical fidelity

Add captured read-content references and bounded full-history pagination. Preserve old schemas and their uncertainty. The current 50-event cache cannot simply be reused as a complete-history API; create a backend query that reports loaded/total-or-unknown coverage and a continuation cursor. Avoid turning every TUI navigation into a full project-log scan.

Add Skills using existing use events. Add References using audited artifact reads and captured prompt/continuation material. Record graph edges remain in Record, with content links into Memory.

### Macros: enrich existing provenance, reuse captured text

Add a compact prompt-construction block within Record → Provenance. Show captured macro invocation metadata and link to recorded expansion segments or the materialized prompt. `collect_macro_sources` is a useful resolver for current definitions, but running it today does not recover yesterday's definition. Do not rerun macro expansion to “inspect” a historical launch: argument substitutions and workflows may execute. [Current definition provenance resolver](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/macro/macro_sources.py).

A general Macros card can wait for a demonstrated browsing need. The initial design already answers both relevant questions: Record explains which macro shaped the launch, and the recorded prompt/content view explains what text was prepared.

### Backend versus TUI boundary

Shared evidence attribution, version/fidelity classification, event joins, pagination, and content resolution belong in **`sase_core`**, exposed through a versioned wire/binding and a thin Python adapter. Card titles, layout, Rich/Textual rendering, selection, and scroll state remain in SASE's TUI. This follows the project's Rust backend boundary rather than copying the existing Python audit helpers into another independent domain implementation.

A minimal conceptual read model could carry:

```text
MemorySubject: project/run/attempt/actor identity and optional session members
MemoryEntry: stable ID, kind, origin channel, source identity, producer,
             time, reason, requested/included relationship,
             version/digest, content locator, evidence/fidelity state
MemorySnapshot: entries, source signature, coverage, next cursor
```

These are proposed concepts, not existing API names. Reuse existing manifests, logs, continuation blobs, and history storage; the projection should not become a second mutable ledger. If new Rust bindings are required, update binding tests and SASE's `sase-core-revision.txt` pin together. Pure presentation relocation does not require migrating unrelated backend code.

### Likely implementation touchpoints

| Concern | Existing starting point |
| --- | --- |
| Registry, selection, persistence | `widgets/decks/model.py`, `spec.py`, `models/agent_deck_persistence.py` |
| Composition and block navigation | `widgets/decks/panel.py`, `card_documents.py`, `panel_blocks.py`, `document_blocks.py` |
| Search, availability, routing | `widgets/decks/search_corpus.py`, `availability.py`, `_agent_detail_deck_*` |
| Remove bundle pages from Files | `file_panel/_file_list.py`, `_instruction_bundles.py`, `_agent_detail_files.py`, done loaders |
| Existing context enrichment | `prompt_panel/_agent_display_header_summary.py`, memory/skill/artifact loaders and version helpers |
| Worker/caching pattern | `widgets/decks/record/loader.py` and its view's generation checks |
| Data sources | `instructions/manifests.py`, memory read schemas, skill/artifact audits, `continuation_capture/` |
| User-facing integration | Default keymap config where changed, help popup, deck documentation, visual snapshots |

Bundle discovery is currently scheduled in the **artifacts** enrichment lane. Give Memory an appropriate independent loading path; a user hiding the artifacts lane must not accidentally lose instructions in Memory. [Enrichment coupling](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/prompt_panel/_agent_display_header_summary.py#L243).

For responsiveness, capture a cheap immutable subject on the UI thread, load evidence in a worker, and reject stale results by subject and generation. Cache bounded summaries and lazily load bodies; availability probes must not hash bundles or query Git. Reuse invalidation signatures for a live run's manifests and event sources. Record's existing worker/cache structure is a useful template, though its specifics need adaptation. [Record loading pattern](https://github.com/sase-org/sase/blob/4b7b98153227a355e7d183ea25df4d56694e2998/src/sase/ace/tui/widgets/decks/record/loader.py).

## 8. Alternatives and critique

| Approach | Benefit | Main drawback | Assessment |
| --- | --- | --- | --- |
| Keep bundles in Files; improve labels | Smallest change | Knowledge evidence remains scattered | Insufficient for the stated goal |
| Add one “Context sources” card to Record | Fewer top-level destinations; cheap pilot | Mixes long reading content with lifecycle/provenance | Best fallback if actual inspection is rare |
| Add Memory with narrow, evidence-backed cards | Coherent reading task; pairs well with reply/diff | Sixth deck and historical-data work | Recommended |
| Create a comprehensive Context deck and rename Main's Context card | Can contain prompts, tools, references, memory | Broad reorganization, overlap with Tools, confusing scope | Too large for this request |
| Build a full context graph/replay UI first | Powerful future analysis | Expensive capture/retention project before validating the UI need | Defer |

I would not add individual cards for every memory type, web, source file, token budget, manifest, macro definition, or warning. The variety belongs in row/block metadata and filters. The navigable categories should remain understandable without knowing SASE's storage schema.

I would also avoid an automatic “Did the agent comply?” score. The deck can demonstrate supplied guidance and recorded retrieval, but semantic compliance requires an independent assessment of behavior. A green bundle-integrity badge must not look like a compliance verdict.

## 9. Requirements adjusted explicitly

1. **“Memory the agent used” → “Recorded instructions and recalled knowledge.”** This avoids claiming attention, obedience, or current retention.
2. **Move the bundle's primary display, not its storage or identity.** Remove its automatic Files page while preserving locators, historical snapshots, and existing inspection entry points as links.
3. **Include procedural guidance through Skills, but not every macro.** Macro mechanics belong in Record; captured `#memory` expansion belongs in Recalled Memory.
4. **Treat input artifacts as a later References card.** This captures useful long-term knowledge without turning every artifact relation or output into memory.
5. **Keep Main as an overview with links.** Do not maintain competing full read timelines in Main and Memory.
6. **Require honest fidelity labels from the first release; improve snapshots incrementally.** Missing historical bytes should not block navigation or be replaced silently.
7. **Do not promise complete context-window reconstruction, automatic editing, or provider-wide capture.** Those are separate capabilities with different evidence requirements.

## 10. Acceptance checks and decision criteria

Implementation should verify these behaviors, not merely whether a new tab renders:

- Bundle-only agents show content in Memory and no automatic bundle page/count in Files, across running, done, and archive paths.
- Explicit, native/legacy, helper, missing, corrupt, and mismatched bundle cases preserve their distinct meaning.
- Unicode section navigation uses byte offsets correctly; reference catalogs and web source lists never imply unread bodies were supplied.
- Multi-selector reads preserve requested/included relationships and reasons; repeated reads and same-name home/project sources do not collapse incorrectly.
- A changed or deleted source never silently replaces historical content with the current version.
- `#memory/foo` capture appears with expansion provenance even though no CLI read exists. Unsupported historical capture states are visible.
- Skills without body snapshots remain metadata-only. General macro expansion is not rerun during inspection.
- Sessions, retries, helpers, and container summaries retain producer attribution; selecting an older attempt does not leak the latest attempt's data.
- More than 50 events cannot masquerade as complete history. Remote/archive absence is distinguishable from zero recorded events.
- Deck refresh preserves selected card/block/scroll; late workers cannot repaint another agent; split panels, search, and unknown persisted deck values remain well behaved.
- Opening Memory appends no new agent read/use events and triggers no macro execution or network resolution.
- Measure navigation and idle refresh using the existing TUI performance tools before and after implementation. Read data off the event loop and avoid new per-keystroke Git/subprocess work.

Relevant existing tests include `tests/instructions/test_launch_root_bundle.py`, `tests/test_memory_capture_evidence.py`, `tests/test_memory_read_report.py`, `tests/test_macro_memory_loader.py`, `tests/ace/tui/widgets/test_agent_memory_versions.py`, the deck card/block/persistence tests, and existing Files instruction-bundle snapshots. Extend their meaningful cases rather than creating a second independent model of the same behavior.

For a small usability check, ask whether a user can quickly: find the selected turn's original instructions; find why a particular strand was read and which version is inspectable; explain a macro's role without confusing it with model-retrieved memory; and tell the difference between an unread catalog entry and supplied content. If the deck adds navigation without improving those tasks, prefer the smaller Record-card alternative.

## Recommended solution

**Implement a Memory deck with Instructions and Recalled Memory first.** Keep the full recorded instruction bundle there, with invocation blocks, a source index, and separate integrity/delivery labels. Represent recalled memory as read-batch blocks, including dependencies and captured `#memory` expansions with their true origin. Retain concise Main links and remove automatic bundle pages from Files.

**Add Skills and input References next, using existing audits and captures with explicit historical-content limits.** Keep general macro invocation details in Record → Provenance, relationship edges in Record → Links, and authored/materialized task prompts in Main. Reuse continuation snapshots rather than creating another macro log.

The guiding boundary is: **Memory reads the recorded knowledge; Record explains its provenance; Tools shows the actions; Files shows the work.** Build that distinction before adding more cards or claiming a complete model-context history.
