# Memory and Agent-Instruction History in SASE

## Executive conclusion

This is a good idea, with one important reframing: SASE should not build a second
version-control system or turn the pager into a second memory catalog. Git should remain
the durable source of truth; the existing Memory panel should remain the place to find
and select memory; and the pager should gain a reusable **file-history mode** for moving
through, comparing, and reading revisions.

The first release should guarantee every **committed** version on the selected branch's
lineage, plus clearly labeled live `WORKTREE` and `INDEX` states. It should not claim to
preserve every editor save. That stronger promise requires a separate local-history
journal, retention policy, crash recovery, and cross-machine semantics. It is useful,
but it is a different feature and should be added only if recovery from intermediate
saves is an observed need.

I do **not** recommend a bespoke persistent index initially. Git already owns the object
store and path history, SASE's current scale is small enough, and Git's commit-graph
changed-path Bloom filters are the native acceleration mechanism if needed. SASE should
add only bounded in-memory caches keyed by repository state.

## Requirement adjustments I recommend

| Original intent | Recommended precise contract | Why |
| --- | --- | --- |
| “All changes are tracked” | All committed versions are durable; current index and worktree versions are visible but explicitly not durable. | Git cannot recover overwritten intermediate saves. Pretending otherwise would be unreliable. |
| “All history” | Default to the locally available, first-parent lineage of the selected `HEAD`, with rename following. Show `SHALLOW` or `LOCAL ONLY` when incomplete. | This produces a coherent sequence of states the branch actually exposed; all-ref history mixes abandoned branches and makes adjacent comparisons ambiguous. |
| Every instruction file has its own timeline | Group exact provider mirrors with their canonical `AGENTS.md`; route installed chezmoi output to its tracked source template. Preserve an exact-file view for custom or diverged files. | Five byte-identical histories are noise, not navigability. |
| Pager is the main interface | Memory panel is the catalog and launch point; pager owns revision reading, diffing, and comparison. | The Memory panel already owns scopes, hierarchy, relationships, and editing. Duplicating that in the pager would create two competing models. |
| Version history includes restore | Keep v1 read-only. | Restore is destructive, needs preview/confirmation and publication semantics, and should not complicate the trustworthy viewing foundation. |

These are scope clarifications, not reductions in long-term capability. A later local
checkpoint provider can appear in the same timeline if “every meaningful save” becomes
a real requirement.

## What SASE already has

The current architecture is unusually well prepared for this feature:

- The Memory panel already provides a cross-project/Home scope ring, a hierarchical
  note/web/strand rail, relational navigation, audit state, editing, and publish state
  (`docs/ace.md`, “Memory panel”). It should stay the canonical discovery surface.
- The pager already has immutable `PagerDocument`/`PagerSection` models, Markdown and
  diff syntax highlighting, line navigation, search, background link resolution,
  revision-aware document-owner provenance, refresh providers, and a bounded 32-entry
  back/forward trail (`src/sase/pager/`).
- `ArtifactRefDocumentOwner` already carries a `revision`, and owner-aware pager link
  resolution already distinguishes unavailable revisions. A historical document can
  therefore resolve links in the historical checkout context rather than silently
  jumping to today's file.
- The VCS provider already exposes `file_at_revision`, and `sase_core` already owns a
  provider-neutral commit-history wire/parser domain (`vcs_log`). File history is a
  natural extension, not a parallel subsystem.
- `sase memory init` normally stages, commits, rebases, and pushes memory sources and
  generated project files. `--no-commit` intentionally leaves a reviewable dirty state,
  which the proposed `WORKTREE`/`INDEX` rows can expose.
- `sase memory agent-docs list` already knows project, subdirectory, Home, and chezmoi
  sources and can distinguish canonical provider shims from custom or missing files.
  That inventory should decide which history is canonical.

There is one architectural constraint worth making explicit: file-history collection,
rename lineage, revision identity, and comparison semantics are shared backend behavior
and belong in `sase_core`; Textual state, keybindings, layout, and rendering belong in
the Python pager. The existing VCS design already follows that split: the host performs
Git I/O while Rust parses and normalizes provider-neutral records.

## Evidence from the current repository

I measured the current checkout on Git 2.43.0. It has 15,449 commits and 115 Markdown
files under `sase/memory/`. `AGENTS.md` has 259 path-touching commits,
`sase/memory/README.md` has 163, and the sampled
`sase/memory/sase_artifacts.md` note has 8.

Five warm runs, with output discarded, produced these medians:

| Query | Median |
| --- | ---: |
| `AGENTS.md` path history, exact path | 103 ms |
| `AGENTS.md` path history, rename-aware | 105 ms |
| Memory README path history, exact path | 132 ms |
| Memory README path history, rename-aware | 423 ms |
| Sample memory note path history, exact path | 141 ms |
| Sample memory note path history, rename-aware | 490 ms |
| Read current `AGENTS.md` blob | 3.4 ms |
| Diff the latest `AGENTS.md` revision | 2.9 ms |

This is not a general benchmark, but it answers the immediate design question. A
rename-aware scan can be perceptible, yet it is well within an asynchronous load with a
cached result. The repository has a 915 KiB commit graph, but its chunk table does not
contain changed-path Bloom chunks. Git documents that `commit-graph write
--changed-paths` provides significant gains for file and directory history queries.
That is a better next optimization than inventing a second authoritative index.

Git's behavior also argues for an explicit lineage mode. `--follow` follows a single
file past detected renames, while path-limited history otherwise applies history
simplification; merge traversal can omit or introduce branches depending on the chosen
mode. Git describes `--first-parent` as the overview of how a topic branch evolved.
That makes first-parent the best default for an ordered “what did this branch expose?”
timeline, with a future full-ancestry investigative mode if users actually need it.

## Product critique and alternatives

### 1. A custom database index now

This would make reads fast, but it creates the hardest parts of the feature before they
are needed: rebase invalidation, garbage-collected commits, multiple worktrees, shallow
clones, force-pushes, rename reconciliation, cache schema migration, and a second answer
to “what versions exist?”. A stale history view would be worse than a half-second load.

**Verdict:** do not build it. Use Git plus session caches. If measured p95 exceeds the
UX budget on real repositories, enable or recommend Git's changed-path commit graph.
Only consider a disposable SQLite projection after that, keyed by object IDs and always
rebuildable from Git.

### 2. Automatic artifact snapshots on every write

This can capture versions Git never sees, including pre-commit saves. It also introduces
retention and privacy questions, makes editor and external-tool writes difficult to
observe consistently, and creates cross-machine histories that do not naturally merge.
JetBrains explicitly treats Local History as a short-lived recovery tool rather than a
replacement for version control. That distinction is correct for SASE too.

**Verdict:** defer. If built later, call these `CHECKPOINT` rows, keep them local and
retention-bound, and never mix them up with durable `COMMIT` rows.

### 3. A history browser entirely inside the Memory panel

This reuses its rail, but overloads a catalog/editor with diff rendering, arbitrary
version comparison, historical links, and revision state. It would also fail to serve
agent instruction files and other tracked documents cleanly.

**Verdict:** the Memory panel should launch history, not render it.

### 4. Treating every generated provider file independently

This is technically faithful but visually hostile. `CLAUDE.md`, `GEMINI.md`,
`QWEN.md`, and `OPENCODE.md` are normally byte-for-byte projections of the adjacent
`AGENTS.md`; their histories add no information. Home output may also be generated from
a tracked chezmoi template.

**Verdict:** show an **instruction family**. Route exact mirrors to the canonical
tracked source and disclose that routing in the chrome. A diverged/custom file gets its
own exact history.

## Recommended UX

### Entry points

1. In the Memory panel, `H` opens history for the selected note, web descriptor, or
   strand. Add a configurable `history` keymap entry and update
   `src/sase/default_config.yml` with the same default.
2. In the pager, `H` enters history for the current file-backed section when the file
   is inside a VCS checkout. Thus `sase pager AGENTS.md`, then `H`, is the direct agent
   instruction workflow without adding a new CLI grammar in v1.
3. The agent-doc inventory should eventually expose its discovered paths as pager
   targets, but that is convenience, not a prerequisite.

Do not add a `--history` CLI flag until its redirected/plain-output contract is clear.
The current pager is safe to invoke in pipelines; an interactive-only flag that changes
meaning when no TTY exists would weaken that property.

### History mode

History adds a dedicated revision axis; it does **not** reuse the pager's link trail.
Back/forward remains “where did I follow links?”, while revision navigation means “which
state of this same file am I viewing?”. Mixing the two would make both unpredictable.

The default body is the selected revision's change against the immediately older state
in the first-parent file timeline. `d` toggles between **change** and **full document**.
`[` selects the older revision and `]` the newer revision. `H` opens a searchable
timeline overlay; `j`/`k` move, `Enter` selects, and `Esc` returns to the document.
`m` marks one revision and `Enter` on another compares those two versions, matching the
useful two-point comparison pattern in VS Code's file Timeline.

