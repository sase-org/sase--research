# Memory & Agent-Instruction Version History — Design Research (cld)

_Researcher: cld · 2026-09-30 · Scope: tracking, indexing, and navigating the history of
SASE memory files and agent instruction files, with the sase pager as the main
interface._

---

## 0. TL;DR

**Verdict: build it, but reframe it.** The request as written ("track every change, add
an index, make the pager the interface") is pointed in the right direction, but three
measured facts change the shape of the best solution:

1. **Storage is already solved.** Every memory file and agent instruction file is in
   git, and one `git log --raw -M` pass over the memory pathspecs returns the whole
   history in **~0.29 s** (465 commits, 1,146 file-changes, 31 renames, 21 deletions).
   Every historical blob (1,047 of them, 9.2 MB) comes back from `git cat-file --batch`
   in **80 ms**. We don't need a new content store. What we need is a small, disposable,
   derived **lineage + classification index** over git. It is keyed by the tip commit,
   rebuilt from scratch in one pass, and updated incrementally in milliseconds.
2. **The real problem is signal-to-noise, not speed.** Raw per-file history is mostly
   noise:
   - Generated notes changed 283 times (e.g. `README.md` 163×).
   - Root `AGENTS.md` changed 207 times since memory existed; 60 of those involved no
     memory edit at all.
   - Each `AGENTS.md` change is copied into four byte-identical provider shims.
   - 88 of 125 home-memory commits are titled `chore: initialize sase memory`.
   - About 42% of the 465 memory-touching commits (195) are `feat`/`fix`/`refactor`
     commits, where the subject describes code, not memory. At least 43 more are
     boilerplate `chore: run sase init…`.

   **The value is in classification (authored vs. regenerated vs. reflow-only),
   provenance (which agent, bead, and note caused it), and summaries derived from the
   diff itself.**
3. **Memory is wrapped prose, so line diffs mislead.** Commit `63d2bdceac` changed one
   word (`shells` → `processes`), but the 88-column rewrap turned it into a 2-line `-/+`
   diff. A paragraph-aware **word diff** is required for the history to be readable.

**Recommended solution:**

- A Rust-core `memory_history` index (pure functions over git output) behind a
  `sase memory history` CLI.
- A generic **time axis for the pager**, available on any memory or instruction section
  with no mode to enter. It uses a bracket-family key system:
  - `(`/`)` step to the previous/next version
  - `[`/`]` jump to the previous/next change
  - `{`/`}` jump to the oldest version / back to now
  - `=` toggles the read/diff lens
  - `@` opens the timeline picker
- A time band with a change-volume sparkline, prose word diffs, scroll anchoring across
  versions, and links that stay at the same point in time.
- A **Memory Changes feed** document (`sase memory history` with no args) as the
  cross-file entry point, plus an `H` key and a "last changed" line in the Memory panel.
- Ship in four phases. Phase 1 needs **no pager core changes**: it builds history
  documents out of existing multi-section pager machinery, which proves the index and
  the value before we touch the pager's keymap.

Requirement changes I'm making (details in §3):

- Collapse the byte-identical provider shims into one tracked subject.
- Add working-copy and unlanded versions to the timeline.
- Add provenance: who/why for each version.
- Add "what did agent X see?" by recording blob hashes in reads and launches.
- Include deleted notes.
- Use the name `history`, because `sase memory log` is already the read-audit command.
- Design the pager time axis generically, but enable the semantic layer for memory
  first.

---

## 1. What exists today (evidence)

### 1.1 The files in scope

| Scope                   | Memory                                                                                              | Agent instruction files                                                                                                 | VCS                                          |
| ----------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Project (`sase`)        | `sase/memory/**` — 116 tracked files now; 162 distinct paths ever (legacy root `memory/` migrated) | Root `AGENTS.md` + 4 shims (`CLAUDE/GEMINI/QWEN/OPENCODE.md`); hand-written `tools/`, `src/sase/ace/`, `demos/tapes/` `AGENTS.md` + shims (20 files) | project git repo                             |
| Home                    | `~/sase/memory/` (source: `~/.local/share/chezmoi/home/sase/memory/`)                                | `~/AGENTS.md` + shims, rendered from chezmoi `*.md.tmpl` (per-host H1 switch)                                           | chezmoi git repo (125 memory commits)        |
| Other SASE projects     | their own `sase/memory/`                                                                            | their own `AGENTS.md` family                                                                                            | their repos                                  |

Key facts (from `src/sase/amd/constants.py`, `content_layout.py`, and
`init_memory_handler.py`):

- The provider shims are **byte-for-byte copies** of the directory's `AGENTS.md`
  (`PROVIDER_SHIM_FILES`). `cmp` confirms they are identical.
- `sase memory init` renders `AGENTS.md` from notes, templates, and config (e.g. the
  linked-repos list). It also regenerates `sase.md`, `README.md` (the directory map),
  `sase_artifacts.md`, `sase_beads.md`, `sase_sizes.md`, `task_types.md`, the
  `task_types` web strands, and web roster lines. Then it **commits and pushes**
  (`docs(memory): …`, or `chore: run sase init memory`).
- Home changes are committed in chezmoi as `chore: initialize sase memory`, then
  `chezmoi apply`.
- There is **no persistent memory index** today. Every command rescans the filesystem.
- `sase memory log` already exists and is the **read-audit** viewer (reads
  `~/.sase/projects/<project>/memory_reads.jsonl`). A new history command cannot be
  called `log`.
- Read events (`MemoryReadEvent`, schema v2) record path, byte count, agent, and reason,
  but **no content hash**. `agent_meta.json` records `vcs_ref` but **no launch commit
  SHA and no instruction-file hash**. So today we cannot say which version of a note or
  of `AGENTS.md` an agent actually saw.

### 1.2 Commit provenance is already rich (but not machine-parsed by git)

sase commits carry footers, for example:

```
SASE_BEAD=[sase-1bc.12][1]
SASE_TYPE=stitch
SASE_AGENT=[bbugyi200.athena.sase-1bc.12][2]
```

- Of 465 memory-touching commits, **185 carry `SASE_AGENT`** and **93 carry
  `SASE_BEAD`**. `SASE_TYPE` is `stitch` in 128 and `memory` in 40.
- The footers use `=`, not `:`, so `git log --format=%(trailers)` does **not** see them.
  sase-core already has `commit_footer.rs::parse_commit_footer`, which should be reused.
- This is the "who/why" layer that plain `git log -p` does not give you, and it is the
  biggest differentiator available.

### 1.3 History volume and signal-to-noise (measured)

Classification of every file-change in `git log --raw -M` over `sase/memory`, `memory`,
and `**/AGENTS.md`:

| Class                                                     | File-changes |
| --------------------------------------------------------- | -----------: |
| Authored edit (words changed)                             |          323 |
| Instruction-file change (`AGENTS.md`, root + subdirs)     |          304 |
| Generated note (`README.md`, `sase.md`, `task_types/*`…)  |          283 |
| Authored create                                           |          125 |
| Frontmatter-only                                          |           57 |
| Authored delete                                           |           20 |
| Pure move / rename (R100)                                 |           16 |
| Reflow / whitespace-only                                  |           13 |
| Binary asset                                              |            5 |

- **Top churners:** `README.md` 163 commits (generated), `glossary.md` 61 (mostly
  regenerated roster), `sase.md` 23 (generated).
- **Root `AGENTS.md` since memory existed (2026-04-12):** 207 versions.
  - 147 were driven by note edits.
  - 60 were not:
    - 18 renderer changes (`src/sase/amd`, `init_memory`)
    - 29 instruction-only regen commits
    - 12 other code changes
    - 1 config change
- **Four shims** multiply every `AGENTS.md` version by five in raw per-file history.
- **Commit subjects are an unreliable memory changelog.**
  - By conventional type, the 465 commits split into 185 `chore` (at least 43 of them
    boilerplate `chore: run sase init…`), 138 `feat`, 38 `fix`, 17
    `ref`/`refactor`, and 61 `docs`/`docs(memory)`.
  - When memory rides inside a feature commit, the subject describes the code. For
    example, `feat(goals): complete G1 acceptance…` added two decisions and a glossary
    strand and edited three more.
- **Cadence:** 10 → 37 → 67 → 52 → 27 → 58 → 108 → 76 commits/month (Feb→Sep). The
  corpus is real and growing.

### 1.4 Git performance (measured on this machine; git 2.43; 15,449 commits)

| Query                                                                               |                            Time |
| ----------------------------------------------------------------------------------- | ------------------------------: |
| `git log -- AGENTS.md` (full history)                                                |                          0.21 s |
| `git log --follow -- sase/memory/tui.md`                                             |                          0.33 s |
| `git log --follow` on a renamed note (bare clone with commit-graph + Bloom filters)  |                          0.89 s |
| **Whole-memory index pass**: `git log --raw -M --no-abbrev -- <memory pathspecs>`    |                     **0.29 s** |
| Single-file `git log` with commit-graph **changed-path Bloom filters**              | **0.03–0.04 s** (vs 0.18–0.30) |
| Whole-memory pass with Bloom filters (multi-pathspec; not accelerated on 2.43)       |                          0.21 s |
| `git cat-file --batch` for all 1,047 historical blobs (9.2 MB)                       |                          0.08 s |
| `git diff --word-diff` between two `AGENTS.md` versions                              |                          0.01 s |
| `git show <sha>:AGENTS.md`                                                           |                          0.006 s |

Takeaways:

- `--follow` is the slow path, and it only follows one file. Building lineage for **all**
  files from a single `--raw -M` pass is both faster and more correct.
- The workspace's commit-graph (`CDAT`, `GDA2`) has **no Bloom chunks** (`BIDX`/`BDAT`).
  Writing them is a cheap optional accelerator for per-file queries. Git reads
  commit-graphs from alternates, so writing them in the primary checkout helps every
  workspace.
- A full scan is O(total repo commits). At about 2k commits/month it will pass ~1 s
  within a year or two. An incremental index (`<indexed_tip>..<tip>`) makes steady-state
  cost O(new commits), which is effectively free.

### 1.5 The pager and Memory panel today

- **Pager** (`src/sase/pager/`): a Textual `PagerScreen` built from mixins (Body, Action,
  Trail, Chrome, Search, Goto, Syntax), hosting a `PagerDocument` of `PagerSection`s. It
  has:
  - A sticky subject line and a 1–2 row trail band (browser-style back/forward,
    `backspace`/`ctrl+o` and `tab`/`ctrl+i`).
  - Prefix-free jump labels, and syntax roles that include `DIFF_ADDED`,
    `DIFF_DELETED`, and `DIFF_HUNK`.
  - A footer legend that lists only verbs that currently do something.
  - `refresh_document_fn` for live sources.
- **Memory and instruction files get no special treatment** in the pager. There is no
  structured diff model and no split view. The commit viewer (`CommitViewModal`) is a
  separate modal.
- **Free pager keys:** all punctuation (`( ) [ ] { } = @ , . < > - + …`). Letters are
  jump-label characters; `PAGER_RESERVED_JUMP_COMMAND_KEYS = "qjkgGyErnN"`, and each new
  letter binding must be added there.
- **Precedent:** ACE already uses `(`/`)` for `files_prev_version`/`files_next_version`
  on the Artifacts Files tab (a `LogicalFile` with `versions`).
- **Memory panel** (`ace/tui/modals/memory_pane*.py`): a catalog list, a card
  (type/parent/children/source), and its own relation trail, with no history. `H`, `(`
  and `)` are unbound there.

Current look, for grounding the mockups below:

- the pager (`tests/pager/visual/snapshots/png/syntax_markdown_dark_120x40.png`,
  `three_section_mid_rule_120x40.png`)
- the Memory panel (`tests/ace/tui/visual/snapshots/png/memory_panel_populated_dark_120x40.png`)
- the commit modal (`commit_view_modal_120x40.png`).

---

## 2. Critique — is this a good idea?

**Yes. Memory is the policy layer that steers every agent, and its changes are
high-leverage and currently close to invisible.** A one-word change to `gotchas.md` or
a note promoted from `reference` to `core` changes the behaviour of every later agent
turn. Today, answering "when did this rule appear, who added it, and why?" takes
`git log -p --follow` plus reading commit subjects that mostly describe unrelated code.
Answering "what did the agent that misbehaved yesterday actually see?" is impossible.

The request needs sharpening in several places:

1. **"Track all changes" is already true. The missing thing is navigation and
   meaning.** git already tracks everything, and the user's instinct to reuse it is
   right. But "an index to navigate quickly" undersells the job. Speed is fine today
   (§1.4). What is missing is a model that knows:
   - that `CLAUDE.md` is `AGENTS.md`;
   - that `lint_and_test.md` used to be `build_and_run.md`;
   - that this `README.md` bump was regenerated by that strand add;
   - that this commit only rewrapped a paragraph.

   The index should exist to hold **lineage and classification**, not to make git
   faster.

2. **Treat agent instruction files as derived views, not peers of notes.** Root
   `AGENTS.md` is a rendering of notes, templates, and config. Its history answers "what
   did agents see?". Note history answers "what did people and agents author?". The UI
   should connect the two: an `AGENTS.md` version should explain itself ("rendered from
   edits to `gotchas.md`, `dispatch.md`" or "renderer change in `src/sase/amd`").
   Tracking the four shims as separate files is pure noise; alias them.

3. **The pager should be the viewer, not the only interface.** The pager is the right
   place to read one document through time: it already has the reading ergonomics
   (search, labels, syntax, trail). It is the wrong place to discover what changed
   across memory this week. You need a **cross-file feed** as a front door, and the
   **Memory panel** should open into history. Both of those can themselves be pager
   documents, so the pager stays the single rendering surface.

4. **Line diffs are the wrong primitive for wrapped Markdown prose.** See the
   `shells → processes` example. Without a paragraph-aware word diff, history browsing
   will feel noisy and untrustworthy.

5. **Commit subjects are not a usable changelog for memory.**
   - About 42% of memory-touching commits are `feat`/`fix`/`refactor` commits whose
     subject describes code.
   - Dozens more are `chore: run sase init…` boilerplate.
   - Home memory is 70% `chore: initialize sase memory` (88/125).
   The UI should summarize each version **from its diff**:
   - which section changed (`§ Default Keymap Config`)
   - how many words changed (`+31w −4w`)
   - frontmatter semantics (`⇧ promoted to core`)

   The commit subject becomes secondary context.

6. **Uncommitted and unlanded states are part of the history.** Memory edits sit in a
   workspace (or the Memory panel) before `sase memory init` commits them. Master also
   moves ahead of a workspace's HEAD. A timeline that only shows committed history on
   HEAD will lie by omission. It needs a working-copy pseudo-version and an "N newer on
   master" indicator.

7. **The most valuable question is not in the request: "what did agent X see?"** This
   is the debugging use case for memory history. It needs two small additions that cost
   bytes, not effort:
   - a content hash (git blob OID) on each `memory_reads.jsonl` event;
   - the instruction-file blob OID and workspace HEAD recorded in `agent_meta.json` at
     launch.

   Without them, "as seen by agent X" can only be approximated from timestamps.

8. **Guard against over-building.** The `corpus-before-mechanism` decision warns
   against memory machinery that runs ahead of a corpus. This proposal passes that test,
   because the corpus exists (465 commits, 162 paths, plus 125 home commits) and so does
   the pain (the noise ratios above). The test still constrains the design:
   - no LLM-generated change summaries
   - no semantic search over history
   - no separate snapshot store
   - no new TUI tab

   The index should stay a derived, disposable cache. SQLite or other heavier storage
   waits until measured scale demands it.

9. **Restore/revert is tempting but dangerous in v1.** Restoring a generated file makes
   no sense (you restore its sources). Restoring a note must go through the
   digest-guarded `memory/mutation.py` path plus publish, and host-owned completion rules
   apply to agents. Ship read-only history first; add "restore this version" (Memory
   panel / TUI only) later.

10. **Generalize the pager mechanism, specialize the semantics.** A time axis on a
    pager section is equally useful for plans, skill sources, xprompts, and research
    docs. Build the lens against a `SectionHistoryProvider` interface. Enable the
    memory provider (index, classification, provenance, feed) first; a plain
    git-file provider is a cheap follow-on. That avoids a memory-only special case
    inside the pager core.

**Would I take a different approach?** Mostly the same direction, with the adjustments
above. The one substantive change is ordering: first ship the index and **history
documents** rendered with today's multi-section pager (§8, Phase 1). This gets most of
the value in a small change and checks that people use it. Only then build the
interactive time-travel lens that changes pager keymaps and chrome.

---

## 3. Requirement adjustments (explicitly called out)

| #   | Original                                                   | Adjusted                                                                                                                                                                                              | Why                                                                                                         |
| --- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| A1  | Track **all** agent instruction file changes               | Track one **instruction subject per directory** (`AGENTS.md`); provider shims are aliases shown only when they diverge (a drift bug)                                                                   | Shims are byte-identical copies; tracking them multiplies noise ×5                                          |
| A2  | Track all memory file changes                              | Track SASE memory in the owning repo **and home memory in the chezmoi repo**; exclude provider-native memories (e.g. Claude Code auto-memory dirs), which are not SASE memory and are not in git     | "All memory" silently spans two repos; provider-native memory needs a different capture mechanism entirely |
| A3  | Version = committed change                                  | Timeline = committed versions on HEAD **+ unlanded commits + working copy**, with an "N newer on canonical branch" indicator                                                                            | Edits sit uncommitted before `sase memory init`; workspaces lag master                                      |
| A4  | (implicit) show commit messages                              | Show **diff-derived summaries** (section path, ±words, frontmatter semantics) and **provenance** (agent, bead, commit) from `SASE_*` footers                                                         | ~42% of memory-touching commits are feat/fix/refactor subjects about code; home subjects are 70% boilerplate |
| A5  | (implicit) all versions equal                                | **Classify** versions (authored / created / deleted / moved / reflow-only / frontmatter-only / regenerated / renderer-driven) and hide no-word-change versions by default                            | Noise ratios in §1.3                                                                                        |
| A6  | (not requested)                                              | **"As seen by agent"**: add blob OIDs to memory read events and instruction snapshot to agent launch metadata                                                                                        | The highest-value debugging question is unanswerable today                                                  |
| A7  | (not requested)                                              | **Deleted notes stay browsable** (tombstone band, last content)                                                                                                                                      | 21 deletions; 162 historical paths vs 116 today; deleted rules are often what you're investigating         |
| A8  | Pager as **main** interface                                  | Pager as the **single rendering surface**; front doors are a **Memory Changes feed**, `sase memory history`, and the Memory panel (`H`)                                                              | Per-file reading vs. cross-file discovery are different jobs                                                |
| A9  | "Memory history"                                             | Name it `history` (`sase memory history`); `log` is taken by read-audit                                                                                                                             | Avoid a collision with `sase memory log`                                                                    |
| A10 | Memory-specific pager support                                | Generic pager **time axis** with a pluggable history provider; memory gets the semantic provider first                                                                                              | Same UX will be wanted for plans/skills/xprompts; keeps pager core clean                                    |
| A11 | (implicit) restore old versions                              | **Read-only in v1**; restore later via the Memory panel's guarded mutation + publish path, disabled for generated files                                                                              | Safety; host-owned completion; generated files have no meaningful restore                                   |

---

## 4. The model: subjects, versions, changesets

**Subject.** One logical, trackable document with a stable identity across renames:

- `note:<scope>/<name>` — a flat note, e.g. `note:project/gotchas`
- `web:<scope>/<web>` — a web descriptor
- `strand:<scope>/<web>/<slug>` — a web strand, identified by filename slug; `keyword:`
  changes are content changes
- `instructions:<repo>/<dir>` — `AGENTS.md` with its shim aliases
- `asset:` (binary, listed only)

Subjects carry `generated: bool`, which is derived from the same source of truth that
refuses direct edits (`generated_memory_note_relative_paths` in `init_memory`). The
classifier must not keep its own hard-coded list.

**Version.** A point where a subject's bytes changed. Fields:

| Field                       | Contents                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `subject`, `ordinal`        | Stable 1-based ordinal over *all* versions (never renumbered by filters)                    |
| `commit`, `parents`         | Commit time (landing time, **committer** date; the log is not author-date monotonic)        |
| `path`                      | Path at that commit (lineage through renames)                                               |
| `blob_oid`, `prev_blob_oid` | The only content handle (content always from git)                                           |
| `change`                    | `created`, `edited`, `moved`, `deleted`                                                     |
| `class`                     | See taxonomy below                                                                          |
| `summary`                   | Heading paths touched, `+words/−words`, frontmatter deltas (`type: reference → core`, `description` changed, …) |
| `provenance`                | `SASE_AGENT`, `SASE_BEAD`, `SASE_TYPE`, commit subject, author                              |
| `cause`                     | Instruction subjects only: `notes[] \| renderer \| config \| regen-only \| other`, from co-changed paths in the same commit |

**Pseudo-versions:** `working` (dirty file differs from the HEAD blob), `unlanded`
(commits on HEAD that are not on the canonical branch), and `upstream` (the canonical
branch is ahead; shown as a count, opt-in to load).

**Changeset.** One commit's versions across subjects. This is the unit of the feed.
Generated consequences (`README.md`, roster lines, `AGENTS.md`) fold under their
authored causes.

**Classification taxonomy and glyphs** (one visual vocabulary everywhere):

| Glyph | Class                     | Default visibility (per-file timeline)                  |
| ----- | ------------------------- | ------------------------------------------------------- |
| `✚`   | created                   | shown                                                   |
| `◆`   | authored edit             | shown                                                   |
| `⇧/⇩` | promoted / demoted (type) | shown, highlighted — changes what every agent loads     |
| `▣`   | frontmatter-only          | shown (dim)                                             |
| `⟳`   | regenerated               | shown for generated subjects; folded in the feed        |
| `⚙`   | renderer-driven           | instruction subjects: shown with the cause              |
| `≈`   | reflow / whitespace-only  | hidden (dim dot in the strip)                           |
| `↦`   | pure move / rename        | hidden (dim dot; the path change is shown in the band)  |
| `✖`   | deleted                   | shown (tombstone)                                       |
| `◌`   | working copy              | shown when dirty                                        |
| `◇`   | unlanded                  | shown                                                   |

---

## 5. The index

### 5.1 Do we need one?

Yes, but not for the reason the request assumes:

- **Git is fast enough for content.** Content always comes from git by blob OID.
- **The index exists for lineage, classification, provenance, and summaries.** These
  need every file in each commit (co-change analysis), both blobs of each change, and
  footer parsing. Recomputing them on every pager keypress would be wasteful and would
  scale with total repo history.
- **It is a pure function** of `(repo, tip, pathspec set, classifier version)`, so it
  can never be "wrong". At worst it is stale, and staleness is detected by key mismatch.

### 5.2 Build and update

```
build(repo, tip):
  raw  = git log --raw -z -M --no-abbrev --topo-order
             --format=<sha, parents, committer time, author, subject, body>
             <tip> -- sase/memory memory ':(glob)**/AGENTS.md' [shims only for drift check]
  idx  = core.memory_history_fold(raw)                 # lineage, footers, cause
  idx += core.memory_history_classify(idx, blobs(cat-file --batch))  # words, frontmatter, headings

update(cache, tip):
  if cache.key != (repo_id, pathspec_hash, classifier_v): rebuild
  elif cache.tip == tip: done
  elif is_ancestor(cache.tip, tip): fold(git log --raw … cache.tip..tip) onto cache
  else: rebuild                                         # rewrite / force-push / branch switch
```

- **Lineage** comes from the one-pass `-M` rename pairs, not from `--follow`. A rename
  from legacy `memory/` to `sase/memory/` is handled because both sides are in the
  pathspec.
- **Home** runs the same algorithm over the chezmoi repo with pathspecs
  `home/sase/memory`, `home/memory`, and `home/*.md.tmpl`. The existing
  `chezmoi_source_path` maps target paths to source paths.
- **Storage:** one JSON file per repo under
  `~/.sase/cache/memory_history/<repo-key>.json`, holding
  `{schema, classifier_version, pathspec_hash, tip, subjects[], versions[]}`.
  - About 1.1k versions × ~250 B ≈ 300 KB, which loads in a few ms. Writes are atomic
    (tmp + rename) under a file lock.
  - SQLite (as used for `agent_artifact_index.sqlite`) is **not** justified yet. Reopen
    that when versions exceed roughly 50k, or when cross-repo queries ("all changes by
    agent X across projects") become a real need.
- **Optional accelerator:** `git commit-graph write --reachable --changed-paths` in the
  primary checkout, run by `git maintenance` or sase workspace upkeep. It cut
  single-file `git log` from ~200 ms to ~30 ms. It is not required for correctness, and
  sase should never write it into a repo it doesn't own without opt-in.

### 5.3 Content, diffs, and summaries

- **Blobs:** read via a long-lived `git cat-file --batch` process per repo per session,
  with an LRU of decoded blobs. Prefetch the ±2 neighbours of the current version off
  the UI thread.
- **Working copy:** read the file, compute its blob OID (`git hash-object`-equivalent),
  and compare it to HEAD's blob. Show the ◌ pseudo-version only when they differ.
- **Diffs:** compute in-process in Rust with the `similar` crate. Use line ops for
  anchoring and gutter marks, and inline word ops, tokenized over the paragraph, for
  prose rendering. Parsing `git diff --word-diff=porcelain` also works, but in-process
  diffs give the line map needed for scroll anchoring and avoid a spawn per step.
- **Section attribution:** map each hunk to its Markdown heading path, e.g.
  `§ Commit First, Then Deploy`, `§ Rules › 3`.
- **Frontmatter semantic diff:** YAML-aware, surfacing `type`, `parent`, `description`,
  `web`, and `roster` changes as words ("promoted to core", "re-parented under
  `tui.md`").

### 5.4 Rust / Python split (per `rust_core_backend_boundary` and `rust-core-required`)

Anything that another frontend would need to match lives in **sase-core**, in a new
`memory_history` module with a wire contract and PyO3 bindings:

- parsing raw log output (extend the `git_query` parsers pattern)
- footer parsing (reuse `commit_footer.rs`)
- lineage folding and incremental merge
- classification and cause attribution
- word/line diff ops
- section and frontmatter summaries

Everything else stays in **Python**:

- IO: git subprocesses with timeouts via the existing non-interactive subprocess
  helpers, cache files, locks;
- the CLI;
- pager and Memory-panel presentation.

This matches the `git_query` precedent: Python runs git, Rust parses. It keeps the
core pure and fixture-testable. Bump `sase-core-revision.txt` as usual.

### 5.5 Reliability: failure modes

| Situation                                        | Behaviour                                                                                                         |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| No git / not a repo / non-git VCS provider       | Live view works; the history band shows `history unavailable (no git)`; the `( )` verbs are absent from the footer |
| Shallow clone                                    | Index up to the boundary; the oldest version shows `history truncated (shallow)`                                  |
| History rewritten (tip not a descendant)         | Full rebuild (~0.3 s), off-thread                                                                                 |
| Chezmoi disabled or missing                      | Home subjects show live content only                                                                              |
| Index cache corrupt or schema mismatch           | Discard and rebuild; never surface as an error                                                                    |
| Binary asset or huge file                        | Listed with size/OID; no diff; open via the existing binary card                                                  |
| Shim diverges from `AGENTS.md`                   | Shown as a `⚠ shim drift` badge (a real bug worth surfacing)                                                      |
| Concurrent writers (two workspaces)              | Lock plus atomic replace; readers never block                                                                     |

**Invariants to test:**

- For every indexed version, `blob_oid == git rev-parse <commit>:<path>`.
- Incremental update produces exactly the same index as a full rebuild.
- Lineage matches `git log --follow` on a corpus of renamed notes.

### 5.6 Performance budgets

- **Opening a live document:** unchanged. History loads after first paint (the band
  shows `indexing…`), following the pager's existing after-paint syntax pattern and
  `tui_perf` rule 2 (`spawn_pump_free_task`, no slow awaits on the pump).
- **Warm version step (`(`/`)`):** ≤ 30 ms to repaint from prefetched blob and diff,
  with a generation counter that discards stale work, as the syntax layer already does.
- **Cold index:** ≤ 0.35 s today, off-thread. **Incremental:** ≤ 20 ms.

---

## 6. UX design

### 6.1 Principles

1. **Time is just another axis of a document.** There is no mode to enter and no
   separate app. If a pager section has history, the time verbs appear in the footer;
   if it doesn't, they don't. This matches the existing availability-driven footer.
2. **You always know when you are in the past.** The historical view gets a distinct
   "sepia/amber" accent, a time band, and a subject chip. Live ("now") uses the normal
   accent. Nobody should edit a rule believing an old version is current.
3. **Keep your place.** Stepping versions keeps the scroll anchored on the same
   paragraph, mapped through the line diff, so you watch one passage evolve.
4. **Small motions don't pollute the trail. Jumps do.** This is vim's jumplist rule.
   `(`/`)` steps don't push trail entries (otherwise `backspace` would walk back through
   30 versions). Jumps via `@`, the feed, or links do. Every trail entry records its
   version pin, so back/forward restores the exact time you were at.
5. **Time-coherent links.** Following a `[[link]]` from a historical version opens the
   target **as of the same commit**, and the band says so. You can browse the memory
   graph as it was on a given day. `}` returns to now.
6. **Meaning over mechanics.** Show "§ Default Keymap Config · +31w −4w · promoted to
   core · by athena.sase-1bc.12 (sase-1bc.12)", not `M sase/memory/gotchas.md`.

### 6.2 Keys — the bracket family

| Key         | Verb                                                                                                  | Mnemonic               |
| ----------- | ----------------------------------------------------------------------------------------------------- | ---------------------- |
| `(` / `)`   | older / newer version (skips hidden `≈`/`↦` versions; pressing `)` at the newest returns to now)      | parens = versions      |
| `[` / `]`   | previous / next change in this view (hunk jump; works in both lenses)                                 | square = changes       |
| `{` / `}`   | first version / **now**                                                                               | braces = the extremes  |
| `=`         | toggle lens: **read** (clean snapshot + change gutter) ⇄ **diff** (inline prose diff)                 | "compare"              |
| `@`         | timeline picker (filterable list of all versions; `a` toggles hidden versions)                        | "at …"                 |
| existing    | `backspace`/`tab` trail, `/` search, labels, `y` copy, `E` edit (**always edits now**, footer says so) |                        |

- All of these are free punctuation in the pager, so there is no new jump-label
  reservation.
- `(`/`)` matches the Artifacts Files tab's `files_prev_version`/`files_next_version`,
  so version stepping means the same thing across ACE.
- Add a `pager:` keymap section to `default_config.yml` for these. The pager currently
  hard-codes `BINDINGS`; this feature is a good moment to make them configurable, per
  the gotchas note.

### 6.3 Chrome: the time band (read lens, viewing a past version)

The band reuses the trail band's 2-row / 1-row degradation. Mockups are illustrative,
at 100 columns:

```
 ▤ gotchas.md  ⟲ v7/9 · 3 days ago                                      34% · ⌘ 2.1Kc · md
 PAST  ◆ edited  § Default Keymap Config  +31w −4w      athena.sase-1bc.12 · sase-1bc.12 · 19abe26
 ▁▁▃▁▂▁▁▇▁▁▂▅▁▁▁▂▁▃▁▁▁▁▂▁▆▂▁▁▃▁▂▁▁▅▁▁▁▂▁▃▁▁▁▂▁▁▆▁▁▁▂▁▁▇▁▁▂▁▁▃▁▁▂▁▁▁▁▅▁▁▂▁▁▁▁▃▁ ▲─────────── now ◌
 ───────────────────────────────────────────────────────────────────────────────────────────────
   1│ ---
   2│ type: core
   3│ parent: AGENTS.md
   4│ ---
   5│
   6│ **Default Keymap Config**
   7▌ When changing keymaps, leader mode keys, or any configuration values, don't forget to
   8▌ update the keymap configuration in the `src/sase/default_config.yml` file if necessary.
    ╴                                                                      (2 lines removed here)
 ───────────────────────────────────────────────────────────────────────────────────────────────
 ( ) version · [ ] change · { } first/now · = diff · @ timeline · ? keys · q close
```

- **Subject chip** `⟲ v7/9 · 3 days ago`, in amber when in the past. When live it reads
  `⟲ 9 versions · changed 3d ago`, or `◌ uncommitted` when the working copy is dirty.
- **Row 1 of the band:** class glyph, section path, word delta, and provenance. The
  agent, bead, and commit are **jump-label targets**, reusing the existing label
  machinery, and open the agent chat, bead doc, or commit card.
- **Row 2 of the band:** a **change-volume sparkline** over the subject's whole
  timeline.
  - Each cell is one version, or a time bucket when the timeline is wider than the
    screen. Bar height is words changed.
  - The cursor `▲` sits under the current version; hidden versions render as dim `·`.
  - Trailing markers: `now`, `◌` for a dirty working copy, and `⇡3` for "3 newer on
    master".
  - The sparkline shows at a glance whether a note is stable or churning, and where the
    big rewrites were.
- **Gutter:** green `▌` marks lines added in this version, amber `▌` lines modified, and
  a red `╴` tick between lines where text was removed. `[`/`]` walks these marks.
- **Tombstone** (for a deleted subject):
  `✖ deleted 2026-07-13 by athena.xyz · last content shown` on a muted red rule.

### 6.4 The diff lens (`=`): prose word diff

```
 ▤ lint_and_test.md  ⟲ v18/18 · diff vs v17                                     61% · md
 DIFF v17→v18  ◆ edited  § PNG Snapshot Tests  +1w −1w              apollo.… · 63d2bdc
 ───────────────────────────────────────────────────────────────────────────────────────
     ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  121 unchanged lines  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  (label: expand)
 125│ Local `just check-full` runs the update form after the other exhaustive gates and can
 126▌ modify goldens. SASE agent ̶s̶h̶e̶l̶l̶s̶ processes export `CI=true`; that flag alone does not
    │ block the update. Detached `sase monitor` commands drop `SASE_AGENT*` identity but set
     ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  38 unchanged lines  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
```

- **Styling:** deleted words are struck through in dim red; inserted words are green
  with a subtle background tint. Colours come from the syntax theme's WCAG-checked
  palette (`syntax_theme.py`), in both light and dark.
- **Reflow is invisible.** The `shells → processes` change is one word, not two
  rewrapped lines. Paragraphs are re-flowed to the pager width in this lens, which is
  safe because the diff is word-level.
- **Unchanged runs fold** into `┄ N unchanged lines ┄` rows. Each fold is a
  **jump-label target** that expands in place, so no new key is needed.
- **Frontmatter changes** render as a small semantic block above the body:
  `type  reference → core  ⇧ now always loaded by every agent`.
- **Why not side-by-side?** Notes wrap at 88 columns. Two panes plus gutters need about
  190 columns, and at the pager's typical 100–120 columns both sides would re-wrap into
  mush. Inline word diff is strictly better here. Side-by-side can be a later wide-screen
  option.

### 6.5 Timeline picker (`@`)

```
╭─ gotchas.md · 9 versions (2 hidden) ─────────────────────────── filter ▏ ─╮
│ now  ◌  working copy        uncommitted                  +2w               │
│ v9   ◆  Sep 27 14:08   3d   § Default Keymap Config      +31w −4w  athena… │
│ v8   ⇧  Sep 20 09:12  10d   promoted reference → core               apollo… │
│ v7   ◆  Sep 02 16:40   4w   § Default Keymap Config      +6w −6w   athena… │
│ v5   ✚  Jul 19 11:03   2mo  created                      412w      apollo… │
│ ·· 2 hidden (reflow, move) · a show                                        │
│ ⏎ open · = open as diff · a all · esc close                                │
╰────────────────────────────────────────────────────────────────────────────╯
```

It is a filterable list: typing filters by section, agent, bead, or word, and jumping
from it pushes a trail entry.

### 6.6 The Memory Changes feed (`sase memory history`, no selector)

This is the cross-file front door. It is a normal pager document, so search, labels,
the trail, and `ctrl+n`/`ctrl+p` between day sections all work unchanged.

```
 ▤ Memory changes · sase + home · last 14 days                     23 changesets · 5 hidden
 ━━ Mon Sep 28 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  18:29  feat(agents-tabs): unflag agent tabs…            athena.sase-1bc.12 · sase-1bc.12
         ✚ glossary:agent-tab        new term · 96w
         ✚ glossary:machine-tab      new term · 71w
         ◆ glossary:node-panel       +12w −9w
           ⟳ glossary roster, README.md (regenerated)
  11:03  feat(goals): complete G1 acceptance…                     athena.sase-1bu.7 · sase-1bu.7
         ✚ decisions:goal-ledger     new decision · 180w
         ✚ decisions:goals-host-binds new decision · 150w
         ✚ glossary:goal             new term · 88w
         ◆ glossary:artifact          +20w −3w   ◆ glossary:artifact-reference +6w
           ⟳ AGENTS.md §3.1 Decisions (+2 entries), README.md, glossary roster
 ━━ Sun Sep 27 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  14:19  feat(tabs): inherit agent tab across launches…  athena.sase-1bc.5 · sase-1bc.5
         ◆ dispatch.md               § Remote dispatch  +44w −10w
  ⋯ 5 regenerated-only changesets hidden (e.g. "chore: run sase init memory") · label to show
```

- Every subject row is a label target and opens `subject@version` in the **diff lens**.
- `⟳` lines show the generated consequences folded under their cause.
- Home changesets interleave, tagged `⌂`.

### 6.7 Instruction files (`AGENTS.md`) specifics

- **Band cause line:**
  - `⟳ rendered from 2 note edits: gotchas.md · dispatch.md`, where the note names are
    label targets that open each note at the same commit in the diff lens;
  - or `⚙ renderer change · src/sase/amd/_template.py`;
  - or `⚙ config change · sase/sase.yml (repos)`.
- **Opening `CLAUDE.md` opens the `AGENTS.md` subject.** The subject chip reads
  `CLAUDE.md ≡ AGENTS.md`.
- **The diff lens shines here.** Seeing §2 gain one reference entry, or a core section
  appear, is exactly "what changed in what every agent loads".
- **Later: a source map.** Each rendered core section in `AGENTS.md` becomes a label
  back to its source note at the same commit. This needs the renderer to emit section
  provenance.

### 6.8 Entry points

1. **CLI.** `sase memory history [SELECTOR ...]` uses the same selector grammar as
   `read`/`show` (`gotchas.md`, `glossary`, `glossary:stitch`), plus instruction paths
   (`AGENTS.md`, `tools/AGENTS.md`). On a TTY it opens the pager; otherwise it prints.
   Options follow `cli_rules`: sorted, each with a short alias.
   - `-a/--all` — include hidden versions
   - `-A/--at REV` — open at a version: `v7`, `~2`, a SHA, or a date
   - `-d/--diff` — open in the diff lens
   - `-D/--deleted` — list deleted subjects
   - `-j/--json` — machine output, useful for agents investigating "why is this rule
     here?"
   - `-l/--list` — print instead of paging
   - `-s/--since DATE`
   - `-S/--scope project|home|all`
2. **Memory panel.**
   - `H` opens the selected note's history in the pager.
   - The card's meta block gains `History   14 versions · changed 3d ago by
     athena.sase-1bc.12`.
   - Update `default_config.yml` `ace.keymaps.memory` with `history: "H"`.
3. **Pager anywhere.** Any section that resolves to a memory or instruction file gets
   the time axis automatically, including via ACE `v` view files, bead/plan links, and
   `sase pager sase/memory/tui.md`.
4. **Later: version refs.** `path@rev` in the pager resolver (`sase pager AGENTS.md@v205`),
   and possibly a `memory:` artifact-ref kind so versions can be linked from beads, plans,
   and chats. The ref grammar would live in Rust, like other artifact refs.

### 6.9 "As seen by agent" (Phase 4)

- Add `blob_oid` (and `head` when the file is clean) to `MemoryReadEvent`. This means a
  schema bump to v3.
- Add `instruction_snapshot: {path: blob_oid}` plus `workspace_head` to agent launch
  metadata.
- From the Agents tab metadata pager (`V`), a "Memory as seen" link opens `AGENTS.md` at
  the exact version the agent launched with. The band then says:
  `as seen by athena.sase-1bc.12 · 2 versions behind now`.
- `sase memory log` (read audit) rows become links to the exact version read.

### 6.10 Visual language checklist ("beautiful")

- **One glyph vocabulary** (§4) across the CLI, feed, band, picker, and Memory panel.
- **Past uses an amber accent; now uses the section accent.** Use the WCAG-checked
  palette derivation in both themes.
- **Relative time** with an absolute tooltip-row (`3 days ago · Sep 27 14:08`) and a
  configured timezone.
- **Width-adaptive chrome:**
  - the sparkline buckets by time when there are more versions than cells;
  - band row 1 drops, in order: commit sha → bead → section path;
  - at 12 rows or fewer the band collapses to one row, as the trail band already does.
- **Visual goldens** at 60×30 and 120×40, light and dark, for:
  - read lens (past)
  - diff lens
  - picker
  - feed
  - tombstone
  - `AGENTS.md` cause band
  - working-copy state

---

## 7. Alternatives considered

| Alternative                                                             | Verdict                                                                                                                                         |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Raw git on demand, no index** (`git log -p --follow` into the pager)  | Good enough as a spike. It lacks lineage across all files, classification, cause, and feed folding, and `--follow` takes ~0.9 s on renamed notes. |
| **Derived index over git** (recommended)                                | Content stays in git; the index is disposable and rebuilt in ~0.3 s; incremental in ms; semantic layer in Rust.                                   |
| **Separate snapshot store** (capture on every write, like artifact captures) | Duplicates git, misses edits made outside sase, drifts. Reject. Working-copy pseudo-versions cover the uncommitted gap.                        |
| **Dedicated memory repo or orphan branch**                              | Breaks the co-location of memory changes with the code commits that motivated them (and loses provenance). Reject.                             |
| **SQLite index now**                                                    | Premature at ~1k versions. Reopen at ~50k versions or with cross-project queries.                                                              |
| **New ACE "Memory History" tab**                                        | Another surface to maintain. The pager is the reading surface; the Memory panel and feed are the front doors. Reject for now.                  |
| **External tools** (`tig`, `lazygit`, `delta`, `git log -p \| less`)    | No prose diff tuned to 88-column Markdown, no sase provenance links, no classification, no time-coherent links. Useful as a power-user escape hatch only. |
| **Side-by-side diff**                                                   | Needs about 190 columns for wrapped prose. Inline word diff is better at 100–120 columns. Maybe later as a wide-screen option.                 |
| **LLM-written change summaries**                                        | Cost, nondeterminism, `corpus-before-mechanism`. Deterministic section, word, and frontmatter summaries cover it.                               |
| **Line blame**                                                          | Worth having later as an **age lens** (gutter tinted by line age, with the version number). Useful for spotting stale rules; not v1.           |

---

## 8. Recommended solution and phased plan

**Summary:** keep git as the store. Add a Rust-core **`memory_history`** index for
lineage, classification, cause, provenance, word diffs, and section/frontmatter
summaries. Expose it as `sase memory history`. Render everything through the pager:
first as history **documents**, then as a generic interactive **time axis** with the
bracket-family keys, time band, sparkline, prose diff lens, scroll anchoring, and
time-coherent links. Add front doors in the feed and Memory panel. Finish with
"as seen by agent" pinning.

### Phase 1 — Index + history documents (no pager core changes)

- **sase-core `memory_history`:**
  - raw-log parser
  - lineage fold with incremental merge
  - footer provenance (reuse `commit_footer.rs`)
  - classifier (taxonomy §4)
  - section and frontmatter summaries
  - word diff ops via `similar`
  - wire types and PyO3 binding
  - fixture corpus built from real sase history, including:
    - the `build_and_run → lint_and_test` rename (R063)
    - the legacy `memory/` → `sase/memory/` migration
    - the reflow-only `shells → processes` commit
    - `type` promotions
    - deletions
- **Python adapter:**
  - git IO and blob batching
  - the cache file (`~/.sase/cache/memory_history/`)
  - working-copy and unlanded pseudo-versions
  - chezmoi scope
- **`sase memory history`** with `-l`/`-j` output and pager output built from
  **existing** multi-section documents:
  - section 1 is a timeline table whose rows are label targets;
  - each later section is one version's word diff, rendered with the existing `DIFF_*`
    syntax roles;
  - `ctrl+n`/`ctrl+p` already steps between versions.
- **Feed document** (no selector) with changeset folding.
- **Acceptance:**
  - index invariants (§5.5);
  - cold ≤ 0.35 s, incremental ≤ 20 ms;
  - `sase memory history AGENTS.md` shows causes;
  - `sase memory history CLAUDE.md` resolves to the `AGENTS.md` subject.

### Phase 2 — The pager time axis

- `SectionHistoryProvider` interface. `PagerSection.history` is optional.
- `PagerHistoryMixin` on `PagerScreen`:
  - `(` `)` `[` `]` `{` `}` `=` `@`
  - version-pinned trail entries
  - scroll anchoring through the line map
  - neighbour prefetch
  - generation-guarded, pump-free workers
- Time band, subject chip, sparkline, change gutter, tombstones, and the amber past
  accent.
- Pager keymap section in `default_config.yml`, with a help sheet (`?`) update.
- **Beta flag:** gate the lens behind `sase flag new memory_history_lens` **only if** a
  landed phase would otherwise expose a partial lens (per `sase_flags`). The epic
  removes the flag before it lands.

### Phase 3 — Diff lens, picker, front doors

- Inline prose diff lens with label-expandable folds and a frontmatter semantic block.
- `@` timeline picker.
- Time-coherent link following: the pager resolver takes an optional `as_of` commit.
- Memory panel `H` and the card History line, plus the `default_config.yml` keymap
  entry.
- Instruction cause band with note labels.
- Visual goldens for all states (§6.10).

### Phase 4 — Provenance pinning and extras

- `MemoryReadEvent` v3 with `blob_oid`.
- Agent launch `instruction_snapshot`.
- "Memory as seen" from the Agents tab.
- Read-audit rows link to versions.
- `path@rev` refs and possibly a `memory:` ref kind.
- Age lens.
- Restore-this-version in the Memory panel (guarded mutation + publish; disabled for
  generated subjects).
- `AGENTS.md` source map.
- A plain git-file history provider for non-memory files (plans, skills, xprompts).

### What I would explicitly not build

- A separate snapshot store.
- A new TUI tab.
- SQLite before measured need.
- LLM summaries.
- Side-by-side diff at default widths.
- Restore in v1.
- History for provider-native (non-SASE) memories.

---

## 9. Risks and open questions

1. **Canonical ref choice.** Should the default timeline be the workspace HEAD or the
   primary checkout's canonical branch? I recommend HEAD plus unlanded commits plus the
   working copy, with a `⇡N newer on master` marker and `-A/--at` to go there. This
   needs a decision on how to find the canonical ref cheaply in workspaces that share
   objects through alternates.
2. **Classifier drift.** "Generated" must come from `init_memory`'s own list, and the
   classifier version is part of the cache key. A renderer change that adds generated
   outputs must bump it. Add a test pinning the two lists together.
3. **Chezmoi templates.** Home `AGENTS.md` history is template source (`.md.tmpl` with
   host conditionals), not rendered output. Showing rendered per-host output would mean
   running `chezmoi execute-template` per version. I'd defer that and show source with a
   `template` chip.
4. **Bloom filter maintenance.** Git 2.43 did not accelerate the multi-pathspec pass. If
   per-file queries become hot, decide whether sase should own
   `git commit-graph write --changed-paths` in the primary checkout (and on which
   cadence), or leave it to `git maintenance`.
5. **Key collisions in ACE hosts.** The pager runs as a modal inside ACE, where
   `(`/`)`, `[`/`]`, and `{`/`}` mean other things on the main screen. Modal isolation
   already prevents conflicts (Textual stops non-priority app bindings at modals), but
   the help sheet should say the meaning is pager-local.
6. **Scale of `glossary` and `decisions` webs.** Per-strand history is fine. Web-level
   history should be the feed filtered to the web, not a merged document of dozens of
   strands.
7. **Adoption.** Measure usage before Phase 4. The feed and the Memory panel's "changed
   3d ago" line are the ambient hooks. If nobody opens history after Phase 3, stop.

---

## Appendix A — Reproduction commands used for the measurements

```bash
# Whole-memory index pass (0.29 s)
git log --raw -M --no-abbrev --format='C%x09%H%x09%P%x09%at%x09%an%x09%s' \
  -- sase/memory memory AGENTS.md
# Per-file history, with and without --follow
git log --format=%H -- AGENTS.md
git log --follow --format=%H -- sase/memory/tui.md
# Bloom-filter experiment (in a throwaway bare clone)
git commit-graph write --reachable --changed-paths
git log --format=%H -- sase/memory/tui.md          # 0.18–0.30 s → 0.03–0.04 s
# Blob batch
git cat-file --batch < blob_oids.txt                # 1,047 blobs, 9.2 MB, 0.08 s
# Reflow example: line diff says 2 lines, word diff says 1 word
git diff 63d2bdceac~1 63d2bdceac -- sase/memory/lint_and_test.md
git diff --word-diff=plain 63d2bdceac~1 63d2bdceac -- sase/memory/lint_and_test.md
# Home memory volume (chezmoi, opened via `sase repo open chezmoi`)
git rev-list --count HEAD -- home/sase/memory home/memory      # 125
git log --format=%s -- home/sase/memory home/memory | sort | uniq -c   # 88× "chore: initialize sase memory"
# Commit-type distribution of the 465 project commits
git log --format=%s -- sase/memory memory ':(glob)**/AGENTS.md' | sed -E 's/^([a-z]+)(\([^)]*\))?!?:.*/\1\2/' | sort | uniq -c
```

## Appendix B — Code touchpoints

- **Pager:**
  - `src/sase/pager/screen.py` (`BINDINGS`, compose)
  - `_screen_trail.py` and `trail.py` (add the version pin to `PagerTrailEntry`)
  - `_chrome.py` (subject chip, footer legend)
  - `_trail_chrome_band.py` (template for the time band)
  - `_gutter.py` (change marks)
  - `syntax.py` / `syntax_theme.py` (diff roles, palette)
  - `document.py` (`PagerSection.history`)
  - `resolve.py` (the `as_of` resolution)
- **Memory:**
  - `src/sase/memory/cli_*.py`, `main/parser_memory.py` (new `history` subcommand)
  - `_read_log_models.py` (v3 `blob_oid`)
  - `main/init_memory/root_rendering_notes.py::generated_memory_note_relative_paths`
    (the generated list)
  - `amd/constants.py` (shim aliases)
- **Memory panel:** `ace/tui/modals/memory_pane.py`, `memory_panel_rendering.py`
  (History meta row), `default_config.yml` `ace.keymaps.memory`.
- **sase-core:**
  - new `crates/sase_core/src/memory_history/`
  - reuse `git_query/parsers.rs` patterns and `commit_footer.rs`
  - `content_layout.rs` (pathspecs per scope)
