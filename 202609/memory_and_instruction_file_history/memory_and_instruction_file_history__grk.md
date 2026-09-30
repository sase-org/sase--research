# Memory and instruction-file history: git as the store, pager as the reader, a HEAD-keyed index as the navigator

**Researcher:** grk (independent swarm report)
**Date:** 2026-09-30
**Repo state:** workspace `sase_21` checkout of `sase`. Git timings, commit-trailer samples, Memory panel/pager/VCS code, and chezmoi home-memory history were measured in this checkout the same day.
**Question:** How should SASE track and navigate versions of memory files and agent instruction files? Should that live in the pager? Is the proposed plan a good idea, and what should change?

---

## Verdict

**Yes, build this. Use git as the only durable store. Do not treat the pager as a second VCS, and do not make generated `AGENTS.md` / provider shims first-class timelines.**

The instinct is right: these files already live in git, SASE already records *who* changed them (`SASE_AGENT`, `SASE_BEAD` trailers), the pager is already the document reader, and humans have no fast way to step a note through time. Chezmoi even has `revert(memory): undo accidental home init refresh` — people already need this.

The plan as stated over-indexes on two things that will make the feature noisy and slow:

1. **Treating generated instruction files as peers of canonical notes.** `CLAUDE.md` is a byte-for-byte copy of `AGENTS.md`. `sase/memory/README.md` changed 163 times in this repo; most of that is `sase memory init` rewriting a generated file. The timeline people want is the *source notes*, with instruction files as a derived view.
2. **A persistent custom history index that stores content.** `git log --follow` on one note is ~600 ms here; doing that per file is unusable. An index is required, but it should be a **cache of git log metadata**, rebuilt from one name-status walk, never a second copy of the blobs.

The product is a **file-scoped version navigator** whose viewing surface is the existing pager, whose discovery surface is the existing Memory panel, and whose backing store is git plus three synthetic lanes git does not cover (working tree, unpublished panel writes, local delete backups).

---

## 1. Critique of the plan

### 1.1 What is already good

- **Git as the version store.** Project memory, managed `AGENTS.md`, and provider shims are committed today by `sase memory init` (`src/sase/main/init_memory/project_deploy.py`) and by ordinary stitches. Home memory is committed in the chezmoi source repo. Commit messages already carry `SASE_AGENT`, `SASE_BEAD`, `SASE_PLAN`, `SASE_TYPE`. Re-implementing a content-addressed store would duplicate git and lose that provenance.
- **Pager as the viewing surface.** The pager already has Markdown and diff syntax, an editor-style gutter, line-addressed landings, a breadcrumb trail, live `r` refresh, `y`/`E` copy/edit, and revision-aware path resolution (`unavailable_revision` in `src/sase/pager/source_resolve.py`). The VCS provider already exposes `vcs_file_at_revision` (`git show <rev>:<path>`). This is the right reader.
- **Fast per-file stepping needs an index.** Confirmed. See §4.

### 1.2 Where the plan should change

| Plan as stated | Problem | Adjustment |
| --- | --- | --- |
| Track *all* instruction-file changes as first-class history | `CLAUDE.md` / `GEMINI.md` / `QWEN.md` / `OPENCODE.md` are copies of `AGENTS.md` (`src/sase/amd/constants.py`). `AGENTS.md` itself is generated from core notes + webs + reference list. Its git log is 259 commits here, many `chore: run sase init memory`. | Track them, but **collapse shims to `AGENTS.md`**, and present `AGENTS.md` history as “which source notes changed,” with the generated diff one key away. |
| “We might need to create an index” | `git log --follow -- <one file>` is **0.61 s** here. `git log --name-status` across all memory + instruction paths is **0.31 s**. Both are illegal on the TUI keystroke path (`tui_perf.md` rule 11: no subprocesses; rule 1: never block the event loop; Agents j/k budget is p95 < 16 ms). | Build a **HEAD-keyed metadata index** from one name-status walk. Do **not** store file bodies. Blobs stay in git (`git show` is ~0.00 s). |
| Pager is *the* main interface | The Memory panel is already the browse/edit surface (`gm`, tree, chips, unpublished badge, `Z` opens the pager, `o` opens `$EDITOR`). Putting discovery, publish, and version-stepping all in the pager fights that. | **Pager = reader of versions. Memory panel = finder + last-published metadata. CLI = `sase memory history`.** |
| Overload the pager trail for versions | The trail is a *spatial* back/forward stack of followed documents (`docs/pager.md`). Versions are a *temporal* axis of one file. Mixing them makes Backspace ambiguous. | A separate one-row **version strip**, using `[` / `]` (currently unbound in the pager). Trail stays for document follows. |
| Git history is complete | It is not. Unpublished panel writes, `--no-commit` publishes, local delete backups under `.sase/memory-backups/` (gitignored), and home files at `~/sase/memory/` (not a git repo — chezmoi source is) are invisible to `git log`. | Three synthetic lanes on top of git: **WIP**, **unpublished**, **backup**. |

