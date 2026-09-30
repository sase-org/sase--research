# Versioned Memory & Agent-Instruction History: Research Report

**Researcher:** mus · **Date:** 2026-09-30 · **Swarm:** 5-researcher (independent conclusions)

**Scope:** add tracked, versioned, quickly navigable change history for (a) all SASE
memory files — flat notes (`sase/memory/*.md`), web descriptors (`sase/memory/<web>.md`),
web strands (`sase/memory/<web>/<slug>.md`) — and (b) agent instruction files —
`AGENTS.md` files (project root, project subdirs, home) plus generated provider shims
(`CLAUDE.md`, `GEMINI.md`, …) — with the SASE pager as the main navigation interface.

All file-architecture claims below were verified by reading the checkout at
`/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_22`
(`src/sase/pager/*`, `src/sase/memory/*`, `sase memory agent-docs list` output).

---

## 1. What exists today (ground truth)

**Memory file layout.** Flat notes live under a canonical/legacy-compatible layout
(`src/sase/memory/paths.py`): canonical `sase/memory/`, legacy `memory/`. Discovery
(`notes.py:discover_memory_notes`) globs `*.md` at the top level only (minus `README.md`).
Memory webs are a descriptor flat note plus a strand directory
(`sase/memory/decisions/*.md`, `sase/memory/glossary/*.md` — confirmed on disk).
Strand bodies are never inlined into agent context; only the descriptor is.

**Memory mutation is already digest-guarded and atomic** (`mutation.py`, `atomic_write.py`):
create/update/delete go through one CLI-free engine, updates require an expected
SHA-256 digest (`MemoryConflictError` on mismatch), deletes back up first. There is
**no changelog, no revision record, no undo** — the backup from delete is the only
historical artifact, and it is unnamed/undiscoverable (no listing command).

**Read auditing exists, write auditing does not.** `sase memory read` appends a
`MemoryReadEvent` (who/when/why/bytes) viewable via `sase memory log` (rich dashboard +
JSON). There is no symmetric "who changed this note and when" surface. The user's
request is precisely that missing half.

**Agent instruction files.** `sase memory agent-docs list` shows the real inventory:
project `AGENTS.md` (managed), project-subdir `AGENTS.md`s (custom, e.g. `demos/…`,
`src/sase…`, `tools/AG…`), home `~/AGENTS.md` (managed), plus generated provider shims
(all shims per file), with chezmoi as a source for home files. Shims are **generated
artifacts** — versioning them directly versions a build output.

**The pager is a real, reusable platform.** `SasePager` (`pager/app.py`) hosts a
`PagerDocument` (title + origin + N `PagerSection`s, each with identity/title/kind/body
+ optional `subject_ref`, link anchors, owner provenance, known-kinds). `PagerScreen`
(`pager/screen.py`) already provides: vim-style navigation, `/` search (re-hosted
`VimSearchController`), `ctrl+n`/`ctrl+p` section jumps, `:`/`;` goto-line, a **bounded
back/forward trail** (`trail.py`, limit 32, full view-state snapshots), `r` refresh via
caller-supplied `refresh_document_fn`, `y`/`E` copy/edit arming, `?` help, and link
presses that resolve to full `DOCUMENT` targets (precedent: `pager/beads.py` resolves
`bead:` refs to live detail documents in-place). `document_from_paths`/`path_section`
(`pager/adapters.py`) already build file-backed sections with owner/checkout provenance
(`document_owner_from_path`) so presses resolve in the file's repo, not the viewer's
cwd. That owner mechanism matters directly for this feature (see §4).

**Git performance is a non-issue for per-file history.** `git log --oneline --follow --
sase/memory/gotchas.md` returns instantly (~15 rows) on this repo. Single-file history
is a cheap porcelain call; no index is needed to make *one file's* history fast.

---

## 2. Critique of the plan as stated