Suggested chrome:

```text
┌ ~/repo/sase/memory/tui.md
│ HISTORY  [3/18]  ◆ COMMIT  7eceb61ad9  vs previous  +12 −4
│ Bryan Bugyi · 2026-09-26 · docs(memory): record machine-link decision
├──────────────────────────────────────────────────────────────────────
│ @@ -42,7 +42,10 @@
│  unchanged context
│ -removed prose
│ +added prose, with changed words emphasized
```

Timeline overlay:

```text
HISTORY · tui.md                                      18 revisions
● WORKTREE   modified                          +3 −1
◇ INDEX      staged                            +8 −2
◆ 7eceb61a   Sep 26  Bryan   docs(memory): record machine-link decision
◆ 4e0b96e3   Sep 26  Bryan   docs(memory): apply reference corrections
R a13f82c0   Sep 11  Bryan   rename tui-performance.md → tui_perf.md
```

The visual language should reuse existing SASE accents: green additions, red removals,
cyan hunk headers, dim context, gold commit IDs, `⚙ GENERATED` for generated documents,
and explicit `R`, `A`, and `D` event badges. Markdown snapshots retain Markdown syntax
highlighting. Markdown diffs should add word-level emphasis inside changed lines so a
reflowed paragraph remains readable; the underlying output must remain an ordinary,
copyable unified diff.

Selection should feel instantaneous after the first load. Show the current document on
first paint, load history off the event loop, debounce preview loads, prefetch the two
adjacent blobs, and preserve the search query across revisions. Move to the first hunk
when opening a diff; preserve and clamp the logical line when stepping through full
documents.

### Generated documents should explain themselves

For a managed `AGENTS.md`, the header should say `GENERATED PROJECTION` and list memory
files changed in the same commit as “related source changes,” without claiming causal
proof. For an exact provider shim it should say, for example, `CLAUDE.md · exact mirror
of AGENTS.md` and display the canonical timeline. For chezmoi-installed output it should
name the tracked template it was rendered from.

This makes instruction history useful rather than merely complete: a user can see both
the generated effect and the likely source notes behind it.

## Backend design

### Provider-neutral records

Add a `file_history` domain to `sase_core` (or extend `vcs_log` if that remains cohesive)
with versioned wire records along these lines:

- `FileHistoryRequestWire`: repository-relative path, start revision, lineage mode,
  rename mode, and bounded result limit.
- `FileRevisionWire`: stable revision kind (`worktree`, `index`, `commit`), commit and
  blob IDs, path at that revision, change kind, old path for renames, author/committer
  metadata, subject, and parent IDs.
- `FileHistoryWire`: ordered revisions, completeness/truncation facts, selected branch
  and `HEAD`, shallow/local-only state, and diagnostics.
- `FileComparisonWire`: endpoints plus structured line and intraline hunks.

Rust should own parsing, validation, ordering, adjacent-version selection, rename-chain
normalization, and comparison structure. The Python Git provider should own bounded
subprocess execution and filesystem reads, consistent with the existing `vcs_log`
boundary. Extend the provider with `file_history`; reuse `file_at_revision` for lazy
content, and add a comparison operation only if the Rust diff domain cannot consume the
two loaded texts directly.

Use a pinned, NUL-safe Git output protocol and argv arrays with a `--` path separator.
Never interpolate a path or revision into a shell string. Pin rename detection rather
than inheriting user config, and surface it as heuristic (`RENAMED 63%`) because Git's
rename classification is similarity-based, not identity. Adjacent state comparisons
should use blob IDs, not whatever the current filesystem path contains.

### Query policy

- Default: locally available `HEAD`, first-parent, rename-aware, newest first.
- Prepend `WORKTREE` when content differs from the index; prepend `INDEX` when it differs
  from `HEAD`. Do not manufacture duplicate rows when contents are identical.
- Initial creation compares against empty content; deletion compares the last content
  against empty content.
- Preserve Git traversal order. Do not resort a non-linear result by wall-clock time.
- Carry both author and committer timestamps; display committer time as publication time
  and disclose author time when different.
- Never fetch, clone, write a commit graph, or prompt for credentials from a keypress.
  A shallow or missing-object result is an honest incomplete result with a retryable
  diagnostic.
- Give the worker a time/output budget and fail visibly rather than returning a silently
  incomplete list.

Historical `PagerSection` instances should carry an owner whose `revision` is the
selected commit. The existing owner-aware resolver can then keep file and artifact
links anchored to the historical source. If a linked target did not exist at that
revision, say so; do not quietly fall back to today's working tree.