### 1.3 Is this a good idea?

Yes, with those adjustments. The missing product is not “version control for memory” — memory is already version-controlled. The missing product is **a navigator that speaks SASE’s file model** (core / reference / web / strand / generated / shim / home / chezmoi) instead of dumping `git log -p sase/memory AGENTS.md CLAUDE.md GEMINI.md …` on the user.

I would not:

- invent a sidecar history database of note bodies
- auto-restore from the pager (memory writes have an authorization and publish path)
- add a new top-level TUI tab
- put this in Artifacts ▸ Files (that pane is workspace files, not the memory model)
- name it `file-history` (`sase file-history` already means recency of file *references* for editor completion)

---

## 2. Adjusted requirements

Call-outs from the original request:

1. **Durable store = git.** No second history log of file contents. The index caches *pointers* (commit, path-at-revision, dates, trailers, rename edges, diffstat), not blobs.
2. **Canonical notes are the default timeline.** Instruction files and generated notes are tracked and reachable, but they are derived.
3. **Pager is the version reader**, auto-enabled when the opened path is a memory note, web descriptor, strand, `AGENTS.md`, or a provider shim. It is not the only entry point.
4. **Two navigation axes stay separate.** Relational/spatial: Memory panel trail and pager follow-trail. Temporal: version strip on the current file.
5. **TUI keystroke paths never spawn git.** `[` / `]` steps a prefetched in-memory list. Index build and blob fetch run off-thread (`tui_perf` rules 1, 2, 8, 11).
6. **Cover the git-blind lanes:** working tree, unpublished panel writes, timestamped delete backups, chezmoi source history for Home.
7. **Restore is a write, not a view.** Viewing a historical blob must not mutate canonical memory. Restore goes through the existing mutation + publish path, or copies into `$EDITOR`.
8. **CLI name is `sase memory history`.** `sase memory log` stays the *read-audit* log. Do not collide.

---

## 3. What exists today (verified)

### 3.1 Files and how they are produced

| Kind | Path | Authored? | Git |
| --- | --- | --- | --- |
| Core / reference notes | `sase/memory/*.md` | Yes (except generated `sase.md`, `task_types.md`, `sase_artifacts.md`, `sase_beads.md`, `sase_sizes.md`) | Project repo |
| Memory webs / strands | `sase/memory/<web>.md`, `sase/memory/<web>/*.md` | Yes | Project repo |
| Generated README | `sase/memory/README.md` | No — `sase memory init` | Project repo, very noisy (163 commits here) |
| Instruction root | `AGENTS.md` | No — generated from core + webs + reference list | Project repo (259 commits here) |
| Provider shims | `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md` | No — byte-for-byte copies of `AGENTS.md` | Project repo (CLAUDE.md 166 commits) |
| Home notes | `~/sase/memory/` | Yes | **Not a git repo.** History is in chezmoi source (`~/.local/share/chezmoi/home/sase/memory`, 93 commits here) |
| Home instructions | `~/AGENTS.md` and shims | Generated | Chezmoi source |
| Delete backups | `.sase/memory-backups/` (project) or `~/.sase/memory-backups/<scope>/` (home) | Snapshot of the pre-delete bytes | Gitignored (`.sase/` is ignored) |

