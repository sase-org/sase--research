# A MEMORY Deck for What an Agent Knew: Critique and Recommended Design

**Date:** 2026-10-19 · **Researcher:** `cld` (swarm `research.4x`) · **sase checkout:**
`e5f2d768ea` (master)

> **Request:** The selected agent's instruction bundle shows in the FILES deck today.
> Move it into a new MEMORY deck that also has cards for other memory the agent used (and
> maybe macros). Decide which cards and blocks belong there, and whether they belong in an
> existing deck such as RECORD instead. Critique the plan, adjust the requirements where
> justified, and recommend a solution.

## Bottom line

1. **Moving the bundle out of FILES is right, and it fixes a real regression.** Since
   `552b38f7ed` (2026-10-16), every explicit-delivery agent shows bundle pages in FILES.
   They count toward the `files N` switcher entry. For an agent with no diffs they also
   become the *default* FILES page. A research agent that touched nothing now shows
   `files 2` (a root and a helper bundle) and opens onto 350 lines of boilerplate. FILES'
   blurb is "Diffs and files the agent touched"; a bundle is neither.
2. **A deck built around the raw bundle would be a weak deck.** Over the last five days,
   401 instruction manifests produced only **27 distinct bundles** and **11 distinct
   common digests**. The top digest covered 160 runs. The bundle text is nearly the same
   for every agent. What differs per agent, and what you need when debugging, is:
   - which memory the agent was handed, and in what form (inlined, listed, excluded);
   - what it actually looked up, and why;
   - at which versions, and whether a retry today would see different text;
   - whether delivery worked.

   So the deck's **default card should be a per-agent Sources view**, not the bundle.
