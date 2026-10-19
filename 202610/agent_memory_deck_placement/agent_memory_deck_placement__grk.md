# A Memory Deck For Instruction Bundles: Where It Belongs And What It Should Hold

**Date:** 2026-10-19 · **Researcher:** grk · **sase checkout:** workspace `sase_18` · **Builds on:** live Agents-tab deck code, plus prior `research:202610/instruction_bundles_provider_parity_and_memory_ledger.md` (R-ledger) and `research:202610/preloaded_memory_size_visibility.md` (R-size)

> **Question:** Should the selected agent's instruction bundle move from the Files deck into a new Memory deck, and what other cards (memory reads, skills, macros, …) belong there versus the Record deck or Main Context?

## Recommendation (read this first)

**Yes: add a sixth agent data deck named MEMORY, and take the instruction bundle out of Files.** The instinct is right. The bundle is not a file the agent touched, Files already claims that job, and the only reason the bundle lives there today is that Files is the only deck that can show a large Markdown document as a full card.

**Do not put the bundle, the memory-read log, or macros on RECORD.** RECORD is the node's identity graph (Lifecycle, Provenance, Relations, Links). Provenance already points at the bundle path; that pointer should stay. The bytes, the section map, and the audited lookups are a different question: *what was this agent told, and what did it look up?*

**Do not dump macros into the Memory deck.** `AGENT MACRO` already lives in the sticky identity header. Macros are the user's invocation, expanded before the agent runs. Memory is what the host inlined or the agent fetched.

**Do not grow Context into a third Main card, and do not dual-home the bundle in Files and Memory.** Dual-homing is the current design, and it is why the Files subtitle lies (it counts host-generated `instructions/NN-*.md` pages as "files").

Ship it in two slices, copying RECORD's shell and Files' document renderer:

1. **Slice A (the user's request).** MEMORY deck with a **Bundle** card (root then helper as card blocks) plus a **Receipt** card (manifest: delivery, digest, size, `bytes match`). Remove bundle pages from Files. Keep a compact MEMORY lane on Context as a jump, not as the document.
2. **Slice B.** A **Ledger** card that joins the manifest's section table with audited `sase memory read` and `sase skill use` events. This is the "other types of memory" the request asked for. The join belongs in `sase-core` (`instructions::ledger_view`); Python only renders.

Picker key **`y`**, glyph **`❖`**, never auto-chosen on split (same rule as RECORD). Default card: **Bundle**, because the stated job is to *show the instructions*.

---

## 1. What we show today

Five decks are registered in `src/sase/ace/tui/widgets/decks/spec.py`. Cycle order is Main → Files → Tools → FINAL → RECORD. Picker letters: `m f t n r`. Reserved inside the picker: `j k q p`.

| Deck | Job | How the instruction bundle appears |
| --- | --- | --- |
| **MAIN** | Context + Reply (or Summary) | Compact `SASE CONTEXT / MEMORY` lane: launch row + at most five audited reads with version chips. Hint opens the pager, not a deck card. |
| **FILES** | "Diffs and files the agent touched" | Root and helper bundles appended as extra pages (`tag="bundle"`, basename `00-claude.md`). Same pages inflate Files availability counts and Files spread. |
| **TOOLS** | Runs + LLM Calls | Absent. |
| **FINAL** | How turns landed | Absent. |
| **RECORD** | Lifecycle, Provenance, Relations, Links | Provenance may show `bundle_path`. Never the Markdown. Always available; never auto-chosen on split. |

Two other MEMORY surfaces exist and must not be conflated with a per-agent deck:

- **Config / prompt Memory panel** (`gm`): browse and edit the project's `sase/memory/` notes, with an `INSTRUCTIONS` rail group for committed `AGENTS.md` and shims.
- **CLI:** `sase instructions show NAME`, `sase instructions render`, `sase instructions verify`.

The dual Files + MEMORY-lane path landed as "open the launched instruction bundle from MEMORY and Files" (changelog `552b38f`). Docs in `docs/reference/memory/history.md` describe it explicitly: the lane's launch row opens the recorded root bundle (or an `AGENTS.md` snapshot for native/fallback/pre-E3 runs); "The Agents-tab Files deck appends the same root and helper bundles as static pages."

That split is a compromise. The lane can point. Files can show bytes. Neither is the right *category*.

### Why Files is the wrong home

`desired_file_pages` in `file_panel/_file_list.py` concatenates commit diffs, the live diff, linked-repo diffs, extra files, **then** `instruction_bundle_pages(agent)`. Consequences:

- Files' blurb and glossary definition ("one card per diff or attached file") become false.
- An agent that touched nothing still lights Files because launch wrote `artifacts/instructions/00-<provider>.md`.
- The default Files card is still the first diff, so the bundle sits at the *end* of `Ctrl+J`. The MEMORY lane exists in part because nobody wants to walk every diff to reach it.
- Files spread (`files_spread.py`) will try to inline those pages, capped at `PLAIN_RENDER_MAX_LINES` (5,000). Instruction bundles are large Markdown; they make spread slower and less about the diff the reader opened Files to see.
- Helper bundles (`NN-<provider>.helper.md`) become extra file tabs with the same basename-ish labels, mixed with `src/foo.py`.

The Files deck is the working "what changed" surface. Host-generated instruction artifacts do not belong on it.

### Why the Context lane is not enough

`CONTEXT_LANE_ORDER` in `_agent_context.py` is already seven lanes: PLAN, BEAD, ARTIFACTS, MEMORY, GLOSSARY, SKILLS, WORKSPACES. MEMORY is capped at five visible reads (`MAX_VISIBLE_READS = 5`). The launch row is one truncated path plus a version chip. The bundle itself is thousands of lines.

Context is the hot path of every `j`/`k` on Main. Header enrichment already computes `instruction_bundle_files` and resolves version chips off-thread, but the lane still occupies Main document layout. Growing it into a full bundle viewer would punish the Reply loop. R-ledger rejected this option for the same reason.

### Why RECORD looks tempting and is still wrong

RECORD's four cards are a closed identity document, loaded off-thread, always present, never auto-chosen (`choose_new_panel` skips `DeckId.RECORD` so `\ `|` keeps the Main↔Files triage pair). Provenance already has `bundle_path`. Putting instruction *content* there would mix:

- **RECORD:** who is this node, where does it live, how is it related, which artifacts link to it.
- **MEMORY:** what durable context did the host give it, and what did it fetch.

Those questions are answered on different cadences. RECORD is useful on unreadable archive rows that have no bundle bytes (`Archive entry unreadable — Record only`). MEMORY is useful when the bytes exist. Collapsing them would make RECORD's "always four cards" contract false, and would hide the bundle behind Lifecycle.

---

## 2. Critique of the proposed plan

The plan as stated: *show the instruction bundle in a new memory deck; also include cards for other types of memory (and maybe macros); think about Record.*

### What is right

- The bundle is first-class, frozen, per-invocation context. It deserves a deck, not a Files afterthought.
- Grouping "what it was given" with "what it read" is the right cut. The MEMORY lane, the SKILLS lane, and the launch row are already trying to tell that story in a five-row gutter.
- Asking the Record question up front is correct. RECORD just landed (`sase-1jm.4.2`); stuffing new content into it would be the cheap-and-wrong merge.

### What is incomplete or risky

1. **A sixth deck is real UX cost.** Cycle length, switcher chrome (`main · files · tools · final · record`), picker rows, persistence (`~/.sase/ace_agents_deck_state.json`), archive hydration, PNG goldens, `j`/`k` benches. RECORD paid this cost once. MEMORY must copy that shell, not invent a seventh pattern. It must also **never auto-choose**, or `\ ` stops opening Files.
2. **"Memory deck" collides with two existing MEMORY nouns.** The Context lane and the Config Memory panel. That collision is survivable if the deck's blurb is "what this agent was told and looked up" (R-ledger's phrase) and the picker letter is **not** `m`.
3. **"Maybe macros" is a category error.** See §4.
4. **Showing the bundle as "another Files card in a new deck" under-sells the manifest.** The JSON sibling (`NN-<provider>.json`) records sections, digests, delivery, and integrity (`launch_root_bundle` in `instructions/manifests.py`). Files currently shows only the `.md`. A Memory deck that is just a relocated file tab misses Receipt/Ledger, which is the actual debugging value.
5. **The glossary is already stale.** `glossary:deck` still lists Main, Files, Tools, FINAL and omits RECORD. A sixth deck without a glossary and `agent-statuses.md` update will drift further.
6. **Prior research already designed this deck.** R-ledger (2026-10-05) proposed MEMORY as a *fifth* deck with Receipt, Ledger, and Bundle cards, picker `y`, glyph `❖`, FINAL as the load template. RECORD did not exist then. The live tree implemented the cheap half of that design (lane + Files pages) and skipped the deck. This request is the rest of that design, plus RECORD as a new neighbor.

**Verdict:** good idea, with a tighter card inventory, an explicit Files *removal*, a RECORD *non-goal*, and a two-slice landing so the bundle move does not wait on a Rust ledger view.

---

## 3. Deck-boundary test