`sase memory init` already partitions dirty paths into foldable memory/source vs foreign (`src/sase/main/init_memory/git_state.py`) and refuses to auto-commit when unrelated files are dirty. Publish from the Memory panel (`I`) is this same command.

### 3.2 Provenance already in git

A typical memory-touching stitch looks like:

```
feat(tabs): inherit agent tab across launches with dispatch preflight (sase-1bc.5)

SASE_BEAD=[sase-1bc.5]
SASE_TYPE=stitch
SASE_AGENT=[bbugyi200.athena.sase-1bc.5]
```

`parse_commit_footer` (`src/sase/core/commit_footer_facade.py`) already understands these tags. `vcs_log` already classifies stitch vs manual vs auto. The navigator should surface **agent** and **bead**, not git author — git author is almost always the human host.

### 3.3 Surfaces that almost do this job

| Surface | What it does | Why it is not enough |
| --- | --- | --- |
| Memory panel (`gm`) | Tree of notes/webs/strands; last *mtime*; last *audited read*; unpublished badge; `Z` → pager; `o` → editor | No git “last published”, no version list |
| `sase memory log` | Read-audit events (who *read* a note) | Opposite axis: consumption, not authorship |
| `sase file-history` | Recency of file *references* for completion | Unrelated product; keep the name |
| `sase stitch list` / `vcs_log` | Cross-repo commit timeline | Commit-scoped, not file-scoped; no memory model |
| Commit view modal | Pretty diff of one stitch | Opened from a stitch, not from a note |
| Pager trail | Followed documents | Spatial, not temporal |
| Local delete backups | One snapshot per delete | Not a timeline, not indexed, not in git |
| Prompt History overlay | List + preview of historical text, `[`/`]` tab cycle | Closest *interaction* analog, different store |

The Memory panel property grid already has the right slot for a “Last published” row, next to “Last modified” and “Last audited read” (`src/sase/ace/tui/modals/memory_panel_rendering.py`).

### 3.4 Volume in this checkout (project repo)

| Query | Count |
| --- | --- |
| Commits touching `sase/memory/` | 194 |
| Commits touching `AGENTS.md` | 259 |
| Unique paths under `sase/memory/` ever touched | 125 |
| `chore: run sase init memory` commits | 44 |
| `sase/memory/README.md` | 163 (generated) |
| `sase/memory/glossary.md` | 61 (descriptor + roster) |
| Typical strand | 1–6 |
| `sase/memory/tui.md` | 2 |
| Renames | Present (`build_and_run` → `lint_and_test`) |

This is a small corpus. The index is required because of **TUI latency rules** and **rename-following cost**, not because the history is large.

### 3.5 Latency (this machine, this checkout)

| Operation | Wall time |
| --- | --- |
| `git log --follow -- <one note>` | **0.61 s** |
| `git log --name-status -- sase/memory AGENTS.md CLAUDE.md GEMINI.md QWEN.md OPENCODE.md` | **0.31 s** |
| `git show <sha>:<path>` | ~0.00 s |
| `git diff <sha>^ <sha> -- <path>` | ~0.00 s |

Per-file `--follow` across 125 paths would be on the order of a minute. One name-status walk plus in-process rename reconstruction is the whole trick.

Workspace clones are **not shallow** (`rev-parse --is-shallow-repository` → `false`), so numbered agent checkouts can build the same index.

---

## 4. Why an index, and what it must not be

### 4.1 What it is

A **HEAD-keyed metadata cache** of file-scoped history for the memory and instruction pathspecs of one git root.

```text
key: (git_root_identity, HEAD sha, pathspec fingerprint)
value: per-path list of FileVersion
```

`FileVersion` (conceptual):