### Caching and indexing

Use two bounded session LRU caches:

1. History metadata keyed by worktree Git directory, `HEAD` OID, index signature,
   worktree file signature, relative path, lineage mode, and rename mode.
2. Blob/comparison results keyed by blob IDs (or a content digest for worktree/index
   endpoints).

This is sufficient for the measured repository and cannot become an alternate source
of truth. A persistent database should require measured evidence such as history-open
p95 above one second after native Git acceleration, or paths with many thousands of
revisions.

Git's changed-path Bloom filters are the first scaling lever. They accelerate
`git log -- <path>` queries, although rename-following can still require more work.
SASE may diagnose their absence and suggest repository maintenance; it should not make
the pager mutate `.git` to create them during an interactive open.

## Reliability details that must not be optional

- **Trackedness is visible.** Show `TRACKED`, `UNTRACKED`, `IGNORED`, or `NO VCS`.
  `sase memory init --check` should eventually report managed memory/instruction files
  that cannot enter history, and publish-and-commit should fail before claiming success
  if an intended source or generated output was not included.
- **Dirty states are honest.** Worktree/index rows are useful, but their chrome must say
  `not durable until committed`.
- **Shallow and partial clones are honest.** Mark history incomplete; no automatic
  network access from the UI.
- **Renames and recreations are explicit.** Display old and new paths, similarity, and
  add/delete gaps. Never silently fuse a delete-and-recreate into one identity.
- **Generated aliases are reversible.** The user can inspect the exact shim history when
  a provider file ever diverged; canonical grouping must not hide a real difference.
- **Multi-worktree cache keys are worktree-specific.** A shared object store does not
  imply shared `HEAD`, index, or dirty state.
- **No restoration in v1.** A future restore action should preview a patch, write through
  the memory mutation/publish workflow, and never check out a historical commit.
- **Performance follows existing TUI rules.** No Git I/O, parsing, or stats in event
  handlers or render paths; workers must use generation checks, coalescing, and
  cancellation so fast navigation cannot apply stale results.

## Validation plan

Backend fixtures should cover add, modify, rename-with-edit, delete, delete/recreate,
merge, first-parent introduction, shallow history, missing blob, detached `HEAD`,
untracked/ignored files, staged-only and worktree-only changes, odd but legal paths,
and timestamps that disagree. Golden parity tests should pin the Python host protocol
against Rust parsing.

Pager tests should prove that revision navigation does not alter the link trail, search
survives version steps, stale worker results are dropped, historical links keep their
revision owner, exact shims route to canonical history, and narrow terminals preserve a
usable one-column layout. Visual snapshots should cover clean, dirty, renamed,
generated, shallow, empty-history, and error states.

Performance acceptance should include: immediate first paint from the already-loaded
document; no event-loop stalls; warm adjacent revision changes under 50 ms; and a
measured first history load budget (suggested p95 under one second for repositories of
the current size). Run the established pager/TUI tracing and screenshot workflows, not
ad hoc timing alone.

## Sources

- Git documents single-file rename following, path-limited history, first-parent
  traversal, and history simplification in the
  [git-log manual](https://git-scm.com/docs/git-log).
- Git documents native changed-path Bloom acceleration in the
  [commit-graph manual](https://git-scm.com/docs/git-commit-graph).
- Git's rename similarity, unified context, and word-diff behavior are specified in the
  [git-diff manual](https://git-scm.com/docs/git-diff).
- VS Code's official history guide validates a file-scoped timeline that includes live
  saves, committed revisions, and explicit two-version comparison:
  [View source control history](https://code.visualstudio.com/docs/sourcecontrol/history).
- JetBrains' Local History guide is useful precisely as a contrast: save-level history
  is local, retention-bound, and not a substitute for VCS:
  [Local History](https://www.jetbrains.com/help/idea/local-history.html).

## Recommended solution

Build a generic, read-only **Git-backed file-history mode in the SASE pager**, launched
with `H` from the existing Memory panel or any tracked file-backed pager section. Keep
the Memory panel as the catalog; use first-parent, rename-aware local Git history as the
durable timeline; prepend honest worktree/index states; collapse generated instruction
mirrors into canonical instruction families; and implement history normalization plus
structured comparison in `sase_core` with Python limited to VCS I/O and Textual
presentation. Ship with bounded asynchronous loading and session caches, not a custom
persistent index. Use Git changed-path commit graphs only as a measured scaling step,
and defer save-level local checkpoints and restoration until the reliable viewing
experience is proven.
