# Memory and Agent-Instruction File History — Consolidated Design

_Lead researcher synthesis · 2026-09-30 · Inputs: five independent reports (`__cdx`,
`__cld`, `__grk`, `__mus`, `__gem`) plus new measurements and code checks. The new work
focused on where the reports disagreed or rested on weak evidence._

---

## 0. Bottom line

**Build it. Keep git as the only store. Put the effort into navigation and meaning, not
storage.** The request is pointed in the right direction, but the evidence changes its
shape in five ways:

1. **Tracking is mostly solved already.** Every project memory file and instruction file
   is committed: `sase/memory/` has 0 untracked files, and 435 first-parent commits touch
   memory or the root `AGENTS.md`. Home memory is committed in the chezmoi source repo.
   What is missing is a *navigator that understands SASE's file model*: notes,
   webs/strands, generated files, provider shims, home templates, renames, and
   deletions.
2. **An index is justified, but not for the reason the request assumes.** Reading one
   version is already fast: 6 ms per blob. The expensive work is building the *version
   list*. The right index is a **derived, tip-keyed, incremental metadata index** built
   from one git pass: lineage across renames, shim aliasing, classification, and
   provenance. It never stores content and is never a source of truth. **New finding:**
   the pathspec shape decides whether that pass takes 0.2 s or 9 s (§2).
3. **The real problem is signal-to-noise.** `README.md` has 163 versions, all generated.
   `AGENTS.md` has 259. 43 commits are `chore: run sase init…` boilerplate, and 127
   `feat` commits describe code rather than memory. Memory is wrapped prose, so line
   diffs exaggerate: a one-word change shows up as a 2-line `-/+` diff. Classification,
   diff-derived summaries, and a word-level prose diff are what make the history
   readable.
4. **The pager should be the single place you read history, but not the only way in.**
   It is the right surface for reading one document through time. It is the wrong
   surface for discovering what changed across memory this week. The ways in are the
   Memory panel (`H`), a cross-file **Memory Changes feed**, and a
   `sase memory history` CLI with `--json` output, so agents (who write most memory)
   can use it too.
5. **The most valuable question is missing from the request: "what did agent X actually
   see?"** Answering it needs a few bytes of capture per launch and per read. SASE does
   not record them today, and evidence that isn't captured now can never be recovered.
   **Start capturing now**, even though the UI comes later.

**Recommended solution (full detail in §9):** a Rust-core `file_history` +
`memory_history` domain over git, exposed as `sase memory history`. It is rendered by a
**modeless time axis** on eligible pager sections with these keys:

- `(` / `)` step to the older / newer version (SASE's existing version keys in ACE)
- `=` switches between the read and diff views
- `@` opens the timeline picker

The pager also gets a one-to-two-row time band with a change sparkline, a prose word
diff, scroll anchoring across versions, links that open at the same revision, and a
distinct "past" accent colour. The front doors are the Memory panel's `H` key and the
feed. Provider shims collapse into `AGENTS.md` whenever their bytes are identical. v1 is
read-only. There is no save-level journal and no SQLite.

---

## 1. Explicit requirement adjustments

These change what was asked. Each one is deliberate.

| # | As requested | Adjusted to | Why |
|---|---|---|---|
| R1 | "All … changes should be tracked" | **Every committed version is durable.** Uncommitted worktree/index states are shown but labelled *not durable*. An untracked or ignored managed memory/instruction file is a `sase memory init --check` / doctor error. **No save-level journal.** | Git cannot recover intermediate saves that were overwritten before a commit. Claiming otherwise would make the feature unreliable. A local "every save" journal is a different feature with its own retention, privacy, and cross-machine problems. JetBrains, for example, treats Local History as a short-lived recovery aid, not version control. *Reopen when* a real memory edit is lost that git could not recover. |
| R2 | History "for each supported file" | History for each **subject**: a logical document whose identity survives renames. Shims alias to their `AGENTS.md` **per version, by blob equality**, and only a diverged version is shown on its own. Deleted notes stay browsable. | Since 2026-02-21, all ~150 `CLAUDE.md` versions are byte-identical to `AGENTS.md`. The 16 that differ are all from 2026-02-15..21, when `CLAUDE.md` was hand-written. A rule based on file names would hide that real history; a rule based on blob equality keeps it. 162 memory paths have ever existed, versus 116 today, and 20 were deleted. |
| R3 | Home instruction files are versioned files | Home instruction history is the **template source** (`home/AGENTS.md.tmpl` etc. in chezmoi), shown with a `template` chip. Per-host rendered output comes later, if ever. | Verified: the five home templates are byte-identical `.tmpl` files with a per-hostname H1 switch. The deployed `~/AGENTS.md` bytes on each host are never committed anywhere. `~/sase/memory` is not a git repo. |
| R4 | "All memory files" | **SASE memory only.** Provider-native memories are out of scope: Claude Code's `~/.claude/projects/*/memory/`, and any provider directory under `~/.claude`, `~/.gemini`, or `~/.qwen` that isn't a SASE-rendered instruction file. | They are not in git, and SASE does not write them. Capturing them would need a watcher or journal (see R1). |
| R5 | Pager as the main interface | Pager is the **single rendering surface**. The front doors are the Memory panel `H`, the cross-file feed, and `sase memory history` (TTY opens the pager; otherwise plain text or `--json`). | One-document reading and cross-file discovery are different jobs. The pager is TTY-only and agents never see it. Agents are the main writers of memory, so they need a non-interactive path. |
| R6 | (not requested) | **"As seen by agent"**: record the workspace HEAD and instruction blob OIDs at launch, and a `blob_oid` on each memory read event. | This is the debugging question memory history exists to answer. Today `agent_meta.json` has `vcs_ref` and `sdd_base_sha` (the *SDD sidecar* HEAD) but not the project HEAD. `MemoryReadEvent` stores `byte_count` but no content hash. |
| R7 | (implied) navigate and act | **Read-only in v1.** "Restore" arrives later, as a guarded unpublished draft written through `memory/mutation.py`, and is disabled for generated files. | Memory writes are authorised, digest-checked, and published by `sase memory init`. Restoring a generated file makes no sense, because you restore its sources. |
| R8 | "Create an index or something" | The index is a **disposable cache derived from git**, keyed by the tip commit, and incremental. It never stores bodies. Persisting it to disk is triggered by measurement (§4.4). | Content always comes from git by blob OID. A cache that can't disagree with git can't make the feature unreliable. |
| R9 | (naming) | `sase memory history`. | `sase memory log` is already the read-audit viewer, and `sase file-history` already means file-reference recency for completion. |
| R10 | Special support for memory files | A **generic pager time axis** with a pluggable history provider. Memory and instruction files get the semantic provider first; a plain git-file provider is a cheap follow-on. | The same UX will be wanted for plans, skills, xprompts, and research docs, and this keeps memory special cases out of the pager core. |

---

## 2. What the evidence says

Measurements on git 2.43.0, workspace checkout at `d59fea8c0d` (15,453 commits, not
shallow). Timings are best of 3–5 warm runs.

### 2.1 Corpus shape

| Fact | Value |
|---|---|
| First-parent commits touching `sase/memory`, legacy `memory/`, and root `AGENTS.md` | **435**. The count is identical without `--first-parent`, so history for these paths is effectively linear. Only 5 merges touch them under `--full-history`. |
| Per path | `sase/memory` 194 · legacy `memory/` 130 · `AGENTS.md` 259 · `README.md` 163 (generated) · `glossary.md` 61 · `gotchas.md` 7 |
| Paths ever / tracked now / deleted | 162 / 116 / 20 · 0 untracked files under `sase/memory` |
| Commit types among the 435 | 179 `chore` (43 of them `chore: run sase init…`) · 127 `feat` · 77 `docs` · 33 `fix` · 13 `ref`/`refactor` |
| Home (chezmoi) | `home/sase/memory` 93 commits (125 including legacy `home/memory`). 88 of the 125 are `chore: initialize sase memory`. |
| Instruction files | Root, `tools/`, `src/sase/ace/`, and `demos/tapes/` each have an `AGENTS.md` plus 4 shims (20 files). HEAD blobs of `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are identical. |
| Prose reflow | Commit `63d2bdceac` shows as `2 insertions, 2 deletions` in a line diff. The word diff is `[-shells-]{+processes+}`. |
| Growth | 1,855 commits in September 2026 alone. |

### 2.2 Git cost (resolves the reports' conflicting numbers)

| Query | Time | Note |
|---|---:|---|
| `git log -- AGENTS.md` (exact path) | 103 ms | |
| `git log -- sase/memory/gotchas.md` | 151 ms | |
| `git log --follow -- gotchas.md` | 345 ms | |
| `git log --follow -- lint_and_test.md` (renamed note) | **733 ms** | `--follow` is the slow path, and it only follows one file. |
| Same, with changed-path Bloom filters | 839 ms | Bloom filters do **not** speed up `--follow`. |
| Single path with Bloom filters | **32–41 ms** | vs 103–151 ms without |
| One pass: memory dirs + root `AGENTS.md` (`--raw -M --first-parent`) | **188 ms** | |
| Same, plus the 3 subdirectory `AGENTS.md` | 319 ms | 381 ms with Bloom filters: multi-pathspec isn't accelerated on 2.43 |
| Same, plus all 16 shims listed explicitly | 456–555 ms | Shims add cost and no information. |
| **Same scope using `':(glob)**/AGENTS.md'`** | **7.9–9.6 s** | **Performance trap.** A glob pathspec defeats tree pruning. cld's index sketch uses this exact pathspec. |
| Incremental: `HEAD~100..HEAD`, same scope | 18 ms | |
| `merge-base --is-ancestor` | 9 ms | |
| `git show <rev>:AGENTS.md` / `git diff` | 6 / 7 ms | |

Conclusions:

- mus's "per-file `--follow` is instant" is **not supported**. It costs 0.35–0.73 s here,
  cannot be accelerated, and follows only one file.
- A **single `--raw -M` pass with an explicit, enumerated pathspec** gives lineage for
  every file at once, faster and more correctly. Enumerate instruction files from the
  `sase memory agent-docs` inventory, **never glob**, and exclude shims from the walk.
  Detect shim drift by comparing HEAD blob OIDs, which is effectively free.
- A full rebuild is O(total repo commits). At ~1.8k commits a month it will pass roughly
  1 s within a year. Incremental updates cost O(new commits), about 18 ms per 100.
- Upgrade headroom that needs no SASE code:
  - Git 2.51 extends Bloom filters to multiple pathspecs.
  - Git 2.52 extends them to wildcard pathspecs.
  - Writing `commit-graph --changed-paths` in the primary checkout cuts single-path
    queries about 4×.

  SASE should suggest this maintenance (doctor/upkeep). It should never write it from a
  keypress.

### 2.3 Code facts that constrain the design

- **Pager keys.** Letters and digits are the jump-label alphabet (`JUMP_HINT_CHARS`).
  Only `qjkgGyErnN` are reserved. Every new letter binding must be reserved and shrinks
  the label space. Punctuation keys `( ) [ ] { } = @` are unbound.
  - gem's `0` would collide with a digit label.
  - `d`, `H`, `B`, `T`, and `m` would each consume a label character.
- **ACE convention.**
  - `(`/`)` already mean prev/next *version*: `files_prev_version`/`files_next_version`
    on Artifacts Files, and card-block stepping.
  - `[`/`]` consistently mean *cycle view/tab/subtab* (Agents tabs, Artifacts subtabs,
    Statistics views).

  Four of the five reports picked `[`/`]` for versions. SASE's own vocabulary says
  `(`/`)`.
- **Memory panel.**
  - `H`, `(`, and `)` are unbound.
  - `h` is travel-back, `Z` opens the viewer, and **`d` deletes a note**. That is a
    reason not to make `d` mean "diff" one screen away.
  - "Unpublished" is session state (`_unpublished_scopes`) over content that lives in
    the worktree, so it is **not a separate version lane**. grk's separate
    "unpublished" lane collapses into the worktree lane.
- **Pager plumbing already exists:**
  - owner provenance with a `revision` (`pager/owner.py`) and the `unavailable_revision`
    resolution state
  - `refresh_document_fn`
  - DIFF syntax roles
  - `PagerTrailEntry` as full view-state snapshots; it has no version field yet
- **sase-core.** It already has `vcs_log/` (with `parse_git_log`, classify, and origin),
  `git_query/`, and `commit_footer.rs::parse_commit_footer`. There is **no diff crate**
  yet, so a word diff means adding `similar` or `imara-diff`. `rusqlite` is already a
  dependency, so SQLite would be cheap later if it is ever warranted.
- **CLI.**
  - `sase memory` has `agent-docs|init|list|log|read|show|web`, so `history` is free.
  - `sase pager` takes `REF|PATH` and falls back to plain output without a TTY, which
    keeps it safe in pipelines.
- **Decisions.**
  - `corpus-before-mechanism` is about retrieval, linking, and recall machinery
    *for agents*, learned from three deleted features. A version navigator over an
    existing 435-commit corpus doesn't violate it. gem and mus overstated it. Its lesson
    still applies: ship the smallest proven thing first and gate the rest on use.
  - `rust-core-required` forbids Python fallbacks. That rules out gem's "pure-Python
    fallback" and mus's "keep Phase 1 in Python".

---

## 3. Is this a good idea? Critique

**Yes. It is high-leverage and currently near-invisible.** Memory is the policy layer
loaded into every agent turn. A one-word edit to a core note, or promoting a note from
`reference` to `core`, changes the behaviour of every later agent. Agents are frequent
writers: cld counted 185 memory-touching commits carrying `SASE_AGENT`. Today, answering
"when did this rule appear, who added it, and why?" means running `git log -p --follow`
and reading commit subjects that mostly describe unrelated code. Answering "what did the
misbehaving agent see?" is impossible.

Where the original plan would go wrong without the adjustments above:

- **Treating every instruction file as a peer timeline** would multiply noise by 5×
  (shims) and bury authored changes under regenerations.
- **An index built to "make git faster"** misses the point. Git is fast for content;
  the index exists for lineage, classification, and provenance. A heavyweight
  persistent database would be the most expensive and least reliable part of the
  feature.
- **A pager-only design** can't answer "what changed across memory this week?" or
  "which other notes changed in the same commit?", and it is invisible to agents.
- **Line diffs of wrapped Markdown** would make the history look noisier than it is and
  erode trust.
- **An overloaded pager trail** would make Backspace walk through 30 versions.
  Link-following ("where did I go?") and version stepping ("when am I?") are separate
  axes.

**Would I take a different approach?** Same direction, with three changes:

- **Order.** Ship the index, the CLI, and the history *documents* rendered with today's
  multi-section pager before changing the pager's keymap and chrome.
- **Sequencing.** Capture the "as seen" evidence immediately.
- **Front door.** Make the feed the place to *review* changes: agents author much of
  the memory, and a human curator should see what changed since they last looked.

---

## 4. Data model and index

### 4.1 Subjects, versions, changesets

- **Subject.** A logical document with identity that survives renames:
  - `note:<scope>/<name>`
  - `web:<scope>/<web>`
  - `strand:<scope>/<web>/<slug>`
  - `instructions:<repo>/<dir>` (an `AGENTS.md` plus its shim aliases)
  - `asset:` (listed only, no diff)

  Each subject carries `generated: bool`. That flag comes from the **same source of
  truth that refuses direct edits** (`generated_memory_note_relative_paths` in
  `init_memory`), never from a second hard-coded list.
- **Version.** Fields:
  - a stable ordinal
  - commit, parents, committer time (the landing time), and author time if it differs
  - path at that revision, `blob_oid`, `prev_blob_oid`
  - change: `created | edited | moved | deleted`
  - class (§6.8)
  - summary: heading paths touched, `+w/−w` word counts, and frontmatter deltas such as
    `type: reference → core`
  - provenance: `SASE_AGENT`, `SASE_BEAD`, `SASE_TYPE`, and the subject line, via
    `parse_commit_footer`. SASE footers use `=`, so `git log --format=%(trailers)`
    can't see them.
  - cause, for instruction subjects: `notes[] | renderer | config | regen-only | other`,
    from paths co-changed in the same commit. This is presented as "related source
    changes", not proof of causation.
- **Pseudo-versions:**
  - `WORKTREE`, only when it differs from the index or HEAD
  - `INDEX`, only when staged content differs from HEAD
  - an `⇡N newer on <canonical branch>` count, loaded on request
- **Changeset.** One commit's versions across subjects, which is the unit of the feed.
  Generated consequences (`README.md`, roster lines, `AGENTS.md`) fold under their
  authored causes.

### 4.2 Build (one pass per repository scope)

```text
git -c core.quotepath=off -c diff.renames=true --no-optional-locks \
  log --first-parent --raw -z -M --no-abbrev --no-ext-diff --no-textconv \
      --format=<sha, parents, ct, at, author, subject, body> <tip> -- \
      sase/memory memory <each AGENTS.md from the agent-docs inventory>
```

- **Explicit pathspecs only; never glob** (§2.2). Shims stay out of the walk. Drift is
  one HEAD blob comparison per directory.
- **Lineage** comes from the `-M` rename pairs across the whole pathspec, not from
  `--follow`. Both sides of the `memory/` → `sase/memory/` migration are in scope, so
  that rename resolves.
- **First-parent, newest first**, in git traversal order, never re-sorted by wall-clock
  time. This is measured to be lossless for these paths today, and it gives an ordered
  answer to "what did this branch expose?".
- **Blobs** for classification come from one `git cat-file --batch` (cld: 1,047 blobs,
  9.2 MB, 80 ms).
- **Home** runs the same algorithm over the chezmoi source repo with pathspecs
  `home/sase/memory home/memory home/*.md.tmpl`, resolved through the same
  content-root logic `sase memory init` uses.
- **Other projects** in the Memory panel's scope ring use each scope's owning repo,
  resolved through owner provenance and never through cwd.

### 4.3 Update

```text
if key(repo_common_dir, pathspec_hash, schema+classifier version) mismatches → rebuild
elif cached tip == HEAD → done
elif is_ancestor(cached tip, HEAD) → fold(log cached_tip..HEAD) onto index   (~18 ms)
else → rebuild (rewrite, force-push, branch switch)                          (~0.2–0.5 s)
```

Invariants (test these):

- For every version, `blob_oid == rev-parse <commit>:<path>`.
- An incremental update produces exactly the same index as a full rebuild.
- Lineage matches `git log --follow` on a fixture corpus of renamed notes.

### 4.4 Persistence: in-process first, snapshot on a measured trigger

The reports split on this: cdx, gem, and mus said memory only; cld said a persisted JSON
snapshot now; grk said an optional one.

**Resolution:**

- **v1 keeps the index in process**, per ACE session and per CLI run, and updates it
  incrementally as HEAD moves.
- **Design the wire to be serializable from day one.** Then add a disposable snapshot at
  `~/.sase/cache/memory_history/<repo-key>.json` (atomic write under a lock, ~300 KB)
  when *either* of these triggers fires:
  - the cold build's p95 exceeds 500 ms on a real owning repo (expected within months
    at the current growth rate), or
  - the Memory panel needs history metadata at first paint across restarts
    (`tui_perf`: serve cached data instantly, reload in the background).
- **Never** store bodies, commit the cache, place it in the project tree, or treat it as
  authoritative. Any doubt means a rebuild.
- **SQLite** is reopened only at roughly 50k versions or when cross-project queries such
  as "all changes by agent X" become a real need.

This keeps cdx's reliability argument (nothing can go stale silently) and cld's scaling
argument (the incremental fold exists from day one). Only the serialization step waits
for evidence.

### 4.5 Content, diffs, summaries

- Content comes from a long-lived `git cat-file --batch` per repo per session, with an
  LRU of decoded blobs. Prefetch the ±2 neighbouring versions off-thread. For the
  worktree, read the file and hash it as git would.
- **Diffs are computed in-process in Rust:**
  - line operations for the change gutter, hunk jumps, and a line map for scroll
    anchoring
  - word operations tokenised over paragraphs for prose rendering

  This needs a new crate dependency. Parsing `git diff --word-diff=porcelain` is a
  fallback, but it provides no line map.
- **Section attribution:** map each hunk to its Markdown heading path
  (`§ Default Keymap Config`).
- **Frontmatter semantic diff:** YAML-aware. `type`, `parent`, `description`, `web`,
  and roster changes render as words ("⇧ promoted to core — now loaded by every
  agent").

---

## 5. Reliability rules (non-negotiable)

1. **Trackedness is visible.** Show `TRACKED`, `UNTRACKED`, `IGNORED`, `NO VCS`,
   `SHALLOW`, or `TEMPLATE`. Publish-and-commit must fail before claiming success if an
   intended source or generated output wasn't included.
2. **Dirty states are honest.** Worktree and index rows say `not durable until
   committed`, in the amber the Memory panel already uses for `⚠ UNPUBLISHED`.
3. **Git runs only off the event loop.**
   - No subprocess, parse, or stat in key handlers or render paths (`tui_perf`).
   - `(`/`)` step through a prefetched in-memory list.
   - Workers use generation counters so stale results are dropped during fast
     stepping.
4. **Background git must not fight agents.**
   - Use `--no-optional-locks` / `GIT_OPTIONAL_LOCKS=0`: `git status`-style refreshes
     otherwise take `index.lock` in checkouts where agents are committing.
   - Use argv arrays with `--`, NUL-separated output, pinned rename settings (don't
     inherit user config), `GIT_TERMINAL_PROMPT=0`, and time and output budgets.
   - Never fetch, clone, or write a commit-graph from a keypress.
5. **Incomplete history is labelled, never silently short.** Cover shallow clones,
   missing objects, the non-chezmoi Home case ("Home memory is not in git"), and
   truncated budgets.
6. **Renames are heuristic, so say so.** Show old and new paths plus similarity
   (`↦ renamed 63%`). Never merge a delete-and-recreate into one identity without
   showing the gap.
7. **Shim aliasing is reversible.** A shim whose blob differs from its `AGENTS.md` at
   some version gets a `⚠ diverged` badge and its own exact timeline, as in the
   Feb 15–21 era.
8. **Links from past versions resolve at that past revision.** They go through the
   owner `revision` and `unavailable_revision` machinery. If a target didn't exist at
   that revision, say so. Never fall back silently to today's file.
9. **Historical views are not audited reads.** Viewing old bodies must not add entries
   to `memory_reads.jsonl`, and `sase memory read` stays current-only.
10. **Fail open to the live document.** If history fails for any reason, the pager
    shows today's content with a one-line notice. A keypress never crashes the pager.

---

## 6. UX design

### 6.1 Principles

1. **Time is an axis of the document, not a mode.** If a section has history, the time
   verbs appear in the availability-driven footer; if not, they don't. There is no
   "enter history mode" step. (This overrides cdx's `H`-to-enter proposal.)
2. **You always know when you're in the past.** Past versions get a dedicated accent on
   the subject chip, band rule, and gutter. That accent must be **distinct from amber**,
   because amber already means uncommitted/unpublished in the Memory panel. cld, grk,
   and gem each assigned amber to a different meaning. Derive it from the WCAG-checked
   `syntax_theme` palette in both themes. `E` (edit) always edits *now*, and the footer
   says so.
3. **Keep your place.** Stepping versions keeps the same passage in view: anchor through
   the line map, then clamp. git-timemachine's content-anchored stepping is what makes
   this feel like magic.
4. **Small motions don't pollute the trail; jumps do** (vim jumplist). `(`/`)` steps
   push nothing. Picker jumps, feed links, and links followed from a past version push
   a trail entry, and every trail entry records its **version pin**, so Backspace
   restores the exact moment in time. This rejects mus's "every step pushes".
5. **Meaning over mechanics.** Show "`§ Default Keymap Config · +31w −4w · ⇧ promoted
   to core · athena.sase-1bc.12 · sase-1bc.12`", not `M sase/memory/gotchas.md`.

### 6.2 Keys (pager-local; all punctuation, so the jump-label alphabet is untouched)

| Key | Verb | Why this key |
|---|---|---|
| `(` / `)` | Older / newer version. `)` on the newest version returns to **now**. Hidden versions are skipped. | Matches ACE `files_prev/next_version`. |
| `=` | Switch between the **read** view and the **diff** view | "compare"; avoids `d` = delete in the Memory panel |
| `@` | Timeline picker | "at …" |
| `[` / `]` | Previous / next change (hunk) in the current view | vim `[c`/`]c` |
| `{` / `}` | First version / **back to now** | braces = the extremes |
| existing | `/` search (the query persists across versions), labels, `y` copy (includes `sha:path` in the past), `E` edit (edits now), `r` refresh (re-checks HEAD and updates the index), `Backspace`/`Tab` trail, `?` keys | |

The footer shows only `( ) · = · @ · }` by default; the rest are in `?`. If pager keys
become configurable, add a `pager:` section to `default_config.yml`. The Memory panel's
`history: "H"` **must** be added to `ace.keymaps.memory` in `default_config.yml` (per the
gotchas note).

### 6.3 Read view (default): past version with a change gutter

_Mockups in §6 are illustrative. Their SHAs, ages, counts, and agent names are
placeholders; only the `63d2bdceac` word-diff example is real._

```text
 ◆ sase/memory/gotchas.md   ⟲ PAST v8/9 · 8 days ago                              34% · md
 ⇧ promoted reference → core · § Default Keymap Config +31w −4w   athena.sase-1au.5 · sase-1au.5 · 1a2b3c4
 ▁▁▃▁▂▁▇▁▁▂▅▁▁▃▁▂▁▁▅▁▂▁▃▁▆▂▁▃▁▂▁▅▁▂ ▲ ────────────────────────────── now ◌ · ⇡2 on master
 ────────────────────────────────────────────────────────────────────────────────────────
   1│ ---
   2▌ type: core
   3│ parent: AGENTS.md
   4│ ---
   6│ **Default Keymap Config**
   7▌ When changing keymaps, leader mode keys, or any configuration values, don't forget to
   8▌ update the keymap configuration in the `src/sase/default_config.yml` file if necessary.
    ╴                                                                   (2 lines removed here)
 ────────────────────────────────────────────────────────────────────────────────────────
 ( ) version · = diff · @ timeline · } now · ? keys · q close
```

- **Subject chip.**
  - When viewing the past: `⟲ PAST v8/9 · 8 days ago`, in the past accent.
  - When live: `⟲ 9 versions · changed 3d ago`, or `◌ uncommitted` in amber when the
    worktree is dirty.
- **Band row 1:** class glyph, section path, word delta, frontmatter semantics, and
  provenance. Agent, bead, and commit are **jump-label targets** that open the agent
  chat, the bead, or the commit card.
- **Band row 2:** a **change-volume sparkline** over the whole timeline.
  - Each cell is one version, bucketed by time when the timeline is wider than the
    screen, and bar height is words changed.
  - `▲` marks the current version; hidden versions render as dim `·`.
  - Trailing markers are `now`, `◌` (dirty), and `⇡N` (newer upstream).

  At a glance it shows whether a note is stable or churning. This row is the feature's
  signature visual.
- **Gutter:** green `▌` for lines added in this version, a modified-accent `▌` for
  changed lines, and a red `╴` tick where text was removed.
- **Degradation:**
  - The band drops row 2 below about 30 rows of height.
  - Row 1 sheds commit, then bead, then section path as width shrinks.
  - At ≤12 rows it folds into the subject line, the same rule the trail band follows.
  - Nothing ever wraps or pushes the body.
- **Tombstone:** `✖ deleted 2026-07-13 by athena.… · last content shown`, on a muted red
  rule.

### 6.4 Diff view (`=`): inline prose word diff

```text
 ◆ sase/memory/lint_and_test.md   ⟲ PAST v18/18 · diff vs v17                    61% · md
 ◆ edited · § PNG Snapshot Tests · +1w −1w                              apollo.… · 63d2bdc
 ────────────────────────────────────────────────────────────────────────────────────────
     ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  121 unchanged lines  a  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
 125│ Local `just check-full` runs the update form after the other exhaustive gates and can
 126▌ modify goldens. SASE agent s̶h̶e̶l̶l̶s̶ processes export `CI=true`; that flag alone does not
     ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  38 unchanged lines  b  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄
```

- **Styling:**
  - Deleted words are struck through in dim red.
  - Inserted words are green with a subtle background tint.
  - Frontmatter changes render as a semantic block above the body.
  - The copyable form (`y`) is still an ordinary unified diff.
- **Reflow disappears** because the diff works on words. The `shells → processes`
  commit reads as one word, not two rewrapped lines.
- **Unchanged runs fold.** Each fold is a jump-label target that expands in place, so no
  new key is needed.
- **Which view opens first depends on how you arrived:**
  - from the feed, a changeset, or an `AGENTS.md` cause link → **diff**
  - from a note or the Memory panel → **read**

  The last choice is sticky for the session. (This resolves cdx's diff-first against
  the others' snapshot-first.)
- **No side-by-side at default widths.** Notes wrap at 88 columns, so two panes need
  about 190. It can be a wide-screen option later.

### 6.5 Timeline picker (`@`)

```text
╭─ gotchas.md · 9 versions · 2 hidden ────────────────────────────── filter ▏ ─╮
│ now  ◌  worktree         not committed                     +2w               │
│ v9   ◆  Sep 27   3d      § Default Keymap Config           +31w −4w  sase-1bc.12 │
│ v8   ⇧  Sep 22   8d      promoted reference → core                   sase-1au.5  │
│ v7   ◆  Sep 12   18d     § Default Keymap Config           +6w −6w               │
│ v1   ✚  Apr 12   5mo     created as memory/gotchas.md      412w                  │
│ ·· 2 hidden (↦ moved memory/ → sase/memory/ 100%, ≈ reflow) · a show          │
│ ⏎ open · = compare with the version you're viewing · a all · esc close        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

- Typing filters by subject, section, agent, bead, or word.
- **`=` on a row compares that row against the version currently open.** This gives
  VS Code Timeline–style two-point comparison without a new mark key. (It replaces
  cdx's `m`.)
- Jumping from the picker pushes a trail entry.

### 6.6 Memory Changes feed (`sase memory history` with no selector)

This is the cross-file front door, and it is a normal pager document, so search,
labels, the trail, and `ctrl+n`/`ctrl+p` between day sections work unchanged.

```text
 ▤ Memory changes · sase + home · last 14 days             23 changesets · 5 regen-only hidden
 ━━ Mon Sep 28 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ● 11:03  feat(goals): complete G1 acceptance…                 athena.sase-1bu.7 · sase-1bu.7
          ✚ decisions:goal-ledger        new decision · 180w
          ✚ decisions:goals-host-binds   new decision · 150w
          ◆ glossary:artifact            +20w −3w
            ⟳ AGENTS.md §3.1 (+2 entries) · README.md · glossary roster
 ━━ Sun Sep 27 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   14:19  feat(tabs): inherit agent tab across launches…     athena.sase-1bc.5 · sase-1bc.5
          ◆ dispatch.md                  § Remote dispatch  +44w −10w
  ⋯ 5 regenerated-only changesets hidden · label to show
```

- Every subject row is a label target that opens `subject@version` in the diff view.
- `⟳` lines fold generated consequences under their cause. Home changesets interleave,
  tagged `⌂`.
- **New (my addition): a per-scope "reviewed through" watermark.**
  - Changesets newer than your last review get a `●` dot.
  - Acknowledging advances the watermark: one commit OID per scope, stored locally.
  - This turns the feed into the oversight tool the request is really about: humans
    reviewing what agents did to shared memory.
  - It is optional and belongs in phase 3.

### 6.7 Instruction files (`AGENTS.md` family)

- **Opening `CLAUDE.md` opens the `AGENTS.md` subject.** The chip reads
  `CLAUDE.md ≡ AGENTS.md` for identical versions and `⚠ diverged` otherwise.
- **The cause band replaces the provenance row.** It shows one of:
  - `⟳ rendered · sources changed in this commit: gotchas.md · dispatch.md`, where each
    name is a label that opens that note at the same commit in the diff view
  - `⚙ renderer change · src/sase/amd/…`
  - `⚙ config change · sase.yml`

  cld measured that 60 of 207 root `AGENTS.md` versions came from something other than
  a note edit.
- **Home templates** show `TEMPLATE · per-host H1` and the template source history.
- **Later: a section source map.** Each rendered core section becomes a label back to
  its source note at that commit. This needs the renderer to emit provenance.

### 6.8 One visual vocabulary everywhere (CLI, feed, band, picker, Memory panel)

| Glyph | Meaning | Default in per-file timeline |
|---|---|---|
| `✚` | created | shown |
| `◆` | authored edit | shown |
| `⇧` / `⇩` | promoted / demoted `type` | shown, highlighted (changes what every agent loads) |
| `▣` | frontmatter-only | shown dim |
| `⟳` | regenerated (generated subject) | shown for generated subjects; folded in the feed |
| `⚙` | renderer- or config-driven (instruction subject) | shown with its cause |
| `≈` | reflow / whitespace-only | hidden (dim dot in the sparkline) |
| `↦` | pure move / rename | hidden (the path change is shown in the band) |
| `✖` | deleted | shown (tombstone) |
| `◌` | worktree / index | shown when dirty (amber) |
| `⇡N` | N newer versions on the canonical branch | marker only |

Relative times carry an absolute time on the band's second row. Conventional-commit
subjects appear as secondary context, dimmed for `chore: run sase init…`.

### 6.9 Entry points

1. **Memory panel `H`** opens the selected note, web, or strand in the pager, positioned
   on now. The card gets a `History  9 versions · changed 3d ago · athena.sase-1bc.12`
   row (loaded after paint). `Z` keeps working, and its viewer gets the time axis
   automatically.
2. **The pager, anywhere.** Any section that resolves to a memory or instruction file
   gets the axis: `sase pager sase/memory/tui.md`, ACE file views, and bead/plan links.
3. **`sase memory history [SELECTOR…]`.**
   - It uses the `read`/`show` selector grammar plus instruction paths.
   - On a TTY it opens the pager. Otherwise, or with `-p/--plain`, it prints.
     `-j/--json` emits the index slice, so agents can investigate "why is this rule
     here?".
   - Other options: `-a/--all`, `-A/--at REV` (`v7`, `~2`, SHA, or date), `-d/--diff`,
     `-D/--deleted`, `-s/--since`, `-S/--scope`.
   - Follow the `cli_rules` memory note when adding them.
   - **Don't** add `--rev` to `sase pager` or `--at` to `sase memory read` in v1, so
     that the audited read semantics stay unchanged.
4. **Agents tab (later):** a "Memory as seen" link opens `AGENTS.md` at the launch
   snapshot. The band says `as seen by athena.sase-1bc.12 · 2 versions behind now`.
   Read-audit rows in `sase memory log` link to the exact version read.

---

## 7. Where the reports disagreed, and the resolution

| Question | Positions | Resolution (evidence) |
|---|---|---|
| Need an index? | cdx, gem, mus: no persistent index. cld: persisted incremental JSON. grk: HEAD-keyed metadata index, optionally on disk. | A **derived, tip-keyed, incremental metadata index** built in one pass. In-process in v1; serialized on a measured trigger (§4.4). Never stores content. |
| Per-file `--follow` cost | mus: "instant". gem: 245 ms (without `--follow`). cdx: 423–490 ms. cld: 330 ms. grk: 610 ms. | **345–733 ms**, and Bloom filters don't help. It's the slow path; the one-pass lineage fold replaces it. |
| Whole-scope pass cost | cld: 0.29 s. grk: 0.31 s. gem: 0.25 s. | **0.19–0.55 s with explicit paths; 7.9–9.6 s with a `**` glob.** Never glob. |
| Version keys | cdx, grk, mus, gem: `[`/`]`. cld: `(`/`)`. | **`(`/`)`.** It's ACE's version convention, and punctuation leaves the jump-label alphabet alone. `[`/`]` become hunk jumps. |
| Letter keys (`d`, `D`, `H`, `B`, `T`, `m`, `0`, `~`) | various | Avoid them in the pager: they eat label characters, `0` *is* a label, and `d` means delete in the Memory panel. Use `=` and `@`. `H` belongs to the Memory panel only. |
| History as a mode or an axis | cdx: `H` enters a mode. cld: modeless. | **Modeless axis.** Verbs appear only where history exists. |
| Default view | cdx: diff. The others: snapshot. | Read view with a change gutter by default. Diff when arriving from a changeset. Sticky per session. |
| Trail interaction | mus: every step pushes. cdx: separate axis. cld: jumplist rule. | **Jumplist rule** plus version-pinned trail entries. |
| Rust or Python | mus: Python first. gem: Python fallback. The others: Rust. | **Rust** (`rust-core-required`). Python owns git IO and presentation only. |
| Lineage mode | cdx: first-parent. cld: topo order over all history. | **First-parent.** It's lossless here (435 = 435) and deterministic. |
| Pseudo-versions | cdx: WORKTREE + INDEX. cld: working copy + unlanded + upstream. grk: WIP + unpublished + backup. | WORKTREE and INDEX (only when they differ), plus an `⇡N` upstream count. "Unpublished" is the worktree (verified). Delete backups arrive as picker rows in phase 3. |
| Blame | gem: early `B`. The others: later. | Later, as an **age lens**: a gutter tinted by line age, labelled back to the introducing version. |
| Home path | gem: `~/.config/sase/memory`. | **Wrong.** It's `~/sase/memory` (deployed, not a git repo), with history in chezmoi `home/sase/memory`. |
| Memory panel history tab | gem: add a tab. | No new tab or screen. `H` opens the pager, and the card shows a History row. |
| Sibling files in a commit | gem: "also changed" links. cld: the feed. | Both. The band's cause and provenance row lists co-changed memory subjects as labels, opened at the same commit. |
| "As seen by agent" | cld only | **Adopt**, and start capturing in phase 0 (§8). |
| Shim collapse rule | Everyone: collapse by name. | Collapse **by blob equality per version**, because the pre-generator `CLAUDE.md` history is real content. |

---

## 8. Architecture and phased plan

### 8.1 Boundary

- **sase-core (Rust):**
  - a generic **`file_history`** domain: raw-log parser (extending the `vcs_log`
    parsers), first-parent lineage fold with rename chains, incremental merge,
    comparison as line and word operations with a line map
  - a **`memory_history`** semantic layer: subjects, shim aliasing by blob, the
    classifier, cause attribution, section and frontmatter summaries, changeset
    folding, and footer provenance (reusing `commit_footer.rs`)
  - versioned wire types and PyO3 bindings. Bump `sase-core-revision.txt` as usual.
- **Python (sase):**
  - git IO: bounded, non-interactive, `--no-optional-locks`, argv plus `--`, one
    `cat-file --batch` per repo, and resolving the owning repo through owner provenance
    and the content-root logic
  - pseudo-versions
  - the CLI
  - `src/sase/pager/_screen_history.py` with an optional `SectionHistoryProvider` on
    `PagerSection`
  - a version pin on `PagerTrailEntry`
  - time-band chrome modelled on `_trail_chrome_band.py`
  - the Memory panel `H` binding and History row
- **Presentation-only:** Textual state, keys, layout, and colours stay in Python.

### 8.2 Phases

**Phase 0: capture evidence now (tiny; land independently).**

- At launch, add `workspace_head` (the project repo HEAD) to `agent_meta.json`. The
  precedent is `capture_sdd_base_sha` in `run_agent_runner_setup_workspace.py`.
- At launch, also add `instruction_snapshot: {path: blob_oid}` for every instruction
  file the provider loads. For bytes that exist in no repo, such as per-host home
  renders, store a deduplicated, content-addressed copy under
  `~/.sase/instruction_snapshots/<oid>`. It changes rarely, so the cost is negligible.
- `MemoryReadEvent` schema v3 adds `blob_oid`.
- **Why first:** the UI can wait, but evidence that isn't captured can't be
  reconstructed.

**Phase 1: index, CLI, and history *documents* (no pager-core changes).**

- The Rust domains above, with a fixture corpus drawn from real history:
  - the `build_and_run → lint_and_test` rename (R063)
  - the legacy `memory/ → sase/memory/` migration
  - the reflow-only `63d2bdceac`
  - `type` promotions and deletions
  - the Feb 15–21 shim divergence
- `sase memory history` in plain and JSON forms, plus a pager form built from
  **existing** multi-section documents:
  - section 1 is a timeline whose rows are label targets
  - each later section is one version's word diff, using the existing DIFF roles
  - `ctrl+n`/`ctrl+p` steps between versions
- The feed document, when no selector is given.
- **Acceptance:**
  - the invariants in §4.3 hold
  - cold build ≤ 0.5 s off-thread; incremental ≤ 20 ms
  - `history CLAUDE.md` resolves to the `AGENTS.md` subject, and the Feb-era versions
    show as diverged
  - chezmoi scope works
  - no glob pathspecs

**Phase 2: the pager time axis and the Memory panel.**

- `PagerHistoryMixin`:
  - the keys `( ) = @ [ ] { }`
  - version-pinned trail entries
  - scroll anchoring through the line map
  - ±2 neighbour prefetch
  - generation-guarded, pump-free workers
- The time band, sparkline, change gutter, tombstones, and past accent.
- The word-diff view with label-expandable folds and the frontmatter block.
- **Links from past versions resolve at that revision.** This is required for
  correctness, not polish.
- Memory panel `H` and the History row, plus the `default_config.yml` keymap entry.
- Visual goldens at 60×30 and 120×40, light and dark: read view, diff view, picker,
  feed, tombstone, dirty state, the `AGENTS.md` cause band, and a narrow terminal.
- If a landed phase would otherwise expose a partial feature, follow the `sase_flags`
  memory note for a temporary flag.

**Phase 3: meaning and oversight.**

- The picker's compare-with-current.
- The `AGENTS.md` cause band.
- The feed's changeset folding polish and the review watermark.
- Delete-backup rows.
- The "Memory as seen" UI from the Agents tab and `memory log`.
- A plain git-file history provider for plans, skills, and xprompts.

**Phase 4: conditional, only if phases 2–3 get used.**

- Age lens.
- Restore-as-unpublished-draft through the mutation engine (never for generated
  subjects).
- The persisted index snapshot, if its trigger hasn't already fired.
- Doctor or upkeep advice for `commit-graph --changed-paths` and Git ≥ 2.51.
- Rendered per-host home instructions.
- Side-by-side diff at 190 or more columns.
- `path@rev` refs.

**Adoption gate:** measure use after phase 2. If nobody opens history, stop there.

### 8.3 Performance budgets

- First paint of a live document is unchanged. History loads after paint, and the band
  shows `indexing…` meanwhile.
- A warm version step takes ≤ 30 ms from prefetched blob to diff to repaint.
- The event loop never stalls. Verify with the established pager/TUI tracing and
  screenshot workflows, not ad hoc timing.

---

## 9. Recommended solution

Ship **memory history** as a git-backed, read-only **time axis** for SASE memory and
instruction files:

- **Store:** git only. Content always comes from git by blob OID. There is no snapshot
  store, save journal, SQLite, dedicated memory repo, or orphan branch.
- **Index:** a Rust-core, tip-keyed, incremental **metadata** index (lineage,
  classification, provenance, cause) built by one first-parent `--raw -M` pass over an
  **explicitly enumerated** pathspec per owning repo (project repo, chezmoi source, and
  each Memory-panel scope). It lives in process in v1 and is serialized to a disposable
  snapshot once a measured trigger fires.
- **Subjects, not files:**
  - Shims collapse into `AGENTS.md` by per-version blob equality.
  - Renames and deletions keep a single identity.
  - Generated notes are classified from `init_memory`'s own list.
  - Home instructions are shown as templates.
- **Pager (the single reading surface):**
  - a modeless axis where `(`/`)` step versions (ACE's version keys), `=` switches the
    read and diff views, `@` opens the picker, `[`/`]` jump between changes, and
    `{`/`}` go to the first version or back to now
  - a one-to-two-row time band with provenance labels and a change sparkline
  - a change gutter and a paragraph-aware prose word diff
  - scroll anchoring, links that open at the same revision, and version-pinned trail
    entries
  - a past accent that is distinct from the uncommitted amber
- **Front doors:**
  - Memory panel `H` and its History row
  - `sase memory history` (feed with no selector; `--json` for agents)
  - later, a review watermark and "Memory as seen by agent"
- **Start capturing now:** workspace HEAD and instruction blob OIDs at launch, and blob
  OIDs on memory reads.
- **Guardrails:**
  - no git on the keystroke path
  - `--no-optional-locks`
  - honest labels for shallow, untracked, template, and dirty states
  - read-only in v1, with restore added later as a guarded draft

This is the smallest design that is **intuitive** (stay in the document and step through
time with SASE's existing version keys), **reliable** (git is the store, the index is a
cache that can't disagree with it, and the TUI performance rules hold), and
**beautiful** (one visual vocabulary, noise pushed into the background, agents and beads
as first-class links, and a sparkline that shows a note's whole life at a glance).

### Open decisions for the user

1. **Timeline ref.** Recommended: the owning checkout's HEAD plus an `⇡N` upstream
   marker. The alternative is always showing `origin/master`.
2. **When to persist the index snapshot.** Recommended: on the measured trigger. The
   alternative is shipping it in v1.
3. **The review watermark.** Should the feed track "reviewed through" per scope?
   (Recommended, phase 3.)
4. **Phase 0 storage.** Is a content-addressed copy of per-host home instruction
   renders acceptable?

---

## Sources

- The five swarm reports (`memory_and_instruction_file_history__{cdx,cld,grk,mus,gem}.md`),
  in this directory.
- Local verification in the sase workspace, the sase-core linked checkout, and the
  chezmoi linked checkout (commands and figures in §2).
- [git-log manual](https://git-scm.com/docs/git-log): `--follow`, `--first-parent`,
  history simplification.
- [git-commit-graph manual](https://git-scm.com/docs/git-commit-graph): changed-path
  Bloom filters.
- [git-diff manual](https://git-scm.com/docs/git-diff): rename similarity and word diff.
- [Highlights from Git 2.51](https://github.blog/open-source/git/highlights-from-git-2-51/):
  Bloom filters for multiple pathspecs. Git 2.52's release notes extend them to
  wildcard pathspecs.
- [VS Code: source control history / Timeline](https://code.visualstudio.com/docs/sourcecontrol/history):
  a file-scoped timeline and two-point compare.
- [JetBrains Local History](https://www.jetbrains.com/help/idea/local-history.html):
  save-level history is local, retention-bound, and not version control.
- Prior art for interaction: Emacs git-timemachine (step through revisions inside the
  buffer and keep the line).