| Field | Source |
| --- | --- |
| `kind` | `commit` / `wip` / `unpublished` / `backup` |
| `sha` | commit id, or `WORKTREE` / `UNPUBLISHED` / backup filename |
| `path_at_rev` | path in that commit (rename-aware) |
| `author_time` | `%aI` |
| `subject` | `%s` |
| `agent`, `bead`, `plan`, `type` | `parse_commit_footer` |
| `origin` | existing stitch/manual/auto classifier |
| `generated` | path is a generated note, `AGENTS.md`, or shim |
| `rename_from` | `R*` name-status |
| `stat` | short `+n -m` from numstat |
| `blob_sha` | optional, for prefetch identity |

Bodies are **not** stored. Fetch with the existing `vcs_file_at_revision` hook.

### 4.2 How to build it (once, off-thread)

One git invocation, not N `--follow`s:

```text
git log --name-status --pretty=format:<VCS_LOG_GIT_FORMAT> -- \
  sase/memory AGENTS.md AGENTS.md.tmpl \
  CLAUDE.md GEMINI.md QWEN.md OPENCODE.md \
  <subdir AGENTS.md + shims from agent-docs inventory>
```

Walk newest-first. Maintain a map `current_path → identity`. On `R100 old new`, retarget the identity. On `D`, close the identity. On `A`/`M`, append a version. This is git’s own follow algorithm, applied to the whole pathspec in one pass.

Reuse `VCS_LOG_GIT_FORMAT` and `parse_git_log` (`src/sase/core/vcs_log_facade.py`) so stitch classification stays consistent with `sase stitch list`.

Invalidation: HEAD change, or a dirty-token over the pathspec (index + worktree mtime, Memory panel unpublished set, backup dir mtime). Rebuild in a worker; serve the previous snapshot until the new one lands (`tui_perf` rule 5: cached data instantly, background reload).

### 4.3 Persistence

**In-process cache is mandatory. On-disk snapshot is optional and small.**

A 300 ms rebuild on Memory panel open is acceptable off-thread if the panel already has mtime-based cards. A disk snapshot under `~/.sase/memory-history/<repo-id>.json` (gitignored, like prompt-history shards) makes the “Last published” row appear on first paint across TUI restarts and across numbered workspaces that share a repo identity.

Do **not** put this in the project tree. Do **not** commit it. Do **not** make it a source of truth. If it is missing or stale, rebuild from git.

Sharing the snapshot across workspaces by `(remote url or git common dir, HEAD)` is a worthwhile optimization: every agent clone of `sase` has the same history at the same HEAD.

### 4.4 What I would not build

- sqlite of blobs
- git notes / extra refs per memory file
- a file watcher that appends to a parallel log on every write (duplicates git, races `sase memory init`, misses chezmoi)
- per-file `--follow` on demand from `[` / `]`

---

## 5. UX design

The interaction to copy is **git-timemachine** (stay in the document, `p`/`n` through revisions, minibuffer shows commit) plus **VS Code Timeline** (git commits and local saves in one file-scoped list, click to diff) plus SASE’s own **pager chrome** (subject, optional band, footer, `?` sheet).

Git Rewind’s horizontal commit strip is visually loud for a terminal pager. lazygit’s `ctrl+s` file filter is commit-first. SASE’s files are already found; the pager should stay document-first.

### 5.1 Entry points

1. **Memory panel `H`** (new, remappable under `ace.keymaps.memory`) — open the selected note/strand/web/instruction file in the pager with version chrome on. Property grid gains `Last published` (`3d ago · sase-1bc.5 · docs(memory): …`).
2. **Memory panel `Z`** — already opens the viewer. When the path is in the memory/instruction set, version chrome is on automatically. No new habit.
3. **`sase pager sase/memory/tui.md`** and `sase memory show` paging — same detection. Standalone pager gets the feature, not only the TUI.
4. **`sase memory history [selector]`** — CLI. No selector: cross-file changelog for the current scope. With a selector: that file’s timeline, then the pager (or `--plain` / `--json`).
5. **Following a historical `file:` / path from a changelog section** — lands on that file at that revision.

Do not add a top-level tab. Do not steal `sase memory log`.

### 5.2 Pager version chrome

When the current section is a tracked memory or instruction file, paint a **one-row version strip** between the subject line and the existing trail band (trail band remains 0–2 rows and only appears when a follow-trail exists). On screens ≤12 rows, fold version identity into the subject line, same compaction rule as the trail (`docs/pager.md`).