3. **The cards do not belong in RECORD.** RECORD answers "what is this run?" with
   fixed-shape fact sheets. It is always present, it serves as the "Record only" fallback
   for unreadable Archive entries, and it is absorbing the retired Artifacts Agent pane.
   Memory content is large and varies per run, and you use it to debug ("why did it do
   that?"). Mixing them would push RECORD into paged mode and bury Lifecycle. It would also
   collide with RECORD's existing `Bundle:` field, which means the *archive* bundle.
4. **Macros mostly stay out.** General macros are prompt composition, already shown twice
   (identity-header chips and the `Macros:` metadata list), and recorded only shallowly
   (top-level names and args in `macros.json`). The exception is **`#memory/<note>`
   macros**. They inject memory through the prompt, and today no read audit or version
   pin sees them. They belong on the Sources card.
5. **Recommendation:** add a sixth deck, **`❖ MEMORY`** (picker `y`), with:
   - **Sources** (default): what the agent knew and looked up, version-pinned, with drift
     since launch.
   - **Instructions**: the exact bundle, rendered by section, with one block per
     invocation, replacing the FILES pages.
   - **Members**, for clan and tribe nodes: whether every member got the same
     instructions.

   Keep the Context card's MEMORY lane as the glance and give it a jump into the deck. Put
   the Sources join in `sase-core`, with CLI parity. Use the sixth deck as the moment to
   extract a small "document deck" seam, so deck seven doesn't cost another ~20 files.

---

## 1. What exists today (verified on this checkout)

### 1.1 The bundle in FILES

- `file_panel/_file_list.py:39-77`: `desired_file_pages()` appends
  `instruction_bundle_pages(agent)` **after** commit, live, linked-repo, and extra-file
  pages (`:66-68`). The default page is `pages[0]`, so an agent with no diffs and no extra
  files defaults to its bundle.
- `decks/availability.py:31-41`: `probe_files_deck` returns `len(pages)`, so bundles are
  counted in the `files N` switcher entry.
- `file_panel/_instruction_bundles.py` holds a no-I/O LRU keyed by agent identity. It is
  filled off-thread by `compute_instruction_bundle_files()`, which calls
  `sase.instructions.manifests.run_bundle_paths()`. Done loaders also set
  `Agent.instruction_bundle_files` (`_done_common.py:114`, snapshot and filesystem
  loaders, merged in `_dedup.py`).
- The golden `agents_deck_view_files_instruction_bundles_160x40.png` shows the result: an
  agent with only bundles reads `files 2`, and the cards are `00-claude.md` and
  `00-claude.helper.md`, rendered as plain numbered lines.

### 1.2 The memory glance in MAIN

The Context card's `SASE CONTEXT` section has seven lanes, in this order
(`prompt_panel/_agent_context.py:55-63`): PLAN, BEAD, ARTIFACTS, MEMORY, GLOSSARY, SKILLS,
WORKSPACES.

- **MEMORY** (`_agent_memory_reads.py:105-200`). The header reads
  `N reads · M files · Instructions as launched`. Next comes a launch row: the bundle with
  its channel, size, and `bytes match`/`MISMATCH`, or an `AGENTS.md as launched` snapshot
  for pre-E3 and native runs. Then up to **5** reads, each with a version chip
  (`≡ now`, `vK ⟲ N newer`, `◌ uncommitted at read`) and its reason.
- **GLOSSARY** reads the *legacy* `glossary_reads.jsonl`. Its last write was 2026-08-24.
  Glossary lookups now arrive as `strand` events in `memory_reads.jsonl` (1,246 so far).
  The lane only ever shows something for old runs.
- **SKILLS** shows `skill_uses.jsonl` events: skill name, time, and reason.

### 1.3 Per-agent data already on disk

| Source | What it records | Current TUI use |
| --- | --- | --- |
| `<artifacts>/instructions/NN-<provider>.md` (+ `.helper.md`) | Exact bundle bytes for each invocation. They are also content-addressed under `~/.sase/instructions/bundles/<sha>.md`. | FILES pages; launch-row `v` hint |
| `<artifacts>/instructions/NN-<provider>.json` (+ `.helper.json`, `.error.json`) | Manifest, schema v2. `bundle{sha256, common_digest, bytes, lines, tokens_est}`. `budget.by_layer`. **`sections[]`**: `{id, layer, status, lifecycle, tokens_est, offset, length, sha256, reason}`, with **`sources[]`**: `{scope, kind, path, blob_oid}`. `delivery{status, channel, cache, render_ms, provider_cli_version, subagent…}`. | Launch-row chip only |
| `~/.sase/projects/<p>/memory_reads.jsonl` (schema v3) | Each audited read: `kind` (note, web, strand), selectors, resolved and included targets, reason, `blob_oid`/`included_blob_oids`, `artifacts_dir` | MEMORY lane (5 rows) |
| `~/.sase/projects/<p>/skill_uses.jsonl` | `skill_name`, reason, time, `artifacts_dir` | SKILLS lane |
| `<artifacts>/macros.json` (+ `macros_<step>.json`) | Top-level macro refs only: `{name, kind, positional, named, tags}`. Nested expansions are not recorded. | Header chips (max 3), the `Macros:` metadata list |
| `agent_meta.json` `instructions`, `instruction_snapshot`, `workspace_head` | Latest-invocation summary; the pre-E3 `AGENTS.md` snapshot | Launch row |
| Memory-history feed (Rust `file_history`) | Changesets with `provenance.agent` and `bead` | Admin Center Memory pane |

My own manifest for this run, `00-claude.json`, has 34 sections:

- 8 package and frame sections;
- 2 inlined core notes (`gotchas`, `rust_core_backend_boundary`);
- 16 listed reference notes (2 home, 14 project);
- 3 webs, carrying 109 strand sources;
- 3 excluded sections: two `superseded_input`, one helper `overlay`.

The **decisions web alone is 1,998 of 5,239 tokens**. Every one of these facts is
per-section and per-blob, and none of them is visible in the TUI today.

### 1.4 Drift detection already exists in the CLI

`sase instructions render -a <agent>` re-renders the agent's facts against current memory
and reports the drift itself:

```
agent research.4j.gem: bundle differs from recorded 1001095412fd: changed sections:
  pkg.sase.memory, proj.ref.ace, proj.ref.demos, proj.ref.docs_writing, proj.ref.tools,
  proj.web.decisions, proj.web.glossary
```

That run took 35 ms; for my own agent it took 78 ms with a cache hit and reported
`bundle matches recorded`. This answers "would a retry see my memory fix?", the most
useful debugging question here, and the TUI does not ask it.

### 1.5 RECORD's charter

The plan is `plan:202610/agents_archive_view_record_deck.md`, documented in
`docs/reference/tui/agent-statuses.md`. RECORD has four fixed cards in a fixed order:

- **Lifecycle**
- **Provenance**: project, workspace, model, tab, tribe, owner, chat, artifacts dir, and
  `Bundle:`, which means the *dismissed-agent archive bundle*
  (`record/facts.py:127-130`)
- **Relations**
- **Links**: artifact graph edges, which already include `read` edges for artifacts the
  agent read

RECORD has no blocks and is reachable only explicitly. It is never auto-chosen for a new
split. It also serves as the "Archive entry unreadable — Record only" fallback, and it is
the planned home for the retired Artifacts Agent pane's Details panel.

### 1.6 What a deck costs (measured from RECORD's history)

RECORD's shell commit `b4dbfcd90e` changed:

- 39 non-PNG files;
- about 250 lines of edits across roughly 20 existing source files, most of them explicit
  `if deck is …` / exhaustive `match` arms, some ending in `AssertionError`;
- 868 lines of new package code, plus a 154-line `panel_record.py` mixin;
- **278 regenerated PNG goldens**, because every Agents footer switcher gained `record`.

Five more commits added its cards. Registry-derived surfaces pick up a new spec
automatically: the picker, palette, help, footer, and persistence decode.

## 2. Measurements that shape the design (last 5–7 days, `sase` project)

| Measure | Value | Design consequence |
| --- | --- | --- |
| Distinct bundles across 401 root and helper manifests | 27 bundle SHAs, 11 common digests (the top digest covers 160 runs) | The raw bundle is mostly boilerplate, so it should not be the default card. Drift results can be cached per bundle SHA, with a high hit rate. |
| Bundle size | 4.9k / 5.2k / 5.6k tokens (min / median / max) | About 350 lines. Paged, never spread with other cards. |
| Root invocations per run | 1 for 270 runs, 2 for 33, 3–4 for 2 | Blocks are needed but usually trivial. Claude runs add a helper bundle. |
| Memory reads per agent (agents that read at all, 7 days) | 487 agents; median 2, p90 5, max 12; **only 35 (7%) exceed the lane's 5-row cap** | An uncapped reads list adds little. The deck's value is the join, versions, and drift, not more rows. |
| Read kinds | 1,119 note, 184 strand, 4 web | Strand reads matter (glossary and decisions). |
| Skill uses (7 days) | 210 events across 139 agents; top: `sase_new_task`, `sase_memory_write`, `sase_memory_read` | Small but meaningful. Skills are procedural memory pulled on demand. |
| Drift check (`render -a`) | 35–78 ms | Affordable off-thread when the Sources card is shown. |

## 3. Critique: is this a good idea?

### 3.1 Yes, for three reasons

1. **FILES is lying a little.** The switcher count and default page now reflect boilerplate
   rather than the agent's work. The `files 0` dim state was a useful "touched nothing"
   signal, and bundles have erased it.
2. **The manifest has structure the file viewer throws away.** Section ids, layers,
   sources, blob OIDs, token costs, and exclusion reasons all exist. A generic file page
   can show none of them.
3. **"What did it know?" is a real, recurring question with no home.** It has a 5-row
   glance in MAIN and a scope-based Memory pane in the Admin Center, which is not
   per-agent. Prior research reached the same conclusion: the
   `instruction_bundles_provider_parity_and_memory_ledger.md` report (2026-10-05)
   proposed a MEMORY deck (`p y`) with Receipt, Ledger, and Bundle cards before the RECORD
   deck existed.

### 3.2 But the plan as stated has the wrong center of gravity

"Show the bundle in a new deck, plus cards for other memory" makes the bundle the main
thing. The numbers say the bundle is the *least* informative per-agent object: 27
distinct texts across 401 runs. The deck earns its slot only if its default card answers
the debugging questions:

- **Did it have the rule?** Inlined, listed, or excluded.
- **Did it look the rule up?** Read, when, and why.
- **At which version?** And is that version stale now?
- **Would a retry see something different?** That is drift.
- **Was it delivered correctly?** Channel, integrity, helper.

### 3.3 Where each candidate card belongs

| Candidate content | MEMORY | RECORD | MAIN Context | FILES | TOOLS | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Instruction bundle bytes | ✔ | ✘ fact sheets only; `Bundle` name collision | ✘ hot path | ✘ not a touched file | ✘ | **MEMORY · Instructions** |
| Delivery and integrity facts | ✔ (block header) | ~ one optional cross-link line | ✔ glance chip (exists) | | | MEMORY, with the glance kept in MAIN |
| Inlined, listed, excluded memory and token budget | ✔ | ✘ | ✘ | | | **MEMORY · Sources** |
| Audited memory and strand reads | ✔ joined into Sources | | ✔ glance (exists) | | raw `Bash` calls (exists) | MEMORY, with the glance kept in MAIN |
| Drift since launch | ✔ | | ~ chip later | | | **MEMORY · Sources** header |
| Skill uses | ✔ (procedural memory) | | ✔ glance (exists) | | | MEMORY · Sources group |
| `#memory/<note>` prompt macros | ✔ (memory, unaudited today) | | | | | **MEMORY · Sources** |
| Other macros (`#gh`, `#research`, swarms) | ✘ | ~ launch provenance | ✔ chips, `Macros:`, RAW PROMPT (exist) | | | **Stay in MAIN** |
| Artifact reads (plans, research, beads) | ✘ | ✔ Links `read` edges (exists) | ✔ ARTIFACTS lane (exists) | | | **Stay put** |
| Opened workspaces and repos | ✘ | | ✔ WORKSPACES lane | | | **Stay put** |
| Memory the agent *changed* | ✔ (v2) | | | diff page (exists) | | MEMORY v2, from history-feed provenance |
| Clan or tribe "same instructions?" | ✔ Members card | | | | | **MEMORY · Members** |

### 3.4 Why not RECORD, in more detail

- **Shape.** RECORD cards are short key/value sheets. They spread on one page when they fit,
  and every node has them. A 350-line bundle and a 40-row sources table would force RECORD
  into paged mode, where Lifecycle stops being the thing you see.
- **Purpose.** RECORD is identity and bookkeeping ("what is this run, where, related to
  what"). MEMORY is cognition ("what did it know, and was that the right thing?"). You
  reach for MEMORY *next to* MAIN/Reply in a split. RECORD is deliberately never
  auto-chosen and lives last in the cycle.
- **Archive fallback.** RECORD must render from the bundle-index light row even when the
  artifacts directory is unreadable. Memory cards require artifacts-dir I/O, and coupling
  them would weaken that guarantee.
- **Vocabulary.** RECORD's `Bundle:` is the archive bundle. Putting instruction bundles
  in the same deck invites confusion.

The one thing RECORD could reasonably gain later is a single Provenance line,
`Instructions: 00-claude 28cf39d · explicit`, as a cross-link to MEMORY. That is
optional, not v1.

### 3.5 Why not just grow the MAIN lane, or use the Admin Center Memory pane

- **The MAIN lane is on the hot path of every selection**, and it is capped at 5 rows on
  purpose. It should stay the glance, the way the ARTIFACTS lane is the glance for FILES.
- **The Memory pane is scope-based, not agent-based.** It lives behind `gm` in the Admin
  Center and cannot sit in a split next to the Reply. It is the right home for the
  *reverse* view later ("Seen by: inlined in 212 runs, read by 14").

### 3.6 Risks and costs

- **Golden churn.** About 280 PNGs regenerate, because the footer switcher gains
  `memory`. This is mechanical, but do it once, in the shell phase.
- **Hard-coded deck branches.** Without a seam, deck six repeats RECORD's ~20-file arm
  hunt, including `AssertionError` fallthroughs. A missed arm can render one deck's
  content under another's header; the RECORD plan named this as the failure to fear.
- **Switcher width.** Six entries widen the subtitle by about 9 cells. Its tiers already
  drop counts, then the whole switcher, so this degrades gracefully but happens sooner in
  side-by-side splits.
- **Naming collisions.**
  - "Bundle" means the archive bundle in RECORD.
  - "Ledger" is already the goal domain's term (`decisions:goal-ledger`).
  - "Context" is MAIN's card name.

  So the cards are **Sources** and **Instructions**.
- **Core boundary.** The sources join (manifest sections × reads × prompt macros × skills
  into per-subject states) is domain logic a CLI or other frontend would need to match.
  Under `rust_core_backend_boundary` it belongs in `sase-core`, not in TUI Python.
  Manifest normalization is already there (`instruction_manifest/normalize.rs`). The join
  is not.
- **Stale vocabulary.** `glossary:agent-data-deck` still lists only Main, Files, Tools,
  and FINAL. It is already stale after RECORD and will need an update through
  `/sase_memory_write`.

## 4. Requirement adjustments (explicitly changed from the request)

| # | Adjustment | Why |
| --- | --- | --- |
| **A1** | The deck's **default card is Sources**, a per-agent view of what it knew and used. The bundle is the second card. | 27 distinct bundles across 401 runs; the debugging questions are about joins, versions, and drift. |
| **A2** | Title the bundle card **Instructions**, not "Bundle", and avoid "Ledger". | Collisions with RECORD's archive `Bundle:` and the goal ledger. It matches the existing "Instructions as launched" wording. |
| **A3** | **Macros: only `#memory/<note>` refs** go in the deck, as prompt-injected sources. Other macros stay in MAIN. | Prompt composition is MAIN's question, macro data is shallow, and they are already shown twice. `#memory/*` is memory that no read audit or version pin covers today. |
| **A4** | **Include skills.** **Exclude** artifact reads and opened workspaces. | Skills are on-demand procedural memory with logged reasons. Artifact reads already live in RECORD Links and the ARTIFACTS lane. |
| **A5** | **Nothing moves into RECORD.** At most, a later one-line Provenance cross-link. | §3.4. |
| **A6** | **Keep the Context-card MEMORY lane** as the glance, and add a hint that opens the MEMORY deck. | The lane is cheap, already pinned, and covers 93% of agents' reads completely. Lane-to-deck mirrors ARTIFACTS-to-FILES. |
| **A7** | **Move, don't copy.** Remove the FILES bundle pages in the same phase that ships the Instructions card. | Restores FILES' count and default page with no window where bundles are unreachable. |
| **A8** | **Drift since launch ships in v1.** | Already computed by `render -a` in 35–78 ms. It is the highest-value signal. |
| **A9** | **The sources join lives in `sase-core`**, with CLI parity (an option on `sase instructions show`; read `cli_rules.md` first). | The core-boundary rule, and a single source of truth for the CLI and TUI. |
| **A10** | **Extract a bounded "document deck" seam** (RECORD and MEMORY only) while adding the deck. | Stops each new deck from costing about 20 hand-placed arms, and keeps the exhaustive-match safety through a typed registry. |

## 5. Recommended design

### 5.1 Deck identity

| Property | Value | Notes |
| --- | --- | --- |
| Name and glyph | `MEMORY`, `❖` | Distinct from MAIN's `◆` and the lane's `◇` row glyph |
| Blurb | "What the agent was told and looked up" | |
| Picker key | **`y`** (memor**y**) | `m f t n r` are taken; `j k q p` are reserved. `e` is the alternative. `y` matches the prior report. |
| Cycle position | After TOOLS: `main · files · tools · memory · final · record` | Keeps the common MAIN→FILES→TOOLS hops. Memory reads are semantically enriched tool calls. If the TOOLS→FINAL hop matters to you, append it last instead. |
| Auto-choose for new splits | Never, like RECORD | A debugging deck you reach for explicitly |
| Accent | One new hue, shared with the MAIN lane's MEMORY label | Avoid TOOLS cyan (`#87D7FF`); today's lane color `#5FD7FF` is too close to it. Also avoid Archive amber and MAIN mauve. Validate in the light theme. |
| Switcher count | Number of audited reads (memory plus strand) | Reuses the lane's already-loaded events, so it needs no I/O |
| Switcher status segment | Red `memory ⚠` when delivery fell back or integrity is `MISMATCH`/`missing`; otherwise the count | "Quiet when correct, loud when wrong". Integrity is already resolved off-thread for the launch row. |
| Dimmed when | No bundle, no snapshot, and no reads (procs, monitors, gates, bash/python steps) | |
| View policy (`P`) | None (AUTO), like Tools, FINAL, and RECORD | |

### 5.2 Cards for an agent or turn node

**Card 1: Sources (the default).** It answers "what did it know, what did it use, at what
version, and is any of it stale?" The mockup is illustrative. Token counts, section
counts, and read rows come from this run's manifest and read log. The `⟲ changed` marks
and the `#memory/dispatch` row are invented to show those states; this run actually
matches current memory.

```text
❖ MEMORY  ‹ 1/2 › Sources
INSTRUCTIONS  00-claude · explicit · append_system_prompt_file · bytes match       [1]
              ≈5.2k tok   frame 0.2k · package 1.4k · project 3.7k · home 0.1k
              ≡ matches current memory    (or: ⟲ 7 sections changed since launch [2])
              helper 00-claude.helper · explicit · subagent channel
PACKAGE   6 sections · 1.4k tok · sase 0.17.1                                     [3]
HOME      ~/sase/memory
  ◇ obsidian.md                      24  listed                 ≡
  ◇ tailnet.md                       38  listed                 ≡
PROJECT   sase/memory
  ● gotchas.md                       62  core                   ≡                   [4]
  ● rust_core_backend_boundary.md   240  core                   ⟲ changed           [5]
  ◆ tui.md                           37  read 08:00             ≡                   [6]
      ↳ researching agent deck/card design for memory deck proposal
  ◆ tui_perf.md, ace.md                  read 08:00 · batch     ≡                   [7]
  ◇ cli_rules.md, demos.md, dispatch.md … 9 more listed, unread
  ◇ decisions   web · 30 strands  2.0k  listed                  ⟲ changed           [8]
  ◇ glossary    web · 71 strands  0.5k  listed
  ◆   └ glossary:agent-data-card +17     read 08:00             ≡                   [9]
PROMPT
  ▣ #memory/dispatch                     injected by prompt macro (unaudited)
SKILLS
  ◆ sase_repo                            used 08:07
      ↳ open sase-core (read-only: check instruction_manifest module…)
EXCLUDED  ○ proj.core.sase, home.core.sase  superseded_input · ○ helper contract  overlay
● inlined  ◇ listed  ◆ read/used  ▣ prompt-injected  ○ excluded  ⟲ changed since launch
```

- **Row states.** Each state comes from joining manifest sections and sources with read
  events, `#memory/*` refs, and skill uses. A read of a subject that was not itself listed
  (for example a child note pulled in through a link closure) shows `via link`.
- **Version chips.** A `⟲ changed` mark comes from one off-thread `render -a` drift result,
  mapped from section to sources. That is a single render, not one timeline per row; it is
  cached by (bundle SHA, facts, memory change token) and shared across agents with
  identical bundles. Read rows keep their existing blob-pinned chips (`vK ⟲ N newer`). The
  "N newer" count for listed rows resolves lazily, when the hint is opened.
- **Hints.**
  - `[n]` on a source opens the memory-history pager pinned to the launched blob. On a
    `⟲` row, the pager opens already comparing the launched blob with now. The
    `MemoryVersionPin` plumbing already exists.
  - `[1]` jumps to the Instructions card.
  - `[2]` shows the section-level diff (v2) or prints the changed section ids (v1).
- **Package group.** Collapsed to one row by default. It changes only with a sase upgrade.

**Card 2: Instructions.** The exact bytes, rendered by section. There is one **block per
invocation**, stepped with `(` and `)` on the block rail: `00 root`, `00 helper`,
`01 root · recovery`. The block header carries the delivery facts.

```text
❖ MEMORY  ‹ 2/2 › Instructions · 00 root                     ( 00 root · 00 helper )
INVOCATION  00 · root · claude opus · 08:00:16 · cache hit · 55 ms
DELIVERY    explicit · claude.append_system_prompt_file · claude 2.1.303 · bytes match
BUNDLE      28cf39d · 20.9 KB · 350 lines · ≈5.2k tok              [1] open  [2] path
── frame.title ──────────────────────────────────────────────────── frame · 28 tok
# SASE = Structured Agentic Software Engineering (sase)
── pkg.sase.memory ──────────── package · memory-sase.template.md@0e884cf · 330 tok
#### SASE Memory
…
── proj.core.gotchas ─────────────────── project · sase/memory/gotchas.md@9bf9ea5 · 62 tok
### Code Conventions and Gotchas (gotchas)
…
```

- **Section rules.** They come from the manifest's `offset` and `length`. A section that
  drifted gets a `⟲` on its rule.
- **Other behavior.** Deck search (`/`) and `Z` zoom work as they do on other cards. `[1]`
  keeps today's "open the launched bundle read-only" action, so nothing the FILES page
  offered is lost.
- **Pre-E3 and native runs.** The card shows the stored `AGENTS.md as launched` snapshot,
  with the existing `vN` and `not in git` states. Where neither exists, it shows an
  explicit empty state.

### 5.3 Cards for other node types

| Node | MEMORY deck shows |
| --- | --- |
| Agent session | Sources for the union of member turns. Read rows carry the member's role label, as the lane's loader already does. Instructions blocks span every turn's invocations. |
| Clan / tribe panel | **Members** card. It shows one common-digest verdict, then one row per member: provider, bundle SHA, delivery, reads count, and drift. An illustrative header: `research.4x · 5 members · common 0348c85 shared by 5/5 ✓`. This answers "did the whole swarm get the same instructions?" |
| Monitor, gate, named proc, bash/python step | Empty state: "No model invocation, so no instructions". The deck is dimmed in the switcher. |
| Archive (read-only) | Same cards, read from the artifacts dir. If retention pruned it: "Instructions pruned by artifact retention". This must never block RECORD's light-row path. |
| Remote/fleet-owned agent | "Recorded on ⌨ <alias>; not available locally" until fleet transport carries manifests. |

### 5.4 Interaction with the rest of the TUI

- **MAIN Context, MEMORY lane.** Unchanged content. Its header gains a hint that opens
  MEMORY in the other panel, using the capital-letter semantics. The natural workflow is
  `|` (vertical split): MAIN/Reply on the left, MEMORY/Sources on the right, so you read
  what it did beside what it knew.
- **GLOSSARY lane.** Leave it. It is legacy-only and already renders nothing for new runs.
  Legacy glossary events can appear as read rows on Sources for old agents.
- **FILES.** Drop the bundle pages, the bundle `source_label` tag, and the Archive and
  done-dispatch bundle branches (`_file_list.py:66-68`, `_agent_detail_files.py:36-39`,
  `:54-58`). The `instruction_bundle_files` field and the off-thread cache stay, moving
  next to the MEMORY loader.
- **Performance rules.** Follow `tui_perf.md`:
  - Capture a frozen subject on the pump.
  - Load in a thread worker, with a stale-generation guard (RECORD's `view.py` pattern).
  - Paint cached data first.
  - Never stat or glob on a render path.
  - Run drift only when the Sources card is visible, coalesced and cached by bundle SHA.

### 5.5 Architecture

```
sase-core (Rust)                      sase (Python)                      TUI
──────────────────────────────────    ────────────────────────────────   ─────────────────────────
instruction_manifest::normalize  ──▶  sase.instructions.manifests   ──▶  decks/memory/loader.py
NEW instruction_sources::join(        (read manifests, bundle paths,     (thread worker, LRU by
  manifests, read_events,              integrity, render -a drift)        artifacts dir + tokens)
  prompt_memory_refs, skill_uses)                                    ──▶  decks/memory/document.py
  → SourcesWire (rows, states,   ──▶  sase instructions show NAME         (Sources / Instructions /
     tokens, blob pins, drift)         --sources  (CLI parity)             Members CardParts)
```

Two notes on this:

- **What moves to Rust.** The join is pure data, so it is cheap to put in `sase-core` with
  table tests, and it removes any temptation to grow a second interpretation in Python.
  Bump `sase-core-revision.txt` past the core commit, per `docs/rust_backend.md`.
- **The document-deck seam (A10).** Today RECORD wires its subject, worker, document,
  `RecordDeckLoaded`, and the `panel_record` mixin by hand. Generalize exactly that path
  into a registry entry: `subject_from_agent`, `load`, `build_document`, `probe`, `tabs`,
  `empty_state`, and `message`. RECORD and MEMORY would both register through it, and the
  `match` arms for document decks would collapse into a registry lookup that raises on
  unknown decks. Leave MAIN, FILES, TOOLS, and FINAL alone, so the refactor stays bounded.

## 6. Phased plan

| Phase | Scope | Size | Exit proof |
| --- | --- | --- | --- |
| **1. Core join + CLI** | `instruction_sources` wire and join in `sase-core`; Python binding; a `sase instructions show NAME` option printing the Sources table (read `cli_rules.md` first) | M | Table tests in Rust; CLI output for a Claude, a Codex, and a pre-E3 run |
| **2. Deck shell + seam** | `DeckId.MEMORY`, spec, picker `y`, accent rules, availability probe, persistence, switcher; the document-deck seam (RECORD migrated onto it with no behavior change); empty states | M–L (≈20 files, ~280 goldens regenerated once) | Existing RECORD tests unchanged; new shell test; j/k bench (p95 < 16 ms) |
| **3. Instructions card + FILES removal** | Section-aware renderer, invocation blocks, delivery header, open/path hints; remove bundle pages from FILES in the same phase | M | Goldens: Instructions dark/light, FILES `files 0` for a bundle-only agent; `test_file_panel_selection_preserved` updated |
| **4. Sources card + drift** | Join rendering, version chips, drift via `render -a` (cached by bundle SHA), pager pins, `#memory/*` rows, skills group, lane-to-deck hint | M | Goldens: clean, drifted, pre-E3, and session; drift worker never on the pump (trace span) |
| **5. Members card + docs** | Clan/tribe common-digest matrix; `agent-statuses.md`, `agents-main-deck.md`, `memory/history.md:208`, `instruction-bundles.md`; `glossary:agent-data-deck` (and the missing RECORD) via `/sase_memory_write` | S–M | Golden for a research-swarm clan; docs build |

Phases 1 and 2 can run in parallel; phases 3 and 4 depend on 2.

## 7. Deferred, on purpose

- **A Timeline card**: memory reads, skills, and legacy glossary reads, chronological and
  uncapped. Only 7% of agents overflow the lane today. Add it if that changes.
- **"Wrote" group**: memory changesets whose history-feed `provenance.agent` is this agent.
  The data exists, but it lands only after host finalizers commit.
- **Observed delivery**: `sase instructions verify -a NAME` reads provider transcripts (up
  to 512 KB each). Offer it as an on-demand key, never on selection.
- **A Prompt card with a macro expansion trace**: name, source path and blob, nesting, and
  the expanded span. This is the symmetric "prompt provenance" story. Record the trace in
  the macro engine first, then decide whether it lives in MAIN or MEMORY. Building the UI
  before the data violates the spirit of `decisions:corpus-before-mechanism`.
- **Reverse view in the Admin Center Memory pane**: "Seen by: inlined in N runs, read by
  M".
- **Section-level drift diff**: an Instructions toggle showing launched vs. now, per
  section.

## 8. Open questions for you

1. Picker letter: `y` (recommended) or `e`?
2. Cycle position: after TOOLS (recommended) or last?
3. Switcher count: reads (recommended), or invocations, or sources?
4. Should the MAIN lane keep its "Instructions as launched" launch row once the deck
   exists? I recommend keeping it: it is the one-line delivery glance.
5. Is the bounded document-deck seam (A10) welcome now, or do you prefer to copy RECORD's
   pattern and refactor at deck seven?

## Recommended solution

Build a sixth Agents-tab deck, **`❖ MEMORY`** (picker `y`, after TOOLS in the cycle,
never auto-chosen), whose job is "what the agent was told and looked up".

- **Sources (default).** One version-pinned table of every memory source:
  - inlined core;
  - listed reference notes and webs;
  - audited note and strand reads, with reasons;
  - `#memory/*` prompt injections;
  - skill uses;
  - excluded sections, with reasons.

  It carries a header with the delivery and integrity chip, the layer token budget, and a
  **drift-since-launch** verdict from the existing `render -a` check.
- **Instructions.** The exact bundle, rendered by manifest section, with one block per
  invocation (root, helper, recovery) and the delivery facts in each block header.
- **Members**, on clan and tribe nodes: a common-digest matrix.

Remove the bundle pages from FILES in the same phase the Instructions card lands. Keep the
MAIN Context MEMORY lane as the glance and give it a jump into the deck. Leave RECORD as
the identity deck. Keep general macros in MAIN. Put the sources join in `sase-core`, with
a matching `sase instructions show` option. Use the sixth deck to extract a small
document-deck seam shared with RECORD, so the next deck is a registry entry rather than
another twenty-file arm hunt.

---

## Appendix: evidence index

- **Bundles in FILES:**
  - `src/sase/ace/tui/widgets/file_panel/_file_list.py:39-77`
  - `.../file_panel/_instruction_bundles.py`
  - `.../decks/availability.py:31-55`
  - commit `552b38f7ed`
  - golden `agents_deck_view_files_instruction_bundles_160x40.png` (`files 2`)
- **Context lanes:**
  - `.../prompt_panel/_agent_context.py:55-63`
  - `.../prompt_panel/_agent_memory_reads.py:105-200`
  - `.../prompt_panel/_agent_memory_versions.py:272-478`
  - `src/sase/ace/tui/glossary_reads.py` (legacy log; last write 2026-08-24)
- **Deck registry and cost:**
  - `.../decks/spec.py`, `.../decks/model.py`
  - `.../decks/titles.py:31` (reserved `j k q p`), `.../decks/titles.py:461-553` (switcher tiers)
  - RECORD commits: `b4dbfcd90e` (shell, 278 PNGs), `e82db580a2`, `a6df5daa01`, `f26ac18475`, `5ba61b41a8`
- **RECORD facts:**
  - `.../decks/record/facts.py:110-131` (Provenance `Bundle:` = archive bundle)
  - `plan:202610/agents_archive_view_record_deck.md`
- **Manifest shape:**
  - `src/sase/instructions/manifest.py`, `.../sections_base.py`, `.../manifests.py:182-360` (`run_bundle_paths`, `launch_root_bundle`, integrity)
  - `sase-core` `crates/sase_core/src/instruction_manifest/{normalize,wire}.rs` (no join exists)
- **Drift:** `sase instructions render -a NAME`, which prints "bundle differs from recorded …: changed sections: …" (measured at 35–78 ms).
- **Read, skill, and macro logs:**
  - `src/sase/memory/_read_log_models.py:52-87`
  - `src/sase/skills/use_log.py`
  - `src/sase/macro/used_macros.py:34-39,159-268`
  - `src/sase/macro/loader_memory.py` (`#memory/*` is a plain part macro, not audited)
- **History provenance:** `sase memory history -f json` changesets carry `provenance.agent` and `bead`.
- **Prior unrelated research consulted:**
  - `research:202610/instruction_bundles_provider_parity_and_memory_ledger.md` (the earlier MEMORY-deck sketch)
  - `research:202610/memory_history_tui_support/memory_history_tui_support__final.md`
  - `research:202610/preloaded_memory_size_visibility.md`
- **Docs drift noticed:**
  - `docs/reference/tui/agents-main-deck.md` still names an `AGENT MACRO` section, but the code renders `AGENT RAW PROMPT` / `AGENT PROMPT`.
  - `glossary:agent-data-deck` omits RECORD.