Use one question per deck. If a card cannot answer that deck's question, it is in the wrong place.

| Deck | Question | Belongs | Does not belong |
| --- | --- | --- | --- |
| MAIN | What did this node *do* this turn? | Prompt, Reply/Output, PLAN/BEAD/ARTIFACTS/WORKSPACES, wait, traceback | Full instruction bytes; five-row memory archaeology |
| FILES | What files did this node *change or attach*? | Commit diffs, live diff, linked-repo diffs, extra/artifact files | `artifacts/instructions/*.md`, manifests |
| TOOLS | What did it *invoke*? | Tool runs, LLM calls | Skill-use audit (that is instruction fetch, not a tool-run card) |
| FINAL | How did the *host* land the turn? | Overview, per-finalizer instances | Instruction delivery (different host step, different store) |
| RECORD | *Who/where/linked?* | Lifecycle, Provenance (including bundle *path*), Relations, Links | Bundle bytes, read logs, skill uses, macros |
| MEMORY (new) | What was it *told*, and what did it *look up*? | Bundle, receipt/manifest, section ledger, audited memory reads, skill uses, helper bundle | Macros, PLAN/BEAD, opened workspaces, artifact links, diffs |

PLAN/BEAD/ARTIFACTS/WORKSPACES stay on Context. They are task and workspace context, not SASE memory. GLOSSARY as a separate lane is already legacy: current `sase memory read glossary:<keyword>` events render in MEMORY; the old `sase glossary read` log can fold into Ledger as ordinary reads.

---

## 4. Card inventory (with keep / move / drop)

Deck → card → block. Cards are `Ctrl+J`/`Ctrl+K`. Blocks are `(`/`)` for repeating units (session turns on Reply; invocations on Receipt/Bundle).

### MEMORY deck cards (recommended)

**1. Bundle (default card).** Exact bytes the agent received. Reuse the Files page renderer (capped at 5,000 lines, `E` opens the editor, search and zoom work). One card, not one card per file:

- Block 0: root bundle (`00-<provider>.md`), or the `AGENTS.md` snapshot for native/fallback/pre-E3 launches (today's launch-row `kind="snapshot"`).
- Further blocks: helper bundle, then later sequences (`01-`, …) if the run recorded more than one invocation.

Section-id gutter (from the manifest's offset table) is Slice B polish; Slice A can show raw Markdown the way Files does today.

**2. Receipt.** Manifest, not bytes. Fields already on `RunManifest` / `LaunchRootBundle` / `BundleIntegrity`: sequence, provider, actor, delivery status (`explicit` / native / fallback), envelope, `common_digest`, size, `bytes match` / `MISMATCH`, helper vs root. Blocks = invocations, landing on the newest, matching Reply.

This is the card RECORD must *not* grow. It is about delivery of instructions, not node identity.

**3. Ledger (Slice B).** One row per memory subject with the R-ledger states: inlined `●`, offered `◇`, offered→read `◆`, unlisted read `◈`, withheld `○`, foreign `⊘`, changed-since `↻`. Groups: PACKAGE, HOME, PROJECT, READS, SKILLS, FOREIGN. Hints pin the memory-history pager to the blob the agent saw (the `MemoryVersionPin` path already exists).

Skill uses (`_agent_skill_uses.py`, `sase skill use` audit) are extra instruction fetched on demand. They are Ledger rows (or a SKILLS group), not a fourth card and not a Tools card.

### Keep on MAIN / header (do not move)

| Surface | Why it stays |
| --- | --- |
| Compact MEMORY lane on Context | Quiet "what did it lean on?" during the Reply loop. Upgrade the launch row into a jump (`[n]` opens MEMORY/Bundle). Cap stays at five reads. |
| PLAN, BEAD, ARTIFACTS, WORKSPACES | Task/workspace context. |
| `AGENT MACRO` in the identity header | User invocation. Already sticky, already hinted. |

Optional later: a muted header chip (`❖ 4.6k · ✓1×`) as in R-ledger. Not required for Slice A.

### Drop / do not add

| Candidate | Decision |
| --- | --- |
| **Macros as a Memory card** | **No.** Macros (`#review`, `#research`, workspace `#gh:`) expand the prompt; they are not durable memory. `#memory/foo` is a memory *macro*, but the thing the agent consumed is the note, which already appears as an inlined section or a read. Duplicating `load_macros_used` into a deck splits the header's job. |
| **One Files-style card per memory note the agent read** | **No.** Read counts grow; bodies are large; the pager plus Ledger hints already open a note at the version seen. Cards are for a handful of kinds, not an unbounded list. |
| **GLOSSARY as its own card** | **No.** Fold into Ledger/Reads. |
| **WORKSPACES** | **No.** Opened repos are Record-adjacent provenance or Context. Not memory. |
| **Instruction manifest JSON as a Files page** | **No.** That is the Receipt card. |
| **Putting Bundle on RECORD Provenance** | **No.** Keep the path only. |
| **Keeping bundle pages on Files after MEMORY exists** | **No.** Dual-home is the bug being fixed. |

### Clan / session / archive

- **Clan and tribe containers:** Files is empty today. MEMORY Slice A can be empty too. Slice B's "audience strip" (shared `common_digest` across members) is the one clan-specific card worth adding, on Receipt, not a new deck.
- **Archive:** hydrate from retained `instruction_bundle_files` the way Files already does. Unreadable archive rows stay Record-only.
- **Pinned attempts (`D`):** Files forces empty. MEMORY should follow the pinned attempt's artifacts dir when it resolves (FINAL's rule), because instructions are per-attempt.

---

## 5. Justified requirement adjustments

These change the request. Each is deliberate.

1. **Remove the bundle from Files** when MEMORY ships. The request said "start showing it in a new memory deck instead." Implement the "instead": delete `pages.extend(instruction_bundle_pages(agent))` from `desired_file_pages`, drop the `/instructions/` basename special case, and stop treating bundles as Files availability. Leaving both is worse than today.
2. **Do not include macros.** Adjustment against the "maybe macros?" probe.
3. **Do not extend RECORD.** Adjustment against the "maybe the record deck?" probe. Keep `bundle_path` on Provenance.
4. **Keep a compact Context MEMORY lane.** Adjustment against a strict "move everything out of Main." The lane is the glance; the deck is the document. R-ledger's four-level model (chip → lane → deck → pager) is the right depth ladder. Emptying Context entirely would hide "3 reads · instructions as launched" from the working loop.
5. **Default card is Bundle, not Receipt.** Adjustment against R-ledger, which led with Receipt. This request is "show me the instructions." Receipt is `Ctrl+J` away. Sticky preferred-card persistence still lets a delivery-debugger stay on Receipt.
6. **Never auto-choose MEMORY on split.** Same as RECORD. Otherwise the first `\ ` from Main would skip Files whenever a bundle exists (and a bundle almost always exists).
7. **Picker key `y`, glyph `❖`, cycle slot after FINAL and before RECORD.** `m` is Main. R-ledger already reserved `y`. RECORD later took `r`. Cycle: Main, Files, Tools, FINAL, **MEMORY**, RECORD — inspection decks grouped, working pair left intact.
8. **Two slices.** Adjustment against a single epic that waits on `sase-core` ledger_view. Slice A is presentation of files that already exist (`run_bundle_paths`, `launch_root_bundle`, MEMORY lane events). Slice B is shared backend (litmus: a CLI `sase instructions show` must print the same ledger states).
9. **No deck-view badge / `P` cycle.** Like RECORD, FINAL, and Tools. Bundle is one (blocked) document; Receipt and Ledger are short. Automatic spread/paged from `ace.agent_decks` thresholds is enough.
10. **Availability is content-based**, like Files, not RECORD's always-on four cards. Empty MEMORY shows the empty-state card. A run with no bundle, no reads, and no skills is rare after E3, but native/fallback snapshots still fill Bundle.

---

## 6. Implementation sketch (Slice A)

Copy RECORD's package shape (`widgets/decks/record/`: `model`, `loader`, `document`, `view`, `facts`) into `widgets/decks/memory/`. Load off-thread. Probe with no I/O: cached `instruction_bundle_files` plus cached memory-read/skill-use counts already computed for Context.

Concrete hooks:

| Site | Change |
| --- | --- |
| `decks/model.py` `DeckId` | Add `MEMORY = "memory"`. |
| `decks/spec.py` | Name MEMORY, glyph `❖`, picker `y`, blurb "What this agent was told and looked up", accent distinct from RECORD's `#87AFAF`. |
| `decks/layout.py` `choose_new_panel` | Skip MEMORY the way RECORD is skipped. |
| `decks/availability.py` | `probe_memory_deck`: true when bundle pages, launch snapshot, reads, or skill uses exist. |
| `file_panel/_file_list.py` | Stop appending instruction bundle pages. |
| `file_panel/_instruction_bundles.py` | Keep the cache; MEMORY's loader consumes it. |
| `commands/catalog.py` | Auto-picks `agents.show_deck.memory` / `_other` from `active_deck_cycle()`. |
| Persistence | `coerce_known_deck` already falls unknown ids back to Main. |
| Docs + glossary | `agent-statuses.md` deck list, picker letters, `glossary:deck` (also add the missing RECORD). |
| Visuals | PNG goldens for Bundle and Receipt; Files goldens that currently include `agents_deck_view_files_instruction_bundles_*` must lose those pages. |
| Perf | Do not read bundle bodies on Main `j`/`k`. Resolve bodies when MEMORY is shown. Version chips can stay on the existing Context enrichment; Ledger join must not. Target: Agents-tab `j`/`k` p95 stays under 16 ms (`tui_perf.md`). |

Rust boundary: Slice A is presentation of Python-owned instruction files. Slice B's ledger join is core (`rust_core_backend_boundary`): any CLI or web view must match the TUI.

---

## 7. Alternatives considered

**A. Files grouping only** (keep bundles in Files, section them as "Instructions"). Cheap. Leaves the Files count dishonest and still has no home for the manifest or the read log. Rejected.

**B. Third Main card (Context, Reply, Memory).** Avoids a sixth deck. Puts a 5,000-line document on the same deck as Reply, fights preferred-card stickiness, and still needs Files-style rendering inside Main. Rejected.

**C. Grow RECORD to five cards.** One picker letter, no sixth cycle slot. Mixes identity with content; breaks RECORD's "exactly four cards, always" contract; makes unreadable archive rows show an empty Bundle in an identity deck. Rejected.

**D. Modal or pager-only.** The pager already opens from the launch-row hint. You lose splits (Reply beside instructions), which is the debugging workflow. R-ledger rejected this. Still rejected.

**E. Full R-ledger deck in one epic** (chip + lane + Receipt + Ledger + Bundle + Seen by + clan strip + core ledger_view). Right end state, wrong first PR. The user cannot inspect a bundle in a proper deck until the Rust join lands. Split.

**F. Name the deck INSTRUCTIONS, picker `i`.** Clearer for Slice A, too narrow once Ledger includes reads and skills. MEMORY matches the existing lane, the Config sub-tab, and R-ledger. Keep MEMORY.

---

## 8. Is this a good idea?

**Yes.** The current Files placement is a category leak that made sense when there was no other document deck for host-generated Markdown. RECORD now exists as the identity deck; MEMORY should exist as the context-consumed deck. Together with Main (work), Files (output), Tools (invocations), and FINAL (host completion), the set is coherent:

```
told  →  did  →  changed  →  invoked  →  landed  →  who
MEMORY   MAIN    FILES       TOOLS      FINAL     RECORD
```

The idea is not new. R-ledger specified this deck two weeks ago; the tree implemented the Files shortcut instead. Doing the deck properly also *fixes* Files (honest counts, cheaper spread) and *protects* RECORD (identity stays identity).

The risk is deck sprawl. Mitigations already in the tree: never-auto-choose, content-based empty states, picker letters, one-deep last-deck (`pp`). Use them.

---

## 9. Recommended solution

**Build MEMORY as a sixth Agents-tab deck. Move the instruction bundle there. Leave RECORD alone. Leave macros in the header. Take the bundle off Files.**

### Slice A (do this)

1. Register `DeckId.MEMORY` with picker `y`, glyph `❖`, cycle after FINAL, skip in `choose_new_panel`.
2. Cards, in order: **Bundle** (default), **Receipt**. Helper and later sequences are blocks on Bundle and Receipt, not extra decks or Files pages.
3. Remove instruction-bundle pages from Files list, labels, probes, spread, and the Files instruction-bundle PNG.
4. Keep the Context MEMORY lane as a five-row glance; its launch hint opens MEMORY/Bundle in the focused (or other) panel.
5. Off-thread loader; no bundle-body I/O on Main navigation.
6. Update glossary `deck` (include RECORD and MEMORY), `agent-statuses.md`, and the Files/history docs that currently say the Files deck appends bundles.

### Slice B (next)

7. **Ledger** card from an `sase-core` `ledger_view` joining manifest sections, `memory_reads.jsonl`, and skill-use events.
8. Fold SKILLS and legacy GLOSSARY lanes into Ledger groups; keep PLAN/BEAD/ARTIFACTS/WORKSPACES on Context.
9. Optional header chip and clan `common_digest` strip.
10. Config Memory panel "Seen by" remains a different surface (project note → agents), not a Memory-deck card.

### Explicit non-goals

- Macros card.
- RECORD gaining instruction content.
- Dual-homing the bundle in Files.
- `P` deck-view cycle on MEMORY.
- One card per audited read.

That is the smallest design that makes Files honest, gives the bundle a real home, and leaves room for the ledger without blocking the move.