Subject line (current file, HEAD-equivalent):

```text
◆ sase/memory/dispatch.md   ·  md   ·  3/22  ·  3d ago
```

Version strip:

```text
[WIP]  ›  ● f379c641 docs(memory): publish dispatch note  ·  sase-1bc.5  ·  athena  ·  3d   [ ] next
```

Visual language, reused:

- `●` current (already used on the pager trail)
- `›` sequence (already used on the trail)
- amber `WIP` / `UNPUBLISHED` matching the Memory panel `⚠ UNPUBLISHED` badge
- dim `GENERATED` / `SHIM` chips matching the panel’s `⚙`
- conventional-commit subject kept intact; `chore: run sase init memory` rows render dim
- agent and bead painted as followable labels (pager already paints `sase-1bc.5`-shaped bead ids on `bead`/`agent` origins, and artifact refs everywhere)

`[` / `]` are unbound in `PagerScreen.BINDINGS` today. Use them:

| Key | Action |
| --- | --- |
| `[` | Older version of this file |
| `]` | Newer version |
| `g[` | Oldest |
| `g]` | Newest / WIP |
| `H` | Version picker overlay (list + one-line preview) |
| `d` | Cycle view: snapshot → diff vs previous → diff vs working tree |
| `y` twice | Already copies the section ref; in version mode include `sha:path` |
| `E` twice | Open *working tree* file in `$EDITOR` (never write a historical blob onto disk via `E`) |
| `r` | Rebuild index if HEAD/WIP moved; keep current version identity if it still exists |

Stepping keeps scroll position by **line content**, not line number, as git-timemachine does (`git-timemachine--find-new-current-line`). First implementation can clamp to the same line number; content-matching is the polish that makes stepping feel magical.

`Backspace` / `Ctrl+O` remain document-trail. Following a bead or agent from the version strip **pushes a trail entry**, so Backspace returns to the same version of the note.

### 5.3 View modes

**Default: snapshot.** The pager is a reader. “What did agents load on Tuesday?” is a snapshot question.

`d` flips to the **introducing diff** (the patch that created this version). Diff origin already exists (`PagerOrigin.DIFF`), so bare SHAs in the patch become commit links and the syntax layer already colors `diff_added` / `diff_deleted` / `diff_header` / `diff_hunk`.

Third mode: **diff vs working tree** — “what would I lose if I restored this?”

Blame is phase 2. The gutter already supports an emphasis rail; a blame mode can put a short agent/time token in the gutter without changing body offsets (the syntax-layer invariant: never mutate document characters). Do not lead with blame. The user asked to *navigate versions*, and blame is a different question (“who last touched this line”).

For **`AGENTS.md` and shims**, invert the default: show a **source-change card** for that commit (which notes/strands/webs actually changed) and keep the generated unified diff behind `d`. Shim files share `AGENTS.md`’s timeline; opening `CLAUDE.md` says `shim of AGENTS.md` and steps the same list.

### 5.4 Version picker (`H`)

A small overlay, not a new screen type. Shape matches Prompt History: filterable list on the left, metadata on the right, `j`/`k` to move, `Enter` to land, `/` to filter.

Row:

```text
WIP          —  unpublished panel write
f379c641  3d  docs(memory): publish dispatch note          stitch  sase-1bc.5
73eaa9fa  5d  chore: run sase init memory                  init    dim
```

Filter grammar, keep it tiny: substring on subject/path, plus optional `agent:`, `bead:`, `kind:commit|wip|backup`. Do not invent a new query language.

### 5.5 Cross-file changelog (CLI default, pager document)

`sase memory history` with no selector builds a pager document whose origin is `FILE` (or a dedicated origin only if we need new bare-token rules — we do not). Sections are commits, newest first, each listing the memory/instruction paths that commit touched, with generated/shim paths folded.

```text
## f379c641  3d ago  feat(tabs): inherit agent tab …  ·  sase-1bc.5
- sase/memory/dispatch.md  +7
```