**The core idea is good.** Memory notes are durable agent context that agents mutate
frequently (`sase_memory_write` skill, `memory init`, digest-guarded edits). Today a bad
edit is silently load-bearing: core memory ships into *every* provider turn, so a
regression in one note degrades every subsequent agent run with no way to see what
changed or revert. Version navigation is a genuine gap, not a nice-to-have. Tying it to
the pager (the surface agents' humans already read in) is the right instinct.

**But three parts of the plan need adjustment:**

1. **"Use git history for free, plus an index for speed" — half-agree.** Git as the
   version store: yes, with caveats (§4). A maintained index: **no, not initially.**
   Per-file `git log --follow` is already millisecond-scale; an index (SQLite DB,
   background maintenance, invalidation, migration) is the most expensive part of the
   proposal and buys nothing until you need *cross-file* queries ("everything that
   changed this week"). Build the per-file feature on live git queries first; derive any
   later cross-file digest from a single `git log -- <memory paths>` call rather than a
   maintained DB. A standing index that can disagree with git is a reliability liability
   for a feature whose entire point is trustworthiness. (This is also consistent with the
   `corpus-before-mechanism` decision: don't build retrieval machinery ahead of a corpus
   that demonstrably needs it.)
2. **"Make the pager the main interface" — yes, but not the only interface.**
   The pager is modal, TTY-only, and invisible to agents (`SASE_AGENT` disables paging;
   `page_or_print` falls back to direct write). If history is *only* in the pager,
   agents — the primary mutators of memory — can never inspect it. The design must be:
   a history **data path** (CLI subcommand with `--json`/plain output, usable by agents
   and pipes) with the pager as the **human navigation layer** on top. Concretely:
   `sase memory history <selector>` prints a revision list non-interactively and opens
   the pager interactively; `sase memory show <selector>@<rev>` (or `--rev <sha>`)
   renders any single revision without a TTY.
3. **"All agent instruction file changes and all memory file changes" is too broad as
   stated.** Two scoping corrections:
   - **Generated shims must not be versioned directly.** `CLAUDE.md` etc. are build
     outputs of project `AGENTS.md` + memory state. Their git history is noise (bulk
     regeneration commits like `50d9c3bc21 chore(memory): trim generated agent
     instructions`). Version the *sources*; when showing a shim's history, resolve to
     the source note(s) + generator version and say so in the UI.
   - **Strand files, descriptors, flat notes, and AGENTS.md variants are all plain
     repo files** — one mechanism covers them uniformly. The supported set should be
     defined as "any tracked file under a memory root or registered as an agent
     document," resolved through the existing `memory_read_root` /
     `document_owner_from_path` machinery, rather than a hardcoded path list.

**One more risk to name: workspaces and checkouts.** SASE agents run in ephemeral
`sase_<N>` clones. `git log` in the viewer's cwd may show a truncated or divergent
history versus the primary checkout. The pager adapters already solved the analogous
problem for link resolution via owner provenance — history must do the same: resolve
the *file's owning repo*, run git there. Additionally, uncommitted working-tree edits
(the most common "what just changed?" case — an agent edited a note this turn) are
invisible to git history by definition; the design must surface the working tree as a
first-class pseudo-revision (§5).

---

## 3. Design space considered

| # | Version store | Navigation UI | Verdict |
|---|---|---|---|
| A | **Git history (live queries), no index** | Pager history document + `history`/`show@rev` CLI | **Recommend** (Phase 1) |
| B | Git + maintained SQLite index of revisions | Same as A, plus cross-file timeline | Defer to Phase 2; index only if cross-file digest proves slow |
| C | Dedicated append-only journal (own log of memory writes, content-addressed snapshots) | Pager reads journal | Reject: duplicates git, breaks "one source of truth," needs GC/migration; only revisit if repos go non-git |
| D | Per-file sidecar `.rev` copies or backup-chain | Pager lists sidecars | Reject: pollutes the tree, races with atomic-write engine, reinvents git badly |
| E | Static `sase memory log`-style timeline only, no pager work | CLI table | Reject as the *whole* solution (no content viewing/diff), but adopt as the non-TTY half of A |

The decisive arguments for A: zero new write-path machinery (mutation engine untouched —
important, since it is digest-guarded and skill-gated), zero background processes, works
on every existing checkout's existing history from day one, and per-file queries are
already fast (measured). Its weaknesses (uncommitted state, renames, shallow clones,
cross-file queries) are all handleable without an index (§4–§5).

---

## 4. Reliability design (the unglamorous part that decides success)

1. **Always resolve the owning repo, never assume cwd.** Reuse
   `document_owner_from_path` semantics: run `git log` in the repo that owns the file
   (project checkout, home/chezmoi source for `~/AGENTS.md`, linked sidecars). Ephemeral
   `sase_<N>` workspaces must not silently show truncated history — if the owning repo
   is shallow or the file's history is absent there, say so in the chrome
   ("history from <repo>, depth-limited") rather than showing a short list as if
   complete.
2. **Follow renames.** Canonical/legacy migration (`memory/` → `sase/memory/`, commit
   `5894a487f3`) means many notes' meaningful history predates their current path. All
   per-file queries must use `git log --follow`. (Verified: current history for
   `gotchas.md` spans the migration — `--follow` is load-bearing here.)
3. **Working tree is revision zero.** The document opens with a pseudo-section for the
   working-tree state (`git diff` / untracked = "no history yet, showing working tree").
   This covers the dominant support case: "an agent just edited this note, what
   changed?" — which committed history alone can never answer. Dirty-state must be
   visually unmistakable (badge, distinct border/style), never presented as a commit.
4. **Generated files redirect, not version.** Detect shims/generated notes via the same
   predicates the mutation engine uses (`raise_if_generated_memory_*`) and render a
   pointer section ("generated from X at <generator rev>; history lives with the
   source") with a press-through link to the source's history.
5. **Read-only git, fail-open rendering.** History runs `git log/show/diff` as
   read-only subprocesses in the owning repo; any failure (not a repo, no git, shallow,
   path untracked) degrades to the current file body with a one-line notice — a keypress
   must never crash the pager (precedent: `beads.py` catches all exceptions per
   keypress). No locks, no writes, no interference with the atomic-write engine.
6. **Cap and lazy-load.** Cap initial revision sections (e.g. 50 newest) with an
   explicit "older revisions available — press X / use `--limit`" affordance; full-text
   bodies load per revision via `git show` on demand rather than one giant snapshot.
   `git log` gives the cheap metadata list; bodies are fetched when navigated to.
7. **Audit interaction with the read log.** Viewing the *current* note through history
   should append the standard `MemoryReadEvent` (it is a read); viewing *historical*
   bodies should either be marked distinctly or excluded, lest history browsing pollute
   the read audit. Open question for implementation — recommend excluding historical
   bodies from the read log and noting the choice in `sase_artifacts`/`lint` docs.
8. **Rust boundary.** Per the `rust_core_backend_boundary` rule, shared behavior belongs
   in `sase-core` if other frontends need it. History navigation is presentation/UX over
   git porcelain: keep Phase 1 in Python (subprocess git, pager adapters). If a second
   frontend later needs identical history semantics, promote the *revision-list model*
   (not the pager) to the core then.

---

## 5. Recommended UX (pager-first, but not pager-only)

**Entry points (minimal CLI surface — one new subcommand, one new flag):**

- `sase memory history <selector> [--limit N] [--diff] [--json]` — revision list for
  one note / one AGENTS.md / one strand. Non-TTY or `--json`: print the list (sha,
  date, author, subject, plus a `working-tree-dirty` row). TTY without `--json`: open
  the pager history document.
- `sase memory show <selector> [--rev <sha|HEAD~n>] [--diff <rev-pair>]` — render any
  single revision (or diff) as plain output; in a TTY pager session it can also jump
  there. Reuses the existing `resolve_memory_view` path; revision resolution is a thin
   `git show <rev>:<path>` layer beneath it.

**Pager history document** (one `PagerDocument`, origin `FILE`):

- **Section 0 — timeline landing:** one-line rows per revision (age, short SHA, author,
  subject), each row an *attached target* (precedent: `AttachedTarget` + handler map in
  `SasePager`) so pressing it jumps to that revision's section. Dirty working tree is
  row 0 with a distinct badge.
- **Sections 1..N — revisions, newest first:** body = full note text at that revision;
  subject chrome = `glyph short-sha · local date · author · subject`. Each revision
  section carries attached targets for "previous/next revision" and "diff against
  neighbor," so `[`/`]`-style keys (§below) and link-presses both work.
- **Diff mode:** `d` toggles the current revision section between full text and a
  word-level diff against its predecessor (adjacent pair only — full-range diff pickers
  are Phase 2). Render diffs with the existing pager syntax-highlighting session so
  added/removed lines match the house theme; reuse `classify_source` with the note's
  real filename so Markdown highlighting keeps working inside diffs.
- **Keybindings** (extend `PagerScreen.BINDINGS`, document in `?` help + `_help.py`):
  `[` / `]` previous/next revision, `d` diff toggle, `T` jump to timeline, existing
  `backspace`/`tab` trail back/forward keep working across revision jumps because each
  jump pushes a `PagerTrailEntry` (full view-state snapshot — scroll/search preserved).
  `r` refresh re-runs the revision list (catches newly committed revisions).
- **Beauty details that make it feel designed, not bolted on:** sticky subject line
  shows `note-name · rev i/N · short-sha` (the pager already has a sticky subject
  widget); timeline rows use the same panel/table idiom as `memory log`'s Rich
  dashboard so the two surfaces rhyme; dirty-tree badge in a warning color, never in
  commit colors; empty states ("untracked file — no history yet", "generated shim —
  see source") as centered dim text, not error panels.

**Why this is the right shape:** every primitive already exists — sections for
revisions, trail for back/forward, attached-target handlers for timeline presses,
`refresh_document_fn` for live updates, owner provenance for cross-repo files, search
for within-revision finding. The work is one new document builder + one CLI subcommand
+ a few bindings, not a new application. And the non-pager half (`--json`,
`show --rev`) keeps agents and scripts first-class.

---

## 6. Recommended solution (phased)

**Phase 1 — per-file history, no index (the actual proposal):**

1. `sase memory history <selector>` backed by live `git log --follow` in the owning
   repo; `sase memory show --rev/--diff` for single-revision rendering; both with
   `--json` for agents.
2. Pager history document: timeline landing + capped revision sections + `d` diff
   toggle + `[`/`]` navigation + dirty-tree section 0 + generated-file redirect
   sections. All git access read-only and fail-open.
3. Explicit non-goals for Phase 1: no SQLite index, no cross-file timeline, no blame
   view, no arbitrary rev-range picker, no write-path changes (mutation engine, skills,
   and digest guards untouched).

**Phase 2 — only if Phase 1 proves the need:** cross-file "what changed recently"
digest derived on demand from one `git log -- <memory roots> <agent-doc paths>`
(no maintained index unless measured slow); blame/annotate view reusing revision
sections; rev-range diff selection.

**Success criteria:** (a) any human can go from "this note looks wrong" to viewing the
last-good version and its diff in under ~10 seconds via the pager; (b) any agent can do
the equivalent non-interactively via `--json`/`--rev`; (c) the feature adds zero
write-path machinery and zero background processes; (d) shallow checkouts, renames,
untracked files, and generated shims all degrade to honest, labeled states rather than
wrong or empty ones.

**Bottom line:** yes, build it — but build Phase 1 only: git-backed per-file history
with the pager as the human layer and a JSON/flag CLI half for agents, no persistent
index, generated files excluded by redirecting to sources, and the working tree treated
as revision zero. That is the smallest design that is still intuitive (timeline +
diff + keyboard flow users already know from the pager), reliable (read-only git,
owner-resolved repos, fail-open), and beautiful (existing chrome, theme, and dashboard
idioms reused rather than reinvented).