Each path is a followable file link with a revision (`path@sha` or a pager-attached target). Following it opens that file’s snapshot at that commit, version chrome on, strip positioned on that version.

This is the answer to “what did memory do this week?” which per-file stepping cannot answer.

Cap the changelog (e.g. 100 commits, `Ctrl+J` to load older — Prompt History already taught this pagination). Do not dump 259 `AGENTS.md` regenerations.

### 5.6 Memory panel

Keep the panel as finder/editor. Add:

- **Last published** on the property grid (from the index; “uncommitted” when WIP differs from HEAD).
- A dim `H` hint in the footer when the index has ≥1 commit for the selected path.
- Rail: no extra glyph unless unpublished (already `⚠ UNPUBLISHED`) or WIP-vs-HEAD (could reuse that badge). Do not clutter the tree with SHAs.

`H` opens the pager; it does not turn the panel into a git client.

### 5.7 Restore (deliberately cautious)

git-timemachine’s FAQ is “just `write-file`,” which is how you destroy uncommitted work. SASE memory writes are authorized, digest-checked, and unpublished until `sase memory init`.

Restore actions, in order of safety:

1. **Copy** the historical body (`y`) — already natural.
2. **Open in `$EDITOR` as a scratch buffer** — do not overwrite the canonical path.
3. **Restore as unpublished draft** — write through `sase.memory.mutation` / web mutation, mark the scope unpublished, offer `I` publish. Generated notes still refuse (existing rule).

No `git checkout <sha> -- sase/memory/foo.md` from the pager. That bypasses conflict detection and can fold into an unrelated dirty tree.

Delete backups appear in the picker as `backup` rows. Restoring a backup is the same unpublished-draft write.

### 5.8 Beauty notes (concrete, not vibe)

- One new row of chrome, same type ramp as the trail band (`#D7D7FF` subject, dim SHA, accent for the current `●`).
- `chore: run sase init memory` and generated-only commits recede (dim), source-note commits hold color.
- WIP/unpublished use the same amber the panel already uses for `⚠ UNPUBLISHED`.
- Shim collapse means the user never sees four identical `CLAUDE.md`/`GEMINI.md`/… timelines.
- Version strip uses `cell_len` fitting like the trail (`_trail_chrome_band.py`); it must not wrap and must not shove the body.
- Snapshot bodies keep Markdown syntax; diffs keep diff syntax; neither path may rewrite characters (pager syntax-layer invariant).
- Prefetch neighbors so `[` / `]` never flash empty. If a blob is still in flight, keep the previous body and put a quiet footer status, same as live `r` refresh.

---

## 6. Scope resolution (project vs home vs chezmoi)

The Memory panel already rings every memory-bearing project plus Home. History must follow that ring:

| Scope | Git root for the index |
| --- | --- |
| Project | That project’s primary checkout (workspace clone is fine; not shallow) |
| Home with `use_chezmoi: true` | `chezmoi source-path` (measured: `~/.local/share/chezmoi`) with paths like `home/sase/memory/…`, `home/AGENTS.md` |
| Home without chezmoi | Only if `~/sase/memory` is itself a git repo; otherwise synthetic lanes only, with a one-line empty state: “Home memory is not in git” |

Deployed `~/sase/memory` is **not** a git root on this machine. Indexing it with `git -C ~` would be wrong even if `$HOME` were a repo. Always resolve through the same content-root logic `sase memory init` uses.

Subdirectory `AGENTS.md` files (tools/, demos/) are instruction files and should be in the pathspec via `sase memory agent-docs` inventory, but they are not the Memory panel’s notes. Opening them in the pager still gets version chrome; they do not appear as rail rows.

---

## 7. Agent-facing CLI

```text
sase memory history
sase memory history tui.md
sase memory history glossary:stitch
sase memory history AGENTS.md
sase memory history -f json --limit 20
```

`--plain` / no TTY writes the changelog or the per-file list. JSON is the index slice (metadata only, or include body when `--include-body` and a single version is selected).

Agents should use this when they need to know *why* a note looks the way it does. Do not inline history into `AGENTS.md`. Do not make `sase memory read` grow a `--at` flag in v1 — historical blobs are a human/TUI concern first; an agent that needs an old body can `sase memory history tui.md -f json` and then the pager is optional.

Naming: **history**, not log, not file-history, not versions-as-a-subcommand-soup.

---

## 8. Implementation sketch

Grounded in code that already exists:

| Piece | Where |
| --- | --- |
| Pathspec + generated/shim classification | `sase.amd.constants`, Memory panel `generated_paths`, `sase memory agent-docs` |
| Git log parse + footers | `VCS_LOG_GIT_FORMAT`, `parse_git_log`, `parse_commit_footer` |
| Blob at revision | `vcs_file_at_revision` |
| Dirty memory vs foreign | `init_memory/git_state.py` `classify()` |
| Backups | `memory/atomic_write.py` `backup_path_for` |
| Pager document | `path_section` + optional `refresh_document_fn`; new `VersionSession` hung on the screen like search/goto mixins |
| Off-thread + cache | Memory panel catalog already mtime-caches; copy that pattern (`memory_panel_catalog.py`) |
| Keymap | `MemoryPanelKeymaps` + pager `BINDINGS` (`[` `]` `H` `d`) |
| Diff paint | existing `PagerOrigin.DIFF` + syntax roles |
| Follow agent/bead | existing link scan; consider `agent` origin on the version strip’s metadata line only |

Suggested package: `src/sase/memory/history/` (index, pathspec, synthetic lanes) and `src/sase/pager/_screen_versions.py` (chrome + keys). Keep git I/O out of `pager/` render paths.

### Phasing

1. **Index + CLI `sase memory history`** (plain/JSON). Proves rename reconstruction, shim collapse, chezmoi root. No TUI yet.
2. **Pager version chrome** on `sase pager` / `Z`: snapshot stepping, `[` `]`, strip, prefetch. Detection by path.
3. **View mode `d`** (introducing diff, then vs working tree).
4. **Memory panel** Last published + `H`.
5. **Changelog document** as the no-selector CLI default, followable into (2).
6. **Synthetic lanes** (WIP, unpublished, backups) in the same list.
7. **Restore as unpublished draft** through mutation.
8. **Blame gutter** only if (2)–(5) are loved.

Phase 1–2 are the product. 3–6 make it SASE-shaped. 7–8 are teeth.

---

## 9. Risks

- **Chrome crowding.** Subject + version strip + trail band + goto line can eat a 12-row pane. Follow the trail’s compact rule; version identity folds into the subject first.
- **Generated-file noise.** If shim collapse and dim-init-commits slip, the feature trains people to ignore it. Default filters matter more than the strip’s beauty.
- **Stale index.** Serving a cache across a `sase memory init` commit must invalidate on HEAD. Show a quiet `stale` footer rather than a wrong WIP.
- **Workspace vs primary.** History is in the clone’s git object store. Unpushed local commits on the primary are invisible to an agent workspace until fetched — same as every other git feature; do not special-case it beyond using the checkout you are in.
- **Authorization.** A beautiful restore key will be pressed. Keep restore behind the mutation engine.
- **`--follow` temptation.** A “correctness” pass that shells `git log --follow` per file will freeze the TUI. The name-status walk is the correctness pass.
- **Home without chezmoi.** Empty state must be honest. Do not pretend mtime is git.

---

## 10. Recommended solution

Ship **memory history**: a HEAD-keyed, rename-aware metadata index over git (plus WIP / unpublished / backup lanes), a pager version mode that steps snapshots with `[` / `]`, and `sase memory history` as the CLI. Keep the Memory panel as the finder. Collapse provider shims to `AGENTS.md`. Treat generated instruction files as a derived view of canonical notes. Do not store bodies, do not spawn git on keystrokes, do not overload the pager trail, and do not one-key restore.

That is the smallest design that is intuitive (stay in the document, step in time), reliable (git is the store; the index is a cache; TUI rules are honored), and beautiful (one row of chrome in the language the pager already speaks, noise pushed into the background, agent and bead as first-class labels).
